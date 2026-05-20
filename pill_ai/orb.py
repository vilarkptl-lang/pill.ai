"""
pill.ai Orb — local Python backend for the Tauri frontend.

Runs a FastAPI server on localhost:7842 that:
  1. Detects intent in the user's query (file search, sysinfo, processes)
  2. Runs local commands to gather context
  3. Forwards everything to the relay at PILLAI_RELAY_URL
  4. Returns the assistant's reply as {"content": "..."}

Start modes:
  python -m pill_ai.orb          # server only (for dev alongside `tauri dev`)
  pillai orb                     # server + Tauri binary (production)
"""
from __future__ import annotations

import sys
import threading
import time


# ── FastAPI app ──────────────────────────────────────────────────────────────

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
        from interpreter.relay_router import RelayRouter, RELAY_URL
        from interpreter._hw_id import get_hw_id
        from interpreter import memory
        from interpreter.context_injector import ContextInjector
        from pill_ai.local_exec import detect_intent, execute, active_window
        from pill_ai.skills_recorder import detect_remember_intent, record_skill
        from interpreter.scheduler import detect_schedule_intent, add_cron, add_trigger
        from pathlib import Path

        if not RELAY_URL:
            return {"content": "[pill.ai] PILLAI_RELAY_URL no configurado"}

        router = RelayRouter(relay_url=RELAY_URL, license_key="FREE", hw_id=get_hw_id())
        sid    = req.session_id

        # Skill recording intent (1.29)
        if detect_remember_intent(req.message):
            history    = memory.load(sid)
            skill_name = record_skill(history, req.message, router)
            return {"content": f"Skill guardada: «{skill_name}»"}

        # Persist user message (1.24)
        memory.append(sid, "user", req.message)

        # Local context: Ableton (1.26) + active window (1.27)
        intent    = detect_intent(req.message)
        local_ctx = execute(req.message, intent) if intent else ""
        win       = active_window()
        if win and win not in local_ctx:
            local_ctx = f"Ventana activa: {win}\n{local_ctx}".strip()

        # Context injection: skills + compact history (1.25 + 1.28)
        injector = ContextInjector(
            skills_path=Path.home() / ".pill.ai" / "skills.md",
            router=router,
        )
        history  = memory.compact_if_needed(sid, router)
        messages = injector.inject(history, req.message)

        if local_ctx:
            messages.insert(-1, {
                "role": "system",
                "content": (
                    "Contexto local de la PC del usuario:\n\n"
                    f"{local_ctx}\n\nResponde de forma concisa y útil."
                ),
            })

        # Ensure user message is last
        if not messages or messages[-1].get("content") != req.message:
            messages.append({"role": "user", "content": req.message})

        try:
            result = router.complete(messages, task_hint=req.message)
        except Exception as exc:
            return {"content": f"Error: {exc}"}

        # Persist response (1.24)
        memory.append(sid, "assistant", result)

        # Cron / trigger scheduling (1.30)
        sched = detect_schedule_intent(req.message)
        if sched:
            try:
                skill_name = record_skill(memory.load(sid), req.message, router)
                if sched["type"] == "cron":
                    add_cron(skill_name, sched["expression"], req.message)
                else:
                    add_trigger(skill_name, sched["process"], req.message)
            except Exception:
                pass

        return {"content": result}

    return app


# ── Entry points ─────────────────────────────────────────────────────────────

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
    """Start the server in a daemon thread and return after it is bound."""
    t = threading.Thread(
        target=start_server, kwargs={"port": port, "log": False}, daemon=True
    )
    t.start()
    time.sleep(1.4)  # give uvicorn time to bind
    return t


def launch_tauri() -> None:
    """Spawn the compiled Tauri binary (orb/src-tauri/target/release/pill-ai-orb)."""
    import os
    import subprocess
    from pathlib import Path

    candidates = [
        Path(__file__).parent.parent / "orb" / "src-tauri" / "target" / "release" / "pill-ai-orb",
        Path(__file__).parent.parent / "orb" / "src-tauri" / "target" / "release" / "pill-ai-orb.exe",
    ]
    binary = next((p for p in candidates if p.exists()), None)

    if binary is None:
        print("[pill.ai orb] Tauri binary not found — run: cd orb && npm run tauri build")
        print("[pill.ai orb] For dev mode run: cd orb && npm run tauri dev")
        sys.exit(1)

    subprocess.run([str(binary)], env=os.environ)


if __name__ == "__main__":
    start_server()
