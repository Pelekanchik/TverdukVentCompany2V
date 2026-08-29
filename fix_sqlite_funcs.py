#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "ventilation_company", "db_integration.py")

with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

# Замінюємо strftime на TO_CHAR для PostgreSQL
# SQLite: strftime('%Y-%m', date)  →  PostgreSQL: TO_CHAR(date, 'YYYY-MM')

old = "func.strftime('%Y-%m', ClientProject.end_date)"
new = "func.to_char(ClientProject.end_date, 'YYYY-MM')"

if old in txt:
    txt = txt.replace(old, new)
    print("✅ strftime('%Y-%m') → to_char(..., 'YYYY-MM')")

# Можуть бути інші strftime — шукаємо
import re
matches = re.findall(r"func\.strftime\((.*?)\)", txt)
if matches:
    print(f"⚠️  Знайдено ще {len(matches)} strftime: {matches}")
    # Замінюємо всі generic
    txt = re.sub(
        r"func\.strftime\('([^']*)',\s*([^)]+)\)",
        lambda m: f"func.to_char({m.group(2)}, '{m.group(1).replace('%Y', 'YYYY').replace('%m', 'MM').replace('%d', 'DD')}')",
        txt
    )
    print("✅ Всі strftime замінено на to_char")

with open(path, "w", encoding="utf-8") as f:
    f.write(txt)

print("\nТепер запустіть:  python main.py")
input("\nНатисніть Enter...")