#!/usr/bin/env python3
"""
ПАТЧ: Автоматичний розрахунок зарплати при збереженні в БД.
"""

import os

# 1. Патчим db_integration.py
db_path = "ventilation_company/db_integration.py"

with open(db_path, "r", encoding="utf-8") as f:
    content = f.read()

old_add = '''    def add_product_to_project(self, project_id, product_data):
        with self._session_scope() as session:
            product = ProjectProduct(project_id=project_id, **product_data)
            session.add(product)
            session.commit()
            return product.id'''

new_add = '''    def add_product_to_project(self, project_id, product_data):
        # Автоматичний розрахунок зарплати перед збереженням
        from ventilation_company.gui.settings_tab import PricingSettings
        settings = PricingSettings.get_instance()
        ptype = product_data.get("product_type", "")
        metal_area = product_data.get("metal_area_m2", 0) or product_data.get("surface_area", 0)
        if metal_area and ptype:
            labor = settings.get_labor_rate(ptype)
            rate = labor.get("rate_per_m2", 120.0)
            difficulty = labor.get("difficulty_percent", 0.0)
            salary = metal_area * rate * (1 + difficulty / 100)
            product_data["salary_per_unit"] = round(salary, 2)
            product_data["salary_total"] = round(salary * product_data.get("quantity", 1), 2)
        
        with self._session_scope() as session:
            product = ProjectProduct(project_id=project_id, **product_data)
            session.add(product)
            session.commit()
            return product.id'''

if old_add in content:
    content = content.replace(old_add, new_add)
    print("OK: db_integration.py пропатчено")
else:
    print("WARNING: Не знайдено add_product_to_project")

with open(db_path, "w", encoding="utf-8") as f:
    f.write(content)

# 2. Патчим main_window.py
mw_path = "ventilation_company/gui/main_window.py"

with open(mw_path, "r", encoding="utf-8") as f:
    content = f.read()

# Додаємо метод _recalculate_salaries перед _save_project
old_save = '''    def _save_project(self):
        """Зберегти проєкт: оновлює існуючий або створює новий."""
        products = self._get_products()'''

new_save = '''    def _recalculate_salaries(self, products):
        """Перерахувати зарплату для всіх виробів з актуальними ставками."""
        from ventilation_company.gui.settings_tab import PricingSettings
        settings = PricingSettings.get_instance()
        for p in products:
            ptype = p.get("product_type", "")
            metal_area = p.get("metal_area_m2", 0) or p.get("surface_area", 0)
            qty = p.get("quantity", 1)
            if metal_area and ptype:
                labor = settings.get_labor_rate(ptype)
                rate = labor.get("rate_per_m2", 120.0)
                difficulty = labor.get("difficulty_percent", 0.0)
                salary = metal_area * rate * (1 + difficulty / 100)
                p["salary_per_unit"] = round(salary, 2)
                p["salary_total"] = round(salary * qty, 2)

    def _save_project(self):
        """Зберегти проєкт: оновлює існуючий або створює новий."""
        products = self._get_products()
        # Перераховуємо зарплати перед збереженням
        self._recalculate_salaries(products)'''

if old_save in content:
    content = content.replace(old_save, new_save)
    print("OK: main_window.py пропатчено (_save_project)")
else:
    print("WARNING: Не знайдено _save_project")

# Додаємо перерахунок в _auto_save
old_auto = '''    def _auto_save(self):
        """Автозбереження тепер у SQLite БД замість JSON-файлів."""
        try:
            products = self._get_products()'''

new_auto = '''    def _auto_save(self):
        """Автозбереження тепер у SQLite БД замість JSON-файлів."""
        try:
            products = self._get_products()
            # Перераховуємо зарплати перед автозбереженням
            self._recalculate_salaries(products)'''

if old_auto in content:
    content = content.replace(old_auto, new_auto)
    print("OK: main_window.py пропатчено (_auto_save)")
else:
    print("WARNING: Не знайдено _auto_save")

with open(mw_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\nГотово! Очисти кеш і перезапусти VentCompany.")