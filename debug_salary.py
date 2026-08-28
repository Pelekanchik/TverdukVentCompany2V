#!/usr/bin/env python3
"""Діагностика: чому зарплата різна у Виробництві vs Архіві."""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from ventilation_company.db_integration import ProjectDatabase
from ventilation_company.gui.settings_tab import PricingSettings

db = ProjectDatabase("data/company.db")
settings = PricingSettings.get_instance()

print("=" * 70)
print("🔍 ДІАГНОСТИКА ЗАРПЛАТИ")
print("=" * 70)

# 1. Показуємо актуальні ставки
print("\n📊 АКТУАЛЬНІ СТАВКИ (PricingSettings):")
for ptype in ["повітропровід прямокутний", "повітропровід круглий", 
              "перехід прямокутний", "трійник прямокутний"]:
    info = settings.get_labor_rate(ptype)
    print(f"   {ptype:30s}: {info['rate_per_m2']:6.2f} грн/м², важкість {info['difficulty_percent']}%")

# 2. Беремо останній проєкт (987 зі скріншоту)
projects = db.get_all_projects()
latest = projects[-1] if projects else None

if latest:
    pid = latest["id"]
    name = latest["name"]
    print(f"\n📁 Проєкт '{name}' (ID:{pid}):")
    print(f"   Зарплата в Архіві (БД): {latest.get('salary_total', 0)} грн")
    
    products = db.get_project_products(pid)
    print(f"\n   Виробів у проєкті: {len(products)}")
    
    total_live = 0.0
    for p in products:
        ptype = p.get("product_type", "???")
        metal_area = p.get("metal_area_m2", 0)
        qty = p.get("quantity", 1)
        stored_salary = p.get("salary_per_unit", 0) or 0
        
        # Розрахунок "на льоту" (як у Виробництві)
        labor_info = settings.get_labor_rate(ptype)
        rate = labor_info.get("rate_per_m2", 120.0)
        difficulty = labor_info.get("difficulty_percent", 0.0)
        live_salary = metal_area * rate * (1 + difficulty / 100)
        
        total_live += live_salary * qty
        
        print(f"\n   📦 {p.get('name', 'Без назви')}")
        print(f"      Тип: {ptype}")
        print(f"      Площа: {metal_area} м²")
        print(f"      Збережена зарплата: {stored_salary:.2f} грн")
        print(f"      Розрахунок 'на льоту': {live_salary:.2f} грн")
        print(f"      Різниця: {abs(live_salary - stored_salary):.2f} грн")
    
    print(f"\n   📊 Підсумок:")
    print(f"      Зарплата в БД (Архів): {float(latest.get('salary_total') or 0):.2f} грн")
    print(f"      Розрахунок 'на льоту': {total_live:.2f} грн")
    print(f"      Різниця: {abs(total_live - float(latest.get('salary_total') or 0)):.2f} грн")

print("\n" + "=" * 70)
print("💡 Якщо 'Розрахунок на льоту' ≠ 'Збережена зарплата' — запусти:")
print("   python sync_all.py")
print("=" * 70)