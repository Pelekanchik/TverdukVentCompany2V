#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))

def clean_cache():
    for root, dirs, files in os.walk(BASE):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d))
                dirs.remove(d)

def replace_func(text, func_name, new_body):
    """Замінити тіло функції (від def до наступного def на тому ж рівні відступу)."""
    pattern = rf'(    def {re.escape(func_name)}\(self.*?\n)(.*?)(?=    def [a-zA-Z_]|\Z)'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return text[:match.start()] + new_body + text[match.end():]
    return None

# 1. Чистимо кеш
clean_cache()
print("🗑️  Кеш очищено\n")

# 2. main_window.py
path = os.path.join(BASE, "ventilation_company", "gui", "main_window.py")
with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

# Додаємо import (якщо ще немає)
if "from ventilation_company.services import ProjectService" not in txt:
    txt = txt.replace(
        "from ventilation_company.gui.price_list_tab import PriceListTab",
        "from ventilation_company.gui.price_list_tab import PriceListTab\nfrom ventilation_company.services import ProjectService"
    )
    print("✅ Додано import ProjectService")

# _recalculate_salaries
new = '''    def _recalculate_salaries(self, products):
        """Перерахувати ціни та зарплати перед збереженням."""
        if not products:
            return
        ProjectService.recalculate_products(products)
'''
result = replace_func(txt, "_recalculate_salaries", new)
if result:
    txt = result
    print("✅ _recalculate_salaries → ProjectService")
else:
    print("⚠️  _recalculate_salaries — не знайдено")

# _recalculate_current_project
new = '''    def _recalculate_current_project(self):
        """Перерахувати ціни поточного проєкту."""
        products = self._get_products()
        if not products:
            messagebox.showwarning("Увага", "Немає виробів для перерахунку.")
            return
        updated = ProjectService.recalculate_products(products)
        self._set_products(products)
        self.status_bar.config(text=f"🔄 Перераховано {updated} виробів")
        messagebox.showinfo("Готово", f"Перераховано {updated} виробів.")
'''
result = replace_func(txt, "_recalculate_current_project", new)
if result:
    txt = result
    print("✅ _recalculate_current_project → ProjectService")
else:
    print("⚠️  _recalculate_current_project — не знайдено")

with open(path, "w", encoding="utf-8") as f:
    f.write(txt)

# 3. production_tab.py
path = os.path.join(BASE, "ventilation_company", "gui", "production_tab.py")
with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

new = '''    def _calculate_salary(self, product):
        """Розрахувати зарплату для виробу."""
        from ventilation_company.services import SalaryService
        return SalaryService.calculate(
            product_type=product.get("product_type", ""),
            dimensions=product.get("dimensions", ""),
            quantity=product.get("quantity", 1),
            area=product.get("metal_area_m2", 0),
        )
'''
result = replace_func(txt, "_calculate_salary", new)
if result:
    txt = result
    print("✅ _calculate_salary → SalaryService")
else:
    print("⚠️  _calculate_salary — не знайдено")

with open(path, "w", encoding="utf-8") as f:
    f.write(txt)

print("\n" + "=" * 60)
print("✅ ГОТОВО!")
print("=" * 60)
print("\nЗапустіть:  python main.py")
print("=" * 60)
input("\nНатисніть Enter...")