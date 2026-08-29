#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "ventilation_company", "services", "salary_service.py")

with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

old = '''        settings = PricingSettings.get_instance()
        labor = settings.get_labor_rate(product_type or "")
        rate = labor.get("rate_per_m2", 120.0)
        difficulty = labor.get("difficulty_percent", 0.0)'''

new = '''        settings = PricingSettings.get_instance()
        labor = settings.get_labor_rate(product_type or "")
        # Якщо конкретний тип не знайдено — беремо default
        if not labor or labor.get("rate_per_m2") is None:
            labor = settings.get_labor_rate("default") or {}
        rate = labor.get("rate_per_m2", 120.0)
        difficulty = labor.get("difficulty_percent", 0.0)'''

if old in txt:
    txt = txt.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    print("✅ SalaryService виправлено — тепер використовує default налаштування")
else:
    print("⚠️  Блок не знайдено")

print("\nТепер запустіть:  python run_tests.py")
input("\nНатисніть Enter...")