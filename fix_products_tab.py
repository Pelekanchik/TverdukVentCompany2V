# -*- coding: utf-8 -*-
"""Patch for products_tab.py - inserts area/weight calculation.

Run: python fix_products_tab.py
"""

FILE_PATH = "ventilation_company/gui_pyside6/products_tab.py"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the line with "project_id = self.parent()" inside get_data()
insert_idx = None
in_get_data = False
for i, line in enumerate(lines):
    if "def get_data(self)" in line:
        in_get_data = True
    if in_get_data and "project_id = self.parent()" in line:
        insert_idx = i
        break

if insert_idx is None:
    # Try alternative: find "return {" in get_data
    for i, line in enumerate(lines):
        if "def get_data(self)" in line:
            in_get_data = True
        if in_get_data and line.strip().startswith("return {"):
            insert_idx = i
            break

if insert_idx is None:
    print("ERROR: Could not find insertion point.")
    exit(1)

new_code = """
        # -- CALCULATED VALUES: area, blank, weight --
        if self._calc_result:
            calc_qty = self._calc_result.quantity if self._calc_result.quantity > 0 else 1
            params["metal_area_m2"] = round(self._calc_result.surface_area_m2 / calc_qty, 4)
            params["blank_area_m2"] = round(self._calc_result.blank_area_m2 / calc_qty, 4)
            params["material_area_m2"] = round(self._calc_result.material_area_m2 / calc_qty, 4)

            # Weight = material_area * thickness(m) * density
            density_map = {
                "Оцинкована сталь": 7850,
                "Нержавіюча сталь": 7900,
                "Алюміній": 2700,
            }
            density = density_map.get(self.combo_material.currentText(), 7850)
            thickness_m = float(self.combo_thickness.currentText()) / 1000
            params["weight_kg"] = round(
                (self._calc_result.material_area_m2 / calc_qty) * thickness_m * density, 4
            )
"""

lines.insert(insert_idx, new_code)

with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Patch applied! Area and weight now saved to DB.")
print("Restart: python main_pyside6.py")
