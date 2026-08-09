"""Модуль для інтеграції 3D-моделей з FreeCAD."""

import json
import os
import subprocess
import tempfile
import platform
import shutil
import sys

FREECAD_AVAILABLE = False
FREECAD_CMD = None
FREECAD_GUI = None

# ── ДІАГНОСТИКА: запис у файл ──
_log_lines = []

def _log(msg):
    _log_lines.append(str(msg))

# ── Шляхи до FreeCAD ──
_freecad_cmd_paths = [
    r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe",
    r"C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe",
    r"C:\Program Files\FreeCAD 1.1\bin\python.exe",
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


def _find_freecad():
    """Знайти FreeCAD з діагностикою."""
    global FREECAD_AVAILABLE, FREECAD_CMD, FREECAD_GUI

    _log("=== FreeCAD search started ===")
    _log(f"Platform: {platform.system()}")
    _log(f"Python: {sys.executable}")

    # 1. Перевірити фіксовані шляхи
    for p in _freecad_cmd_paths:
        exists = os.path.exists(p)
        _log(f"Check CMD path: {p} -> {exists}")
        if exists:
            FREECAD_CMD = p
            FREECAD_AVAILABLE = True
            break

    for p in _freecad_gui_paths:
        exists = os.path.exists(p)
        _log(f"Check GUI path: {p} -> {exists}")
        if exists:
            FREECAD_GUI = p
            break

    # 2. Пошук через PATH
    if not FREECAD_CMD:
        for cmd in ["freecadcmd", "FreeCADCmd", "freecadcmd-daily"]:
            p = shutil.which(cmd)
            _log(f"which({cmd}) = {p}")
            if p and os.path.exists(p):
                FREECAD_CMD = p
                FREECAD_AVAILABLE = True
                break

    if not FREECAD_GUI:
        for cmd in ["freecad", "FreeCAD", "freecad-daily"]:
            p = shutil.which(cmd)
            _log(f"which({cmd}) = {p}")
            if p and os.path.exists(p):
                FREECAD_GUI = p
                break

    # 3. Пошук через where (Windows)
    if platform.system() == "Windows" and not FREECAD_CMD:
        for cmd in ["freecadcmd.exe", "FreeCADCmd.exe"]:
            try:
                result = subprocess.run(
                    ["where", cmd],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                _log(f"where {cmd}: rc={result.returncode} out={result.stdout.strip()[:100]}")
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        p = line.strip()
                        if "freecad" in p.lower() and os.path.exists(p):
                            FREECAD_CMD = p
                            FREECAD_AVAILABLE = True
                            break
                    if FREECAD_CMD:
                        break
            except Exception as e:
                _log(f"where error: {e}")

    # 4. Пошук через where для GUI
    if platform.system() == "Windows" and not FREECAD_GUI:
        for cmd in ["freecad.exe", "FreeCAD.exe"]:
            try:
                result = subprocess.run(
                    ["where", cmd],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                _log(f"where {cmd}: rc={result.returncode} out={result.stdout.strip()[:100]}")
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        p = line.strip()
                        if "freecad" in p.lower() and os.path.exists(p):
                            FREECAD_GUI = p
                            break
                    if FREECAD_GUI:
                        break
            except Exception as e:
                _log(f"where GUI error: {e}")

    # 5. Пошук через os.listdir (обхід проблем з os.path.exists)
    if platform.system() == "Windows" and not FREECAD_AVAILABLE:
        search_dirs = [
            r"C:\Program Files",
            r"C:\Program Files (x86)",
        ]
        for base_dir in search_dirs:
            try:
                if os.path.isdir(base_dir):
                    for entry in os.listdir(base_dir):
                        if "freecad" in entry.lower():
                            bin_dir = os.path.join(base_dir, entry, "bin")
                            _log(f"Found FreeCAD dir: {bin_dir}")
                            if os.path.isdir(bin_dir):
                                for exe in ["freecadcmd.exe", "FreeCADCmd.exe", "python.exe"]:
                                    p = os.path.join(bin_dir, exe)
                                    if os.path.exists(p):
                                        FREECAD_CMD = p
                                        FREECAD_AVAILABLE = True
                                        _log(f"Found CMD via listdir: {p}")
                                        break
                                for exe in ["freecad.exe", "FreeCAD.exe"]:
                                    p = os.path.join(bin_dir, exe)
                                    if os.path.exists(p):
                                        FREECAD_GUI = p
                                        _log(f"Found GUI via listdir: {p}")
                                        break
                            if FREECAD_AVAILABLE:
                                break
            except Exception as e:
                _log(f"listdir error for {base_dir}: {e}")
            if FREECAD_AVAILABLE:
                break

    # 6. Якщо знайдено GUI але не CMD — використати GUI
    if not FREECAD_CMD and FREECAD_GUI:
        FREECAD_CMD = FREECAD_GUI
        FREECAD_AVAILABLE = True
        _log(f"Using GUI as CMD: {FREECAD_CMD}")

    _log(f"=== Result: AVAILABLE={FREECAD_AVAILABLE}, CMD={FREECAD_CMD}, GUI={FREECAD_GUI} ===")

    # Записати лог
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "freecad_debug.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(_log_lines))
    except Exception:
        pass


_find_freecad()


def check_freecad():
    return FREECAD_AVAILABLE


def _get_macro_path():
    module_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(module_dir, "freecad_macro.py")


def _open_in_freecad(filepath):
    """Відкрити файл у FreeCAD GUI (не блокує основну програму)."""
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


def export_products_to_freecad(products, filepath, fmt="fcstd"):
    if not FREECAD_AVAILABLE:
        raise RuntimeError(
            "FreeCAD not found. Searched paths:\n" +
            "\n".join([p for p in _freecad_cmd_paths if "FreeCAD" in p]) +
            "\n\nCheck freecad_debug.log in ventilation_company folder."
        )

    data = []
    for p in products:
        d = p.to_dict() if hasattr(p, "to_dict") else dict(p)
        data.append(d)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        json_path = f.name

    macro_path = _get_macro_path()

    try:
        result = subprocess.run(
            [FREECAD_CMD, macro_path, json_path, filepath, fmt],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            err = result.stderr if result.stderr else result.stdout
            raise RuntimeError(f"FreeCAD error:\n{err}")
        if not os.path.exists(filepath):
            out = result.stdout if result.stdout else "(empty output)"
            raise RuntimeError(f"File not created. Output:\n{out}")

        # Відкрити у FreeCAD GUI
        _open_in_freecad(filepath)
        return filepath
    finally:
        if os.path.exists(json_path):
            os.unlink(json_path)


def build_product_model(product, builder=None):
    data = [product.to_dict()] if hasattr(product, "to_dict") else [dict(product)]

    with tempfile.NamedTemporaryFile(suffix=".FCStd", delete=False) as f:
        filepath = f.name

    export_products_to_freecad(data, filepath, "fcstd")
    return filepath
