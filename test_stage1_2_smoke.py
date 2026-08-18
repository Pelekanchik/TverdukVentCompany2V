"""Smoke test для Етапів 1 і 2 — покращений розрахунок площі + JSON-налаштування."""

from ventilation_company.standard_products import (
    RectDuct, RoundDuct, RectElbow, RoundElbow,
    MaterialType, Thickness, ProductLibrary,
    make_rect_duct, make_round_duct,
)
from ventilation_company.manufacturing_params import (
    ProductCategory,
    get_params,
    get_all_params,
    load_settings,
    update_category,
    validate_settings,
    reset_to_defaults,
)

print("=" * 60)
print("SMOKE TEST: Етап 1 (площі) + Етап 2 (JSON-налаштування)")
print("=" * 60)

# ═══════════════════════════════════════════════════════════
# 1. Перевірка завантаження JSON-налаштувань
# ═══════════════════════════════════════════════════════════
print("\n[1] Завантаження manufacturing_settings.json...")
settings = load_settings()
assert "categories" in settings
assert "material_densities_kg_m3" in settings
assert "seam_allowance_formula" in settings
print("   ✓ JSON завантажено успішно")

# ═══════════════════════════════════════════════════════════
# 2. Перевірка валідації
# ═══════════════════════════════════════════════════════════
print("\n[2] Валідація налаштувань...")
errors = validate_settings()
if errors:
    print(f"   ✗ Помилки: {errors}")
else:
    print("   ✓ Всі налаштування валідні")

# ═══════════════════════════════════════════════════════════
# 3. Параметри за категоріями
# ═══════════════════════════════════════════════════════════
print("\n[3] Параметри за категоріями...")
params = get_all_params()
for cat, p in params.items():
    print(f"   {cat.value:20s}: KIM={p.kim:.2f}, seam={p.seam_allowance_mm:.1f}mm, "
          f"cut={p.cut_allowance_mm:.1f}mm, bend={p.bend_allowance_mm:.1f}mm, "
          f"waste={p.waste_percent:.1f}%")

# ═══════════════════════════════════════════════════════════
# 4. RectDuct — порівняння площ
# ═══════════════════════════════════════════════════════════
print("\n[4] RectDuct 400×200×1000, t=0.7...")
d1 = RectDuct(name="ПП", width=400, height=200, length=1000)
print(f"   surface_area:  {d1.surface_area:.4f} m²")
print(f"   blank_area:    {d1.blank_area:.4f} m²  (+{(d1.blank_area/d1.surface_area-1)*100:.1f}%)")
print(f"   material_area: {d1.material_area:.4f} m²  (+{(d1.material_area/d1.surface_area-1)*100:.1f}%)")
print(f"   weight:        {d1.weight:.4f} kg")
print(f"   unit_price:    {d1.unit_price} грн")
assert d1.surface_area == d1.metal_area, "metal_area must equal surface_area"
assert d1.blank_area > d1.surface_area, "blank_area must be > surface_area"
assert d1.material_area > d1.blank_area, "material_area must be > blank_area"
print("   ✓ Площі зростають правильно")

# ═══════════════════════════════════════════════════════════
# 5. RoundDuct — спіральна труба
# ═══════════════════════════════════════════════════════════
print("\n[5] RoundDuct Ø250×1000, t=0.7...")
d2 = RoundDuct(name="КП", width=250, length=1000)
print(f"   surface_area:  {d2.surface_area:.4f} m²")
print(f"   blank_area:    {d2.blank_area:.4f} m²")
print(f"   material_area: {d2.material_area:.4f} m²")
print(f"   weight:        {d2.weight:.4f} kg")
print(f"   unit_price:    {d2.unit_price} грн")

# ═══════════════════════════════════════════════════════════
# 6. RectElbow — коліно
# ═══════════════════════════════════════════════════════════
print("\n[6] RectElbow 400×200, 90°, R=50...")
e1 = RectElbow(name="Відвід", width=400, height=200, angle=90, radius=50,
               top_extension=100, bottom_extension=100)
print(f"   surface_area:  {e1.surface_area:.4f} m²")
print(f"   blank_area:    {e1.blank_area:.4f} m²")
print(f"   material_area: {e1.material_area:.4f} m²")
print(f"   weight:        {e1.weight:.4f} kg")
print(f"   unit_price:    {e1.unit_price} грн")

# ═══════════════════════════════════════════════════════════
# 7. RoundElbow
# ═══════════════════════════════════════════════════════════
print("\n[7] RoundElbow Ø250, 90°, R=50...")
e2 = RoundElbow(name="Відвід", width=250, angle=90, radius=50,
                top_extension=100, bottom_extension=100)
print(f"   surface_area:  {e2.surface_area:.4f} m²")
print(f"   blank_area:    {e2.blank_area:.4f} m²")
print(f"   material_area: {e2.material_area:.4f} m²")
print(f"   weight:        {e2.weight:.4f} kg")
print(f"   unit_price:    {e2.unit_price} грн")

# ═══════════════════════════════════════════════════════════
# 8. Enum backward compat
# ═══════════════════════════════════════════════════════════
print("\n[8] Enum backward compatibility...")
d3 = make_rect_duct(400, 200, 1000, thickness=Thickness.T1_0, material=MaterialType.GALVANIZED)
print(f"   material: {d3.material} (type: {type(d3.material).__name__})")
print(f"   thickness: {d3.thickness} (type: {type(d3.thickness).__name__})")
assert isinstance(d3.material, MaterialType)
assert isinstance(d3.thickness, Thickness)
print("   ✓ Enum compatibility OK")

# ═══════════════════════════════════════════════════════════
# 9. Оновлення налаштувань через API
# ═══════════════════════════════════════════════════════════
print("\n[9] Оновлення налаштувань через API...")
old_kim = get_params(ProductCategory.RECT_DUCT).kim
update_category(ProductCategory.RECT_DUCT, kim=0.95)
new_params = get_params(ProductCategory.RECT_DUCT)
assert abs(new_params.kim - 0.95) < 0.001, f"Expected KIM=0.95, got {new_params.kim}"
print(f"   RectDuct KIM: {old_kim} → {new_params.kim}")
# Відновлюємо назад
update_category(ProductCategory.RECT_DUCT, kim=old_kim)
print("   ✓ Оновлення та відновлення працюють")

# ═══════════════════════════════════════════════════════════
# 10. ProductLibrary
# ═══════════════════════════════════════════════════════════
print("\n[10] ProductLibrary...")
lib = ProductLibrary()
lib.add(d1)
lib.add(d2)
print(f"   get_total_metal_area (legacy): {lib.get_total_metal_area():.4f} m²")
print(f"   get_total_surface_area:        {lib.get_total_surface_area():.4f} m²")
print(f"   get_total_blank_area:          {lib.get_total_blank_area():.4f} m²")
print(f"   get_total_material_area:       {lib.get_total_material_area():.4f} m²")
print(f"   get_total_weight:              {lib.get_total_weight():.4f} kg")
print(f"   get_total_price:               {lib.get_total_price():.2f} грн")

# ═══════════════════════════════════════════════════════════
# 11. FlexibleConnector — float compatibility
# ═══════════════════════════════════════════════════════════
print("\n[11] FlexibleConnector (float compat)...")
from ventilation_company.standard_products import FlexibleConnector
f = FlexibleConnector(name="Вставка", width=400, height=200, length=200,
                      fabric_type="поліестер", quantity=2)
print(f"   unit_price type: {type(f.unit_price).__name__}")
print(f"   total_price type: {type(f.total_price).__name__}")
assert isinstance(f.unit_price, float), "FlexibleConnector must use float"
assert isinstance(f.total_price, float), "FlexibleConnector must use float"
print("   ✓ FlexibleConnector uses float (backward compat)")

print("\n" + "=" * 60)
print("УСІ ТЕСТИ ПРОЙДЕНІ! ✅")
print("=" * 60)
