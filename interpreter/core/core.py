"""
Fork of OpenInterpreter/open-interpreter — interpreter/core/core.py
Extended with:
  - pill.ai license gating
  - LangGraph multi-agent routing
  - LiteLLM ultra-cheap model routing
  - skills.md auto-update
  - Confirmation hooks for dangerous actions
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from ..llm import LLMRouter
from licensing.activation import require_license, get_license_status
from licensing.models import LicenseInfo


class Interpreter:
    """
    Central class — mirrors OpenInterpreter's public API,
    extended with multi-agent routing and license enforcement.
    """

    def __init__(
        self,
        license_key: Optional[str] = None,
        model: str = "deepseek/deepseek-chat",   # DeepSeek V4 Pro via LiteLLM
        auto_run: bool = False,
        safe_mode: str = "ask",                  # ask | off | auto
        verbose: bool = False,
        system_message: Optional[str] = None,
        context_window: int = 110_000,
        max_budget_per_task: float = 0.50,       # USD hard stop
    ):
        # ── License check ─────────────────────────────────────────────────
        if license_key:
            os.environ["PILLAI_LICENSE_KEY"] = license_key
        self.license: LicenseInfo = require_license()

        # ── Settings ──────────────────────────────────────────────────────
        self.model = model
        self.auto_run = auto_run
        self.safe_mode = safe_mode
        self.verbose = verbose
        self.context_window = context_window
        self.max_budget_per_task = max_budget_per_task

        self.messages: list[dict] = []
        self.computer = _ComputerNamespace()

        default_system = (
            "You are pill.ai — an ultra-cheap, computer-use AI agent.\n"
            "You control the user's desktop, browser, and terminal.\n"
            "Always confirm before running destructive or irreversible commands.\n"
        )
        self.system_message = system_message or default_system

        # ── Router & agents ───────────────────────────────────────────────
        self._router = LLMRouter(
            default_model=self.model,
            budget_per_task=self.max_budget_per_task,
        )
        self._graph = None   # lazy-loaded LangGraph

        # ── Skills ────────────────────────────────────────────────────────
        self._skills_path = Path("skills.md")
        self._compactor = None   # lazy-loaded SkillsCompactor

        self._print_banner()
        self._ask_permissions_on_first_run()

    # ── Public API (matches Open Interpreter) ─────────────────────────────

    def chat(self, message: Optional[str] = None, display: bool = True, stream: bool = False):
        """Main entry point — send a message and get a response."""
        if self.license.calls_remaining() == 0:
            print(
                f"[pill.ai] Daily call limit reached ({self.license.daily_call_limit}).\n"
                "  Upgrade at https://pill.ai/pricing"
            )
            return

        if message is None:
            return self._interactive_loop()

        self.messages.append({"role": "user", "content": message})
        response = self._dispatch(message)
        self.messages.append({"role": "assistant", "content": response})

        if display:
            print(response)
        return response

    def reset(self):
        self.messages = []

    # ── Internal ──────────────────────────────────────────────────────────

    def _dispatch(self, message: str) -> str:
        """Route to the LangGraph multi-agent graph."""
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
        return result.get("output", "")

    def _get_graph(self):
        if self._graph is None:
            from agents.graph import build_graph
            self._graph = build_graph(router=self._router)
        return self._graph

    def _update_skills(self, description: str):
        """Append new skill entry to skills.md, compacting if entries exceed threshold."""
        import datetime
        from interpreter.skills_compactor import SkillsCompactor, COMPACT_THRESHOLD

        if self._compactor is None:
            self._compactor = SkillsCompactor(self._router)

        entry = (
            f"\n## {description.split(chr(10))[0][:80]}\n"
            f"_Added: {datetime.date.today()}_\n\n"
            f"{description}\n"
        )

        existing = self._skills_path.read_text() if self._skills_path.exists() else ""
        current_entries = [e for e in existing.split("\n## ") if e.strip()]

        if len(current_entries) >= COMPACT_THRESHOLD:
            compacted = self._compactor.compact(current_entries)
            if compacted:
                header = existing.split("\n## ")[0] if existing else ""
                self._skills_path.write_text(header + "\n" + compacted + entry)
                return

        with open(self._skills_path, "a") as f:
            f.write(entry)

    def _ask_permissions_on_first_run(self):
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
                msg = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if msg.lower() in ("exit", "quit"):
                break
            if msg:
                self.chat(msg)

    def _print_banner(self):
        tier = self.license.tier.value.upper()
        print(f"\n  pill.ai  [{tier}]  —  ultra-cheap multi-agent computer AI\n")
        if self.license.message:
            print(f"  {self.license.message}\n")


class _ComputerNamespace:
    """Thin namespace so `interpreter.computer.mouse.click()` works."""
    def __init__(self):
        from interpreter.tools.desktop import DesktopTool
        from interpreter.tools.browser import BrowserTool
        from interpreter.tools.shell import ShellTool
        self.mouse = DesktopTool()
        self.keyboard = DesktopTool()
        self.browser = BrowserTool()
        self.terminal = ShellTool()
