#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "ventilation_company", "gui", "production_tab.py")

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print("📄 Рядки з '_calculate_salary' у production_tab.py:\n")
for i, line in enumerate(lines, 1):
    if "_calculate_salary" in line:
        print(f"   Рядок {i}: {line.rstrip()}")

print("\n" + "=" * 55)
print("Якщо бачите 'def _calculate_salary(self, product):' — треба змінити на '(self, product=None)'")
print("=" * 55)
input("\nНатисніть Enter...")