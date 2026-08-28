#!/usr/bin/env python3
"""Виправляє баг у FreeCAD VentCompanyWorkbench — 'Додати' не створює деталь."""

import os

# Шлях до воркбенча FreeCAD
workbench_path = os.path.expanduser(r"~\AppData\Roaming\FreeCAD\v1-1\Mod\VentCompanyWorkbench\commands\import_preset.py")

if not os.path.exists(workbench_path):
    print(f"❌ Не знайдено: {workbench_path}")
    print("Шукаємо воркбенч...")
    # Альтернативний пошук
    for root, dirs, files in os.walk(os.path.expanduser(r"~\AppData\Roaming\FreeCAD")):
        if "import_preset.py" in files:
            workbench_path = os.path.join(root, "import_preset.py")
            print(f"🔍 Знайдено: {workbench_path}")
            break

if not os.path.exists(workbench_path):
    print("❌ Воркбенч не знайдено!")
    exit(1)

with open(workbench_path, "r", encoding="utf-8") as f:
    content = f.read()

# Перевіряємо, чи вже є accept()
if "def accept(self):" in content:
    print("ℹ️ accept() вже є")
else:
    # Додаємо метод accept() перед get_selected()
    old_get_selected = """    def get_selected(self):
        return self.selected_preset"""
    
    new_get_selected = """    def accept(self):
        \"\"\"Встановити selected_preset перед закриттям діалогу\"\"\"
        row = self.table.currentRow()
        if row >= 0:
            self.selected_preset = self.table.item(row, 0).data(QtCore.Qt.UserRole)
        super(PresetDialog, self).accept()

    def get_selected(self):
        return self.selected_preset"""
    
    if old_get_selected in content:
        content = content.replace(old_get_selected, new_get_selected)
        print("✅ Додано accept() — тепер 'Додати' створює деталь!")
    else:
        print("⚠️ Не вдалося знайти get_selected()")

with open(workbench_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\n✅ {workbench_path} оновлено")
print("🔄 Перезапусти FreeCAD і спробуй 'Додати' виріб з бібліотеки")