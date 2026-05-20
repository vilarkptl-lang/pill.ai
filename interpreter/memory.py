"""
Persistent conversation memory for pill.ai. (1.28 + 1.24)

Sessions are saved to ~/.pill.ai/sessions/<id>.json
History is compacted automatically when it grows beyond COMPACT_THRESHOLD messages:
  - The oldest messages are summarized via the relay (1 cheap call)
  - The summary replaces them as a system message
  - The last TAIL_KEEP messages are kept verbatim
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

_PILLAI_DIR    = Path.home() / ".pill.ai"
_SESSIONS_DIR  = _PILLAI_DIR / "sessions"
_lock          = threading.Lock()

COMPACT_THRESHOLD = 20   # compact when history exceeds this many messages
TAIL_KEEP         = 10   # always keep the N most recent messages verbatim


# ── I/O ───────────────────────────────────────────────────────────────────────

def _session_path(session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return _SESSIONS_DIR / f"{safe or 'default'}.json"


def load(session_id: str = "default") -> list[dict]:
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = _session_path(session_id)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save(session_id: str, messages: list[dict]) -> None:
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        _session_path(session_id).write_text(
            json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def append(session_id: str, role: str, content: str) -> list[dict]:
    """Append one message and persist. Returns the full updated history."""
    messages = load(session_id)
    messages.append({"role": role, "content": content})
    save(session_id, messages)
    return messages


# ── Compaction (1.28) ─────────────────────────────────────────────────────────

def compact_if_needed(session_id: str, router=None) -> list[dict]:
    """
    If history is long, summarize the oldest messages and replace them with a
    single system message. Returns the (possibly compacted) history.
    """
    messages = load(session_id)
    if len(messages) < COMPACT_THRESHOLD:
        return messages

    tail         = messages[-TAIL_KEEP:]
    to_summarize = messages[:-TAIL_KEEP]

    if not to_summarize:
        return messages

    summary = _summarize(to_summarize, router)
    compacted = [
        {"role": "system", "content": f"[Resumen de conversación anterior]\n{summary}"}
    ] + tail
    save(session_id, compacted)
    return compacted


def _summarize(messages: list[dict], router=None) -> str:
    if router is None:
        return f"[{len(messages)} mensajes anteriores — resumen no disponible]"
    excerpt = "\n".join(
        f"{m['role']}: {str(m.get('content', ''))[:400]}"
        for m in messages
    )
    prompt = (
        "Summarize the following conversation in 3-5 sentences. "
        "Focus on tasks done and key results:\n\n" + excerpt
    )
    try:
        return router.complete([{"role": "user", "content": prompt}])
    except Exception:
        return f"[{len(messages)} mensajes anteriores]"


# ── Convenience ───────────────────────────────────────────────────────────────

def list_sessions() -> list[str]:
    if not _SESSIONS_DIR.exists():
        return []
    return [p.stem for p in _SESSIONS_DIR.glob("*.json")]


def delete_session(session_id: str) -> None:
    path = _session_path(session_id)
    if path.exists():
        path.unlink()
