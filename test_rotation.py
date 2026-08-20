from ventilation_company.metal_cutting import Detail, Sheet, MetalCutter

d1 = Detail(name="Деталь1", width=800, height=600, quantity=2, allow_rotation=True)
d2 = Detail(name="Деталь2", width=600, height=800, quantity=1, allow_rotation=False)

s = Sheet(1250, 2500, 0.7)
print("Place d1 normal:", s.place_detail(d1, 0, 0, False))
print("Place d2 rotated:", s.place_detail(d2, 0, 0, True))  # allow_rotation=False → тільки False

# Test MetalCutter with rotation
cutter = MetalCutter(1250, 2500, 0.7)
plan = cutter.calculate_cutting([d1, d2])
print("Sheets:", plan.total_sheets)
print("Unplaced:", len(plan.unplaced_details))
print("OK")
