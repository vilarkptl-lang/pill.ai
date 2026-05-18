"""
Context injection for pill.ai — mirrors relay-master's context injection pattern.

Before each LangGraph dispatch, the ContextInjector builds an enriched system
prefix that includes:
  1. Relevant skills from ~/.pill.ai/skills.md (top-k by keyword match)
  2. Conversation summary when history exceeds the token budget
  3. Machine context (OS, working directory, available tools)

This is the "context injection" half of relay-master. The compaction half
lives in skills_compactor.py (semantic dedup) and compact_conversation() here.

The injector is stateless — call inject() before each graph.invoke().
"""
from __future__ import annotations

import os
import platform
import re
from pathlib import Path
from typing import Optional

# Characters → rough token estimate (4 chars ≈ 1 token)
_CHARS_PER_TOKEN = 4
_MAX_SKILLS_TOKENS = 800
_MAX_HISTORY_TOKENS = 6_000
_SUMMARY_TRIGGER_TOKENS = 8_000


class ContextInjector:
    """
    Build enriched context for the supervisor node.

    Usage (wired into Interpreter._dispatch):
        injector = ContextInjector(skills_path, router)
        enriched_messages = injector.inject(messages, task)
        graph.invoke({..., "messages": enriched_messages})
    """

    def __init__(self, skills_path: Path, router):
        self._skills_path = skills_path
        self._router = router
        self._conversation_summary: Optional[str] = None

    def inject(self, messages: list[dict], task: str) -> list[dict]:
        """
        Return a new message list with injected context prepended.
        Original messages are not modified.
        """
        parts = []

        # 1. Machine context
        parts.append(self._machine_context())

        # 2. Relevant skills
        skill_ctx = self._relevant_skills(task)
        if skill_ctx:
            parts.append(skill_ctx)

        # 3. Conversation summary if history is long
        messages = self._maybe_compact(messages)

        if parts:
            system_inject = "\n\n".join(parts)
            return [{"role": "system", "content": system_inject}] + messages
        return messages

    # ── Machine context ───────────────────────────────────────────────────

    def _machine_context(self) -> str:
        info = [
            f"OS: {platform.system()} {platform.release()}",
            f"CWD: {os.getcwd()}",
            f"Home: {Path.home()}",
        ]
        return "Machine context:\n" + "\n".join(f"  {i}" for i in info)

    # ── Skill injection ───────────────────────────────────────────────────

    def _relevant_skills(self, task: str) -> str:
        """
        Pull top-k skills from skills.md that share keywords with `task`.
        Budget: _MAX_SKILLS_TOKENS tokens worth of content.
        """
        if not self._skills_path.exists():
            return ""
        content = self._skills_path.read_text(encoding="utf-8", errors="ignore")
        if not content.strip():
            return ""

        sections = _split_sections(content)
        task_words = set(re.findall(r"\w+", task.lower()))
        scored = []
        for header, body in sections:
            if not header:
                continue
            skill_words = set(re.findall(r"\w+", (header + " " + body).lower()))
            score = len(task_words & skill_words)
            if score > 0:
                scored.append((score, header, body))

        scored.sort(reverse=True)
        budget = _MAX_SKILLS_TOKENS * _CHARS_PER_TOKEN
        selected = []
        for _, header, body in scored:
            entry = f"## {header}\n{body}"
            if len("\n".join(selected) + entry) > budget:
                break
            selected.append(entry)

        if not selected:
            return ""
        return "Relevant skills from memory:\n" + "\n\n".join(selected)

    # ── Conversation compaction ───────────────────────────────────────────

    def _maybe_compact(self, messages: list[dict]) -> list[dict]:
        """
        If conversation history is too long, summarize old messages and
        replace them with [summary] + recent tail.
        Mirrors relay-master's context-compactor pattern.
        """
        history_chars = sum(len(str(m.get("content", ""))) for m in messages)
        if history_chars < _SUMMARY_TRIGGER_TOKENS * _CHARS_PER_TOKEN:
            return messages

        # Keep the most recent messages within MAX_HISTORY budget
        tail_budget = _MAX_HISTORY_TOKENS * _CHARS_PER_TOKEN
        tail: list[dict] = []
        tail_chars = 0
        for m in reversed(messages):
            chunk = len(str(m.get("content", "")))
            if tail_chars + chunk > tail_budget:
                break
            tail.insert(0, m)
            tail_chars += chunk

        to_summarize = messages[: len(messages) - len(tail)]
        if not to_summarize:
            return messages

        summary = self._summarize(to_summarize)
        self._conversation_summary = summary

        summary_msg = {
            "role": "system",
            "content": f"[Conversation summary — earlier context]\n{summary}",
        }
        return [summary_msg] + tail

    def _summarize(self, messages: list[dict]) -> str:
        if self._conversation_summary:
            prior = f"Previous summary: {self._conversation_summary}\n\n"
        else:
            prior = ""

        text = "\n".join(
            f"{m['role']}: {str(m.get('content',''))[:500]}"
            for m in messages
        )
        prompt = (
            f"{prior}Summarize the following conversation excerpt concisely "
            f"(2-4 sentences). Focus on tasks attempted and results:\n\n{text}"
        )
        try:
            return self._router.complete([{"role": "user", "content": prompt}])
        except Exception:
            return f"[{len(messages)} earlier messages — summary unavailable]"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _split_sections(content: str) -> list[tuple[str, str]]:
    parts = content.split("\n## ")
    result = [("", parts[0])]
    for part in parts[1:]:
        lines = part.split("\n", 1)
        header = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        result.append((header, body))
    return result
