"""
Floating overlay window — appears on Ctrl+Space, disappears after response.
Uses only tkinter (stdlib) so no extra deps for the UI.
"""
from __future__ import annotations

import threading
import tkinter as tk


_BG       = "#0f0f0f"
_BG2      = "#1a1a1a"
_ACCENT   = "#0f62fe"
_TEXT     = "#f4f4f4"
_SUBTEXT  = "#8d8d8d"
_RADIUS   = 12
_WIDTH    = 640
_MAX_H    = 480


class OverlayWindow:
    """
    Floating input + response window.
    Thread-safe: show() can be called from any thread.
    """

    def __init__(self):
        self._root: tk.Tk | None = None
        self._lock = threading.Lock()
        self._relay = _build_relay()

    def show(self):
        """Show or bring-to-front the overlay."""
        if self._root and self._root.winfo_exists():
            self._root.after(0, self._focus)
            return
        threading.Thread(target=self._launch, daemon=True).start()

    def _launch(self):
        root = tk.Tk()
        self._root = root

        root.title("")
        root.configure(bg=_BG)
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.97)

        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - _WIDTH) // 2
        y = int(sh * 0.28)
        root.geometry(f"{_WIDTH}x80+{x}+{y}")

        frame = tk.Frame(root, bg=_BG, padx=16, pady=12)
        frame.pack(fill="x")

        label = tk.Label(frame, text="pill.ai", bg=_BG, fg=_ACCENT,
                         font=("Segoe UI", 11, "bold"))
        label.pack(side="left", padx=(0, 10))

        entry_var = tk.StringVar()
        entry = tk.Entry(frame, textvariable=entry_var, bg=_BG2, fg=_TEXT,
                         insertbackground=_TEXT, relief="flat",
                         font=("Segoe UI", 13), bd=0)
        entry.pack(side="left", fill="x", expand=True, ipady=6)
        entry.focus_set()

        status = tk.Label(frame, text="", bg=_BG, fg=_SUBTEXT,
                          font=("Segoe UI", 9))
        status.pack(side="right", padx=(8, 0))

        resp_frame = tk.Frame(root, bg=_BG)

        resp_text = tk.Text(resp_frame, bg=_BG2, fg=_TEXT, relief="flat",
                            font=("Segoe UI", 11), wrap="word",
                            padx=12, pady=10, bd=0,
                            state="disabled", cursor="arrow")
        resp_text.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        def _submit(event=None):
            query = entry_var.get().strip()
            if not query:
                return
            entry.config(state="disabled")
            status.config(text="pensando…")
            _show_response("")
            threading.Thread(target=_call_relay, args=(query,), daemon=True).start()

        def _close(event=None):
            root.destroy()
            self._root = None

        entry.bind("<Return>", _submit)
        entry.bind("<Escape>", _close)
        root.bind("<Escape>", _close)

        def _start_drag(e): root._drag_x, root._drag_y = e.x, e.y
        def _drag(e):
            dx, dy = e.x - root._drag_x, e.y - root._drag_y
            nx = root.winfo_x() + dx
            ny = root.winfo_y() + dy
            root.geometry(f"+{nx}+{ny}")
        frame.bind("<Button-1>", _start_drag)
        frame.bind("<B1-Motion>", _drag)
        label.bind("<Button-1>", _start_drag)
        label.bind("<B1-Motion>", _drag)

        def _show_response(text: str):
            if not text:
                resp_frame.pack_forget()
                root.geometry(f"{_WIDTH}x80+{x}+{y}")
                return
            resp_text.config(state="normal")
            resp_text.delete("1.0", "end")
            resp_text.insert("end", text)
            resp_text.config(state="disabled")
            lines = text.count("\n") + 1
            h = min(80 + 24 * lines + 24, _MAX_H)
            root.geometry(f"{_WIDTH}x{h}+{x}+{y}")
            resp_frame.pack(fill="both", expand=True)

        def _call_relay(query: str):
            try:
                result = self._relay(query)
                root.after(0, lambda: _on_done(result))
            except Exception as exc:
                msg = f"Error: {exc}"
                root.after(0, lambda: _on_done(msg))

        def _on_done(result: str):
            entry.config(state="normal")
            status.config(text="")
            _show_response(result)

        root.mainloop()

    def _focus(self):
        if self._root:
            self._root.lift()
            self._root.focus_force()


def _build_relay():
    """Return a callable(query) → str that calls the relay server."""
    try:
        from interpreter.relay_router import RelayRouter, RELAY_URL
        from interpreter._hw_id import get_hw_id
    except ImportError:
        def _no_relay(query):
            return "[pill.ai] relay no configurado — falta PILLAI_RELAY_URL"
        return _no_relay

    if not RELAY_URL:
        def _no_url(query):
            return "[pill.ai] PILLAI_RELAY_URL no está configurado"
        return _no_url

    router = RelayRouter(relay_url=RELAY_URL, license_key="FREE", hw_id=get_hw_id())

    def _call(query: str) -> str:
        messages = [{"role": "user", "content": query}]
        return router.complete(messages, task_hint=query)

    return _call
