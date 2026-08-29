#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))

# 1. Чистимо кеш
for root, dirs, files in os.walk(BASE):
    for d in list(dirs):
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d))
            dirs.remove(d)
print("🗑️  Кеш очищено")

# 2. Завантажуємо оригінал production_tab.py
print("⬇️  Завантаження оригіналу...")
url = "https://raw.githubusercontent.com/Pelekanchik/TverdukVentCompany2V/main/ventilation_company/gui/production_tab.py"
try:
    with urllib.request.urlopen(url, timeout=15) as r:
        txt = r.read().decode('utf-8')
    print("✅ Завантажено")
except Exception as e:
    print(f"❌ Помилка: {e}")
    input("Enter...")
    exit(1)

# 3. Замінюємо блок розрахунку зарплати на SalaryService
old = '''            # Отримати ставку та важкість
            labor = settings.get_labor_rate(ptype)
            rate = labor.get("rate_per_m2", 120.0)
            difficulty = labor.get("difficulty_percent", 0.0)

            # Розрахунок
            salary_per_unit = area * rate * (1 + difficulty / 100)'''

new = '''            # Розрахунок через SalaryService (уніфікований з усім проєктом)
            from ventilation_company.services import SalaryService
            salary_per_unit = SalaryService.calculate(
                product_type=ptype,
                dimensions=product.get("dimensions", ""),
                quantity=1,
                area=area,
            )
            # Отримати ставку та важкість для відображення
            labor = settings.get_labor_rate(ptype)
            rate = labor.get("rate_per_m2", 120.0)
            difficulty = labor.get("difficulty_percent", 0.0)'''

if old in txt:
    txt = txt.replace(old, new)
    print("✅ Розрахунок зарплати → SalaryService")
else:
    print("⚠️  Блок розрахунку не знайдено")

# 4. Зберігаємо
path = os.path.join(BASE, "ventilation_company", "gui", "production_tab.py")
with open(path, "w", encoding="utf-8") as f:
    f.write(txt)

print("\n" + "=" * 60)
print("✅ ГОТОВО!")
print("=" * 60)
print("\nЗапустіть:  python main.py")
print("=" * 60)
input("\nНатисніть Enter...")