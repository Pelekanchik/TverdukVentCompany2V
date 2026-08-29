#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "run_tests.py")

with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

# Міняємо ставку для круглого на 120 і важкість 20% (як у прямокутного)
old = '"повітропровід круглий": {"rate_per_m2": 130.0, "difficulty_percent": 5.0}'
new = '"повітропровід круглий": {"rate_per_m2": 120.0, "difficulty_percent": 20.0}'

if old in txt:
    txt = txt.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    print("✅ Ставка для круглого змінена: 130/5% → 120/20%")
else:
    print("⚠️  Блок не знайдено")

print("\nТепер запустіть:  python run_tests.py")
input("\nНатисніть Enter...")