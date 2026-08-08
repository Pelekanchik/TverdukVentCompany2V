# test_price.py
from ventilation_company.gui.settings_tab import PricingSettings
from ventilation_company.standard_products import RectFlange, MaterialType, Thickness

pricing = PricingSettings()

# Фланець 500×300 мм, оцинк 0.7 мм
flange = RectFlange(
    name="Фланець 500×300",
    width=500,
    height=300,
    thickness=Thickness.T0_7,
    material=MaterialType.GALVANIZED,
)

price = pricing.calculate_product_price({
    'type': 'Фланець прямокутний',
    'material': 'оцинкована сталь',
    'thickness': 0.7,
    'metal_area_m2': flange.metal_area,
    'weight_kg': flange.weight,
    'quantity': 1,
    'bolt_count': 12,  # кількість болтів для фланця
})

print(f"Площа металу: {flange.metal_area:.4f} м²  (для статистики)")
print(f"Вага: {flange.weight:.4f} кг  (для статистики)")
print(f"Ціна фланця: {price:.2f} грн")
print(f"Ціна за м²: ~{price / flange.metal_area:.0f} грн/м²")