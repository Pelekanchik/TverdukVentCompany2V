#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "ventilation_company", "config.py")

with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

old = 'DATABASE_URL = "sqlite:///ventcompany.db"'
new = '# DATABASE_URL = "sqlite:///ventcompany.db"  # SQLite (старий варіант)\nDATABASE_URL = "postgresql://vent:vent123@localhost/ventcompany"  # PostgreSQL'

if old in txt:
    txt = txt.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    print("✅ config.py змінено: SQLite → PostgreSQL")
else:
    # Можливо, вже змінено або інший формат
    if "postgresql" in txt:
        print("✅ PostgreSQL вже налаштовано у config.py")
    else:
        print("⚠️  Рядок з DATABASE_URL не знайдено — перевірте config.py вручну")

print("\nТепер запустіть:  python main.py")
print("Програма використовуватиме PostgreSQL замість SQLite.")
input("\nНатисніть Enter...")