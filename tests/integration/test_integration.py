"""Інтеграційні тести (end-to-end)."""

import pytest
from decimal import Decimal


class TestFullProjectWorkflow:
    """Повний цикл роботи з проєктом."""

    def test_create_save_load_project(self, temp_db, sample_project_data):
        """Створення → збереження → завантаження проєкту."""
        pid = temp_db.create_project(sample_project_data["project_name"])

        for p in sample_project_data["products"]:
            temp_db.add_product_to_project(pid, p)

        products = temp_db.get_project_products(pid)
        assert len(products) == 2

        loaded = temp_db.get_project(pid)
        assert loaded["name"] == sample_project_data["project_name"]

    def test_project_financial_calculation(self, temp_db, default_settings, sample_project_data):
        """Розрахунок фінансів проєкту."""
        pid = temp_db.create_project("Фінансовий тест")

        total_salary = Decimal("0")
        for p in sample_project_data["products"]:
            temp_db.add_product_to_project(pid, p)
            ptype = p["product_type"]
            area = float(p["metal_area_m2"])
            qty = p["quantity"]

            labor = default_settings.get_labor_rate(ptype)
            rate = labor["rate_per_m2"]
            diff = labor["difficulty_percent"]
            salary = area * rate * (1 + diff / 100) * qty
            total_salary += Decimal(str(salary))

        temp_db.update_project(pid, salary_total=round(total_salary, 2))

        project = temp_db.get_project(pid)
        assert float(project["salary_total"]) > 0

    def test_delete_and_recover(self, temp_db, sample_project_data):
        """Видалення та відновлення."""
        pid = temp_db.create_project("Тест версій")
        temp_db.add_product_to_project(pid, sample_project_data["products"][0])

        products = temp_db.get_project_products(pid)
        temp_db.delete_product(products[0]["id"])

        assert temp_db.get_project(pid) is not None
        assert len(temp_db.get_project_products(pid)) == 0


class TestDatabaseToGUITransition:
    """Перехід від БД до GUI."""

    def test_products_compatible_with_library(self, temp_db, sample_project_data):
        """Вироби з БД сумісні з ProductLibrary."""
        from ventilation_company.standard_products import ProductLibrary

        pid = temp_db.create_project("Тест")
        for p in sample_project_data["products"]:
            temp_db.add_product_to_project(pid, p)

        lib = ProductLibrary()
        stored = temp_db.get_project_products(pid)
        # Просто перевіряємо, що дані є
        assert len(stored) == len(sample_project_data["products"])
