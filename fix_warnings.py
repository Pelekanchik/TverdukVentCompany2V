#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))

# Чистимо кеш
for root, dirs, files in os.walk(BASE):
    for d in list(dirs):
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d))
            dirs.remove(d)

# Знаходимо файли з "📊" і замінюємо на текст "Chart" або просто прибираємо
files_to_check = [
    "ventilation_company/production_gantt.py",
    "ventilation_company/gui/production_tab.py",
]

for fname in files_to_check:
    path = os.path.join(BASE, fname)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read()
        if "📊" in txt:
            txt = txt.replace("📊", "")  # просто прибираємо емодзі
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
            print(f"✅ Прибрано 📊 з {fname}")
        else:
            print(f"[OK] {fname} — немає 📊")
    else:
        print(f"[SKIP] {fname} — не знайдено")

print("\nТепер запустіть:  python main.py")
print("Попереджень не буде.")
input("\nНатисніть Enter...")