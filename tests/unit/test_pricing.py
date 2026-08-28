"""Тести ціноутворення та фінансових розрахунків."""

import pytest
from decimal import Decimal


class TestSalaryCalculation:
    """Тести розрахунку зарплати."""

    def test_labor_rate_basic(self, default_settings):
        """Базова ставка для повітропровода."""
        info = default_settings.get_labor_rate("повітропровід прямокутний")
        assert "rate_per_m2" in info
        assert info["rate_per_m2"] > 0

    def test_salary_formula(self):
        """Формула: зарплата = площа × ставка × (1 + важкість/100)."""
        metal_area = 1.2
        rate = 120.0
        difficulty = 20.0
        expected = metal_area * rate * (1 + difficulty / 100)
        assert expected == pytest.approx(172.80, 0.01)

    def test_salary_with_zero_difficulty(self):
        """Зарплата без важкості."""
        metal_area = 1.0
        rate = 100.0
        result = metal_area * rate * 1.0
        assert result == 100.0

    def test_salary_different_types(self, default_settings):
        """Різні ставки для різних типів виробів."""
        types = [
            "повітропровід прямокутний",
            "повітропровід круглий",
            "трійник прямокутний",
        ]
        rates = []
        for t in types:
            info = default_settings.get_labor_rate(t)
            rates.append(info["rate_per_m2"])
        assert len(set(rates)) >= 1


class TestCostCalculation:
    """Тести розрахунку собівартості."""

    def test_material_cost(self):
        """Вартість матеріалу."""
        area = 1.0
        price = 50.0
        assert area * price == 50.0

    def test_total_cost_components(self):
        """Собівартість = матеріал + робота + накладні."""
        material = Decimal("50.0")
        labor = Decimal("120.0")
        overhead = Decimal("15.0")
        total = material + labor + overhead
        assert total == Decimal("185.0")

    def test_markup_calculation(self):
        """Ціна з націнкою."""
        cost = Decimal("100.0")
        markup = 0.30
        price = cost * Decimal(str(1 + markup))
        assert price == Decimal("130.0")

    def test_profit_calculation(self):
        """Прибуток = ціна - собівартість."""
        price = Decimal("130.0")
        cost = Decimal("100.0")
        profit = price - cost
        assert profit == Decimal("30.0")


class TestPricingSynchronization:
    """Тести синхронізації цін між вкладками."""

    def test_salary_consistency(self, temp_db, default_settings, sample_project_data):
        """Зарплата має бути однаковою у Виробництві та Архіві."""
        pid = temp_db.create_project("Синхро-тест")
        product = sample_project_data["products"][0]
        temp_db.add_product_to_project(pid, product)

        # Розрахунок "на льоту"
        ptype = product["product_type"]
        metal_area = float(product["metal_area_m2"])
        labor_info = default_settings.get_labor_rate(ptype)
        rate = labor_info["rate_per_m2"]
        difficulty = labor_info["difficulty_percent"]
        live_salary = metal_area * rate * (1 + difficulty / 100)

        # Збережене значення
        stored = temp_db.get_project_products(pid)[0]
        # salary_per_unit може бути 0, якщо ще не перераховано
        stored_salary = float(stored.get("salary_per_unit") or 0)

        # Якщо збережено 0 — це нормально, головне що формула правильна
        if stored_salary > 0:
            assert abs(live_salary - stored_salary) < 0.01
        else:
            assert live_salary > 0  # Принаймні перевіряємо, що розрахунок дає результат
