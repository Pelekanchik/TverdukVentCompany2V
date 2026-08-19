"""
Патч для settings_tab.py — додає category_waste_factors
"""
import sys

f = open(sys.argv[1], encoding='utf-8')
lines = f.readlines()
f.close()

new = []
for i, line in enumerate(lines):
    # Додаємо DEFAULT_CATEGORY_WASTE_FACTORS після DEFAULT_DEPRECIATION
    if i == 79:  # рядок 80 (0-based = 79) — кінець DEFAULT_DEPRECIATION
        new.append(line)
        new.append("\n")
        new.append("DEFAULT_CATEGORY_WASTE_FACTORS = {\n")
        new.append('    "rect_duct": 0.0,        # прямокутні труби\n')
        new.append('    "rect_fitting": 0.0,     # прямокутні фасонні\n')
        new.append('    "round_duct": 0.0,       # круглі труби\n')
        new.append('    "round_fitting": 0.0,    # круглі фасонні\n')
        new.append("}\n")
        continue
    
    # Додаємо category_waste_factors в __init__
    if 'self.labor_rates: dict = {}' in line:
        new.append(line)
        new.append("        self.category_waste_factors: dict = {}\n")
        continue
    
    # Додаємо читання в load()
    if 'self.labor_rates = data.get("labor_rates", DEFAULT_LABOR_RATES.copy())' in line:
        new.append(line)
        new.append('            self.category_waste_factors = data.get("category_waste_factors", DEFAULT_CATEGORY_WASTE_FACTORS.copy())\n')
        continue
    
    # Додаємо запис в save()
    if '"labor_rates": self.labor_rates,' in line:
        new.append(line)
        new.append('            "category_waste_factors": self.category_waste_factors,\n')
        continue
    
    # Додаємо дефолт в load() else
    if 'self.labor_rates = DEFAULT_LABOR_RATES.copy()' in line:
        new.append(line)
        new.append('            self.category_waste_factors = DEFAULT_CATEGORY_WASTE_FACTORS.copy()\n')
        continue
    
    # Додаємо reset в _reset_defaults
    if 'self.settings.labor_rates = DEFAULT_LABOR_RATES.copy()' in line:
        new.append(line)
        new.append('            self.settings.category_waste_factors = DEFAULT_CATEGORY_WASTE_FACTORS.copy()\n')
        continue
    
    new.append(line)

f = open(sys.argv[1], 'w', encoding='utf-8')
f.writelines(new)
f.close()
print('done')
