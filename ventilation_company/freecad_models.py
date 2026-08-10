"""Модуль для інтеграції 3D-моделей з FreeCAD.

Покращення:
  • Кешування шляху до FreeCAD у файлі налаштувань
  • Вбудований 3D-перегляд через matplotlib (без FreeCAD)
  • Прогрес експорту
  • Перевірка версії FreeCAD
  • Підтримка додаткових форматів (OBJ, IGES)
  • Пакетний експорт
"""

import json
import os
import subprocess
import tempfile
import platform
import shutil
import sys
from typing import List, Any, Optional, Callable

# ── Імпорт прев'ю ──
try:
    from ventilation_company.freecad_preview import FreeCADPreview, show_preview_dialog
    PREVIEW_AVAILABLE = True
except ImportError:
    PREVIEW_AVAILABLE = False

# ── Конфіг кешування ──
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".ventcompany")
CONFIG_FILE = os.path.join(CONFIG_DIR, "freecad_config.json")

FREECAD_AVAILABLE = False
FREECAD_CMD = None
FREECAD_GUI = None
FREECAD_VERSION = None

_log_lines = []

def _log(msg):
    _log_lines.append(str(msg))


# ── Шляхи до FreeCAD ──
_freecad_cmd_paths = [
    r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe",
    r"C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe",
    r"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe",
    r"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe",
    r"C:\Program Files\FreeCAD 0.21\bin\freecadcmd.exe",
    r"C:\Program Files\FreeCAD 0.21\bin\FreeCADCmd.exe",
    r"C:\Program Files\FreeCAD\bin\freecadcmd.exe",
    r"C:\Program Files\FreeCAD\bin\FreeCADCmd.exe",
    r"C:\Program Files (x86)\FreeCAD 1.1\bin\freecadcmd.exe",
    r"C:\Program Files (x86)\FreeCAD 1.1\bin\FreeCADCmd.exe",
    "/usr/bin/freecadcmd",
    "/usr/bin/freecadcmd-daily",
    "/usr/local/bin/freecadcmd",
    "/Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd",
]

_freecad_gui_paths = [
    r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe",
    r"C:\Program Files\FreeCAD 1.1\bin\FreeCAD.exe",
    r"C:\Program Files\FreeCAD 1.0\bin\freecad.exe",
    r"C:\Program Files\FreeCAD 1.0\bin\FreeCAD.exe",
    r"C:\Program Files\FreeCAD 0.21\bin\freecad.exe",
    r"C:\Program Files\FreeCAD 0.21\bin\FreeCAD.exe",
    r"C:\Program Files\FreeCAD\bin\freecad.exe",
    r"C:\Program Files\FreeCAD\bin\FreeCAD.exe",
    r"C:\Program Files (x86)\FreeCAD 1.1\bin\freecad.exe",
    r"C:\Program Files (x86)\FreeCAD 1.1\bin\FreeCAD.exe",
    "/usr/bin/freecad",
    "/usr/bin/freecad-daily",
    "/usr/local/bin/freecad",
    "/Applications/FreeCAD.app/Contents/MacOS/FreeCAD",
]


def _load_cached_config() -> dict:
    """Load cached FreeCAD path from config file."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        _log(f"Config load error: {e}")
    return {}


def _save_cached_config(config: dict):
    """Save FreeCAD path to config file."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        _log(f"Config save error: {e}")


def _get_freecad_version(cmd_path: str) -> Optional[str]:
    """Try to get FreeCAD version string."""
    try:
        result = subprocess.run(
            [cmd_path, "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
    except Exception:
        pass
    try:
        result = subprocess.run(
            [cmd_path, "-c", "import FreeCAD; print(FreeCAD.Version())"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _find_freecad():
    """Find FreeCAD with diagnostics and caching."""
    global FREECAD_AVAILABLE, FREECAD_CMD, FREECAD_GUI, FREECAD_VERSION

    _log("=== FreeCAD search started ===")
    _log(f"Platform: {platform.system()}")
    _log(f"Python: {sys.executable}")

    # 1. Check cached config first
    cached = _load_cached_config()
    if cached.get("cmd") and os.path.exists(cached["cmd"]):
        FREECAD_CMD = cached["cmd"]
        FREECAD_GUI = cached.get("gui")
        FREECAD_AVAILABLE = True
        FREECAD_VERSION = cached.get("version")
        _log(f"Using cached path: {FREECAD_CMD}")

    # 2. If not cached, search
    if not FREECAD_AVAILABLE:
        # Fixed paths
        for p in _freecad_cmd_paths:
            if os.path.exists(p):
                FREECAD_CMD = p
                FREECAD_AVAILABLE = True
                break

        for p in _freecad_gui_paths:
            if os.path.exists(p):
                FREECAD_GUI = p
                break

        # PATH search
        if not FREECAD_CMD:
            for cmd in ["freecadcmd", "FreeCADCmd", "freecadcmd-daily"]:
                p = shutil.which(cmd)
                if p and os.path.exists(p):
                    FREECAD_CMD = p
                    FREECAD_AVAILABLE = True
                    break

        if not FREECAD_GUI:
            for cmd in ["freecad", "FreeCAD", "freecad-daily"]:
                p = shutil.which(cmd)
                if p and os.path.exists(p):
                    FREECAD_GUI = p
                    break

        # Windows where search
        if platform.system() == "Windows":
            if not FREECAD_CMD:
                for cmd in ["freecadcmd.exe", "FreeCADCmd.exe"]:
                    try:
                        result = subprocess.run(
                            ["where", cmd], capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            for line in result.stdout.strip().split("\n"):
                                p = line.strip()
                                if "freecad" in p.lower() and os.path.exists(p):
                                    FREECAD_CMD = p
                                    FREECAD_AVAILABLE = True
                                    break
                    except Exception as e:
                        _log(f"where error: {e}")

            if not FREECAD_GUI:
                for cmd in ["freecad.exe", "FreeCAD.exe"]:
                    try:
                        result = subprocess.run(
                            ["where", cmd], capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            for line in result.stdout.strip().split("\n"):
                                p = line.strip()
                                if "freecad" in p.lower() and os.path.exists(p):
                                    FREECAD_GUI = p
                                    break
                    except Exception:
                        pass

        # Windows listdir fallback
        if platform.system() == "Windows" and not FREECAD_AVAILABLE:
            for base_dir in [r"C:\Program Files", r"C:\Program Files (x86)"]:
                try:
                    if os.path.isdir(base_dir):
                        for entry in os.listdir(base_dir):
                            if "freecad" in entry.lower():
                                bin_dir = os.path.join(base_dir, entry, "bin")
                                if os.path.isdir(bin_dir):
                                    for exe in ["freecadcmd.exe", "FreeCADCmd.exe"]:
                                        p = os.path.join(bin_dir, exe)
                                        if os.path.exists(p):
                                            FREECAD_CMD = p
                                            FREECAD_AVAILABLE = True
                                            break
                                    for exe in ["freecad.exe", "FreeCAD.exe"]:
                                        p = os.path.join(bin_dir, exe)
                                        if os.path.exists(p):
                                            FREECAD_GUI = p
                                            break
                                if FREECAD_AVAILABLE:
                                    break
                except Exception:
                    pass
                if FREECAD_AVAILABLE:
                    break

        # Fallback: use GUI as CMD
        if not FREECAD_CMD and FREECAD_GUI:
            FREECAD_CMD = FREECAD_GUI
            FREECAD_AVAILABLE = True
            _log(f"Using GUI as CMD: {FREECAD_CMD}")

    # 3. Get version and cache
    if FREECAD_AVAILABLE and FREECAD_CMD:
        FREECAD_VERSION = _get_freecad_version(FREECAD_CMD)
        _save_cached_config({
            "cmd": FREECAD_CMD,
            "gui": FREECAD_GUI,
            "version": FREECAD_VERSION,
            "found_at": str(datetime.now()) if 'datetime' in dir() else "unknown"
        })

    _log(f"=== Result: AVAILABLE={FREECAD_AVAILABLE}, CMD={FREECAD_CMD}, GUI={FREECAD_GUI}, VER={FREECAD_VERSION} ===")

    # Write debug log
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "freecad_debug.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(_log_lines))
    except Exception:
        pass


_find_freecad()


def check_freecad():
    return FREECAD_AVAILABLE


def get_freecad_info() -> dict:
    """Get info about detected FreeCAD installation."""
    return {
        "available": FREECAD_AVAILABLE,
        "cmd_path": FREECAD_CMD,
        "gui_path": FREECAD_GUI,
        "version": FREECAD_VERSION,
    }


def _get_macro_path():
    module_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(module_dir, "freecad_macro.py")


def _open_in_freecad(filepath):
    """Open file in FreeCAD GUI (non-blocking)."""
    if FREECAD_GUI and os.path.exists(FREECAD_GUI):
        subprocess.Popen(
            [FREECAD_GUI, filepath],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
    else:
        if platform.system() == "Windows":
            os.startfile(filepath)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", filepath])
        else:
            subprocess.Popen(["xdg-open", filepath])


def export_products_to_freecad(products, filepath, fmt="fcstd",
                                  progress_callback: Optional[Callable[[int, int], None]] = None):
    """Export products to FreeCAD file.

    Args:
        products: List of product dicts or StandardProduct objects
        filepath: Output file path
        fmt: Format — fcstd, step, stl, obj, iges
        progress_callback: Called with (current, total) during export
    """
    if not FREECAD_AVAILABLE:
        raise RuntimeError(
            "FreeCAD не знайдено. Перевірте налаштування або встановіть FreeCAD.\n"
            "Деталі у файлі freecad_debug.log"
        )

    data = []
    for p in products:
        d = p.to_dict() if hasattr(p, "to_dict") else dict(p)
        data.append(d)

    if progress_callback:
        progress_callback(0, len(data))

    json_path = os.path.join(tempfile.gettempdir(), "ventcad_export.data")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    macro_path = _get_macro_path()

    log_path = filepath + ".export.log"
    try:
        if progress_callback:
            progress_callback(1, len(data))

        # Use FreeCAD's bundled Python if available, otherwise freecadcmd
        freecad_dir = os.path.dirname(FREECAD_CMD)
        python_exe = os.path.join(freecad_dir, "python.exe")
        if os.path.exists(python_exe):
            run_cmd = [python_exe, macro_path, json_path, filepath, fmt]
        else:
            run_cmd = [FREECAD_CMD, "--run", macro_path, json_path, filepath, fmt]

        result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=180,
        )

        # Check for log file with detailed info
        log_content = ""
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    log_content = f.read()
            except Exception:
                pass

        if result.returncode != 0:
            err = result.stderr if result.stderr else result.stdout
            detail = f"\n\nДетальний лог:\n{log_content}" if log_content else ""
            raise RuntimeError(f"Помилка FreeCAD:\n{err}{detail}")

        if not os.path.exists(filepath):
            out = result.stdout if result.stdout else "(пустий вивід)"
            detail = f"\n\nДетальний лог:\n{log_content}" if log_content else ""
            raise RuntimeError(f"Файл не створено. Вивід:\n{out}{detail}")

        if progress_callback:
            progress_callback(len(data), len(data))

        _open_in_freecad(filepath)
        return filepath
    finally:
        if os.path.exists(json_path):
            os.unlink(json_path)
        # Log file is kept for debugging — check same folder as output


def build_product_model(product, builder=None):
    """Build a single product model and return temp file path."""
    data = [product.to_dict()] if hasattr(product, "to_dict") else [dict(product)]
    with tempfile.NamedTemporaryFile(suffix=".FCStd", delete=False) as f:
        filepath = f.name
    export_products_to_freecad(data, filepath, "fcstd")
    return filepath


def export_batch(products, output_dir: str, fmt="step",
                    progress_callback: Optional[Callable[[int, int], None]] = None):
    """Export each product to a separate file in output_dir."""
    os.makedirs(output_dir, exist_ok=True)
    ext = {"fcstd": ".FCStd", "step": ".step", "stl": ".stl",
           "obj": ".obj", "iges": ".igs"}[fmt]

    exported = []
    for i, p in enumerate(products):
        name = getattr(p, "name", p.get("name", f"product_{i}"))
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(name))
        filepath = os.path.join(output_dir, f"{safe}{ext}")
        export_products_to_freecad([p], filepath, fmt)
        exported.append(filepath)
        if progress_callback:
            progress_callback(i + 1, len(products))

    return exported


def show_preview(parent, products: List[Any]):
    """Show 3D preview dialog (no FreeCAD required)."""
    if PREVIEW_AVAILABLE:
        show_preview_dialog(parent, products)
    else:
        raise RuntimeError("Попередній перегляд недоступний. Встановіть matplotlib: pip install matplotlib")
