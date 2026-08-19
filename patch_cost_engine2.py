"""
Патч для cost_engine.py — додає _get_category_waste_percent
"""
import sys

f = open(sys.argv[1], encoding='utf-8')
lines = f.readlines()
f.close()

new = []
for i, line in enumerate(lines):
    # Додаємо метод _get_category_waste_percent після _get_markup_percent
    if 'return self.pricing.get("markup_percent", 30.0)' in line:
        new.append(line)
        new.append("\n")
        new.append("    def _get_category_waste_percent(self, product_type: str) -> float:\n")
        new.append('        """Отримати %% запасу на брак/поворот для категорії виробу."""\n')
        new.append("        factors = self.pricing.get(\"category_waste_factors\", {})\n")
        new.append("        pt = product_type.lower().strip()\n")
        new.append('        if "повітропровід прямокутний" in pt:\n')
        new.append('            return factors.get("rect_duct", 0.0)\n')
        new.append('        elif "повітропровід круглий" in pt:\n')
        new.append('            return factors.get("round_duct", 0.0)\n')
        new.append('        elif any(k in pt for k in ["фланець прямокутний", "трійник прямокутний", "перехід прямокутний", "відвід прямокутний", "заглушка прямокутна"]):\n')
        new.append('            return factors.get("rect_fitting", 0.0)\n')
        new.append('        elif any(k in pt for k in ["фланець круглий", "трійник круглий", "перехід круглий", "відвід круглий", "заглушка кругла"]):\n')
        new.append('            return factors.get("round_fitting", 0.0)\n')
        new.append('        return 0.0\n')
        continue
    
    # Змінюємо calculate() — якщо category_waste_percent = 0, беремо з pricing
    if 'result.category_waste_percent = category_waste_percent' in line:
        new.append('        if category_waste_percent == 0.0:\n')
        new.append('            category_waste_percent = self._get_category_waste_percent(product_type)\n')
        new.append(line)
        continue
    
    new.append(line)

f = open(sys.argv[1], 'w', encoding='utf-8')
f.writelines(new)
f.close()
print('done')
