"""
Fork of OpenInterpreter computer/files.py
OI had minimal file helpers; pill.ai adds find, read_lines, safe_write.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Optional


class FilesTool:
    """Basic file I/O helpers — mirrors OI's computer.files interface."""

    # ── Read ──────────────────────────────────────────────────────────────

    def read(self, path: str, encoding: str = "utf-8") -> str:
        return Path(path).expanduser().read_text(encoding=encoding)

    def read_lines(self, path: str, start: int = 1, end: Optional[int] = None) -> str:
        lines = Path(path).expanduser().read_text().splitlines()
        return "\n".join(lines[start - 1 : end])

    def exists(self, path: str) -> bool:
        return Path(path).expanduser().exists()

    def is_dir(self, path: str) -> bool:
        return Path(path).expanduser().is_dir()

    def size(self, path: str) -> int:
        return Path(path).expanduser().stat().st_size

    # ── Write ─────────────────────────────────────────────────────────────

    def write(self, path: str, content: str, encoding: str = "utf-8") -> str:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding=encoding)
        return str(p)

    def append(self, path: str, content: str) -> str:
        p = Path(path).expanduser()
        with p.open("a") as f:
            f.write(content)
        return str(p)

    # ── Browse ────────────────────────────────────────────────────────────

    def list(self, path: str = ".", pattern: str = "*") -> List[str]:
        return [str(p) for p in Path(path).expanduser().glob(pattern)]

    def find(self, root: str, name_pattern: str) -> List[str]:
        """Recursive find by filename glob."""
        return [str(p) for p in Path(root).expanduser().rglob(name_pattern)]

    def tree(self, path: str = ".", max_depth: int = 3) -> str:
        lines: List[str] = []
        root = Path(path).expanduser()

        def _walk(p: Path, depth: int):
            if depth > max_depth:
                return
            prefix = "  " * depth
            lines.append(f"{prefix}{p.name}{'/' if p.is_dir() else ''}")
            if p.is_dir():
                for child in sorted(p.iterdir()):
                    _walk(child, depth + 1)

        _walk(root, 0)
        return "\n".join(lines)

    # ── Manage ────────────────────────────────────────────────────────────

    def mkdir(self, path: str) -> str:
        p = Path(path).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return str(p)

    def copy(self, src: str, dst: str) -> str:
        return str(shutil.copy2(src, dst))

    def move(self, src: str, dst: str) -> str:
        return str(shutil.move(src, dst))

    def delete(self, path: str) -> None:
        p = Path(path).expanduser()
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
