"""
Fork of OpenInterpreter computer/clipboard.py
OI used AppKit/xclip directly; pill.ai uses pyperclip (cross-platform).
"""
from __future__ import annotations

try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False


class ClipboardTool:
    """Read and write the system clipboard — mirrors OI's computer.clipboard interface."""

    def copy(self, text: str) -> None:
        """Write text to the clipboard."""
        self._require()
        pyperclip.copy(text)

    def paste(self) -> str:
        """Read text from the clipboard."""
        self._require()
        return pyperclip.paste()

    def clear(self) -> None:
        self.copy("")

    # ── Helpers ───────────────────────────────────────────────────────────

    def _require(self):
        if not HAS_CLIPBOARD:
            raise RuntimeError(
                "pyperclip not installed. Run: pip install pyperclip\n"
                "Linux also needs: sudo apt-get install xclip"
            )
