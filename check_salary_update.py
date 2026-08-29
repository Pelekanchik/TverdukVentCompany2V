#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "ventilation_company", "gui", "production_tab.py")

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print("📄 Рядки 265-285 (навколо виклику _calculate_salary):\n")
for i in range(264, min(285, len(lines))):
    print(f"   {i+1}: {lines[i].rstrip()}")

print("\n📄 Пошук 'salary_tree' у файлі:\n")
for i, line in enumerate(lines, 1):
    if "salary_tree" in line and ("insert" in line or "item(" in line or "delete" in line):
        print(f"   {i}: {line.rstrip()}")

print("\n" + "=" * 55)
input("\nНатисніть Enter...")