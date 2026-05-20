"""
Local command execution for the pill.ai overlay.

Detects intent from the user query, runs the appropriate local command,
and returns a context string that gets sent to the relay alongside the query.
The relay then interprets the results and responds naturally.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


# ── Intent detection ────────────────────────────────────────────────────

_FILE_SEARCH_KEYWORDS = {
    "busca", "encuentra", "encontrar", "buscar", "archivos", "documentos",
    "files", "find", "search", "documents", "carpeta", "folder",
    "relacionados", "nombre", "llamado", "llamados",
}

_SYSINFO_KEYWORDS = {
    "hora", "fecha", "time", "date", "sistema", "system", "cpu", "memoria",
    "memory", "ram", "disco", "disk", "espacio", "space", "procesador",
    "processor", "version", "windows", "ip", "red", "network",
}

_PROCESS_KEYWORDS = {
    "proceso", "procesos", "process", "processes", "corriendo", "running",
    "abierto", "abiertos", "open", "apps", "aplicaciones",
}

_ABLETON_KEYWORDS = {
    "ableton", "live", "daw", "proyecto", "project", ".als", "pista", "track",
    "tempo", "bpm", "plugin", "vst", "midi", "session", "clip", "mix",
}


def detect_intent(query: str) -> str | None:
    words = set(query.lower().split())
    if words & _ABLETON_KEYWORDS:
        return "ableton"
    if words & _FILE_SEARCH_KEYWORDS:
        return "file_search"
    if words & _SYSINFO_KEYWORDS:
        return "system_info"
    if words & _PROCESS_KEYWORDS:
        return "processes"
    return None


def active_window() -> str:
    """Return the name of the currently focused window/app. (1.27)"""
    try:
        if sys.platform == "win32":
            import ctypes
            hwnd   = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf    = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value
        elif sys.platform == "darwin":
            script = (
                'tell application "System Events" to name of first '
                'application process whose frontmost is true'
            )
            return subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=3,
            ).stdout.strip()
        else:
            return subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=3,
            ).stdout.strip()
    except Exception:
        return ""


# ── Executors ────────────────────────────────────────────────────────────

def execute(query: str, intent: str) -> str:
    try:
        if intent == "ableton":
            return _ableton_context()
        if intent == "file_search":
            return _file_search(query)
        if intent == "system_info":
            return _system_info()
        if intent == "processes":
            return _running_processes()
    except Exception as e:
        return f"[error ejecutando comando local: {e}]"
    return ""


def _file_search(query: str) -> str:
    """Search for files/folders matching terms extracted from the query."""
    stopwords = {
        "busca", "encuentra", "encontrar", "buscar", "todos", "todas",
        "los", "las", "con", "para", "que", "del", "relacionados",
        "documentos", "archivos", "nombre", "esta", "computadora",
        "existentes", "find", "all", "files", "documents", "related",
        "the", "for", "with",
    }
    words = [w for w in query.split() if len(w) > 3 and w.lower() not in stopwords]
    if not words:
        return "[no se pudo extraer término de búsqueda]"

    search_term = " ".join(words[:4])

    home = Path.home()
    search_dirs = [
        home / "Documents",
        home / "Desktop",
        home / "Downloads",
        home,
    ]

    results = []
    seen = set()

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        try:
            for word in words[:4]:
                for path in search_dir.rglob(f"*{word}*"):
                    if str(path) not in seen and len(results) < 50:
                        seen.add(str(path))
                        size = ""
                        try:
                            if path.is_file():
                                size = f" ({path.stat().st_size // 1024} KB)"
                        except OSError:
                            pass
                        results.append(f"  {path}{size}")
        except (PermissionError, OSError):
            continue

    if not results and sys.platform == "win32":
        try:
            for word in words[:2]:
                cmd = f'dir /s /b /a "%USERPROFILE%" 2>nul | findstr /i "{word}"'
                out = subprocess.run(cmd, shell=True, capture_output=True,
                                     text=True, timeout=15).stdout
                for line in out.splitlines()[:30]:
                    if line.strip() and line not in seen:
                        seen.add(line)
                        results.append(f"  {line.strip()}")
        except Exception:
            pass

    if not results:
        return f"No se encontraron archivos relacionados con: {search_term}"

    header = f"Archivos encontrados para '{search_term}' ({len(results)} resultados):"
    return header + "\n" + "\n".join(results[:40])


def _system_info() -> str:
    import platform
    import shutil
    import datetime

    info = [
        f"Sistema: {platform.system()} {platform.release()} {platform.version()}",
        f"Máquina: {platform.machine()} — {platform.processor()}",
        f"Python: {platform.python_version()}",
    ]

    try:
        usage = shutil.disk_usage(Path.home())
        info.append(f"Disco: {usage.free / 1e9:.1f} GB libres de {usage.total / 1e9:.1f} GB")
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            out = subprocess.run(
                "wmic OS get TotalVisibleMemorySize,FreePhysicalMemory /value",
                shell=True, capture_output=True, text=True, timeout=5
            ).stdout
            for line in out.splitlines():
                if "TotalVisible" in line:
                    info.append(f"RAM total: {int(line.split('=')[1].strip()) // 1024} MB")
                elif "FreePhysical" in line:
                    info.append(f"RAM libre: {int(line.split('=')[1].strip()) // 1024} MB")
        except Exception:
            pass

    info.append(f"Fecha/hora: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return "\n".join(info)


def _running_processes() -> str:
    if sys.platform == "win32":
        try:
            out = subprocess.run(
                "tasklist /fo csv /nh", shell=True,
                capture_output=True, text=True, timeout=10
            ).stdout
            procs = []
            for line in out.splitlines()[:40]:
                parts = line.strip('"').split('","')
                if parts:
                    procs.append(parts[0])
            return "Procesos activos:\n" + "\n".join(f"  {p}" for p in procs)
        except Exception as e:
            return f"[error listando procesos: {e}]"
    else:
        try:
            out = subprocess.run(
                ["ps", "aux", "--no-headers"],
                capture_output=True, text=True, timeout=10
            ).stdout
            lines = out.splitlines()[:30]
            return "Procesos activos:\n" + "\n".join(
                f"  {l.split()[10]}" for l in lines if len(l.split()) > 10
            )
        except Exception as e:
            return f"[error listando procesos: {e}]"


def _ableton_context() -> str:  # (1.26)
    """Detect Ableton running + find recent .als project files."""
    import datetime

    ableton_running = False
    try:
        if sys.platform == "win32":
            out = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=5).stdout
            ableton_running = "ableton" in out.lower()
        else:
            out = subprocess.run(["pgrep", "-i", "ableton"], capture_output=True, text=True, timeout=3).stdout
            ableton_running = bool(out.strip())
    except Exception:
        pass

    search_dirs = [Path.home() / "Music", Path.home() / "Documents", Path.home()]
    als_files: list[Path] = []
    for d in search_dirs:
        if not d.exists():
            continue
        try:
            for p in d.rglob("*.als"):
                als_files.append(p)
                if len(als_files) >= 30:
                    break
        except (PermissionError, OSError):
            continue

    als_files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)

    result = ["Estado: Ableton Live está corriendo" if ableton_running
              else "Estado: Ableton Live no está corriendo"]

    if als_files:
        result.append(f"\nProyectos .als recientes ({len(als_files)} total):")
        for p in als_files[:8]:
            try:
                mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d")
                result.append(f"  {p.name}  ({mtime})  →  {p.parent}")
            except OSError:
                result.append(f"  {p.name}")
    else:
        result.append("No se encontraron archivos .als")

    return "\n".join(result)
