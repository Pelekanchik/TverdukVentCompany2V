#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))

# 1. Чистимо кеш
for root, dirs, files in os.walk(BASE):
    for d in list(dirs):
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d))
            dirs.remove(d)
print("🗑️  Кеш очищено")

# 2. Завантажуємо оригінал
print("⬇️  Завантаження оригіналу...")
url = "https://raw.githubusercontent.com/Pelekanchik/TverdukVentCompany2V/main/ventilation_company/gui/main_window.py"
try:
    with urllib.request.urlopen(url, timeout=15) as r:
        txt = r.read().decode('utf-8')
    print("✅ Завантажено")
except Exception as e:
    print(f"❌ Помилка: {e}")
    input("Enter...")
    exit(1)

# 3. Правильно видаляємо Прайс-лист — ПОВНІСТЮ видаляємо рядки, не коментуємо
replacements = [
    # import
    ("from ventilation_company.gui.price_list_tab import PriceListTab\n", ""),
    # створення
    ("        self.price_list_tab = PriceListTab(self.finance_nb, self.theme_manager, self.db, self)\n", ""),
    # додавання у finance_nb
    ('        self.finance_nb.add(self.price_list_tab.frame, text="🏷️ Прайс-лист")\n', ""),
    # пункт у сайдбарі — ВИДАЛЯЄМО ЦЕЙ ЕЛЕМЕНТ
    ('            ("🏷️", "Прайс-лист", self.finance_nb, 1),\n', ""),
    # _save_project
    ("        self.price_list_tab._current_project_id = project_id\n", ""),
    # _load_project_data
    ("        self.price_list_tab._current_project_id = self.current_project_id\n", ""),
    # _on_theme_change — ВИДАЛЯЄМО цей елемент зі списку (важливо: не коментувати, а видалити!)
    ('                 "price_list_tab",\n', ""),
]

for old, new in replacements:
    if old in txt:
        txt = txt.replace(old, new)
        print(f"🗑️  Видалено: {old.strip()}")
    else:
        print(f"⚠️  Не знайдено: {old.strip()[:50]}")

# 4. Зберігаємо
path = os.path.join(BASE, "ventilation_company", "gui", "main_window.py")
with open(path, "w", encoding="utf-8") as f:
    f.write(txt)

# 5. Перевіряємо синтаксис
try:
    compile(txt, path, 'exec')
    print("\n✅ Синтаксис Python OK")
except SyntaxError as e:
    print(f"\n❌ Синтаксична помилка: {e}")
    print("   Файл збережено, але має помилку!")

print("\n" + "=" * 55)
print("✅ Прайс-лист видалено!")
print("=" * 55)
print("\nТепер запустіть:  python main.py")
print("=" * 55)
input("\nНатисніть Enter...")