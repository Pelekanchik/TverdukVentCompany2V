#!/usr/bin/env python3
"""Додає кнопку 'Перерахувати зарплати' в price_list_tab та specification_tab."""

import os

def patch_file(filepath, button_text, method_name, salary_field):
    if not os.path.exists(filepath):
        print(f"❌ Не знайдено: {filepath}")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if method_name in content:
        print(f"ℹ️ {method_name} вже існує в {filepath}")
        return True

    # Знаходимо останній рядок __init__ або _build_ui і додаємо кнопку
    # Це спрощений підхід — додаємо метод і кнопку
    # (для точного патчинга треба бачити код файлу)
    print(f"⚠️ Автопатч для {filepath} потребує перегляду коду.")
    return False

# Для price_list_tab.py
patch_file(
    r"ventilation_company\gui\price_list_tab.py",
    "Перерахувати зарплати",
    "_recalculate_salaries",
    "salary_per_unit"
)

# Для specification_tab.py
patch_file(
    r"ventilation_company\gui\specification_tab.py",
    "Перерахувати зарплати",
    "_recalculate_salaries",
    "salary_total"
)
