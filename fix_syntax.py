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

# 2. Завантажуємо оригінал main_window.py
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

# 3. Правильно видаляємо Прайс-лист — замінюємо рядки на pass/пропуск, зберігаючи синтаксис
# 3a. Import
txt = txt.replace(
    "from ventilation_company.gui.price_list_tab import PriceListTab",
    "# from ventilation_company.gui.price_list_tab import PriceListTab  # ВИДАЛЕНО"
)

# 3b. Створення у __init__
txt = txt.replace(
    "        self.price_list_tab = PriceListTab(self.finance_nb, self.theme_manager, self.db, self)",
    "        # self.price_list_tab = PriceListTab(...)  # ВИДАЛЕНО\n        self.price_list_tab = None  # заглушка"
)

# 3c. Додавання у finance_nb
txt = txt.replace(
    '        self.finance_nb.add(self.price_list_tab.frame, text="🏷️ Прайс-лист")',
    '        # self.finance_nb.add(self.price_list_tab.frame, text="🏷️ Прайс-лист")  # ВИДАЛЕНО'
)

# 3d. Пункт у сайдбарі — ВИДАЛЯЄМО ЦЕЙ ЕЛЕМЕНТ З СПИСКУ повністю
old_sidebar = '''            ("🏷️", "Прайс-лист", self.finance_nb, 1),
            ("🧾", "Документи", self.finance_nb, 2),'''
new_sidebar = '''            # ("🏷️", "Прайс-лист", self.finance_nb, 1),  # ВИДАЛЕНО
            ("🧾", "Документи", self.finance_nb, 2),'''
txt = txt.replace(old_sidebar, new_sidebar)

# 3e. Звернення у _save_project
txt = txt.replace(
    "        self.price_list_tab._current_project_id = project_id",
    "        # self.price_list_tab._current_project_id = project_id  # ВИДАЛЕНО"
)

# 3f. Звернення у _load_project_data
txt = txt.replace(
    "        self.price_list_tab._current_project_id = self.current_project_id",
    "        # self.price_list_tab._current_project_id = ...  # ВИДАЛЕНО"
)

# 3g. _on_theme_change
txt = txt.replace(
    '            "price_list_tab",',
    '            # "price_list_tab",  # ВИДАЛЕНО'
)

# 4. Зберігаємо
path = os.path.join(BASE, "ventilation_company", "gui", "main_window.py")
with open(path, "w", encoding="utf-8") as f:
    f.write(txt)
print(f"✅ Файл збережено")

# 5. Перевіряємо синтаксис
try:
    compile(txt, path, 'exec')
    print("✅ Синтаксис Python OK")
except SyntaxError as e:
    print(f"❌ Синтаксична помилка: {e}")

print("\n" + "=" * 55)
print("✅ Прайс-лист видалено, синтаксис виправлено!")
print("=" * 55)
print("\nТепер запустіть:  python main.py")
print("=" * 55)
input("\nНатисніть Enter...")