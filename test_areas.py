"""Тест для перевірки значень площ та розмірів розкрою."""
from ventilation_company.standard_products import RectFlange, RectDuct, make_rect_duct, make_round_duct
from ventilation_company.cutting_integration import product_to_detail

# Фланець 400×200 з profile=20 (як на скріншоті)
f = RectFlange(
    name="Фланець 400×200",
    width=400, height=200, length=0,
    profile=20, thickness=0.7,
    quantity=1
)
print(f"RectFlange 400×200, profile=20:")
print(f"  surface_area = {f.surface_area:.4f} м²")
print(f"  blank_area   = {f.blank_area:.4f} м²")
print(f"  material_area= {f.material_area:.4f} м²")
d = product_to_detail(f)
print(f"  detail size  = {d.width:.1f} × {d.height:.1f} мм")
print()

# Фланець 400×200 з profile=30
f30 = RectFlange(
    name="Фланець 400×200 П30",
    width=400, height=200, length=0,
    profile=30, thickness=0.7,
    quantity=1
)
print(f"RectFlange 400×200, profile=30:")
print(f"  surface_area = {f30.surface_area:.4f} м²")
print(f"  blank_area   = {f30.blank_area:.4f} м²")
print(f"  material_area= {f30.material_area:.4f} м²")
d30 = product_to_detail(f30)
print(f"  detail size  = {d30.width:.1f} × {d30.height:.1f} мм")
print()

# Повітропровід 400×200×1000
duct = make_rect_duct(400, 200, 1000)
print(f"RectDuct 400×200×1000:")
print(f"  surface_area = {duct.surface_area:.4f} м²")
print(f"  blank_area   = {duct.blank_area:.4f} м²")
print(f"  material_area= {duct.material_area:.4f} м²")
dd = product_to_detail(duct)
print(f"  detail size  = {dd.width:.1f} × {dd.height:.1f} мм")
