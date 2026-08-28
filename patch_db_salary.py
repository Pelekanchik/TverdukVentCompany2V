#!/usr/bin/env python3
"""Універсальний патч db_integration.py — додає розрахунок зарплати."""

import os

filepath = "ventilation_company/db_integration.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Знаходимо рядок з "def add_product_to_project"
insert_idx = None
for i, line in enumerate(lines):
    if "def add_product_to_project" in line:
        insert_idx = i
        break

if insert_idx is None:
    print("ERROR: Не знайдено add_product_to_project")
    exit(1)

# Перевіряємо, чи вже є розрахунок зарплати
content = "".join(lines)
if "PricingSettings" in content and "add_product_to_project" in content:
    print("INFO: Можливо, розрахунок вже є — перевірте вручну")

# Знаходимо рядок "with self._session_scope()" всередині методу
session_idx = None
for i in range(insert_idx, min(insert_idx + 15, len(lines))):
    if "with self._session_scope()" in lines[i]:
        session_idx = i
        break

if session_idx is None:
    print("ERROR: Не знайдено session_scope в add_product_to_project")
    exit(1)

# Вставляємо розрахунок зарплати перед session_scope
indent = "        "
new_code = [
    indent + "# Автоматичний розрахунок зарплати\n",
    indent + "from ventilation_company.gui.settings_tab import PricingSettings\n",
    indent + "settings = PricingSettings.get_instance()\n",
    indent + "ptype = product_data.get('product_type', '')\n",
    indent + "metal_area = product_data.get('metal_area_m2', 0) or product_data.get('surface_area', 0)\n",
    indent + "if metal_area and ptype:\n",
    indent + "    labor = settings.get_labor_rate(ptype)\n",
    indent + "    rate = labor.get('rate_per_m2', 120.0)\n",
    indent + "    difficulty = labor.get('difficulty_percent', 0.0)\n",
    indent + "    salary = metal_area * rate * (1 + difficulty / 100)\n",
    indent + "    product_data['salary_per_unit'] = round(salary, 2)\n",
    indent + "    product_data['salary_total'] = round(salary * product_data.get('quantity', 1), 2)\n",
    "\n",
]

lines = lines[:session_idx] + new_code + lines[session_idx:]

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(lines)

print(f"OK: {filepath} пропатчено")
print("Розрахунок зарплати додано перед session_scope")
