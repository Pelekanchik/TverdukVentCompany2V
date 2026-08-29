#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "ventilation_company", "gui", "production_tab.py")

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print("📄 Тіло _calculate_salary (рядки 175-210):\n")
for i in range(174, min(210, len(lines))):
    print(f"   {i+1}: {lines[i].rstrip()}")

print("\n📄 Виклик (рядок 274):\n")
print(f"   274: {lines[273].rstrip()}")

print("\n📄 Рядок 132 (кнопка):\n")
print(f"   132: {lines[131].rstrip()}")

print("\n" + "=" * 55)
input("\nНатисніть Enter...")