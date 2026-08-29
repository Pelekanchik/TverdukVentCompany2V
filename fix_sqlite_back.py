#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "ventilation_company", "db_integration.py")

with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

# Замінюємо to_char назад на strftime для SQLite
replacements = [
    ("func.to_char(ClientProject.end_date, 'YYYY-MM')", 'func.strftime("%Y-%m", ClientProject.end_date)'),
    ("func.to_char(ClientProject.start_date, 'YYYY-MM')", 'func.strftime("%Y-%m", ClientProject.start_date)'),
    ("ClientProject.end_date >= since", 'ClientProject.end_date >= since.strftime("%Y-%m") + "-01"'),
    ("ClientProject.start_date >= since", 'ClientProject.start_date >= since'),
]

for old, new in replacements:
    if old in txt:
        txt = txt.replace(old, new)
        print(f"✅ {old[:40]}... → {new[:40]}...")

with open(path, "w", encoding="utf-8") as f:
    f.write(txt)

print("\nТепер запустіть:  python main.py")
input("\nНатисніть Enter...")