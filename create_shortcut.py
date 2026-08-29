#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable  # повний шлях до python.exe
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")

# 1. Створюємо launch.vbs — запускає Python без вікна консолі
vbs_path = os.path.join(BASE, "launch.vbs")
vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{BASE}"
WshShell.Run "{PYTHON} main.py", 0, False
'''
with open(vbs_path, "w", encoding="utf-8") as f:
    f.write(vbs_content)
print(f"✅ Створено: {vbs_path}")

# 2. Створюємо ярлик на робочому столі через PowerShell
shortcut_path = os.path.join(DESKTOP, "VentCompany.lnk")
ps_code = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{vbs_path}"
$Shortcut.WorkingDirectory = "{BASE}"
$Shortcut.Description = "VentCompany — програма для вентиляційної компанії"
$Shortcut.IconLocation = "{PYTHON},0"
$Shortcut.Save()
'''

result = subprocess.run(["powershell", "-Command", ps_code], capture_output=True, text=True)
if result.returncode == 0:
    print(f"✅ Ярлик створено: {shortcut_path}")
else:
    print(f"⚠️  Помилка створення ярлика: {result.stderr}")

print("\n" + "=" * 55)
print("ГОТОВО!")
print("=" * 55)
print(f"\nНа робочому столі з'явився ярлик 'VentCompany'")
print("Подвійний клік — програма запускається БЕЗ вікна консолі")
print("\nЯкщо ярлика немає — запустіть цей скрипт від імені адміністратора")
print("=" * 55)
input("\nНатисніть Enter...")