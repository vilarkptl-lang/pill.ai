"""
LangGraph multi-agent orchestration for pill.ai.

Graph topology:
  user_input
      │
  supervisor  (DeepSeek V4 Pro — routes + reasons)
      ├─► vision_agent     (Gemini Flash — analyzes screenshots)
      ├─► browser_agent    (Playwright — web tasks)
      ├─► desktop_agent    (pyautogui — GUI control)
      ├─► shell_agent      (terminal/sudo) ──► [human_approval?]
      └─► coder_agent      (generates code / dashboards)
              │
          END (returns output + optional new_skill)

Human-in-the-loop (HITL):
  shell_agent and desktop_agent flag dangerous proposed actions in state.
  The router sends those to human_approval before executing.
  safe_mode="off" bypasses HITL entirely.
"""
from __future__ import annotations

import re
from typing import Annotated, Any, Optional, TypedDict

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

from interpreter.llm import LLMRouter
from interpreter.tools.browser import BrowserTool
from interpreter.tools.desktop import DesktopTool
from interpreter.tools.shell import ShellTool, _DANGEROUS_PATTERNS


# ── State schema ─────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list[dict], add_messages] if HAS_LANGGRAPH else list[dict]
    task: str
    safe_mode: str
    license_tier: str
    route: Optional[str]            # which agent to call next
    agent_output: str               # last agent's text output
    output: str                     # final answer to user
    new_skill: Optional[str]        # description to append to skills.md
    iteration: int
    pending_command: Optional[str]  # HITL: command waiting for approval
    pending_agent: Optional[str]    # HITL: which agent resumes after approval


# ── HITL helpers ──────────────────────────────────────────────────────────────

def _is_dangerous(text: str) -> bool:
    return any(re.search(p, text) for p in _DANGEROUS_PATTERNS)


def _hitl_confirm(action: str, safe_mode: str) -> bool:
    """Print the proposed action and ask the user to approve. Returns True = proceed."""
    if safe_mode == "off":
        return True
    print(f"\n[pill.ai] ⚠  Dangerous action proposed:\n  {action}")
    try:
        answer = input("  Allow? [y/N] ").strip().lower()
    except EOFError:
        answer = "n"
    approved = answer in ("y", "yes")
    if not approved:
        print("  Blocked.\n")
    return approved


# ── Node implementations ──────────────────────────────────────────────────────

def _supervisor_node(state: AgentState, router: LLMRouter) -> AgentState:
    """
    DeepSeek V4 Pro decides which specialist agent to call.
    Returns route = one of: vision | browser | desktop | shell | coder | final
    """
    system = (
        "You are the supervisor of a multi-agent computer-use system.\n"
        "Given the user task and conversation, decide which specialist to call:\n"
        "  vision   — analyze screenshot of screen/browser\n"
        "  browser  — web browsing, form filling, web scraping\n"
        "  desktop  — GUI clicking, drag-drop, keyboard shortcuts\n"
        "  shell    — terminal commands, file ops, scripts\n"
        "  coder    — write/run Python code, build dashboards\n"
        "  final    — task complete, return answer\n"
        "\nRespond with ONLY the route name. Nothing else."
    )
    messages = [
        {"role": "system", "content": system},
        *state["messages"],
        {"role": "user", "content": f"Task: {state['task']}\nPrevious output: {state.get('agent_output', '')}"},
    ]
    route = router.complete(messages).strip().lower()
    valid = {"vision", "browser", "desktop", "shell", "coder", "final"}
    if route not in valid:
        route = "final"

    new_state = dict(state)
    new_state["route"] = route
    new_state["iteration"] = state.get("iteration", 0) + 1
    return new_state


def _human_approval_node(state: AgentState, router: LLMRouter) -> AgentState:
    """
    HITL gate: show the pending command/action to the user and ask for approval.
    If approved, resume the originating agent. If denied, go to final.
    """
    pending = state.get("pending_command", "")
    approved = _hitl_confirm(pending, state["safe_mode"])

    new_state = dict(state)
    if approved:
        new_state["route"] = state.get("pending_agent", "final")
        new_state["messages"] = state["messages"] + [
            {"role": "system", "content": f"[HITL] User approved: {pending}"}
        ]
    else:
        new_state["route"] = "final"
        new_state["agent_output"] = f"Action blocked by user: {pending}"
        new_state["messages"] = state["messages"] + [
            {"role": "system", "content": f"[HITL] User blocked: {pending}"}
        ]
    new_state["pending_command"] = None
    new_state["pending_agent"] = None
    return new_state


def _vision_node(state: AgentState, router: LLMRouter) -> AgentState:
    """Gemini Flash analyzes a desktop screenshot."""
    desktop = DesktopTool(safe_mode=state["safe_mode"])
    try:
        description = desktop.screenshot_and_describe(router)
    except Exception as e:
        description = f"[vision error: {e}]"

    messages = [
        {"role": "system", "content": "Analyze the screen and determine the next step."},
        *state["messages"],
        {"role": "user", "content": f"Screen shows: {description}\nTask: {state['task']}"},
    ]
    answer = router.complete(messages, model="gemini/gemini-2.0-flash", has_images=False)
    new_state = dict(state)
    new_state["agent_output"] = answer
    new_state["messages"] = state["messages"] + [{"role": "assistant", "content": f"[vision] {answer}"}]
    return new_state


def _browser_node(state: AgentState, router: LLMRouter) -> AgentState:
    """Browser agent: asks the LLM for Playwright steps, executes them."""
    system = (
        "You control a Playwright browser. Generate a JSON action list.\n"
        "Actions: [{\"action\": \"goto\", \"url\": \"...\"}, "
        "{\"action\": \"click\", \"selector\": \"...\"}, "
        "{\"action\": \"fill\", \"selector\": \"...\", \"text\": \"...\"}, "
        "{\"action\": \"extract_text\"}, {\"action\": \"screenshot\"}]\n"
        "Return ONLY valid JSON array."
    )
    messages = [
        {"role": "system", "content": system},
        *state["messages"],
        {"role": "user", "content": state["task"]},
    ]
    raw = router.complete(messages)
    result = _execute_browser_actions(raw, state["safe_mode"])
    new_state = dict(state)
    new_state["agent_output"] = result
    new_state["messages"] = state["messages"] + [{"role": "assistant", "content": f"[browser] {result}"}]
    return new_state


def _desktop_node(state: AgentState, router: LLMRouter) -> AgentState:
    """Desktop agent: clicks, types, hotkeys. Flags mass-click patterns for HITL."""
    system = (
        "You control a desktop via pyautogui. Generate JSON action list.\n"
        "Actions: [{\"action\": \"click\", \"x\": 100, \"y\": 200}, "
        "{\"action\": \"type\", \"text\": \"...\"}, "
        "{\"action\": \"hotkey\", \"keys\": [\"ctrl\",\"c\"]}, "
        "{\"action\": \"screenshot\"}]\n"
        "Return ONLY valid JSON array."
    )
    messages = [
        {"role": "system", "content": system},
        *state["messages"],
        {"role": "user", "content": state["task"]},
    ]
    raw = router.complete(messages)

    # Flag mass-click (>10 clicks) for HITL
    import json, re as _re
    match = _re.search(r"\[.*\]", raw, _re.DOTALL)
    if match and state["safe_mode"] != "off":
        try:
            actions = json.loads(match.group())
            click_count = sum(1 for a in actions if a.get("action") == "click")
            if click_count > 10:
                new_state = dict(state)
                new_state["pending_command"] = f"{click_count} automated clicks on desktop"
                new_state["pending_agent"] = "desktop_execute"
                new_state["route"] = "human_approval"
                new_state["_desktop_pending_raw"] = raw
                return new_state
        except (json.JSONDecodeError, TypeError):
            pass

    result = _execute_desktop_actions(raw, state["safe_mode"])
    new_state = dict(state)
    new_state["agent_output"] = result
    new_state["messages"] = state["messages"] + [{"role": "assistant", "content": f"[desktop] {result}"}]
    return new_state


def _shell_node(state: AgentState, router: LLMRouter) -> AgentState:
    """
    Shell agent: generates terminal command. Routes to human_approval if dangerous.
    On resume from HITL approval, executes the approved command directly.
    """
    # Resumed from human_approval — state has the approved command in messages
    if state.get("pending_command") is None and state.get("_approved_command"):
        command = state["_approved_command"]
    else:
        system = (
            "Generate a shell command to accomplish the task. "
            "Return ONLY the shell command, nothing else."
        )
        messages = [
            {"role": "system", "content": system},
            *state["messages"],
            {"role": "user", "content": state["task"]},
        ]
        command = router.complete(messages).strip()

    # HITL check: dangerous command needs user approval
    if _is_dangerous(command) and state["safe_mode"] != "off":
        new_state = dict(state)
        new_state["pending_command"] = command
        new_state["pending_agent"] = "shell"
        new_state["route"] = "human_approval"
        new_state["_approved_command"] = command
        return new_state

    shell = ShellTool(safe_mode="off")  # HITL already handled above
    result = shell.run(command)
    output = result["stdout"] or result["stderr"] or f"exit code {result['returncode']}"
    new_state = dict(state)
    new_state["agent_output"] = output
    new_state["_approved_command"] = None
    new_state["messages"] = state["messages"] + [
        {"role": "assistant", "content": f"[shell] $ {command}\n{output}"}
    ]
    return new_state


def _coder_node(state: AgentState, router: LLMRouter) -> AgentState:
    """Coder agent: writes Python code, optionally runs it. Always updates skills.md."""
    system = (
        "Write clean Python 3.12+ code to accomplish the task.\n"
        "If the task mentions 'dashboard', use Streamlit.\n"
        "Return the code inside a ```python block."
    )
    messages = [
        {"role": "system", "content": system},
        *state["messages"],
        {"role": "user", "content": state["task"]},
    ]
    code_response = router.complete(messages)
    code = _extract_code(code_response)

    skill_desc = None
    if code:
        shell = ShellTool(safe_mode=state["safe_mode"])
        run_result = shell.run_python(code)
        output = run_result["stdout"] or run_result["stderr"]
        # Always generate a skill description for skills.md
        skill_desc = f"Task: {state['task'][:200]}\n\n```python\n{code[:1000]}\n```"
    else:
        output = code_response

    new_state = dict(state)
    new_state["agent_output"] = output
    new_state["new_skill"] = skill_desc
    new_state["messages"] = state["messages"] + [{"role": "assistant", "content": f"[coder]\n{code_response}"}]
    return new_state


def _final_node(state: AgentState, router: LLMRouter) -> AgentState:
    """Synthesize all agent outputs into a final user-facing answer."""
    system = "Summarize what was accomplished. Be concise and helpful."
    messages = [
        {"role": "system", "content": system},
        *state["messages"],
        {"role": "user", "content": f"Original task: {state['task']}"},
    ]
    final = router.complete(messages)
    new_state = dict(state)
    new_state["output"] = final
    return new_state


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph(router: LLMRouter):
    if not HAS_LANGGRAPH:
        raise ImportError("langgraph not installed: pip install langgraph")

    g = StateGraph(AgentState)

    g.add_node("supervisor",      lambda s: _supervisor_node(s, router))
    g.add_node("human_approval",  lambda s: _human_approval_node(s, router))
    g.add_node("vision",          lambda s: _vision_node(s, router))
    g.add_node("browser",         lambda s: _browser_node(s, router))
    g.add_node("desktop",         lambda s: _desktop_node(s, router))
    g.add_node("shell",           lambda s: _shell_node(s, router))
    g.add_node("coder",           lambda s: _coder_node(s, router))
    g.add_node("final",           lambda s: _final_node(s, router))

    g.set_entry_point("supervisor")

    def _route_from_supervisor(state: AgentState) -> str:
        if state.get("iteration", 0) >= 8:
            return "final"
        return state.get("route", "final")

    g.add_conditional_edges("supervisor", _route_from_supervisor, {
        "vision":          "vision",
        "browser":         "browser",
        "desktop":         "desktop",
        "shell":           "shell",
        "coder":           "coder",
        "final":           "final",
        "human_approval":  "human_approval",
    })

    def _route_from_hitl(state: AgentState) -> str:
        return state.get("route", "final")

    # Shell/desktop can request HITL mid-execution
    def _route_from_shell(state: AgentState) -> str:
        if state.get("pending_command"):
            return "human_approval"
        return "supervisor"

    def _route_from_desktop(state: AgentState) -> str:
        if state.get("pending_command"):
            return "human_approval"
        return "supervisor"

    g.add_conditional_edges("shell",   _route_from_shell,   {"human_approval": "human_approval", "supervisor": "supervisor"})
    g.add_conditional_edges("desktop", _route_from_desktop, {"human_approval": "human_approval", "supervisor": "supervisor"})
    g.add_conditional_edges("human_approval", _route_from_hitl, {
        "shell":    "shell",
        "desktop":  "desktop",
        "final":    "final",
    })

    for node in ("vision", "browser", "coder"):
        g.add_edge(node, "supervisor")

    g.add_edge("final", END)

    return g.compile()


# ── Action executors ──────────────────────────────────────────────────────────

def _execute_browser_actions(raw_json: str, safe_mode: str) -> str:
    import json, re
    match = re.search(r"\[.*\]", raw_json, re.DOTALL)
    if not match:
        return f"[could not parse actions: {raw_json[:200]}]"
    try:
        actions = json.loads(match.group())
    except json.JSONDecodeError:
        return "[invalid JSON from browser agent]"

    browser = BrowserTool(safe_mode=safe_mode)
    results = []
    with browser:
        for act in actions:
            try:
                a = act.get("action")
                if a == "goto":
                    browser.goto(act["url"])
                    results.append(f"Navigated to {act['url']}")
                elif a == "click":
                    browser.click(act["selector"])
                    results.append(f"Clicked {act['selector']}")
                elif a == "fill":
                    browser.fill(act["selector"], act["text"])
                    results.append(f"Filled {act['selector']}")
                elif a == "extract_text":
                    text = browser.text()[:2000]
                    results.append(f"Page text: {text}")
                elif a == "screenshot":
                    results.append("[screenshot taken]")
            except Exception as e:
                results.append(f"[error on {act}: {e}]")
    return "\n".join(results)


def _execute_desktop_actions(raw_json: str, safe_mode: str) -> str:
    import json, re
    match = re.search(r"\[.*\]", raw_json, re.DOTALL)
    if not match:
        return f"[could not parse actions: {raw_json[:200]}]"
    try:
        actions = json.loads(match.group())
    except json.JSONDecodeError:
        return "[invalid JSON from desktop agent]"

    desktop = DesktopTool(safe_mode=safe_mode)
    results = []
    for act in actions:
        try:
            a = act.get("action")
            if a == "click":
                desktop.click(act["x"], act["y"], act.get("button", "left"))
                results.append(f"Clicked ({act['x']},{act['y']})")
            elif a == "type":
                desktop.type(act["text"])
                results.append(f"Typed: {act['text'][:50]}")
            elif a == "hotkey":
                desktop.hotkey(*act["keys"])
                results.append(f"Hotkey: {act['keys']}")
            elif a == "screenshot":
                results.append("[screenshot taken]")
        except Exception as e:
            results.append(f"[error on {act}: {e}]")
    return "\n".join(results)


def _extract_code(text: str) -> str:
    import re
    match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else ""
