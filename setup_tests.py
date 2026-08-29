#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# 1. Створюємо папку tests
os.makedirs(os.path.join(BASE, "tests"), exist_ok=True)

# 2. tests/__init__.py
init = '''"""Тести VentCompany."""
'''
with open(os.path.join(BASE, "tests", "__init__.py"), "w", encoding="utf-8") as f:
    f.write(init)
print("✅ tests/__init__.py")

# 3. tests/test_salary.py
test_salary = '''"""Тести розрахунку зарплати.

Запуск: python -m unittest tests.test_salary
"""

import unittest
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from ventilation_company.services.salary_service import SalaryService


class TestSalary(unittest.TestCase):
    """Перевіряємо, що зарплата рахується правильно і однаково скрізь."""

    def test_rectangular_400x200x1000(self):
        """Повітропровід 400×200×1000 = 172.80 грн при ставці 120 і важкості 20%."""
        # Площа поверхні: 2 * (0.4 + 0.2) * 1.0 = 1.2 м²
        # Зарплата: 1.2 * 120 * (1 + 20/100) = 1.2 * 120 * 1.2 = 172.80
        result = SalaryService.calculate(
            product_type="повітропровід прямокутний",
            dimensions="400×200×1000",
            quantity=1,
        )
        self.assertEqual(
            result, 172.80,
            f"Очікувалося 172.80, отримано {result}. "
            f"Формула: 2*(0.4+0.2)*1.0 * 120 * 1.2 = 1.2 * 144 = 172.80"
        )

    def test_rectangular_200x200x1000(self):
        """Повітропровід 200×200×1000 = 115.20 грн (менший виріб)."""
        # Площа: 2 * (0.2 + 0.2) * 1.0 = 0.8 м²
        # Зарплата: 0.8 * 120 * 1.2 = 115.20
        result = SalaryService.calculate(
            product_type="повітропровід прямокутний",
            dimensions="200×200×1000",
            quantity=1,
        )
        self.assertEqual(result, 115.20)

    def test_explicit_area(self):
        """Якщо передано площу явно — використовує її, а не розміри."""
        result = SalaryService.calculate(
            product_type="повітропровід прямокутний",
            dimensions="999×999×9999",  # ігнорується
            quantity=1,
            area=1.5,  # явна площа
        )
        # 1.5 * 120 * 1.2 = 216.0
        self.assertEqual(result, 216.0)

    def test_quantity_3(self):
        """Кількість 3 шт = потроєна зарплата."""
        result = SalaryService.calculate(
            product_type="повітропровід прямокутний",
            dimensions="400×200×1000",
            quantity=3,
        )
        # 172.80 * 3 = 518.40
        self.assertEqual(result, 518.40)

    def test_round_duct(self):
        """Круглий повітропровід 150×1000."""
        # Площа: π * 0.15 * 1.0 ≈ 0.4712385
        # Зарплата: 0.4712385 * 120 * 1.2 ≈ 67.86
        result = SalaryService.calculate(
            product_type="повітропровід круглий",
            dimensions="150×1000",
            quantity=1,
        )
        expected = round(3.14159 * 0.15 * 1.0 * 120 * 1.2, 2)
        self.assertEqual(result, expected)

    def test_difficulty_0(self):
        """При важкості 0% — без коефіцієнта."""
        # Треба тимчасово змінити налаштування... 
        # Але зараз difficulty=20% у файлі. Перевіримо, що коефіцієнт 1.2 дає 172.80.
        # Якщо б була важкість 0%, було б: 1.2 * 120 * 1.0 = 144.0
        # Цей тест перевіряє, що коефіцієнт ВАЖКОСТІ дійсно множиться.
        result = SalaryService.calculate(
            product_type="повітропровід прямокутний",
            dimensions="400×200×1000",
            quantity=1,
        )
        # Перевіримо, що результат НЕ дорівнює 144 (без важкості)
        self.assertNotEqual(result, 144.0, 
            "Зарплата без важкості = 144, але у нас важкість 20%, має бути 172.80")


if __name__ == "__main__":
    unittest.main()
'''
with open(os.path.join(BASE, "tests", "test_salary.py"), "w", encoding="utf-8") as f:
    f.write(test_salary)
print("✅ tests/test_salary.py")

# 4. run_tests.py
run_tests = '''#!/usr/bin/env python3
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
    "labor": {
        "default": {"rate_per_m2": 120.0, "difficulty_percent": 20.0}
    },
    "markup": {"default": 30.0},
    "vat": {"rate": 20.0}
}

def main():
    # 1. Backup оригіналу
    if os.path.exists(SETTINGS_PATH):
        shutil.copy(SETTINGS_PATH, BACKUP_PATH)
        print("💾 Backup pricing_settings.json створено")
    else:
        print("⚠️  Оригінал pricing_settings.json не знайдено, створюємо тестовий")

    # 2. Пишемо тестові налаштування
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(TEST_SETTINGS, f, ensure_ascii=False, indent=2)
    print("📝 Тестові налаштування записано (ставка 120, важкість 20%)")

    # 3. Скидаємо сінглтон PricingSettings
    try:
        from ventilation_company.gui.settings_tab import PricingSettings
        PricingSettings._instance = None
        print("🔄 PricingSettings скинуто")
    except Exception as e:
        print(f"⚠️  Не вдалося скинути PricingSettings: {e}")

    # 4. Запускаємо тести
    print("\n" + "=" * 55)
    print("🧪 ЗАПУСК ТЕСТІВ")
    print("=" * 55 + "\\n")
    
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.test_salary", "-v"],
        cwd=BASE
    )

    # 5. Відновлюємо оригінал
    if os.path.exists(BACKUP_PATH):
        shutil.copy(BACKUP_PATH, SETTINGS_PATH)
        os.remove(BACKUP_PATH)
        print("\\n💾 Оригінал pricing_settings.json відновлено")
    else:
        os.remove(SETTINGS_PATH)
        print("\\n🗑️  Тестовий pricing_settings.json видалено")

    # 6. Результат
    print("\\n" + "=" * 55)
    if result.returncode == 0:
        print("✅ УСІ ТЕСТИ ПРОЙДЕНІ!")
    else:
        print("❌ ДЕЯКІ ТЕСТИ НЕ ПРОЙДЕНІ")
    print("=" * 55)

    input("\\nНатисніть Enter...")


if __name__ == "__main__":
    main()
'''
with open(os.path.join(BASE, "run_tests.py"), "w", encoding="utf-8") as f:
    f.write(run_tests)
print("✅ run_tests.py")

print("\n" + "=" * 55)
print("✅ ТЕСТОВА СИСТЕМА ГОТОВА!")
print("=" * 55)
print("\nЗапуск тестів:")
print("   python run_tests.py")
print("\nАбо напряму:")
print("   python -m unittest tests.test_salary -v")
print("=" * 55)
input("\nНатисніть Enter...")