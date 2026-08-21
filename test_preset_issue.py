import sys
sys.path.insert(0, r"C:\Users\Admin\Desktop\TverdukVentCompany2V")

import copy
from ventilation_company.standard_products import RectDuct, Thickness, MaterialType

# Створюємо пресет
preset = RectDuct(
    name="Труба 100×50×500",
    product_type="повітропровід прямокутний",
    width=100, height=50, length=500,
    thickness=Thickness.T0_7,
    material=MaterialType.GALVANIZED,
    quantity=1,
)

print(f"PRESET: surface_area={preset.surface_area:.4f}, blank_area={preset.blank_area:.4f}, unit_price={preset.unit_price}, total_price={preset.total_price}")

# Імітуємо додавання з бібліотеки (як у preset_dialog.py)
result = copy.deepcopy(preset)
result.quantity = 3
result.__post_init__()

print(f"RESULT: surface_area={result.surface_area:.4f}, blank_area={result.blank_area:.4f}, unit_price={result.unit_price}, total_price={result.total_price}")
print(f"Types: unit_price={type(result.unit_price)}, total_price={type(result.total_price)}")
