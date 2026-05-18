"""
Fork of OpenInterpreter computer/vision.py
OI used GPT-4V; pill.ai routes vision to Gemini 2.0 Flash via LiteLLM
(5x cheaper than GPT-4V for the same quality on screenshots).
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional


class VisionTool:
    """
    Image analysis via Gemini 2.0 Flash.
    Mirrors OI's computer.vision.query(query, screenshot) interface.
    """

    def __init__(self, router=None):
        self._router = router

    def set_router(self, router) -> None:
        self._router = router

    def query(self, query: str, image: Optional[bytes] = None, image_path: Optional[str] = None) -> str:
        """
        Ask a question about an image.
        Provide either raw PNG bytes (image=) or a file path (image_path=).
        """
        if image is None and image_path is None:
            raise ValueError("Provide either image= (bytes) or image_path=")
        if image is None:
            image = Path(image_path).read_bytes()

        b64 = base64.b64encode(image).decode()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text", "text": query},
                ],
            }
        ]
        return self._get_router().complete(messages, has_images=True)

    def describe(self, image: Optional[bytes] = None, image_path: Optional[str] = None) -> str:
        return self.query(
            "Describe what you see. Be concise and focus on interactive elements, text, and layout.",
            image=image,
            image_path=image_path,
        )

    def ocr(self, image: Optional[bytes] = None, image_path: Optional[str] = None) -> str:
        return self.query(
            "Extract all text visible in this image. Return only the text, preserving layout.",
            image=image,
            image_path=image_path,
        )

    def find_element(self, description: str, image: Optional[bytes] = None, image_path: Optional[str] = None) -> str:
        return self.query(
            f"Find the UI element that matches: '{description}'. "
            "Return its approximate location as: top-left, top-right, center, etc. "
            "If you can estimate pixel coordinates (x, y), include them.",
            image=image,
            image_path=image_path,
        )

    # ── Helpers ───────────────────────────────────────────────────────────

    def _get_router(self):
        if self._router is None:
            from interpreter.llm import LLMRouter
            self._router = LLMRouter()
        return self._router
