#!/usr/bin/env python3
"""Патчить FreeCAD воркбенч — автовибір + логування + обробка помилок."""

import os

filepath = os.path.expanduser(
    r"~\AppData\Roaming\FreeCAD\v1-1\Mod\VentCompanyWorkbench\commands\import_preset.py"
)

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Автовибір першого рядка після завантаження
old_load_end = """            self.info_label.setText(f"📦 Завантажено {len(presets)} пресетів. Виберіть і натисніть «Додати»")"""

new_load_end = """            self.info_label.setText(f"📦 Завантажено {len(presets)} пресетів. Виберіть і натисніть «Додати»")
            # Автоматично вибираємо перший рядок
            if self.table.rowCount() > 0:
                self.table.selectRow(0)"""

if old_load_end in content:
    content = content.replace(old_load_end, new_load_end)
    print("✅ Додано автовибір першого рядка")
else:
    print("⚠️ Не вдалося додати автовибір")

# 2. Логування + перевірка в Activated
old_activated = """    def Activated(self):
        dialog = PresetDialog(FreeCADGui.getMainWindow())
        if dialog.exec_() == QtGui.QDialog.Accepted:
            preset = dialog.get_selected()
            if preset:
                self.create_component(preset)"""

new_activated = """    def Activated(self):
        dialog = PresetDialog(FreeCADGui.getMainWindow())
        result = dialog.exec_()
        FreeCAD.Console.PrintMessage(f"[VC] Dialog result: {result}\\n")
        if result == QtGui.QDialog.Accepted:
            preset = dialog.get_selected()
            FreeCAD.Console.PrintMessage(f"[VC] Preset: {preset is not None}\\n")
            if preset:
                try:
                    self.create_component(preset)
                    FreeCAD.Console.PrintMessage("[VC] OK: component created\\n")
                except Exception as e:
                    FreeCAD.Console.PrintError(f"[VC] ERROR: {e}\\n")
                    QtGui.QMessageBox.critical(None, "Помилка", f"Не вдалося створити деталь:\\n{e}")
            else:
                QtGui.QMessageBox.warning(None, "Увага", "Оберіть виріб у таблиці перед натисканням 'Додати'")
        else:
            FreeCAD.Console.PrintWarning(f"[VC] Dialog rejected\\n")"""

if old_activated in content:
    content = content.replace(old_activated, new_activated)
    print("✅ Додано логування і обробку помилок")
else:
    print("⚠️ Activated() не знайдено у стандартному вигляді")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\n✅ {filepath} оновлено")
print("🔄 Перезапусти FreeCAD і спробуй:")
print("   1. Відкрити бібліотеку VentCompany")
print("   2. Переконатися, що перший рядок виділений (синій)")
print("   3. Натиснути 'Додати'")
print("   4. Подивитися Вигляд → Панелі → Report view на [VC] повідомлення")