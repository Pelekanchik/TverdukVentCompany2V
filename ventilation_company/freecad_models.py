"""Параметричні 3D-моделі вентиляційних виробів для FreeCAD.

Використовує FreeCAD через subprocess (freecadcmd) замість прямого імпорту.
Це уникає конфліктів версій Python на Windows.
"""

import json
import os
import subprocess
import tempfile

FREECAD_AVAILABLE = False
FREECAD_CMD = None

_freecad_cmd_paths = [
    r"C:\Program Files\FreeCAD 1.0\bin\python.exe",
    r"C:\Program Files\FreeCAD 0.21\bin\python.exe",
    r"C:\Program Files\FreeCAD 1.1\bin\python.exe",
    r"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe",
    r"C:\Program Files\FreeCAD 0.21\bin\freecadcmd.exe",
    "/usr/bin/freecadcmd",
    "/usr/bin/freecadcmd-daily",
    "/usr/local/bin/freecadcmd",
    "/Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd",
]

for p in _freecad_cmd_paths:
    if os.path.exists(p):
        FREECAD_CMD = p
        FREECAD_AVAILABLE = True
        break


def _find_in_path(cmd):
    import shutil

    return shutil.which(cmd)


if not FREECAD_AVAILABLE:
    for cmd in ["freecadcmd", "freecadcmd-daily", "FreeCADCmd"]:
        p = _find_in_path(cmd)
        if p:
            FREECAD_CMD = p
            FREECAD_AVAILABLE = True
            break


def check_freecad():
    return FREECAD_AVAILABLE


def _get_macro_path():
    module_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(module_dir, "freecad_macro.py")


def export_products_to_freecad(products, filepath, fmt="fcstd"):
    if not FREECAD_AVAILABLE:
        raise RuntimeError(
            "FreeCAD не знайдено. Встановіть FreeCAD:\n"
            "Windows: https://www.freecad.org/downloads.php\n"
            "Linux: sudo apt install freecad\n"
            "macOS: brew install --cask freecad"
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
            raise RuntimeError(f"FreeCAD помилка:\n{err}")
        if not os.path.exists(filepath):
            out = result.stdout if result.stdout else "(немає виводу)"
            raise RuntimeError(f"Файл не створено. Вивід:\n{out}")
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
