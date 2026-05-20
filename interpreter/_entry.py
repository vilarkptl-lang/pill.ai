"""
Entry point para el .exe de PyInstaller.
Arranca en modo bandeja por defecto (sin importar litellm).
"""
import os
import sys

# Evita que litellm crashee si el JSON de precios no está en el bundle
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "1")


def _check_for_updates() -> None:
    """Non-blocking update check — runs in background, prints if new version found."""
    import threading

    def _check():
        try:
            import httpx
            from interpreter._version import VERSION
            from interpreter.relay_router import RELAY_URL
            if not RELAY_URL:
                return
            data = httpx.get(f"{RELAY_URL}/version", timeout=5).json()
            latest = data.get("version", "")
            if latest and latest != VERSION:
                key = "win" if sys.platform == "win32" else ("mac" if sys.platform == "darwin" else "linux")
                url = data.get("download_url", {}).get(key, "")
                print(
                    f"\n[pill.ai] Nueva versión disponible: {latest}  (tienes {VERSION})\n"
                    f"  Descarga: {url}\n"
                )
        except Exception:
            pass  # never crash on update check

    threading.Thread(target=_check, daemon=True).start()


def main():
    from interpreter.relay_router import is_relay_mode
    _check_for_updates()
    # Modo bandeja: cuando hay relay URL y no se pasó --cli ni un task directo
    if is_relay_mode() and len(sys.argv) == 1:
        from pill_ai.tray import run_tray
        run_tray()
    else:
        from pill_ai.cli import main as cli_main
        cli_main()


if __name__ == "__main__":
    main()
