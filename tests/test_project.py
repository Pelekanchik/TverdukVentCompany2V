#!/usr/bin/env python3
"""
Тести для модуля project_builder
"""

import os
import sys
import unittest

# Додаємо корінь проекту в шлях
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ventilation_company.config import VENTILATION_TYPES
from ventilation_company.models.project import Project
from ventilation_company.project_builder.components import ComponentCatalog, DuctCalculator


class TestProject(unittest.TestCase):
    def setUp(self):
        self.project = Project(
            name="Тестовий проект",
            client="ТОВ 'Тест'",
            address="м. Київ",
            ventilation_type="припливно-витяжна",
            air_flow=5000,
            pressure=300,
        )

    def test_project_creation(self):
        self.assertEqual(self.project.name, "Тестовий проект")
        self.assertEqual(self.project.client, "ТОВ 'Тест'")
        self.assertIn(self.project.ventilation_type, VENTILATION_TYPES)

    def test_project_validation(self):
        valid, errors = self.project.validate()
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

    def test_add_component(self):
        total = self.project.add_component("вентилятор_радіальний", 2, "шт", 8500)
        self.assertEqual(total, 17000)
        self.assertEqual(len(self.project._components), 1)

    def test_add_material(self):
        total = self.project.add_material("оцинкована_сталь_0.7", 100, "м²", 580)
        self.assertEqual(total, 58000)
        self.assertEqual(len(self.project._materials), 1)

    def test_add_work(self):
        total = self.project.add_work("монтаж_повітропроводу", 50, "м²", 420)
        self.assertEqual(total, 21000)
        self.assertEqual(len(self.project._works), 1)

    def test_get_summary(self):
        self.project.add_component("фільтр_грубої_очистки", 2, "шт", 1200)
        self.project.add_material("оцинкована_сталь_0.7", 10, "м²", 580)
        summary = self.project.get_summary()
        self.assertEqual(summary["components_cost"], 2400)
        self.assertEqual(summary["materials_cost"], 5800)
        self.assertEqual(summary["total_base"], 8200)


class TestDuctCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = DuctCalculator()

    def test_round_duct(self):
        result = self.calc.calculate_round_duct(250, 10)
        self.assertEqual(result["type"], "круглий")
        self.assertEqual(result["diameter_mm"], 250)
        self.assertGreater(result["area_m2"], 0)
        self.assertGreater(result["total_cost"], 0)

    def test_rectangular_duct(self):
        result = self.calc.calculate_rectangular_duct(400, 250, 5)
        self.assertEqual(result["type"], "прямокутний")
        self.assertEqual(result["width_mm"], 400)
        self.assertEqual(result["height_mm"], 250)
        self.assertGreater(result["area_m2"], 0)

    def test_air_velocity(self):
        velocity = self.calc.calculate_air_velocity(1000, 160)
        self.assertGreater(velocity, 0)

    def test_recommend_duct_size(self):
        rec = self.calc.recommend_duct_size(2000, shape="round")
        self.assertIn("diameter_mm", rec)
        self.assertIn(rec["shape"], ["круглий", "прямокутний"])


class TestComponentCatalog(unittest.TestCase):
    def test_get_materials(self):
        mats = ComponentCatalog.get_materials()
        self.assertIsInstance(mats, dict)
        self.assertIn("оцинкована_сталь_0.7", mats)

    def test_get_components(self):
        comps = ComponentCatalog.get_components()
        self.assertIsInstance(comps, dict)
        self.assertIn("вентилятор_радіальний", comps)

    def test_get_material_price(self):
        price = ComponentCatalog.get_material_price("оцинкована_сталь_0.7")
        self.assertEqual(price, 580)

    def test_search_materials(self):
        results = ComponentCatalog.search_materials("сталь")
        self.assertIsInstance(results, dict)
        self.assertGreater(len(results), 0)


if __name__ == "__main__":
    unittest.main()
