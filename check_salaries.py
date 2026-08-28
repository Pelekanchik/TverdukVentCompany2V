#!/usr/bin/env python3
"""Показує зарплату для кожного проєкту у Виробництві vs Архів."""

import os
import sys
from decimal import Decimal

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from ventilation_company.db_integration import ProjectDatabase
from ventilation_company.gui.settings_tab import PricingSettings

db = ProjectDatabase("data/company.db")
settings = PricingSettings.get_instance()

print("=" * 80)
print("🔍 ПЕРЕВІРКА СИНХРОНІЗАЦІЇ ЗАРПЛАТ")
print("=" * 80)

projects = db.get_all_projects()

for project in projects:
    pid = project["id"]
    name = project["name"]
    products = db.get_project_products(pid)

    # Розрахунок "на льоту" (як у Виробництві)
    total_live = Decimal("0")
    for p in products:
        qty = p.get("quantity", 1)
        ptype = p.get("product_type", "")
        metal_area = float(p.get("metal_area_m2", 0))

        labor_info = settings.get_labor_rate(ptype)
        rate = labor_info.get("rate_per_m2", 120.0)
        difficulty = labor_info.get("difficulty_percent", 0.0)
        salary_per_unit = Decimal(str(metal_area * rate * (1 + difficulty / 100)))

        total_live += salary_per_unit * Decimal(str(qty))

    # Значення з БД (Архів)
    total_db = project.get("salary_total") or Decimal("0")

    diff = abs(total_live - total_db)
    status = "✅ ОК" if diff < Decimal("0.01") else f"❌ РОЗБІЖНІСТЬ {diff:.2f} грн"

    print(f"\n📁 Проєкт '{name}' (ID:{pid})")
    print(f"   Виробництво (на льоту): {total_live:.2f} грн")
    print(f"   Архів (з БД):           {total_db:.2f} грн")
    print(f"   {status}")

print("\n" + "=" * 80)