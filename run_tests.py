#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Запуск тестів з backup/restore pricing_settings.json."""

import os
import sys
import json
import shutil
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(BASE, "data", "pricing_settings.json")
BACKUP_PATH = SETTINGS_PATH + ".test_backup"

# Тестові налаштування (ставка 120, важкість 20%)
TEST_SETTINGS = {
    "materials": {},
    "labor_rates": {
        "повітропровід прямокутний": {"rate_per_m2": 120.0, "difficulty_percent": 20.0},
        "повітропровід круглий": {"rate_per_m2": 120.0, "difficulty_percent": 20.0}
    },
    "markup_percent": 30.0,
    "vat": {"rate": 20.0}
}

def main():
    # 1. Backup оригіналу
    if os.path.exists(SETTINGS_PATH):
        shutil.copy(SETTINGS_PATH, BACKUP_PATH)
        print("Backup pricing_settings.json створено")
    else:
        print("Оригінал pricing_settings.json не знайдено, створюємо тестовий")

    # 2. Пишемо тестові налаштування
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(TEST_SETTINGS, f, ensure_ascii=False, indent=2)
    print("Тестові налаштування записано (ставка 120, важкість 20%)")

    # 3. Скидаємо сінглтон PricingSettings
    try:
        from ventilation_company.gui.settings_tab import PricingSettings
        PricingSettings._instance = None
        print("PricingSettings скинуто")
    except Exception as e:
        print("Не вдалося скинути PricingSettings:", e)

    # 4. Запускаємо тести
    print("")
    print("=" * 55)
    print("ЗАПУСК ТЕСТІВ")
    print("=" * 55)
    print("")
    
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.test_salary", "-v"],
        cwd=BASE
    )

    # 5. Відновлюємо оригінал
    if os.path.exists(BACKUP_PATH):
        shutil.copy(BACKUP_PATH, SETTINGS_PATH)
        os.remove(BACKUP_PATH)
        print("")
        print("Оригінал pricing_settings.json відновлено")
    else:
        os.remove(SETTINGS_PATH)
        print("")
        print("Тестовий pricing_settings.json видалено")

    # 6. Результат
    print("")
    print("=" * 55)
    if result.returncode == 0:
        print("УСІ ТЕСТИ ПРОЙДЕНІ!")
    else:
        print("ДЕЯКІ ТЕСТИ НЕ ПРОЙДЕНІ")
    print("=" * 55)

    input("")
    print("Натисніть Enter...")


if __name__ == "__main__":
    main()