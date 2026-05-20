"""pill.ai Orb — local Python backend for the Tauri frontend.

Runs a FastAPI server on localhost:7842 that:
  1. Detects intent in the user's query (file search, sysinfo, processes)
  2. Runs local commands to gather context
  3. Forwards everything to the relay at PILLAI_RELAY_URL
  4. Returns the assistant's reply as {"content": "..."}

Start modes:
  python -m pill_ai.orb          # server only
  pillai orb                     # server + Tauri binary
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path


def _build_app():
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from pydantic import BaseModel
    except ImportError:
        print("[pill.ai orb] Install: pip install fastapi uvicorn")
        sys.exit(1)

    app = FastAPI(title="pill.ai Orb backend", docs_url=None, redoc_url=None)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "tauri://localhost",
            "http://localhost:1420",
            "http://127.0.0.1:1420",
        ],
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )

    class ChatRequest(BaseModel):
        message: str
        session_id: str = "default"

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "pill.ai-orb"}

    @app.post("/chat")
    def chat(req: ChatRequest):
        from pill_ai.local_exec import detect_intent, execute
        from interpreter.relay_router import RelayRouter, RELAY_URL
        from interpreter._hw_id import get_hw_id

        if not RELAY_URL:
            return {"content": "[pill.ai] PILLAI_RELAY_URL no configurado"}

        intent = detect_intent(req.message)
        local_ctx = execute(req.message, intent) if intent else ""

        messages = []
        if local_ctx:
            messages.append({
                "role": "system",
                "content": (
                    "Eres un asistente de computadora. Contexto local:\n\n"
                    f"{local_ctx}\n\nResponde de forma concisa y útil."
                ),
            })
        messages.append({"role": "user", "content": req.message})

        try:
            router = RelayRouter(relay_url=RELAY_URL, license_key="FREE", hw_id=get_hw_id())
            result = router.complete(messages, task_hint=req.message)
            return {"content": result}
        except Exception as exc:
            return {"content": f"Error: {exc}"}

    return app


def start_server(port: int = 7842, log: bool = True) -> None:
    try:
        import uvicorn
    except ImportError:
        print("[pill.ai orb] Install: pip install uvicorn")
        sys.exit(1)

    app = _build_app()
    if log:
        print(f"[pill.ai orb] Backend en http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")


def start_server_background(port: int = 7842) -> threading.Thread:
    t = threading.Thread(
        target=start_server, kwargs={"port": port, "log": False}, daemon=True
    )
    t.start()
    time.sleep(1.4)
    return t


def launch_tauri() -> None:
    import os, subprocess
    candidates = [
        Path(__file__).parent.parent / "orb" / "src-tauri" / "target" / "release" / "pill-ai-orb",
        Path(__file__).parent.parent / "orb" / "src-tauri" / "target" / "release" / "pill-ai-orb.exe",
    ]
    binary = next((p for p in candidates if p.exists()), None)
    if binary is None:
        print("[pill.ai orb] Binario Tauri no encontrado.")
        print("[pill.ai orb] Compila con: cd orb && npm run tauri build")
        print("[pill.ai orb] Para dev:    cd orb && npm run tauri dev")
        sys.exit(1)
    subprocess.run([str(binary)], env=os.environ)


if __name__ == "__main__":
    start_server()
