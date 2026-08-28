#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))

# 1. Чистимо кеш
for root, dirs, files in os.walk(BASE):
    for d in list(dirs):
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d))
            dirs.remove(d)
print("🗑️  Кеш очищено\n")

# 2. Дивимося, що насправді у cost_engine.py
path = os.path.join(BASE, "ventilation_company", "calculations", "cost_engine.py")
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print("📄 cost_engine.py — рядки з 'labor_cost':")
for i, line in enumerate(lines, 1):
    if "labor_cost" in line:
        print(f"   Рядок {i}: {line.rstrip()}")

# 3. Виправляємо жорстко — шукаємо ТОЧНО цей рядок
fixed = False
for i, line in enumerate(lines):
    if "result.labor_cost" in line and "blank_area_m2" in line:
        old = line
        new = line.replace("blank_area_m2", "surface_area_m2")
        lines[i] = new
        print(f"\n🔧 ЗАМІНЕНО:\n   БУЛО: {old.rstrip()}\n   СТАЛО: {new.rstrip()}")
        fixed = True
        break

if fixed:
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("✅ cost_engine.py виправлено")
else:
    print("\n⚠️  Рядок з blank_area_m2 НЕ знайдено")
    print("   Можливо, вже виправлено, або файл сильно відрізняється")

# 4. Дивимося price_list_tab.py
path = os.path.join(BASE, "ventilation_company", "gui", "price_list_tab.py")
with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

print("\n📄 price_list_tab.py:")
if "_estimate_area" in txt:
    print("   ✅ _estimate_area() — Є")
else:
    print("   ❌ _estimate_area() — НЕМАЄ (файл не виправлений)")

if "item.recalculate()" in txt and "_recalculate_salaries" in txt:
    print("   ✅ _recalculate_salaries() — спрощено")
else:
    print("   ❌ _recalculate_salaries() — НЕ спрощено")

if "CostEngine(pricing)" in txt:
    print("   ✅ CostEngine — додано у import_from_products")
else:
    print("   ❌ CostEngine — НЕ додано")

print("\n" + "=" * 60)
print("Тепер запустіть:  python main.py")
print("Потім у Прайс-листі натисніть '🔄 Оновити прайс'")
print("=" * 60)
input("\nНатисніть Enter...")