"""
pill.ai CLI — `pillai` command.

Usage:
  pillai                         # interactive chat
  pillai "do X"                  # one-shot task
  pillai activate PILLAI-XXXX    # activate license
  pillai deactivate              # deactivate this seat
  pillai status                  # show license status
  pillai server                  # start license server (owner only)
"""
from __future__ import annotations

import sys


def main():
    args = sys.argv[1:]

    if not args:
        _run_interactive()
        return

    command = args[0].lower()

    if command == "activate":
        if len(args) < 2:
            print("Usage: pillai activate <LICENSE-KEY>")
            sys.exit(1)
        _activate(args[1])

    elif command == "deactivate":
        _deactivate()

    elif command == "status":
        _status()

    elif command == "server":
        _start_server()

    else:
        # Treat all other args as a one-shot task
        task = " ".join(args)
        _run_task(task)


def _activate(key: str):
    from licensing.activation import activate
    info = activate(key)
    if info.is_usable():
        print(f"[pill.ai] Activated! Tier: {info.tier.value}  Email: {info.email}")
    else:
        print(f"[pill.ai] Activation failed: {info.status.value} — {info.message}")
        sys.exit(1)


def _deactivate():
    from licensing.activation import deactivate
    deactivate()
    print("[pill.ai] License removed from this machine.")


def _status():
    from licensing import get_license_status
    from rich.console import Console
    from rich.table import Table
    info = get_license_status()
    c = Console()
    t = Table(title="pill.ai License Status")
    t.add_column("Field")
    t.add_column("Value")
    t.add_row("Status", info.status.value)
    t.add_row("Tier", info.tier.value)
    t.add_row("Email", info.email or "-")
    t.add_row("Daily limit", str(info.daily_call_limit))
    t.add_row("Calls remaining", str(info.calls_remaining()))
    if info.message:
        t.add_row("Message", info.message)
    c.print(t)


def _run_interactive():
    from interpreter.core.core import Interpreter
    i = Interpreter()
    i.chat()


def _run_task(task: str):
    from interpreter.core.core import Interpreter
    i = Interpreter()
    i.chat(task)


def _start_server():
    try:
        import uvicorn
        from licensing.server import app
    except ImportError:
        print("Install server deps: pip install 'pill-ai[server]'")
        sys.exit(1)
    print("[pill.ai] Starting license server on http://0.0.0.0:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
