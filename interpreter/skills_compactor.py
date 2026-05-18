"""
Port of agentic-repo/financial/bot/agents/context-compactor.js to Python.

Integrates with _update_skills(): before appending a new entry to skills.md,
compact similar/redundant entries so the file doesn't grow unboundedly.
"""
from __future__ import annotations

import time
from typing import Optional


COMPACT_THRESHOLD = 12   # minimum entries before compaction kicks in
CACHE_TTL_MS = 90_000    # 90 seconds, matching JS original


class SkillsCompactor:
    """
    In-memory compactor for skills.md entries.
    Uses DeepSeek to collapse semantically similar skills into one summary.
    """

    def __init__(self, router):
        self._router = router
        self._cache: dict[str, dict] = {}   # key → {result, expires_at}

    def compact(self, entries: list[str]) -> Optional[str]:
        """
        Given a list of skills.md entry strings, return a compacted version
        or None if below threshold (caller should just append normally).
        """
        if len(entries) < COMPACT_THRESHOLD:
            return None

        cache_key = _entries_key(entries)
        cached = self._cache.get(cache_key)
        if cached and cached["expires_at"] > time.time() * 1000:
            return cached["result"]

        prompt = (
            "You are a skills log compactor. "
            "Below are skill entries recorded by an AI agent. "
            "Collapse semantically duplicate or highly similar entries into one concise summary per skill group. "
            "Return a clean markdown list — one entry per unique skill. "
            "Discard redundant entries. Keep the most recent date.\n\n"
            + "\n---\n".join(entries)
        )
        result = self._router.complete([{"role": "user", "content": prompt}])

        self._cache[cache_key] = {
            "result": result,
            "expires_at": time.time() * 1000 + CACHE_TTL_MS,
        }
        return result

    def invalidate(self, cache_key: str):
        self._cache.pop(cache_key, None)

    def clear(self):
        self._cache.clear()


def _entries_key(entries: list[str]) -> str:
    import hashlib
    return hashlib.md5("\n".join(entries[:COMPACT_THRESHOLD]).encode()).hexdigest()
