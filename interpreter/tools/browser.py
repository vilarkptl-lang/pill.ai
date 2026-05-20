"""
Fork of OpenInterpreter tools/browser.py
Uses Playwright (async or sync) for full browser control.
"""
from __future__ import annotations

import base64
from typing import Optional

try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class BrowserTool:
    """
    Synchronous Playwright wrapper.
    Supports: navigate, click, type, screenshot, extract_text, execute_js.
    """

    def __init__(self, headless: bool = False, safe_mode: str = "ask"):
        self._pw = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self.headless = headless
        self.safe_mode = safe_mode

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> None:
        self._require_playwright()
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        self._page = self._context.new_page()

    def close(self) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._page = None
        self._context = None
        self._browser = None
        self._pw = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.close()

    # ── Navigation ────────────────────────────────────────────────────────

    def goto(self, url: str, wait_until: str = "domcontentloaded") -> None:
        self._ensure_page()
        self._page.goto(url, wait_until=wait_until, timeout=30_000)

    def reload(self) -> None:
        self._ensure_page()
        self._page.reload()

    def back(self) -> None:
        self._ensure_page()
        self._page.go_back()

    def current_url(self) -> str:
        return self._page.url if self._page else ""

    # ── Interaction ───────────────────────────────────────────────────────

    def click(self, selector: str, timeout: int = 10_000) -> None:
        self._ensure_page()
        self._page.click(selector, timeout=timeout)

    def fill(self, selector: str, text: str) -> None:
        self._ensure_page()
        self._page.fill(selector, text)

    def press(self, selector: str, key: str) -> None:
        self._ensure_page()
        self._page.press(selector, key)

    def select(self, selector: str, value: str) -> None:
        self._ensure_page()
        self._page.select_option(selector, value)

    def hover(self, selector: str) -> None:
        self._ensure_page()
        self._page.hover(selector)

    # ── Content extraction ────────────────────────────────────────────────

    def text(self, selector: str = "body") -> str:
        self._ensure_page()
        return self._page.inner_text(selector)

    def html(self, selector: str = "html") -> str:
        self._ensure_page()
        return self._page.inner_html(selector)

    def title(self) -> str:
        self._ensure_page()
        return self._page.title()

    def execute_js(self, script: str):
        self._ensure_page()
        return self._page.evaluate(script)

    # ── Screenshot ────────────────────────────────────────────────────────

    def screenshot(self, full_page: bool = False) -> bytes:
        self._ensure_page()
        return self._page.screenshot(full_page=full_page)

    def screenshot_b64(self, full_page: bool = False) -> str:
        return base64.b64encode(self.screenshot(full_page=full_page)).decode()

    def screenshot_and_describe(self, router, full_page: bool = False) -> str:
        b64 = self.screenshot_b64(full_page=full_page)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text", "text": f"What is shown on this webpage? URL: {self.current_url()}. Describe interactive elements."},
                ],
            }
        ]
        return router.complete(messages, has_images=True)

    # ── Waiting ───────────────────────────────────────────────────────────

    def wait_for(self, selector: str, timeout: int = 10_000) -> None:
        self._ensure_page()
        self._page.wait_for_selector(selector, timeout=timeout)

    def wait_for_url(self, url_pattern: str, timeout: int = 15_000) -> None:
        self._ensure_page()
        self._page.wait_for_url(url_pattern, timeout=timeout)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _require_playwright(self):
        if not HAS_PLAYWRIGHT:
            raise RuntimeError(
                "playwright not installed. Run: pip install playwright && playwright install chromium"
            )

    def _ensure_page(self):
        if self._page is None:
            self.start()
