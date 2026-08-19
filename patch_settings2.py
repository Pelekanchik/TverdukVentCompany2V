"""
Патч для settings_tab.py — додає метод get_category_waste_factor
"""
import sys

f = open(sys.argv[1], encoding='utf-8')
lines = f.readlines()
f.close()

new = []
for i, line in enumerate(lines):
    # Додаємо метод get_category_waste_factor після get_labor_rate
    if 'return {"rate_per_m2": 120.0, "difficulty_percent": 0.0}' in line and i > 290:
        new.append(line)
        new.append("\n")
        new.append("    def get_category_waste_factor(self, product_type: str) -> float:\n")
        new.append('        """Отримати %% запасу на брак/поворот для категорії виробу."""\n')
        new.append("        self.reload()\n")
        new.append("        ptype = product_type.lower().strip()\n")
        new.append("        # Визначаємо категорію\n")
        new.append("        category = self._classify_category(ptype)\n")
        new.append("        return self.category_waste_factors.get(category, 0.0)\n")
        new.append("\n")
        new.append("    def _classify_category(self, product_type: str) -> str:\n")
        new.append('        """Класифікувати виріб у одну з 4 категорій."""\n')
        new.append("        pt = product_type.lower().strip()\n")
        new.append('        if "повітропровід прямокутний" in pt:\n')
        new.append('            return "rect_duct"\n')
        new.append('        elif "повітропровід круглий" in pt:\n')
        new.append('            return "round_duct"\n')
        new.append('        elif any(k in pt for k in ["фланець прямокутний", "трійник прямокутний", "перехід прямокутний", "відвід прямокутний", "заглушка прямокутна"]):\n')
        new.append('            return "rect_fitting"\n')
        new.append('        elif any(k in pt for k in ["фланець круглий", "трійник круглий", "перехід круглий", "відвід круглий", "заглушка кругла"]):\n')
        new.append('            return "round_fitting"\n')
        new.append('        else:\n')
        new.append('            return "rect_duct"  # fallback\n')
        continue
    
    new.append(line)

f = open(sys.argv[1], 'w', encoding='utf-8')
f.writelines(new)
f.close()
print('done')
