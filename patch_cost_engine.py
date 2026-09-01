# -*- coding: utf-8 -*-
"""Patch: fixes CostEngine to read material prices from pricing_settings.json

Run: python patch_cost_engine.py
"""

FILE_PATH = "ventilation_company/calculations/cost_engine.py"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add _get_material_price method before _get_labor_rate
old_method = "    def _get_labor_rate(self, product_type: str) -> tuple[float, float]:"
new_method = """    def _get_material_price(self, material_name: str, thickness_mm: float) -> float:
        # Get material price from pricing_settings.json or manufacturing_params fallback
        material_prices = self.pricing.get("material_prices", {})
        if isinstance(material_prices, dict):
            for mat_name, thicknesses in material_prices.items():
                if isinstance(thicknesses, dict):
                    if mat_name.lower() == material_name.lower():
                        price = thicknesses.get(str(thickness_mm), 0)
                        if price:
                            return float(price)
        # Fallback to manufacturing_params.py
        return get_material_price(material_name, thickness_mm)

    def _get_labor_rate(self, product_type: str) -> tuple[float, float]:"""

if old_method in content:
    content = content.replace(old_method, new_method)
    print("_get_material_price method added.")
else:
    print("ERROR: could not find _get_labor_rate.")

# 2. Replace get_material_price call with self._get_material_price
old_call = "material_price = get_material_price(material_name, thickness_mm)"
new_call = "material_price = self._get_material_price(material_name, thickness_mm)"

if old_call in content:
    content = content.replace(old_call, new_call)
    print("get_material_price call replaced.")
else:
    print("ERROR: could not find get_material_price call.")

with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("Done! Restart: python main_pyside6.py")
