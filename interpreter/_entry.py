"""
Entry point para el .exe de PyInstaller.
Arranca en modo bandeja por defecto (sin importar litellm).
"""
import os
import sys

# Evita que litellm crashee si el JSON de precios no está en el bundle
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "1")


def main():
    from interpreter.relay_router import is_relay_mode
    # Modo bandeja: cuando hay relay URL y no se pasó --cli ni un task directo
    if is_relay_mode() and len(sys.argv) == 1:
        from pill_ai.tray import run_tray
        run_tray()
    else:
        from pill_ai.cli import main as cli_main
        cli_main()


if __name__ == "__main__":
    main()
