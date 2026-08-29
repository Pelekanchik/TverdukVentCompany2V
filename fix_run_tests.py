#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "run_tests.py")

with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

# Виправляємо структуру JSON — має бути "labor_rates", а не "labor"
old = '''TEST_SETTINGS = {
    "materials": {},
    "labor": {
        "default": {"rate_per_m2": 120.0, "difficulty_percent": 20.0}
    },
    "markup": {"default": 30.0},
    "vat": {"rate": 20.0}
}'''

new = '''TEST_SETTINGS = {
    "materials": {},
    "labor_rates": {
        "повітропровід прямокутний": {"rate_per_m2": 120.0, "difficulty_percent": 20.0},
        "повітропровід круглий": {"rate_per_m2": 130.0, "difficulty_percent": 5.0}
    },
    "markup_percent": 30.0,
    "vat": {"rate": 20.0}
}'''

if old in txt:
    txt = txt.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    print("✅ run_tests.py виправлено — тепер 'labor_rates' замість 'labor'")
else:
    print("⚠️  Блок не знайдено")

print("\nТепер запустіть:  python run_tests.py")
input("\nНатисніть Enter...")