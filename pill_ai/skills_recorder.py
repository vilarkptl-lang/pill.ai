"""
Skill recording for pill.ai. (1.29)

When the user says "recuerda esto" / "remember this" / "guarda este proceso",
the agent extracts a skill from the recent conversation and appends it to
~/.pill.ai/skills.md.

Semantic deduplication is handled by interpreter.skills_compactor before saving.
"""
from __future__ import annotations

import re
from pathlib import Path

_PILLAI_DIR  = Path.home() / ".pill.ai"
_SKILLS_PATH = _PILLAI_DIR / "skills.md"

# Patterns that signal the user wants to record a skill
_REMEMBER_RE = re.compile(
    r"\b("
    r"recuerda\s+(esto|este\s+proceso|esta\s+forma|c[oó]mo|este\s+paso)"
    r"|remember\s+this"
    r"|guarda\s+(esto|esta\s+skill|este\s+proceso|esta\s+acci[oó]n)"
    r"|aprende\s+(esto|c[oó]mo)"
    r"|save\s+this(\s+skill)?"
    r"|memoriza\s+esto"
    r")\b",
    re.IGNORECASE,
)


def detect_remember_intent(query: str) -> bool:
    return bool(_REMEMBER_RE.search(query))


def record_skill(
    conversation: list[dict],
    query: str,
    router=None,
) -> str:
    """
    Extract a skill from the recent conversation and append it to skills.md.
    Returns the skill name saved, or an error string.
    """
    _PILLAI_DIR.mkdir(parents=True, exist_ok=True)

    recent  = conversation[-8:] if len(conversation) > 8 else conversation
    excerpt = "\n".join(
        f"{m['role']}: {str(m.get('content', ''))[:600]}"
        for m in recent
    )

    if router:
        try:
            skill_name = router.complete([{
                "role": "user",
                "content": (
                    "Based on this conversation, write a SHORT skill title "
                    "(3–8 words, imperative verb, no punctuation) describing what was done:\n\n"
                    + excerpt
                ),
            }]).strip().strip("#").strip()

            skill_body = router.complete([{
                "role": "user",
                "content": (
                    "Write a concise skill entry (4–8 lines) for a skills.md file. "
                    "Format as numbered steps the agent should follow to repeat this task. "
                    "No preamble — start directly with step 1:\n\n"
                    + excerpt
                ),
            }]).strip()
        except Exception:
            skill_name = _fallback_name(query)
            skill_body = f"Repeat the task: {query}"
    else:
        skill_name = _fallback_name(query)
        skill_body = f"Repeat the task: {query}"

    # Semantic dedup: skip if equivalent skill already exists
    try:
        from interpreter.skills_compactor import check_duplicate
        dup = check_duplicate(skill_name, _SKILLS_PATH, router) if router else None
        if dup:
            return f"[Ya existe una skill similar: '{dup}' — no se duplicó]"
    except Exception:
        pass

    entry = f"\n## {skill_name}\n{skill_body}\n"
    with open(_SKILLS_PATH, "a", encoding="utf-8") as f:
        f.write(entry)

    return skill_name


def _fallback_name(query: str) -> str:
    words = query.lower().split()
    # Strip trigger words
    skip = {"recuerda", "remember", "guarda", "aprende", "esto", "this", "save"}
    words = [w for w in words if w not in skip]
    return " ".join(words[:6]).strip(".,!?") or "tarea sin nombre"
