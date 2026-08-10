"""Debug script for FreeCAD export — runs in VS Code terminal and shows ALL output."""

import subprocess
import sys
import os
import json
import tempfile

# ═══ Find FreeCAD ═══
FREECAD_CMD = None
paths = [
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
]
for p in paths:
    if os.path.exists(p):
        FREECAD_CMD = p
        break

if not FREECAD_CMD:
    import shutil
    for cmd in ["freecadcmd.exe", "FreeCADCmd.exe"]:
        p = shutil.which(cmd)
        if p:
            FREECAD_CMD = p
            break

if not FREECAD_CMD:
    print("❌ FreeCAD не знайдено!")
    sys.exit(1)

print(f"✅ FreeCAD: {FREECAD_CMD}")

# ═══ Create test products ═══
test_products = [
    {"name": "Повітропровід 400x200x1000", "width": 400, "height": 200, "length": 1000, "thickness": 0.7, "product_type": "rect_duct"},
    {"name": "Перехід 400x200→300x150", "width": 400, "height": 200, "length": 1000, "end_width": 300, "end_height": 150, "thickness": 0.7, "product_type": "rect_transition"}
]

# Write .data file directly (not NamedTemporaryFile)
json_path = os.path.join(tempfile.gettempdir(), "freecad_input.data")
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(test_products, f, ensure_ascii=False, indent=2)

output_path = os.path.join(os.path.expanduser("~"), "Desktop", "TestExport.step")
macro_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ventilation_company", "freecad_macro.py")

# Find python.exe in same folder as freecadcmd.exe (FreeCAD's bundled Python)
freecad_dir = os.path.dirname(FREECAD_CMD)
python_exe = os.path.join(freecad_dir, "python.exe")

if os.path.exists(python_exe):
    cmd = [python_exe, macro_path, json_path, output_path, "step"]
    print(f"\n🚀 Запускаю через FreeCAD Python: {python_exe}")
else:
    # Fallback: try freecadcmd with --run flag
    cmd = [FREECAD_CMD, "--run", macro_path, json_path, output_path, "step"]
    print(f"\n🚀 Запускаю через freecadcmd --run: {FREECAD_CMD}")

print("=" * 70)

# Run and stream output LIVE
process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding='utf-8',
    errors='replace'
)

for line in process.stdout:
    print(line, end='')

process.wait()
print("=" * 70)
print(f"📊 Return code: {process.returncode}")
print(f"📁 Файл створено: {os.path.exists(output_path)}")
if os.path.exists(output_path):
    print(f"📦 Розмір: {os.path.getsize(output_path):,} bytes")

# Cleanup
if os.path.exists(json_path):
    os.unlink(json_path)
