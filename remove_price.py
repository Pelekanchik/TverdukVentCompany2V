#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))

# 1. Чистимо кеш
for root, dirs, files in os.walk(BASE):
    for d in list(dirs):
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d))
            dirs.remove(d)
print("🗑️  Кеш очищено")

# 2. Відкриваємо main_window.py
path = os.path.join(BASE, "ventilation_company", "gui", "main_window.py")
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # Закоментовуємо створення PriceListTab
    if "from ventilation_company.gui.price_list_tab import PriceListTab" in line:
        new_lines.append("# " + line)
        print("🗑️  Закоментовано: import PriceListTab")
    # Закоментовуємо створення вкладки
    elif "self.price_list_tab = PriceListTab" in line:
        new_lines.append("# " + line)
        print("🗑️  Закоментовано: створення price_list_tab")
    # Закоментовуємо додавання у finance_nb
    elif 'self.finance_nb.add(self.price_list_tab.frame, text="🏷️ Прайс-лист")' in line:
        new_lines.append("# " + line)
        print("🗑️  Закоментовано: додавання у finance_nb")
    # Закоментовуємо пункт у сайдбарі
    elif '("🏷️", "Прайс-лист", self.finance_nb, 1),' in line:
        new_lines.append("# " + line)
        print("🗑️  Закоментовано: пункт у сайдбарі")
    # Закоментовуємо звернення до price_list_tab у _save_project
    elif "self.price_list_tab._current_project_id = project_id" in line:
        new_lines.append("# " + line)
        print("🗑️  Закоментовано: звернення у _save_project")
    # Закоментовуємо звернення у _load_project_data
    elif "self.price_list_tab._current_project_id = self.current_project_id" in line:
        new_lines.append("# " + line)
        print("🗑️  Закоментовано: звернення у _load_project_data")
    # Закоментовуємо у _on_theme_change
    elif '"price_list_tab"' in line:
        new_lines.append("# " + line)
        print("🗑️  Закоментовано: звернення у _on_theme_change")
    else:
        new_lines.append(line)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("\n" + "=" * 55)
print("✅ Прайс-лист видалено з програми!")
print("=" * 55)
print("\nТепер запустіть:  python main.py")
print("Вкладки: Проєкт, Фінанси (Ціноутворення, Документи),")
print("          Виробництво, Аналітика, Кабінет")
print("=" * 55)
input("\nНатисніть Enter...")