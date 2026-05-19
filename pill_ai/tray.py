"""
System tray app for pill.ai.
Runs in background, registers Ctrl+Space hotkey, opens overlay on demand.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path


def _make_icon():
    """Generate a simple tray icon programmatically — no external image needed."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (15, 98, 254, 255))   # pill.ai blue
    d = ImageDraw.Draw(img)
    # White rounded rectangle to suggest a pill shape
    d.rounded_rectangle([8, 20, 56, 44], radius=12, fill=(255, 255, 255, 255))
    # Blue "p" in center
    d.text((23, 21), "p", fill=(15, 98, 254, 255))
    return img


def run_tray():
    """Start the system tray icon and global hotkey. Blocks until exit."""
    try:
        import pystray
        import keyboard
    except ImportError:
        print("[pill.ai] pystray / keyboard not installed — running in CLI mode")
        from .cli import _run_interactive
        _run_interactive()
        return

    from .overlay import OverlayWindow

    overlay = OverlayWindow()

    def _show_overlay():
        overlay.show()

    def _open_chat(icon, item):
        overlay.show()

    def _exit(icon, item):
        keyboard.unhook_all_hotkeys()
        icon.stop()
        sys.exit(0)

    # Global hotkey — works in any app (Excel, Chrome, Word, etc.)
    keyboard.add_hotkey("ctrl+space", _show_overlay, suppress=False)

    menu = pystray.Menu(
        pystray.MenuItem("Abrir pill.ai  (Ctrl+Space)", _open_chat, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Salir", _exit),
    )

    icon = pystray.Icon(
        name="pill.ai",
        icon=_make_icon(),
        title="pill.ai — Ctrl+Space para abrir",
        menu=menu,
    )

    print("[pill.ai] Corriendo en la bandeja del sistema. Usa Ctrl+Space para abrir.")
    icon.run()
