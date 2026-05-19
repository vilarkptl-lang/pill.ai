"""Run this on Windows to fix overlay.py and build_exe.py before rebuilding."""
import pathlib

ROOT = pathlib.Path(__file__).parent

# Fix 1: overlay.py
overlay = ROOT / "pill_ai" / "overlay.py"
src = overlay.read_text(encoding="utf-8")
old = 'except Exception as e:\n                root.after(0, lambda: _on_done(f"Error: {e}"))'
new = 'except Exception as exc:\n                msg = f"Error: {exc}"\n                root.after(0, lambda: _on_done(msg))'
if old in src:
    overlay.write_text(src.replace(old, new), encoding="utf-8")
    print("[OK] overlay.py fixed")
elif 'except Exception as exc:' in src and 'msg = f"Error: {exc}"' in src:
    print("[OK] overlay.py already correct")
else:
    print("[WARN] overlay.py: pattern not found")
    print("  Looking for:", repr(old[:60]))

# Fix 2: build_exe.py
build = ROOT / "installers" / "build_exe.py"
src2 = build.read_text(encoding="utf-8")
old2 = "config_path.unlink(missing_ok=True)"
new2 = "config_py.unlink(missing_ok=True)\n        config_txt.unlink(missing_ok=True)"
if old2 in src2:
    build.write_text(src2.replace(old2, new2), encoding="utf-8")
    print("[OK] build_exe.py fixed")
elif "config_py.unlink" in src2 and "config_txt.unlink" in src2:
    print("[OK] build_exe.py already correct")
else:
    print("[WARN] build_exe.py: pattern not found")
