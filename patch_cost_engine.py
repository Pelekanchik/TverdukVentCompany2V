"""
Патч для cost_engine.py — додає category_waste_percent
"""
import sys

f = open(sys.argv[1], encoding='utf-8')
lines = f.readlines()
f.close()

new = []
for i, line in enumerate(lines):
    # Додаємо поля в CostBreakdown (після markup_percent)
    if 'markup_percent: float = 0.0' in line and 'vat_rate' not in line:
        new.append(line)
        new.append("    category_waste_percent: float = 0.0\n")
        new.append("    category_waste_cost: float = 0.0\n")
        continue
    
    # Додаємо в per_unit() — category_waste_cost
    if 'final_price=self.final_price / self.quantity,' in line:
        new.append(line)
        new.append("            category_waste_percent=self.category_waste_percent,\n")
        new.append("            category_waste_cost=self.category_waste_cost / self.quantity,\n")
        continue
    
    # Додаємо параметр category_waste_percent в calculate()
    if 'flange_price: float = 0.0,' in line:
        new.append(line)
        new.append("        category_waste_percent: float = 0.0,\n")
        continue
    
    # Застосовуємо category_waste до material_cost
    if 'result.material_cost = material_area_m2 * material_price * quantity' in line:
        new.append(line)
        new.append("\n")
        new.append("        # ── 1b. Запас на брак/поворот по категорії ──\n")
        new.append("        result.category_waste_percent = category_waste_percent\n")
        new.append("        result.category_waste_cost = result.material_cost * category_waste_percent / 100\n")
        new.append("        result.material_cost += result.category_waste_cost\n")
        continue
    
    # Додаємо category_waste_cost в base_cost
    if 'result.base_cost = (' in line:
        new.append(line)
        continue
    if 'result.other_cost' in line and i > 270 and i < 290:
        new.append(line)
        new.append("            + result.category_waste_cost\n")
        continue
    
    # Додаємо category_waste_percent в calculate_from_product
    if 'flange_price=float(getattr(product, "flange_price", 0)),' in line:
        new.append(line)
        new.append('            category_waste_percent=getattr(product, "category_waste_percent", 0.0),\n')
        continue
    
    new.append(line)

f = open(sys.argv[1], 'w', encoding='utf-8')
f.writelines(new)
f.close()
print('done')
