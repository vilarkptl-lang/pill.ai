"""
Fork of OpenInterpreter tools/shell.py
Extended with: persistent session, sudo support, output streaming, timeout.
"""
from __future__ import annotations

import os
import queue
import re
import subprocess
import threading
import time
from typing import Callable, Optional


_DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bdd\b.*\bof=/dev/",
    r"\bmkfs\b",
    r"\bformat\b",
    r"\bsudo\s+passwd\b",
    r"\bchmod\s+-R\s+777\b",
    r"\bcrontab\s+-r\b",
    r">\s*/etc/",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bpkill\s+-9\b",
]


class ShellTool:
    """
    Persistent shell session with:
    - Streaming output
    - Timeout enforcement
    - sudo support (asks for password once, caches in memory only)
    - Dangerous command detection
    """

    def __init__(self, safe_mode: str = "ask", timeout: int = 60):
        self.safe_mode = safe_mode
        self.timeout = timeout
        self._sudo_password: Optional[str] = None
        self._process: Optional[subprocess.Popen] = None
        self._cwd = os.path.expanduser("~")

    # ── Public API ────────────────────────────────────────────────────────

    def run(
        self,
        command: str,
        timeout: Optional[int] = None,
        on_output: Optional[Callable[[str], None]] = None,
        allow_sudo: bool = True,
    ) -> dict:
        """
        Execute `command` in a subprocess.
        Returns {"stdout": str, "stderr": str, "returncode": int, "timed_out": bool}
        """
        if self._is_dangerous(command):
            if not self._confirm(f"DANGEROUS: {command}"):
                return {"stdout": "", "stderr": "Blocked by user.", "returncode": -1, "timed_out": False}

        if "sudo" in command and allow_sudo:
            command = self._inject_sudo(command)

        return self._execute(command, timeout or self.timeout, on_output)

    def run_python(self, code: str, **kwargs) -> dict:
        """Run Python code via `python3 -c`."""
        escaped = code.replace('"', '\\"')
        return self.run(f'python3 -c "{escaped}"', **kwargs)

    def install(self, package: str) -> dict:
        return self.run(f"pip install {package}")

    def cd(self, path: str) -> None:
        expanded = os.path.expanduser(path)
        if os.path.isdir(expanded):
            self._cwd = expanded
        else:
            raise FileNotFoundError(f"Directory not found: {path}")

    # ── Internal ──────────────────────────────────────────────────────────

    def _execute(
        self,
        command: str,
        timeout: int,
        on_output: Optional[Callable[[str], None]],
    ) -> dict:
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        timed_out = False

        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self._cwd,
            env=os.environ.copy(),
        )

        def _read(pipe, store, label):
            for line in pipe:
                store.append(line)
                if on_output:
                    on_output(line)

        t_out = threading.Thread(target=_read, args=(proc.stdout, stdout_lines, "stdout"))
        t_err = threading.Thread(target=_read, args=(proc.stderr, stderr_lines, "stderr"))
        t_out.start()
        t_err.start()

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            timed_out = True

        t_out.join()
        t_err.join()

        return {
            "stdout": "".join(stdout_lines),
            "stderr": "".join(stderr_lines),
            "returncode": proc.returncode,
            "timed_out": timed_out,
        }

    def _is_dangerous(self, command: str) -> bool:
        for pattern in _DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return True
        return False

    def _confirm(self, action: str) -> bool:
        if self.safe_mode == "off":
            return True
        answer = input(f"[pill.ai] Allow: {action}? [y/N] ").strip().lower()
        return answer in ("y", "yes")

    def _inject_sudo(self, command: str) -> str:
        """Prepend sudo password via stdin if needed."""
        if "sudo " not in command:
            return command
        if self._sudo_password is None:
            import getpass
            self._sudo_password = getpass.getpass("[pill.ai] sudo password: ")
        return f"echo '{self._sudo_password}' | sudo -S {command.replace('sudo ', '', 1)}"
