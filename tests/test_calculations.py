#!/usr/bin/env python3
"""
Тести для модуля calculations
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ventilation_company.calculations.pricing import PricingEngine
from ventilation_company.calculations.salary_calculator import SalaryCalculator
from ventilation_company.config import MARKUP_PERCENTAGE


class TestPricingEngine(unittest.TestCase):
    def setUp(self):
        self.engine = PricingEngine(base_cost=10000)

    def test_cost_plus_pricing(self):
        result = self.engine.cost_plus_pricing()
        self.assertEqual(result["method"], "cost_plus")
        self.assertEqual(result["base_cost"], 10000)
        self.assertGreater(result["final_price"], result["base_cost"])
        self.assertEqual(result["markup_percent"], MARKUP_PERCENTAGE)

    def test_competitive_pricing(self):
        result = self.engine.competitive_pricing(competitor_price=15000)
        self.assertEqual(result["method"], "competitive")
        self.assertGreaterEqual(result["recommended_price_without_vat"], 10000 * 1.1)

    def test_value_based_pricing(self):
        result = self.engine.value_based_pricing(client_value=50000)
        self.assertEqual(result["method"], "value_based")
        self.assertGreaterEqual(result["price_without_vat"], 10000 * 1.15)

    def test_compare_methods(self):
        results = self.engine.compare_methods(competitor_price=15000, client_value=50000)
        self.assertIn("cost_plus", results)
        self.assertIn("competitive", results)
        self.assertIn("value_based", results)


class TestSalaryCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = SalaryCalculator()
        self.calc.add_employee("Тестовий Працівник", "інженер_проектувальник")

    def test_add_employee(self):
        self.assertEqual(len(self.calc.employees), 1)
        self.assertEqual(self.calc.employees[0]["full_name"], "Тестовий Працівник")

    def test_calculate_employee_net(self):
        result = self.calc.calculate_employee_net(30000)
        self.assertEqual(result["gross_salary"], 30000)
        self.assertGreater(result["pit"], 0)
        self.assertGreater(result["military_tax"], 0)
        self.assertLess(result["net_salary"], 30000)
        self.assertGreater(result["esv"], 0)

    def test_calculate_payroll(self):
        result = self.calc.calculate_payroll()
        self.assertEqual(result["employees_count"], 1)
        self.assertGreater(result["total_gross"], 0)
        self.assertGreater(result["total_net"], 0)
        self.assertGreater(result["total_employer_cost"], result["total_gross"])


if __name__ == "__main__":
    unittest.main()
