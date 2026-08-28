#!/usr/bin/env python3
"""
СИНХРОНІЗАЦІЯ ВСІХ ФІНАНСОВИХ ПОКАЗНИКІВ
"""

import os
import sys
from decimal import Decimal

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from ventilation_company.db_integration import ProjectDatabase
from ventilation_company.gui.settings_tab import PricingSettings

db = ProjectDatabase("data/company.db")
settings = PricingSettings.get_instance()

print("=" * 70)
print("🔄 СИНХРОНІЗАЦІЯ ВСІХ ФІНАНСОВИХ ПОКАЗНИКІВ")
print("=" * 70)

projects = db.get_all_projects()
updated_projects = 0


def get_overhead_safe(settings_obj, product_type):
    if hasattr(settings_obj, "get_overhead_rate"):
        return settings_obj.get_overhead_rate(product_type)
    data = getattr(settings_obj, "_data", {})
    rates = data.get("overhead_rates", {})
    rate = float(rates.get(product_type, data.get("overhead_rate", 15.0)))
    return rate / 100 if rate > 1 else rate


def get_markup_safe(settings_obj, product_type):
    if hasattr(settings_obj, "get_markup"):
        return settings_obj.get_markup(product_type)
    data = getattr(settings_obj, "_data", {})
    rates = data.get("markup_rates", {})
    rate = float(rates.get(product_type, data.get("markup_percent", 30.0)))
    return rate / 100 if rate > 1 else rate


def get_material_price_safe(settings_obj, material, thickness):
    if hasattr(settings_obj, "get_material_price"):
        return settings_obj.get_material_price(material, thickness)
    data = getattr(settings_obj, "_data", {})
    prices = data.get("metal_prices", {})
    key = f"{material}_{thickness}"
    return float(prices.get(key, 50.0))


for project in projects:
    pid = project["id"]
    name = project["name"]
    products = db.get_project_products(pid)

    if not products:
        continue

    total_salary = Decimal("0")
    total_cost = Decimal("0")
    total_price = Decimal("0")

    for p in products:
        qty = p.get("quantity", 1)
        ptype = p.get("product_type", "")
        metal_area = float(p.get("metal_area_m2", 0))

        # ЗАРПЛАТА
        labor_info = settings.get_labor_rate(ptype)
        rate = labor_info.get("rate_per_m2", 120.0)
        difficulty = labor_info.get("difficulty_percent", 0.0)
        salary_per_unit = Decimal(str(metal_area * rate * (1 + difficulty / 100)))
        salary_total = salary_per_unit * Decimal(str(qty))
        total_salary += salary_total

        # МАТЕРІАЛ
        material = p.get("material", "оцинкована сталь")
        thickness = str(p.get("thickness", 0.7))
        mat_price = get_material_price_safe(settings, material, thickness)
        material_cost = Decimal(str(metal_area * mat_price))

        # НАКЛАДНІ
        overhead_rate = get_overhead_safe(settings, ptype)
        overhead = (material_cost + salary_per_unit) * Decimal(str(overhead_rate))

        # СОБІВАРТІСТЬ
        cost_per_unit = material_cost + salary_per_unit + overhead
        cost_total = cost_per_unit * Decimal(str(qty))
        total_cost += cost_total

        # ЦІНА
        markup = get_markup_safe(settings, ptype)
        price_per_unit = cost_per_unit * Decimal(str(1 + markup))
        price_total = price_per_unit * Decimal(str(qty))
        total_price += price_total

        # Оновлюємо виріб у БД через **kwargs
        db.update_product(
            p["id"],
            salary_per_unit=round(salary_per_unit, 2),
            salary_total=round(salary_total, 2),
            cost_price=round(cost_per_unit, 2),
            unit_price=round(price_per_unit, 2),
            total_price=round(price_total, 2),
        )

    # Оновлюємо проєкт
    profit = total_price - total_cost
    db.update_project(
        pid,
        salary_total=round(total_salary, 2),
        cost_total=round(total_cost, 2),
        price_total=round(total_price, 2),
        profit=round(profit, 2),
    )

    print(f"✅ '{name}' (ID:{pid}): зарплата={total_salary:.2f} | собівартість={total_cost:.2f} | ціна={total_price:.2f} | прибуток={profit:.2f}")
    updated_projects += 1

print(f"\n🎉 Готово! Оновлено {updated_projects} проєктів.")
print("Перезапусти VentCompany, щоб побачити актуальні дані.")