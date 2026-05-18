"""
pill.ai — Interpreter core.

API-compatible fork of OpenInterpreter/open-interpreter (MIT).
Every public param from OI's __init__ is present here so existing OI code
works without modification.  Internals are different:

  OI                           pill.ai
  ─────────────────────────    ─────────────────────────────────────────
  Single ReAct loop            LangGraph multi-agent StateGraph
  Custom LLM classes           LiteLLM (multi-provider)
  GPT-4o default               DeepSeek V4 Pro (95% cheaper)
  Inline input() for HITL      Explicit human_approval node in graph
  No skills memory             ~/.pill.ai/skills.md + semantic dedup
  MIT license                  BSL-1.1 → Apache 2.0 (2028-01-01)

Params added by pill.ai (not in OI):
  license_key, max_budget_per_task, context_window
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List, Optional

from ..llm import LLMRouter
from licensing.activation import require_license, get_license_status
from licensing.models import LicenseInfo


_DEFAULT_SYSTEM = (
    "You are pill.ai — an ultra-cheap, computer-use AI agent.\n"
    "You control the user's desktop, browser, and terminal.\n"
    "Always confirm before running destructive or irreversible commands.\n"
)


class Interpreter:
    """
    API-compatible with OpenInterpreter.  Drop-in replacement:

        from interpreter import interpreter   # same import path as OI
        interpreter.chat("do something")      # same call
    """

    # ─────────────────────────────────────────────────────────────────────
    # __init__: every OI param + pill.ai extensions
    # ─────────────────────────────────────────────────────────────────────

    def __init__(
        self,
        # ── OI params (same names, same defaults) ────────────────────────
        messages: Optional[List[dict]] = None,
        offline: bool = False,
        auto_run: bool = False,
        verbose: bool = False,
        debug: bool = False,
        max_output: int = 2800,
        safe_mode: str = "off",               # OI default is "off"
        shrink_images: bool = True,
        loop: bool = False,
        loop_message: str = (
            "Proceed. You CAN run code on my machine. If the entire task I asked for is done, "
            "say exactly 'The task is done.' If you need some specific information (like username "
            "or password) say EXACTLY 'Please provide more information.' If it's impossible, say "
            "'The task is impossible.' (If I haven't provided a task, say exactly 'Let me know "
            "what you'd like to do next.') Otherwise keep going."
        ),
        loop_breakers: Optional[List[str]] = None,
        disable_telemetry: bool = True,        # pill.ai default: privacy-first
        in_terminal_interface: bool = False,
        conversation_history: bool = True,
        conversation_filename: Optional[str] = None,
        conversation_history_path: Optional[str] = None,
        os: bool = False,                      # OI "OS mode" (full computer control)
        speak_messages: bool = False,
        llm: Optional[Any] = None,             # OI LLM settings object (ignored — we use LiteLLM)
        system_message: Optional[str] = None,
        custom_instructions: str = "",
        user_message_template: str = "{content}",
        always_apply_user_message_template: bool = False,
        code_output_template: str = "Code output: {content}\n\nWhat does this output mean / what's next?",
        empty_code_output_template: str = "The code above was executed on my machine. It produced no text output. what's next (if anything, or are we done?)",
        code_output_sender: str = "user",
        computer: Optional[Any] = None,
        sync_computer: bool = False,
        import_computer_api: bool = False,
        skills_path: Optional[str] = None,
        import_skills: bool = False,
        multi_line: bool = True,
        contribute_conversation: bool = False,  # OI telemetry — no-op in pill.ai
        plain_text_display: bool = False,
        model: str = "deepseek/deepseek-chat",  # OI default was GPT-4o
        # ── pill.ai-only params ───────────────────────────────────────────
        license_key: Optional[str] = None,
        max_budget_per_task: float = 0.50,
        context_window: int = 110_000,
    ):
        # ── License (optional — local use is always free) ─────────────────
        if license_key:
            os.environ["PILLAI_LICENSE_KEY"] = license_key
        self.license: LicenseInfo = require_license()   # never raises; FREE if no key

        # ── OI-compatible attributes ──────────────────────────────────────
        self.messages: List[dict] = messages or []
        self.offline = offline
        self.auto_run = auto_run
        self.verbose = verbose
        self.debug = debug
        self.max_output = max_output
        self.safe_mode = safe_mode
        self.shrink_images = shrink_images
        self.loop = loop
        self.loop_message = loop_message
        self.loop_breakers: List[str] = loop_breakers or [
            "The task is done.",
            "The task is impossible.",
            "Let me know what you'd like to do next.",
            "Please provide more information.",
        ]
        self.disable_telemetry = disable_telemetry
        self.in_terminal_interface = in_terminal_interface
        self.conversation_history = conversation_history
        self.conversation_filename = conversation_filename
        self.conversation_history_path = Path(
            conversation_history_path or Path.home() / ".pill.ai" / "conversations"
        )
        self.os = os
        self.speak_messages = speak_messages
        self.custom_instructions = custom_instructions
        self.user_message_template = user_message_template
        self.always_apply_user_message_template = always_apply_user_message_template
        self.code_output_template = code_output_template
        self.empty_code_output_template = empty_code_output_template
        self.code_output_sender = code_output_sender
        self.sync_computer = sync_computer
        self.import_computer_api = import_computer_api
        self.import_skills = import_skills
        self.multi_line = multi_line
        self.contribute_conversation = contribute_conversation
        self.plain_text_display = plain_text_display
        self.model = model

        # system_message: OI appends custom_instructions
        base_sys = system_message or _DEFAULT_SYSTEM
        self.system_message = base_sys + (f"\n\n{custom_instructions}" if custom_instructions else "")

        # ── OI state tracking (kept for API parity) ───────────────────────
        self.responding = False
        self.last_messages_count = 0
        self.highlight_active_line = True

        # ── pill.ai-only attributes ───────────────────────────────────────
        self.max_budget_per_task = max_budget_per_task
        self.context_window = context_window

        # ── Computer namespace ────────────────────────────────────────────
        self.computer: _ComputerNamespace = computer or _ComputerNamespace()

        # ── Skills ────────────────────────────────────────────────────────
        # Respects OI's skills_path if given, else ~/.pill.ai/skills.md
        if skills_path:
            self._skills_path = Path(skills_path)
        else:
            self._skills_path = Path.home() / ".pill.ai" / "skills.md"
        self._skills_path.parent.mkdir(parents=True, exist_ok=True)

        # ── Router & LangGraph ────────────────────────────────────────────
        self._router = LLMRouter(
            default_model=self.model,
            budget_per_task=self.max_budget_per_task,
        )
        self.computer.vision.set_router(self._router)
        self._graph = None   # lazy-loaded LangGraph

        self._print_banner()
        self._ask_permissions_on_first_run()

    # ── Public API (matches Open Interpreter exactly) ─────────────────────

    def chat(
        self,
        message: Optional[str] = None,
        display: bool = True,
        stream: bool = False,
    ):
        """
        Main entry point — identical signature to OI's interpreter.chat().
        Returns the assistant's reply (string).
        """
        if self.license.daily_call_limit > 0 and self.license.calls_remaining() == 0:
            print(
                f"[pill.ai] Daily call limit reached ({self.license.daily_call_limit}).\n"
                "  Upgrade at https://pill.ai/pricing"
            )
            return

        if message is None:
            return self._interactive_loop()

        if self.user_message_template != "{content}" and (
            self.always_apply_user_message_template or not self.messages
        ):
            message = self.user_message_template.format(content=message)

        self.messages.append({"role": "user", "content": message})
        response = self._dispatch(message)

        if self.loop and not any(b.lower() in response.lower() for b in self.loop_breakers):
            self.messages.append({"role": "assistant", "content": response})
            return self.chat(self.loop_message, display=display, stream=stream)

        self.messages.append({"role": "assistant", "content": response})

        if self.conversation_history:
            self._save_conversation()

        if display and not self.plain_text_display:
            print(response)
        return response

    def reset(self):
        """Clear conversation history — same as OI's interpreter.reset()."""
        if hasattr(self.computer, "terminal"):
            try:
                self.computer.terminal.terminate()
            except Exception:
                pass
        self.messages = []
        self.last_messages_count = 0

    # ── OI API methods (parity) ───────────────────────────────────────────

    def wait(self):
        """Block until responding=False, return new messages since last call."""
        import time
        while self.responding:
            time.sleep(0.2)
        return self.messages[self.last_messages_count:]

    def local_setup(self):
        """Interactive wizard to pick a local model (mirrors OI's local_setup)."""
        print("\n[pill.ai] Local model setup")
        print("  Set DEEPSEEK_API_KEY for DeepSeek V4 Pro (recommended, $0.14/M)")
        print("  Set GEMINI_API_KEY for Gemini 2.0 Flash (vision, free tier)")
        print("  Set OPENAI_API_KEY for GPT-4o-mini (fallback)")
        model = input("\n  Model to use [default: deepseek/deepseek-chat]: ").strip()
        if model:
            self.model = model
            self._router.default_model = model
        print(f"  Model set to: {self.model}\n")

    def display_message(self, markdown: str):
        """Display a markdown message (mirrors OI's display_message)."""
        if self.plain_text_display:
            print(markdown)
        else:
            try:
                from rich.console import Console
                from rich.markdown import Markdown
                Console().print(Markdown(markdown))
            except ImportError:
                print(markdown)

    def get_oi_dir(self) -> str:
        """Return pill.ai's config dir (mirrors OI's get_oi_dir)."""
        return str(Path.home() / ".pill.ai")

    @property
    def anonymous_telemetry(self) -> bool:
        """OI had telemetry; pill.ai is always False."""
        return False

    @property
    def will_contribute(self) -> bool:
        """OI had conversation contribution; pill.ai is always False."""
        return False

    # ── Internal dispatch ─────────────────────────────────────────────────

    def _dispatch(self, message: str) -> str:
        graph = self._get_graph()
        result = graph.invoke({
            "messages": self.messages,
            "task": message,
            "safe_mode": self.safe_mode,
            "license_tier": self.license.tier.value,
        })
        skill_desc = result.get("new_skill")
        if skill_desc:
            self._update_skills(skill_desc)
        output = result.get("output", "")
        if len(output) > self.max_output:
            output = output[: self.max_output] + "\n…[truncated]"
        return output

    def _get_graph(self):
        if self._graph is None:
            from agents.graph import build_graph
            self._graph = build_graph(router=self._router)
        return self._graph

    # ── Skills ────────────────────────────────────────────────────────────

    def _update_skills(self, description: str):
        import datetime
        from interpreter.skills_compactor import check_duplicate, merge_into_existing

        entry = (
            f"## {description.split(chr(10))[0][:80]}\n"
            f"_Added: {datetime.date.today()}_\n\n"
            f"{description}\n"
        )
        duplicate_header = check_duplicate(description, self._skills_path, self._router)
        if duplicate_header:
            merge_into_existing(duplicate_header, entry, self._skills_path, self._router)
            return
        with open(self._skills_path, "a") as f:
            f.write("\n" + entry)

    # ── Conversation persistence ──────────────────────────────────────────

    def _save_conversation(self):
        import json, datetime
        path = self.conversation_history_path
        path.mkdir(parents=True, exist_ok=True)
        fname = self.conversation_filename or f"{datetime.date.today()}.json"
        (path / fname).write_text(json.dumps(self.messages, indent=2))

    # ── First-run permissions ─────────────────────────────────────────────

    def _ask_permissions_on_first_run(self):
        if self.safe_mode != "off":
            return
        marker = Path.home() / ".pill.ai" / "permissions_asked"
        if marker.exists():
            return
        print(
            "\n[pill.ai] First run — what can I do on this machine?\n"
            "  1. Full access (sudo, browser, files, GUI clicks)\n"
            "  2. No sudo — browser + files + GUI only\n"
            "  3. Safe mode — ask before every action\n"
            "  4. Read-only — no execution\n"
        )
        choice = input("Choice [1-4, default 3]: ").strip() or "3"
        levels = {"1": "off", "2": "off", "3": "ask", "4": "read_only"}
        self.safe_mode = levels.get(choice, "ask")
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(self.safe_mode)
        print(f"  Saved. safe_mode = {self.safe_mode}\n")

    def _interactive_loop(self):
        print("pill.ai  (type 'exit' to quit)\n")
        while True:
            try:
                sep = "\n" if self.multi_line else ""
                msg = input(f"{sep}> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if msg.lower() in ("exit", "quit"):
                break
            if msg:
                self.chat(msg)

    def _print_banner(self):
        if self.license.key == "LOCAL":
            mode = "LOCAL FREE"
        else:
            mode = self.license.tier.value.upper()
        print(f"\n  pill.ai  [{mode}]  —  ultra-cheap multi-agent computer AI\n")
        if self.license.message:
            print(f"  {self.license.message}\n")


# ── Computer namespace (mirrors OI's computer.* interface) ────────────────

class _ComputerNamespace:
    """
    Mirrors OpenInterpreter's Computer class.
    OI has 15 sub-modules; pill.ai implements the most-used 8.
    Phase 2 will add: mail, sms, calendar, contacts, docs, ai.
    """
    def __init__(self):
        from interpreter.tools.desktop import DesktopTool
        from interpreter.tools.browser import BrowserTool
        from interpreter.tools.shell import ShellTool
        from interpreter.tools.display import DisplayTool
        from interpreter.tools.clipboard import ClipboardTool
        from interpreter.tools.files import FilesTool
        from interpreter.tools.vision import VisionTool

        _desktop = DesktopTool()

        # OI sub-modules (same attribute names)
        self.mouse = _desktop        # computer.mouse.click(x, y)
        self.keyboard = _desktop     # computer.keyboard.hotkey("ctrl", "c")
        self.browser = BrowserTool() # computer.browser.goto(url)
        self.terminal = ShellTool()  # computer.terminal.run(cmd)
        self.display = DisplayTool() # computer.display.screenshot()
        self.clipboard = ClipboardTool()  # computer.clipboard.paste()
        self.files = FilesTool()     # computer.files.read(path)
        self.vision = VisionTool()   # computer.vision.query(q, image)

        # OI aliases
        self.os = self.terminal      # computer.os → same as terminal in pill.ai
        self.screen = self.display   # computer.screen alias

    def screenshot(self) -> bytes:
        """Convenience: computer.screenshot() → same as computer.display.screenshot()."""
        return self.display.screenshot()
