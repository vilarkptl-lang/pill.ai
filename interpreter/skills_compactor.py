"""
Semantic deduplication for skills.md entries + conversation compaction.

Skills compaction:
  Unlike the ContextCompactor in relay-master (which collapses conversation
  history by recency), skills are unique capabilities — they don't expire and
  shouldn't be collapsed by count. The correct trigger is semantic similarity:
  "does this new skill already exist under a different name?"

  On each new skill, we ask the router to check against existing skill headers.
  No TTL, no count threshold, no in-memory cache needed.

Conversation compaction:
  Mirrors relay-master's context-compactor.js pattern. When conversation history
  grows beyond a token budget, old messages are summarized in a single system
  message and the tail is kept verbatim.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def check_duplicate(
    new_description: str,
    skills_path: Path,
    router,
) -> Optional[str]:
    """
    Return the header of an existing skill that semantically duplicates
    `new_description`, or None if no duplicate exists.

    Costs ~1 cheap DeepSeek call (< $0.0001). Only called when skills_path
    has at least one existing entry.
    """
    if not skills_path.exists():
        return None

    existing_headers = _parse_headers(skills_path.read_text())
    if not existing_headers:
        return None

    header_list = "\n".join(f"- {h}" for h in existing_headers)
    new_title = new_description.split("\n")[0][:120]

    prompt = (
        "You are checking a skills log for duplicates.\n"
        "Existing skill headers:\n"
        f"{header_list}\n\n"
        f"New skill to add: {new_title}\n\n"
        "If the new skill is semantically equivalent or a subset of an existing skill, "
        "reply with EXACTLY the matching header text and nothing else.\n"
        "If it is genuinely new or distinct, reply with: UNIQUE"
    )

    response = router.complete([{"role": "user", "content": prompt}]).strip()

    if response == "UNIQUE" or response not in existing_headers:
        return None
    return response


def merge_into_existing(
    existing_header: str,
    new_description: str,
    skills_path: Path,
    router,
) -> None:
    """
    Merge new_description into the existing skill entry rather than appending.
    Calls the router to produce a merged entry, then replaces in-place.
    """
    content = skills_path.read_text()
    sections = _split_sections(content)

    target_idx = next(
        (i for i, (h, _) in enumerate(sections) if h == existing_header), None
    )
    if target_idx is None:
        return

    _, existing_body = sections[target_idx]

    prompt = (
        "Merge these two skill entries into one concise markdown section. "
        "Keep the most specific and complete information. Remove redundancy.\n\n"
        f"## {existing_header}\n{existing_body}\n\n"
        f"---\n\n{new_description}"
    )
    merged = router.complete([{"role": "user", "content": prompt}]).strip()
    sections[target_idx] = (existing_header, merged.removeprefix(f"## {existing_header}").strip())

    preamble = sections[0][1] if sections and sections[0][0] == "" else ""
    body = "\n\n".join(
        f"## {h}\n{b}" if h else b for h, b in sections
    )
    skills_path.write_text(body if preamble else body)


def _parse_headers(content: str) -> list[str]:
    return [
        line[3:].strip()
        for line in content.splitlines()
        if line.startswith("## ")
    ]


def _split_sections(content: str) -> list[tuple[str, str]]:
    """Split content into (header, body) pairs. First tuple has header='' for preamble."""
    parts = content.split("\n## ")
    result = [("", parts[0])]
    for part in parts[1:]:
        lines = part.split("\n", 1)
        header = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        result.append((header, body))
    return result
