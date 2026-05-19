"""
Fork of OpenInterpreter computer/display.py
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
    import PIL  # noqa: F401
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class DisplayTool:
    def size(self) -> Tuple[int, int]:
        self._require_gui()
        return pyautogui.size()

    def width(self) -> int:
        return self.size()[0]

    def height(self) -> int:
        return self.size()[1]

    def center(self) -> Tuple[int, int]:
        w, h = self.size()
        return w // 2, h // 2

    def screenshot(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        show: bool = False,
    ) -> bytes:
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
        data = self.screenshot(region=region)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def _require_gui(self):
        if not HAS_GUI:
            raise RuntimeError("pyautogui not installed. Run: pip install pyautogui")
