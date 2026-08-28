#!/usr/bin/env python3
"""Виправляє 'Додати' у FreeCAD VentCompanyWorkbench."""

import os

# Шлях до файлу команди імпорту у воркбенчі FreeCAD
filepath = os.path.expanduser(
    r"~\AppData\Roaming\FreeCAD\v1-1\Mod\VentCompanyWorkbench\commands\import_preset.py"
)

if not os.path.exists(filepath):
    print(f"❌ Не знайдено: {filepath}")
    exit(1)

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Перевіряємо, чи вже є accept()
if "def accept(self):" in content:
    print("ℹ️ accept() вже є, пропускаємо")
else:
    # Додаємо accept() перед get_selected()
    old = """    def get_selected(self):
        return self.selected_preset"""
    
    new = """    def accept(self):
        \"\"\"Встановити selected_preset при натисканні 'Додати'\"\"\"
        row = self.table.currentRow()
        if row >= 0:
            self.selected_preset = self.table.item(row, 0).data(QtCore.Qt.UserRole)
        super(PresetDialog, self).accept()

    def get_selected(self):
        return self.selected_preset"""
    
    if old in content:
        content = content.replace(old, new)
        print("✅ accept() додано!")
    else:
        print("⚠️ Не вдалося знайти get_selected()")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\n✅ {filepath} оновлено")
print("🔄 ПЕРЕЗАПУСТИ FreeCAD і спробуй 'Додати' виріб!")
