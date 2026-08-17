from decimal import Decimal
"""Розширені тести для SalaryCalculator."""

import pytest

from ventilation_company.calculations.salary_calculator import SalaryCalculator


class TestSalaryCalculatorInit:
    """Тести ініціалізації."""

    def test_empty_employees(self):
        calc = SalaryCalculator()
        assert calc.employees == []

    def test_tax_rates(self):
        calc = SalaryCalculator()
        assert calc.PIT_RATE == 0.18
        assert calc.MILITARY_TAX_RATE == 0.015
        assert calc.ESV_RATE == 0.22


class TestAddEmployee:
    """Тести додавання співробітників."""

    def test_add_single(self):
        calc = SalaryCalculator()
        calc.add_employee("Іванов Іван", "інженер_проектувальник")
        assert len(calc.employees) == 1
        assert calc.employees[0]["full_name"] == "Іванов Іван"
        assert calc.employees[0]["position"] == "інженер_проектувальник"
        assert calc.employees[0]["base_salary"] == 28000
        assert calc.employees[0]["bonus_percent"] == 10

    def test_add_multiple(self):
        calc = SalaryCalculator()
        calc.add_employee("Іванов", "інженер_проектувальник")
        calc.add_employee("Петров", "зварник")
        calc.add_employee("Сидоров", "монтажник")
        assert len(calc.employees) == 3

    def test_add_unknown_position(self):
        calc = SalaryCalculator()
        calc.add_employee("Тест", "невідома_посада")
        assert calc.employees[0]["base_salary"] == 0
        assert calc.employees[0]["bonus_percent"] == 0

    def test_director_position(self):
        calc = SalaryCalculator()
        calc.add_employee("Директор", "директор")
        assert calc.employees[0]["base_salary"] == 45000
        assert calc.employees[0]["bonus_percent"] == 20

    def test_welder_position(self):
        calc = SalaryCalculator()
        calc.add_employee("Зварник", "зварник")
        assert calc.employees[0]["base_salary"] == 22000
        assert calc.employees[0]["bonus_percent"] == 15


class TestCalculateEmployeeNet:
    """Тести розрахунку зарплати одного співробітника."""

    def test_basic_calculation(self):
        calc = SalaryCalculator()
        result = calc.calculate_employee_net(30000)
        assert result["gross_salary"] == 30000.0
        assert result["pit"] == 5400.0  # 30000 * 0.18
        assert result["military_tax"] == 450.0  # 30000 * 0.015
        assert result["net_salary"] == 24150.0  # 30000 - 5400 - 450
        assert result["esv"] == 6600.0  # 30000 * 0.22

    def test_zero_salary(self):
        calc = SalaryCalculator()
        result = calc.calculate_employee_net(0)
        assert result["gross_salary"] == 0
        assert result["net_salary"] == 0
        assert result["esv"] == 0

    def test_minimum_wage(self):
        calc = SalaryCalculator()
        result = calc.calculate_employee_net(8000)
        assert result["pit"] == 1440.0
        assert result["military_tax"] == 120.0
        assert result["net_salary"] == 6440.0
        assert result["esv"] == 1760.0

    def test_high_salary(self):
        calc = SalaryCalculator()
        result = calc.calculate_employee_net(100000)
        assert result["pit"] == 18000.0
        assert result["military_tax"] == 1500.0
        assert result["net_salary"] == 80500.0
        assert result["esv"] == 22000.0

    def test_precision(self):
        calc = SalaryCalculator()
        result = calc.calculate_employee_net(12345.67)
        assert isinstance(result["pit"], float)
        assert isinstance(result["net_salary"], float)
        assert round(result["pit"] + result["military_tax"] + result["net_salary"], 2) == 12345.67

    def test_net_less_than_gross(self):
        calc = SalaryCalculator()
        result = calc.calculate_employee_net(50000)
        assert result["net_salary"] < result["gross_salary"]

    def test_esv_positive(self):
        calc = SalaryCalculator()
        result = calc.calculate_employee_net(1000)
        assert result["esv"] > 0


class TestCalculatePayroll:
    """Тести розрахунку зарплатного фонду."""

    def test_single_employee(self):
        calc = SalaryCalculator()
        calc.add_employee("Іванов", "інженер_проектувальник")
        result = calc.calculate_payroll()
        assert result["employees_count"] == 1
        expected_gross = 28000 * 1.10  # base + 10% bonus
        assert result["total_gross"] == round(expected_gross, 2)
        assert result["total_net"] < result["total_gross"]
        assert result["total_esv"] > 0
        assert result["total_employer_cost"] == round(expected_gross + result["total_esv"], 2)

    def test_multiple_employees(self):
        calc = SalaryCalculator()
        calc.add_employee("Іванов", "інженер_проектувальник")  # 28000 + 10%
        calc.add_employee("Петров", "зварник")  # 22000 + 15%
        calc.add_employee("Сидоров", "монтажник")  # 20000 + 12%
        result = calc.calculate_payroll()
        assert result["employees_count"] == 3
        expected_gross = 28000 * 1.10 + 22000 * 1.15 + 20000 * 1.12
        assert result["total_gross"] == round(expected_gross, 2)

    def test_empty_payroll(self):
        calc = SalaryCalculator()
        result = calc.calculate_payroll()
        assert result["employees_count"] == 0
        assert result["total_gross"] == 0.0
        assert result["total_net"] == 0.0
        assert result["total_esv"] == 0.0
        assert result["total_employer_cost"] == 0.0

    def test_employer_cost_greater_than_gross(self):
        calc = SalaryCalculator()
        calc.add_employee("Тест", "інженер_проектувальник")
        result = calc.calculate_payroll()
        assert result["total_employer_cost"] > result["total_gross"]

    def test_all_positions(self):
        """Тест для всіх посад з config.py."""
        from ventilation_company.config import POSITIONS
        calc = SalaryCalculator()
        for position in POSITIONS:
            calc.add_employee(f"Співробітник_{position}", position)
        result = calc.calculate_payroll()
        assert result["employees_count"] == len(POSITIONS)
        assert result["total_gross"] > 0
        assert result["total_net"] > 0
        assert result["total_esv"] > 0


class TestSalaryCalculatorEdgeCases:
    """Граничні випадки."""

    def test_very_low_salary(self):
        calc = SalaryCalculator()
        result = calc.calculate_employee_net(1)
        assert result["pit"] == 0.18
        assert result["military_tax"] == 0.01  # round(1 * 0.015, 2) = 0.01
        assert result["esv"] == 0.22

    def test_very_high_salary(self):
        calc = SalaryCalculator()
        result = calc.calculate_employee_net(1000000)
        assert result["pit"] == 180000.0
        assert result["military_tax"] == 15000.0
        assert result["esv"] == 220000.0
