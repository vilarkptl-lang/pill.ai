"""
Cron jobs and process triggers for pill.ai. (1.30)

When the user says "repite esto cada mañana" or "hazlo cuando abra Ableton",
a schedule entry is created in ~/.pill.ai/schedules.json.

The background scheduler thread checks every 30 s:
  - cron entries: fire once per matching minute
  - trigger entries: fire once when the target process appears
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Callable

_PILLAI_DIR     = Path.home() / ".pill.ai"
_SCHEDULES_PATH = _PILLAI_DIR / "schedules.json"
_lock           = threading.Lock()

# ── Natural-language → cron ───────────────────────────────────────────────────

_CRON_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bcada\s+ma[ñn]ana\b",        re.I), "0 9 * * *"),
    (re.compile(r"\bcada\s+tarde\b",             re.I), "0 18 * * *"),
    (re.compile(r"\bcada\s+noche\b",             re.I), "0 22 * * *"),
    (re.compile(r"\btodos\s+los\s+d[ií]as?\b",   re.I), "0 9 * * *"),
    (re.compile(r"\bcada\s+hora\b",              re.I), "0 * * * *"),
    (re.compile(r"\bevery\s+morning\b",          re.I), "0 9 * * *"),
    (re.compile(r"\bevery\s+(?:day|daily)\b",    re.I), "0 9 * * *"),
    (re.compile(r"\bevery\s+night\b",            re.I), "0 22 * * *"),
    (re.compile(r"\bevery\s+hour\b",             re.I), "0 * * * *"),
]

_TRIGGER_RE = re.compile(
    r"\b(?:cuando\s+(?:abra?|inicie|corra|ejecute)|"
    r"when\s+(?:i\s+(?:open|start|launch)|(.+?)\s+(?:opens?|starts?)))\s+(.+)",
    re.I,
)


def detect_schedule_intent(query: str) -> dict | None:
    """
    Return {"type": "cron", "expression": "..."} or
           {"type": "trigger", "process": "..."} or None.
    """
    for pattern, cron_expr in _CRON_PATTERNS:
        if pattern.search(query):
            return {"type": "cron", "expression": cron_expr}

    m = _TRIGGER_RE.search(query)
    if m:
        process = (m.group(1) or m.group(2) or "").strip().rstrip(".,!?")
        if process:
            return {"type": "trigger", "process": process}

    return None


# ── Schedule store ────────────────────────────────────────────────────────────

def load_schedules() -> list[dict]:
    if not _SCHEDULES_PATH.exists():
        return []
    try:
        return json.loads(_SCHEDULES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_schedules(schedules: list[dict]) -> None:
    _PILLAI_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        _SCHEDULES_PATH.write_text(
            json.dumps(schedules, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def add_cron(skill_name: str, cron_expr: str, task: str) -> dict:
    entry = {
        "id":         str(uuid.uuid4())[:8],
        "type":       "cron",
        "skill":      skill_name,
        "task":       task,
        "expression": cron_expr,
        "enabled":    True,
        "last_run":   None,
    }
    schedules = load_schedules()
    schedules.append(entry)
    save_schedules(schedules)
    return entry


def add_trigger(skill_name: str, process_name: str, task: str) -> dict:
    entry = {
        "id":       str(uuid.uuid4())[:8],
        "type":     "trigger",
        "skill":    skill_name,
        "task":     task,
        "process":  process_name,
        "enabled":  True,
        "last_run": None,
    }
    schedules = load_schedules()
    schedules.append(entry)
    save_schedules(schedules)
    return entry


def list_schedules() -> list[dict]:
    return load_schedules()


def remove_schedule(schedule_id: str) -> bool:
    schedules = load_schedules()
    new = [s for s in schedules if s.get("id") != schedule_id]
    if len(new) == len(schedules):
        return False
    save_schedules(new)
    return True


# ── Process detection ─────────────────────────────────────────────────────────

def _is_process_running(name: str) -> bool:
    try:
        if sys.platform == "win32":
            out = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True, text=True, timeout=5
            ).stdout
            return name.lower() in out.lower()
        else:
            out = subprocess.run(
                ["pgrep", "-i", "-f", name],
                capture_output=True, text=True, timeout=3
            ).stdout
            return bool(out.strip())
    except Exception:
        return False


# ── Background scheduler ──────────────────────────────────────────────────────

def run_scheduler(
    relay_fn: Callable[[str], str],
    check_interval: int = 30,
) -> threading.Thread:
    """
    Start the background scheduler daemon thread.
    relay_fn(task) → reply str (wraps the relay call).
    """
    def _loop():
        seen_processes: set[str] = set()   # track trigger IDs already fired
        while True:
            try:
                schedules = load_schedules()
                now       = time.time()
                changed   = False

                for sched in schedules:
                    if not sched.get("enabled"):
                        continue

                    if sched["type"] == "cron":
                        if _cron_should_run(sched["expression"], sched.get("last_run"), now):
                            try:
                                relay_fn(sched["task"])
                            except Exception:
                                pass
                            sched["last_run"] = now
                            changed = True

                    elif sched["type"] == "trigger":
                        proc = sched.get("process", "")
                        sid  = sched["id"]
                        if _is_process_running(proc):
                            if sid not in seen_processes:
                                seen_processes.add(sid)
                                try:
                                    relay_fn(sched["task"])
                                except Exception:
                                    pass
                                sched["last_run"] = now
                                changed = True
                        else:
                            seen_processes.discard(sid)

                if changed:
                    save_schedules(schedules)

            except Exception:
                pass

            time.sleep(check_interval)

    t = threading.Thread(target=_loop, daemon=True, name="pillai-scheduler")
    t.start()
    return t


# ── Cron math ─────────────────────────────────────────────────────────────────

def _cron_should_run(expression: str, last_run: float | None, now: float) -> bool:
    import datetime
    parts = expression.split()
    if len(parts) != 5:
        return False
    minute_s, hour_s = parts[0], parts[1]
    dt = datetime.datetime.fromtimestamp(now)
    try:
        target_minute = int(minute_s) if minute_s != "*" else dt.minute
        target_hour   = int(hour_s)   if hour_s   != "*" else dt.hour
    except ValueError:
        return False
    if not (dt.hour == target_hour and dt.minute == target_minute):
        return False
    # Don't re-fire within the same minute
    return last_run is None or (now - last_run) >= 60
