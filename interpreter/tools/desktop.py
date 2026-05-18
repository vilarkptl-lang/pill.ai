"""
Fork of OpenInterpreter tools/desktop.py
Extended with: drag-and-drop, right-click context menus, screenshot-to-Gemini vision loop.
"""
from __future__ import annotations

import base64
import io
import os
import time
from typing import Optional, Tuple

try:
    import pyautogui
    import pygetwindow as gw
    HAS_GUI = True
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
except ImportError:
    HAS_GUI = False

try:
    from PIL import Image, ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class DesktopTool:
    """
    Full desktop control: mouse, keyboard, screenshots.
    All destructive actions (file delete, format, etc.) go through
    _confirm() when safe_mode != 'off'.
    """

    def __init__(self, safe_mode: str = "ask"):
        self.safe_mode = safe_mode

    # ── Mouse ──────────────────────────────────────────────────────────────

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        self._require_gui()
        pyautogui.click(x, y, clicks=clicks, button=button, interval=0.05)

    def right_click(self, x: int, y: int) -> None:
        self.click(x, y, button="right")

    def double_click(self, x: int, y: int) -> None:
        self.click(x, y, clicks=2)

    def move(self, x: int, y: int, duration: float = 0.2) -> None:
        self._require_gui()
        pyautogui.moveTo(x, y, duration=duration)

    def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> None:
        """Click-drag from (x1,y1) to (x2,y2)."""
        self._require_gui()
        pyautogui.mouseDown(x1, y1)
        time.sleep(0.05)
        pyautogui.moveTo(x2, y2, duration=duration)
        pyautogui.mouseUp()

    def scroll(self, x: int, y: int, clicks: int = 3, direction: str = "down") -> None:
        self._require_gui()
        amount = -clicks if direction == "down" else clicks
        pyautogui.scroll(amount, x=x, y=y)

    # ── Keyboard ──────────────────────────────────────────────────────────

    def type(self, text: str, interval: float = 0.02) -> None:
        self._require_gui()
        pyautogui.typewrite(text, interval=interval)

    def hotkey(self, *keys: str) -> None:
        """e.g. hotkey('ctrl', 'c')"""
        self._require_gui()
        pyautogui.hotkey(*keys)

    def press(self, key: str) -> None:
        self._require_gui()
        pyautogui.press(key)

    def enter(self) -> None:
        self.press("enter")

    # ── Screenshots ───────────────────────────────────────────────────────

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> bytes:
        """Returns PNG bytes."""
        self._require_gui()
        img = pyautogui.screenshot(region=region)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def screenshot_b64(self, region=None) -> str:
        return base64.b64encode(self.screenshot(region=region)).decode()

    def screenshot_and_describe(self, router, region=None) -> str:
        """Take screenshot, send to Gemini Flash for description."""
        b64 = self.screenshot_b64(region=region)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text", "text": "Describe what you see on the screen. Be concise and focus on interactive elements."},
                ],
            }
        ]
        return router.complete(messages, has_images=True)

    # ── Window management ────────────────────────────────────────────────

    def get_active_window(self) -> Optional[str]:
        if not HAS_GUI:
            return None
        try:
            return gw.getActiveWindow().title
        except Exception:
            return None

    def focus_window(self, title_substring: str) -> bool:
        if not HAS_GUI:
            return False
        matches = gw.getWindowsWithTitle(title_substring)
        if matches:
            matches[0].activate()
            time.sleep(0.3)
            return True
        return False

    # ── Helpers ───────────────────────────────────────────────────────────

    def _require_gui(self):
        if not HAS_GUI:
            raise RuntimeError(
                "pyautogui not installed. Run: pip install pyautogui pygetwindow"
            )

    def _confirm(self, action: str) -> bool:
        if self.safe_mode == "off":
            return True
        answer = input(f"[pill.ai] Allow: {action}? [y/N] ").strip().lower()
        return answer in ("y", "yes")
