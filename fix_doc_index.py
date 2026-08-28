#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "ventilation_company", "gui", "main_window.py")

with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

# Знаходимо рядок з "Документи" і змінюємо індекс з 2 на 1
if '"Документи", self.finance_nb, 2' in txt:
    txt = txt.replace('"Документи", self.finance_nb, 2', '"Документи", self.finance_nb, 1')
    print("✅ Індекс 'Документи' змінено: 2 → 1")
elif "self.finance_nb, 2" in txt:
    txt = txt.replace("self.finance_nb, 2", "self.finance_nb, 1")
    print("✅ Індекс змінено: 2 → 1")
else:
    print("⚠️  Індекс 2 не знайдено — можливо, вже виправлено")

with open(path, "w", encoding="utf-8") as f:
    f.write(txt)

print("\nТепер запустіть:  python main.py")
input("\nНатисніть Enter...")