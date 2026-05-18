"""
Fork of OpenInterpreter computer/display.py
Provides screen geometry, multi-monitor info, and screenshot capture.
OI used python-xlib / AppKit; pill.ai uses pyautogui (cross-platform).
"""
from __future__ import annotations

import base64
import io
from typing import Optional, Tuple

try:
    import pyautogui
    HAS_GUI = True
except ImportError:
    HAS_GUI = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class DisplayTool:
    """Screen geometry and capture — mirrors OI's computer.display interface."""

    # ── Screen info ──────────────────────────────────────────────────────

    def size(self) -> Tuple[int, int]:
        """Return (width, height) of the primary screen."""
        self._require_gui()
        return pyautogui.size()

    def width(self) -> int:
        return self.size()[0]

    def height(self) -> int:
        return self.size()[1]

    def center(self) -> Tuple[int, int]:
        w, h = self.size()
        return w // 2, h // 2

    # ── Screenshot ────────────────────────────────────────────────────────

    def screenshot(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        show: bool = False,
    ) -> bytes:
        """Return PNG bytes. region=(left, top, width, height)."""
        self._require_gui()
        img = pyautogui.screenshot(region=region)
        if show:
            img.show()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def screenshot_b64(self, region=None) -> str:
        return base64.b64encode(self.screenshot(region=region)).decode()

    def save_screenshot(self, path: str, region=None) -> str:
        """Save screenshot to path; return the path."""
        data = self.screenshot(region=region)
        with open(path, "wb") as f:
            f.write(data)
        return path

    # ── Helpers ───────────────────────────────────────────────────────────

    def _require_gui(self):
        if not HAS_GUI:
            raise RuntimeError(
                "pyautogui not installed. Run: pip install pyautogui"
            )
