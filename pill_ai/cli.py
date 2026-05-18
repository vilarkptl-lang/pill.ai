"""
pill.ai CLI — `pillai` command.

Usage:
  pillai                         # interactive chat
  pillai "do X"                  # one-shot task
  pillai run                     # guided interactive demo
  pillai batch tasks.txt         # run tasks from file (one per line)
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

    elif command == "run":
        _run_demo()

    elif command == "batch":
        if len(args) < 2:
            print("Usage: pillai batch <tasks.txt>")
            sys.exit(1)
        _run_batch(args[1])

    else:
        # Treat all other args as a one-shot task
        _run_task(" ".join(args))


# ── Commands ──────────────────────────────────────────────────────────────────

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
    try:
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
        t.add_row("Daily limit", "unlimited" if info.daily_call_limit == 0 else str(info.daily_call_limit))
        t.add_row("Calls remaining", "unlimited" if info.daily_call_limit == 0 else str(info.calls_remaining()))
        if info.message:
            t.add_row("Message", info.message)
        c.print(t)
    except ImportError:
        info = get_license_status()
        print(f"Status: {info.status.value}")
        print(f"Tier:   {info.tier.value}")


def _run_interactive():
    from interpreter.core.core import Interpreter
    ai = Interpreter()
    ai.chat()


def _run_task(task: str):
    from interpreter.core.core import Interpreter
    ai = Interpreter()
    ai.chat(task)


def _run_demo():
    """Guided interactive demo — shows pill.ai capabilities step by step."""
    _print_demo_banner()

    demos = [
        ("Shell", "list the 5 largest files in the current directory"),
        ("Python", "write and run a Python script that prints the first 10 Fibonacci numbers"),
        ("Info", "what is the current date and time, and what OS am I running?"),
    ]

    print("  Choose a demo task or type your own:\n")
    for i, (label, task) in enumerate(demos, 1):
        print(f"  {i}. [{label}] {task}")
    print("  4. Type a custom task")
    print("  5. Start interactive chat\n")

    try:
        choice = input("  Choice [1-5, default 5]: ").strip() or "5"
    except (EOFError, KeyboardInterrupt):
        print()
        return

    from interpreter.core.core import Interpreter
    ai = Interpreter()

    if choice in ("1", "2", "3"):
        _, task = demos[int(choice) - 1]
        print(f"\n  Running: {task}\n")
        ai.chat(task)
    elif choice == "4":
        try:
            task = input("\n  Your task: ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if task:
            ai.chat(task)
    else:
        ai.chat()


def _run_batch(tasks_file: str):
    """Run tasks from a text file (one task per line) and print summary."""
    from pathlib import Path
    path = Path(tasks_file)
    if not path.exists():
        print(f"[pill.ai] File not found: {tasks_file}")
        sys.exit(1)

    tasks = [t.strip() for t in path.read_text().splitlines() if t.strip() and not t.startswith("#")]
    if not tasks:
        print("[pill.ai] No tasks found in file.")
        sys.exit(1)

    print(f"[pill.ai] Running {len(tasks)} tasks from {tasks_file}\n")

    from interpreter.core.core import Interpreter
    ai = Interpreter()

    def _progress(result):
        mark = "✓" if result.status == "ok" else "✗"
        print(f"  {mark} [{result.duration_s:.1f}s ${result.cost_usd:.4f}] {result.task[:60]}")

    batch = ai.run_batch(tasks, on_result=_progress)
    print(f"\n{batch.summary()}")


def _start_server():
    try:
        import uvicorn
        from licensing.server import app
    except ImportError:
        print("Install server deps: pip install 'pill-ai[server]'")
        sys.exit(1)
    print("[pill.ai] Starting license server on http://0.0.0.0:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)


def _print_demo_banner():
    print("""
  ╔══════════════════════════════════════════════════════╗
  ║          pill.ai — interactive demo                  ║
  ║  Ultra-cheap multi-agent computer AI                 ║
  ║  Local use: FREE forever. No account needed.         ║
  ╚══════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
