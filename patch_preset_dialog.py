#!/usr/bin/env python3
"""Патчить preset_dialog.py — додає створення 3D-моделі в FreeCAD при натисканні 'Додати'."""

import os
import shutil

filepath = r"ventilation_company\gui\preset_dialog.py"

if not os.path.exists(filepath):
    print(f"❌ Не знайдено: {filepath}")
    exit(1)

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Резервна копія
backup = filepath + ".backup"
if not os.path.exists(backup):
    shutil.copy2(filepath, backup)
    print(f"💾 Резервна копія: {backup}")

# 1. Додаємо імпорт freecad_models
old_import = """from ventilation_company.standard_products import (
    FlexibleConnector,
    MaterialType,
    ProductLibrary,
    RectCap,
    RectElbow,
    RectFlange,
    RectTee,
    RectTransition,
    RoundCap,
    RoundElbow,
    RoundFlange,
    RoundTee,
    RoundTransition,
    StandardProduct,
    Thickness,
    make_rect_duct,
    make_round_duct,
)"""

new_import = """from ventilation_company.standard_products import (
    FlexibleConnector,
    MaterialType,
    ProductLibrary,
    RectCap,
    RectElbow,
    RectFlange,
    RectTee,
    RectTransition,
    RoundCap,
    RoundElbow,
    RoundFlange,
    RoundTee,
    RoundTransition,
    StandardProduct,
    Thickness,
    make_rect_duct,
    make_round_duct,
)
from ventilation_company.freecad_models import FREECAD_AVAILABLE, create_freecad_model"""

if old_import in content:
    content = content.replace(old_import, new_import)
    print("✅ Додано імпорт freecad_models")
else:
    print("⚠️ Імпорт standard_products не знайдено у стандартному вигляді")

# 2. Заміна _on_ok — додаємо створення 3D-моделі + on_select callback
old_on_ok = """    def _on_ok(self):
        idx = self._get_selected_index()
        if idx < 0:
            messagebox.showwarning("Увага", "Оберіть виріб з таблиці.")
            return
        self.result = self.library.products[idx]
        self.destroy()"""

new_on_ok = """    def _on_ok(self):
        idx = self._get_selected_index()
        if idx < 0:
            messagebox.showwarning("Увага", "Оберіть виріб з таблиці.")
            return
        self.result = self.library.products[idx]
        
        # Викликати callback, якщо задано (наприклад, з FreeCAD workbench)
        if self.on_select:
            self.on_select(self.result)
        
        # Створити 3D-модель у FreeCAD, якщо доступно
        if FREECAD_AVAILABLE:
            try:
                create_freecad_model(self.result)
            except Exception as e:
                print(f"[VentCompany] Помилка створення 3D-моделі: {e}")
        
        self.destroy()"""

if old_on_ok in content:
    content = content.replace(old_on_ok, new_on_ok)
    print("✅ Оновлено _on_ok (додано створення 3D-моделі + on_select callback)")
else:
    print("⚠️ _on_ok не знайдено у стандартному вигляді")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print(f"✅ {filepath} збережено")
print("\n🔄 Очисти кеш і перезапусти FreeCAD:")
print('   Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force')