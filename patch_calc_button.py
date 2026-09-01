# -*- coding: utf-8 -*-
"""Patch: adds "Details" button to ProductDialog.

Run: python patch_calc_button.py
"""

FILE_PATH = "ventilation_company/gui_pyside6/products_tab.py"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add import
if "calc_details_dialog" not in content:
    old_imp = "from ventilation_company.calculations.cost_engine import CostEngine, CostBreakdown"
    new_imp = old_imp + "\nfrom ventilation_company.gui_pyside6.calc_details_dialog import CalcDetailsDialog"
    if old_imp in content:
        content = content.replace(old_imp, new_imp)
        print("Import added.")
    else:
        print("WARN: import line not found, add manually.")

# 2. Add button after "Calculate price"
old_btn = "form.addRow(btn_calc)"
new_btn = old_btn + "\n\n        btn_details = QPushButton(\"📊 Деталі розрахунку\")\n        btn_details.setMinimumHeight(32)\n        btn_details.clicked.connect(self._on_show_details)\n        form.addRow(btn_details)"
if old_btn in content:
    content = content.replace(old_btn, new_btn)
    print("Button added.")
else:
    print("WARN: button row not found, add manually.")

# 3. Add method before _on_save
old_meth = "    def _on_save(self):"
new_meth = """    def _on_show_details(self):
        if not self._calc_result:
            QMessageBox.warning(self, "Увага", "Спочатку розрахуйте ціну")
            return
        dlg = CalcDetailsDialog(
            product_type=self.combo_type.currentText(),
            material=self.combo_material.currentText(),
            thickness=float(self.combo_thickness.currentText()),
            width=self.spin_width.value(),
            height=self.spin_height.value() if self.spin_height.isEnabled() else 0,
            length=self.spin_length.value() if self.spin_length.isEnabled() else 0,
            qty=self.spin_qty.value(),
            surface=self._calc_result.surface_area_m2 / max(self._calc_result.quantity, 1),
            blank=self._calc_result.blank_area_m2 / max(self._calc_result.quantity, 1),
            material_area=self._calc_result.material_area_m2 / max(self._calc_result.quantity, 1),
            with_flanges=self.chk_with_flanges.isChecked(),
            flange_count=self.spin_flange_count.value() if self.chk_with_flanges.isChecked() else 0,
            flange_price=150.0 if self.combo_flange_profile.currentText() == "P30" else 200.0,
            markup_name=self.combo_category.currentText(),
            parent=self,
        )
        dlg.exec()

    def _on_save(self):"""
if old_meth in content:
    content = content.replace(old_meth, new_meth)
    print("Method added.")
else:
    print("WARN: _on_save not found, add _on_show_details manually.")

with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("Done! Restart: python main_pyside6.py")
