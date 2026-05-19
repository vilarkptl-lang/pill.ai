"""
Build the pill.ai .exe / binary with PyInstaller.

Usage:
    # Windows .exe (run from Windows or cross-compile)
    PILLAI_RELAY_URL=https://your-server.com python installers/build_exe.py

    # Or via Makefile:
    PILLAI_RELAY_URL=https://your-server.com make exe

The relay URL is baked into the binary — users never configure it.
Output: dist/pillai.exe (Windows) or dist/pillai (Linux/Mac)
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

def main():
    # Verificar versión de Python — 3.14 no es compatible con pydantic/litellm
    if sys.version_info >= (3, 14):
        print("ERROR: Python 3.14+ no es compatible. Usa Python 3.12 o 3.11.")
        print("  Descarga: https://www.python.org/downloads/release/python-3128/")
        sys.exit(1)

    relay_url = os.getenv("PILLAI_RELAY_URL", "").strip()
    if not relay_url:
        print("ERROR: set PILLAI_RELAY_URL before building")
        print("  Example: set PILLAI_RELAY_URL=http://tu-ip:8181 && python installers/build_exe.py")
        sys.exit(1)

    # Escribir URL en dos formatos para máxima compatibilidad con PyInstaller
    config_py  = ROOT / "interpreter" / "_relay_config.py"
    config_txt = ROOT / "interpreter" / "_relay_url.txt"
    config_py.write_text(f'RELAY_URL = "{relay_url}"\n')
    config_txt.write_text(relay_url)
    print(f"[build] Relay URL baked: {relay_url}")

    # Incluir el JSON de precios de litellm (PyInstaller no lo detecta solo)
    import litellm as _litellm
    litellm_dir = Path(_litellm.__file__).parent
    litellm_json = litellm_dir / "model_prices_and_context_window_backup.json"

    sep = ";" if sys.platform == "win32" else ":"

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "pillai",
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--specpath", str(ROOT / "installers"),
        # Entry point
        str(ROOT / "interpreter" / "_entry.py"),
        # Datos que PyInstaller no incluye automáticamente
        "--add-data", f"{litellm_json}{sep}litellm",
        "--add-data", f"{ROOT / 'interpreter' / '_relay_url.txt'}{sep}interpreter",
        # Hidden imports
        "--hidden-import", "litellm",
        "--hidden-import", "litellm.utils",
        "--hidden-import", "litellm.main",
        "--hidden-import", "litellm.litellm_core_utils",
        "--hidden-import", "pydantic",
        "--hidden-import", "rich",
        "--hidden-import", "httpx",
        "--hidden-import", "tkinter",
        "--hidden-import", "pystray",
        "--hidden-import", "keyboard",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "PIL.ImageDraw",
        "--hidden-import", "licensing.activation",
        "--hidden-import", "licensing.models",
        "--hidden-import", "interpreter.relay_router",
        "--hidden-import", "interpreter._relay_config",
        "--hidden-import", "interpreter._hw_id",
        "--hidden-import", "pill_ai.tray",
        "--hidden-import", "pill_ai.overlay",
        "--clean",
        "--noconfirm",
    ]

    print(f"[build] Running PyInstaller...")
    result = subprocess.run(cmd, cwd=ROOT)

    if result.returncode == 0:
        out = ROOT / "dist" / ("pillai.exe" if sys.platform == "win32" else "pillai")
        print(f"\n[build] SUCCESS: {out}")
        print(f"[build] Distribute this file — no Python or API keys needed on the user's PC.")
    else:
        print("\n[build] FAILED — check output above")
        # Clean up baked config on failure
        config_path.unlink(missing_ok=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
