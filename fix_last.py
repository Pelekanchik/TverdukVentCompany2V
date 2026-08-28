#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "ventilation_company", "gui", "main_window.py")

with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

# Закоментовуємо рядок, де створюється PriceListTab
old = "        self.price_list_tab = PriceListTab(self.finance_nb, get_products_callback=self._get_products)"
new = "        # self.price_list_tab = PriceListTab(...)  # ВИДАЛЕНО"

if old in txt:
    txt = txt.replace(old, new)
    print("✅ Видалено: створення PriceListTab у _build_ui")
else:
    print("⚠️  Не знайдено")

with open(path, "w", encoding="utf-8") as f:
    f.write(txt)

print("\nТепер запустіть:  python main.py")
input("\nНатисніть Enter...")