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
print("🗑️  Кеш очищено")

# 2. Видаляємо вкладку "Прайс-лист" з main_window.py
path = os.path.join(BASE, "ventilation_company", "gui", "main_window.py")
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    # Пропускаємо рядки, що додають прайс-лист
    if "self.price_list_tab" in line or 'text="Прайс-лист"' in line or "PriceListTab" in line:
        print(f"🗑️  Видалено: {line.strip()}")
        continue
    new_lines.append(line)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("\n✅ Вкладка 'Прайс-лист' видалена з програми")
print("=" * 55)
print("Тепер запустіть:  python main.py")
print("Вкладки: Проєкт, Виробництво, Аналітика, Кабінет")
print("Прайс-листа НЕМАЄ — плутатися не будете")
print("=" * 55)
input("\nНатисніть Enter...")