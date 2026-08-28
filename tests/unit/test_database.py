"""Тести бази даних та міграцій."""

import pytest
from decimal import Decimal


class TestProjectDatabase:
    """Тести ProjectDatabase."""

    def test_create_project(self, temp_db):
        """Створення проєкту."""
        pid = temp_db.create_project("Тест")
        assert pid > 0
        project = temp_db.get_project(pid)
        assert project["name"] == "Тест"

    def test_add_product_to_project(self, temp_db, sample_project_data):
        """Додавання виробу до проєкту."""
        pid = temp_db.create_project("Тест")
        products = sample_project_data["products"]
        for p in products:
            temp_db.add_product_to_project(pid, p)

        stored = temp_db.get_project_products(pid)
        assert len(stored) == 2
        assert stored[0]["name"] == "Повітропровід 400×200×1000"

    def test_update_project(self, temp_db):
        """Оновлення проєкту."""
        pid = temp_db.create_project("Старе ім'я")
        temp_db.update_project(pid, name="Нове ім'я", salary_total=Decimal("150.50"))
        project = temp_db.get_project(pid)
        assert project["name"] == "Нове ім'я"
        assert float(project["salary_total"]) == 150.50

    def test_delete_product(self, temp_db, sample_project_data):
        """Видалення виробу."""
        pid = temp_db.create_project("Тест")
        temp_db.add_product_to_project(pid, sample_project_data["products"][0])
        stored = temp_db.get_project_products(pid)
        temp_db.delete_product(stored[0]["id"])
        assert len(temp_db.get_project_products(pid)) == 0

    def test_standard_products_library(self, temp_db):
        """Бібліотека стандартних виробів."""
        sid = temp_db.add_standard_product(
            name="Тестовий виріб",
            product_type="повітропровід",
            width=100,
            height=50,
            length=500,
            thickness=0.7,
            material="оцинкована сталь",
        )
        assert sid > 0
        products = temp_db.get_standard_products()
        assert len(products) >= 1


class TestDatabaseIntegrity:
    """Тести цілісності даних."""

    def test_project_cascade_delete(self, temp_db, sample_project_data):
        """Каскадне видалення: при видаленні проєкту вироби теж видаляються."""
        pid = temp_db.create_project("Тест")
        temp_db.add_product_to_project(pid, sample_project_data["products"][0])
        temp_db.delete_project(pid)
        assert temp_db.get_project(pid) is None
        assert len(temp_db.get_project_products(pid)) == 0

    def test_decimal_precision(self, temp_db):
        """Точність Decimal для грошових значень."""
        pid = temp_db.create_project("Тест")
        temp_db.update_project(pid, salary_total=Decimal("123.45"))
        project = temp_db.get_project(pid)
        assert abs(float(project["salary_total"]) - 123.45) < 0.01
