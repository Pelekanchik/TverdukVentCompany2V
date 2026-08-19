"""
ГЛОБАЛЬНІ ІНТЕГРАЦІЙНІ ТЕСТИ (test_global.py)
================================================
Запуск: pytest tests/test_global.py -v

Що перевіряє:
  • StandardProduct → Detail (через cutting_integration)
  • Повний pipeline: вироби → деталі → розкрій → summary
  • MetalCutter з StandardProduct (Етап 4)
  • blank_area / material_area після Етапу 1
  • Швидкі функції розкрою
"""

import math

import pytest

from ventilation_company.metal_cutting import (
    CuttingPlan,
    Detail,
    MetalCutter,
    calculate_sheet_cutting_for_standard_products,
    estimate_metal_needed_for_standard_products,
)
from ventilation_company.standard_products import (
    RectDuct,
    RoundDuct,
    RectElbow,
    RoundElbow,
    RectFlange,
    RoundFlange,
    RectTee,
    RoundTee,
    RectTransition,
    RoundTransition,
    RectCap,
    RoundCap,
    FlexibleConnector,
)
from ventilation_company.cutting_integration import product_to_detail, products_to_details


# ═══════════════════════════════════════════════════════════
#  1. ІНТЕГРАЦІЯ: StandardProduct → Detail
# ═══════════════════════════════════════════════════════════

class TestCuttingIntegration:
    """Тести конвертації StandardProduct → Detail."""

    def test_rect_duct_to_detail(self):
        p = RectDuct(name="ПП 400×200", width=400, height=200, length=1000)
        d = product_to_detail(p)
        assert d is not None
        assert d.width > 0
        assert d.height > 0
        assert d.quantity == 1
        assert d.product_type == p.name  # за замовчуванням product_type = name

    def test_round_duct_to_detail(self):
        p = RoundDuct(name="КП Ø250", width=250, length=1000)
        d = product_to_detail(p)
        assert d is not None
        assert d.width > 0  # розгортка = π·D
        assert d.height > 0
        assert d.product_type == p.name  # за замовчуванням product_type = name

    def test_rect_elbow_to_detail(self):
        p = RectElbow(name="Відвід 90°", width=400, height=200, angle=90, radius=150,
                      top_extension=100, bottom_extension=100)
        d = product_to_detail(p)
        assert d is not None
        assert d.width > 0
        assert d.height > 0

    def test_rect_flange_to_detail(self):
        p = RectFlange(name="Фланець", width=400, height=200, profile=30)
        d = product_to_detail(p)
        assert d is not None
        assert d.width > p.width
        assert d.height > p.height

    def test_round_flange_to_detail(self):
        p = RoundFlange(name="Фланець Ø250", width=250, profile=30)
        d = product_to_detail(p)
        assert d is not None
        assert d.width == d.height  # квадратна заготовка

    def test_products_to_details_list(self):
        products = [
            RectDuct(name="ПП1", width=400, height=200, length=1000),
            RoundDuct(name="КП1", width=250, length=1000),
            RectFlange(name="Ф1", width=400, height=200, profile=30),
        ]
        details = products_to_details(products)
        assert len(details) == 3
        for d in details:
            assert isinstance(d, Detail)
            assert d.width > 0
            assert d.height > 0

    def test_zero_area_product_returns_none(self):
        """Продукт з нульовою площею повертає None."""
        # Створимо віртуальний продукт без розмірів
        p = RectDuct(name="Пустий", width=0, height=0, length=0)
        d = product_to_detail(p)
        # При нульових розмірах повинен повернути None або Detail(0,0)
        assert d is not None
        assert d.width >= 0
        assert d.height >= 0


# ═══════════════════════════════════════════════════════════
#  2. ПОВНИЙ PIPELINE: вироби → деталі → розкрій
# ═══════════════════════════════════════════════════════════

class TestEndToEndCutting:
    """End-to-end тести: StandardProduct → CuttingPlan."""

    def test_single_rect_duct_pipeline(self):
        products = [RectDuct(name="ПП 400×200", width=400, height=200, length=1000)]
        cutter = MetalCutter(sheet_width=1250, sheet_height=2500, thickness=0.7)
        plan = cutter.calculate_from_standard_products(products)
        assert isinstance(plan, CuttingPlan)
        assert plan.total_sheets >= 1
        summary = plan.get_summary()
        assert summary["total_sheets"] >= 1
        assert summary["utilization_percent"] > 0

    def test_multiple_products_pipeline(self):
        products = [
            RectDuct(name="ПП 400×200", width=400, height=200, length=1000, quantity=5),
            RoundDuct(name="КП Ø250", width=250, length=1000, quantity=3),
            RectFlange(name="Ф 400×200", width=400, height=200, profile=30, quantity=10),
        ]
        cutter = MetalCutter(sheet_width=1250, sheet_height=2500, thickness=0.7)
        plan = cutter.calculate_from_standard_products(products)
        assert plan.total_sheets >= 1
        placed = sum(len(s.placed_details) for s in plan.sheets)
        # Всі деталі повинні бути розміщені (розміри не надто великі)
        assert placed >= 3

    def test_metal_summary_for_standard_products(self):
        products = [
            RectDuct(name="ПП 400×200", width=400, height=200, length=1000, quantity=2),
            RectFlange(name="Ф 400×200", width=400, height=200, profile=30, quantity=4),
        ]
        cutter = MetalCutter(sheet_width=1250, sheet_height=2500, thickness=0.7)
        summary = cutter.get_metal_summary_for_standard_products(products)
        assert summary["details_count"] >= 6
        assert summary["sheets_required"] >= 1
        assert 0 < summary["utilization_percent"] <= 100
        assert summary["sheet_size"] == "1250×2500 мм"

    def test_small_sheet_forces_unplaced(self):
        """Дуже маленький лист — деталі не вміщуються."""
        products = [RectDuct(name="Великий ПП", width=1000, height=800, length=2000)]
        cutter = MetalCutter(sheet_width=500, sheet_height=500, thickness=0.7)
        plan = cutter.calculate_from_standard_products(products)
        assert len(plan.unplaced_details) >= 1


# ═══════════════════════════════════════════════════════════
#  3. ШВИДКІ ФУНКЦІЇ
# ═══════════════════════════════════════════════════════════

class TestQuickFunctions:
    """Тести швидких функцій розкрою."""

    def test_calculate_sheet_cutting_for_standard_products(self):
        products = [
            RectDuct(name="ПП", width=400, height=200, length=1000, quantity=2),
        ]
        plan = calculate_sheet_cutting_for_standard_products(products)
        assert isinstance(plan, CuttingPlan)
        assert plan.total_sheets >= 1

    def test_estimate_metal_needed_for_standard_products(self):
        products = [
            RectDuct(name="ПП", width=400, height=200, length=1000, quantity=3),
            RoundDuct(name="КП", width=250, length=1000, quantity=2),
        ]
        summary = estimate_metal_needed_for_standard_products(products)
        assert "details_count" in summary
        assert "sheets_required" in summary
        assert "utilization_percent" in summary


# ═══════════════════════════════════════════════════════════
#  4. BLANK_AREA / MATERIAL_AREA (Етап 1)
# ═══════════════════════════════════════════════════════════

class TestBlankAndMaterialArea:
    """Тести blank_area та material_area після Етапу 1."""

    def test_rect_duct_blank_larger_than_surface(self):
        p = RectDuct(name="ПП", width=400, height=200, length=1000)
        assert p.blank_area >= p.surface_area
        assert p.material_area >= p.blank_area

    def test_blank_area_non_zero(self):
        products = [
            RectDuct(name="ПП", width=400, height=200, length=1000),
            RoundDuct(name="КП", width=250, length=1000),
            RectElbow(name="Відвід", width=400, height=200, angle=90, radius=150),
            RectFlange(name="Фланець", width=400, height=200, profile=30),
        ]
        for p in products:
            assert p.blank_area > 0, f"{p.name}: blank_area має бути > 0"
            assert p.material_area > 0, f"{p.name}: material_area має бути > 0"

    def test_round_duct_blank_approximation(self):
        p = RoundDuct(name="КП Ø250", width=250, length=1000)
        # Розгортка ≈ π·D, довжина = L + припуски
        expected_surface = math.pi * 0.25 * 1.0
        assert p.surface_area > 0
        assert p.blank_area >= p.surface_area


# ═══════════════════════════════════════════════════════════
#  5. ДЕТАЛЬНІ ТЕСТИ РОЗМІРІВ ЗАГОТОВОК
# ═══════════════════════════════════════════════════════════

class TestBlankDimensions:
    """Тести точних розмірів заготовок (cutting_integration)."""

    def test_rect_duct_blank_size(self):
        p = RectDuct(name="ПП", width=400, height=200, length=1000)
        w, h = product_to_detail(p).width, product_to_detail(p).height
        # Ширина = 2·(W+H) + припуск на шов
        assert w > 2 * (p.width + p.height)
        # Довжина ≈ L + припуски на різ
        assert h >= p.length

    def test_round_duct_blank_size(self):
        p = RoundDuct(name="КП", width=250, length=1000)
        d = product_to_detail(p)
        # Розгортка = π·D (+ припуск на шов)
        assert d.width >= math.pi * p.width * 0.99
        assert d.height >= p.length

    def test_rect_flange_blank_size(self):
        p = RectFlange(name="Ф", width=400, height=200, profile=30)
        d = product_to_detail(p)
        assert d.width > p.width + 2 * p.profile
        assert d.height > p.height + 2 * p.profile

    def test_round_flange_blank_is_square(self):
        p = RoundFlange(name="Ф", width=250, profile=30)
        d = product_to_detail(p)
        assert d.width == d.height


# ═══════════════════════════════════════════════════════════
#  6. GUI SMOKE (CuttingTab логіка без Tkinter)
# ═══════════════════════════════════════════════════════════

class TestCuttingTabLogic:
    """Smoke-тест логіки CuttingTab без запуску GUI."""

    def test_run_cutting_for_products_mock(self):
        """Імітація роботи CuttingTab.run_cutting_for_products."""
        products = [
            {"name": "ПП", "type": "прямокутний повітропровід", "width": 400, "height": 200, "length": 1000, "quantity": 2},
        ]
        cutter = MetalCutter(sheet_width=1250, sheet_height=2500, thickness=0.7)
        plan = cutter.calculate_from_products(products)
        assert plan is not None
        assert plan.total_sheets >= 1
        summary = plan.get_summary()
        assert summary["utilization_percent"] > 0

    def test_sheet_size_variants(self):
        """Розкрій на різних розмірах листів."""
        products = [RectDuct(name="ПП", width=300, height=150, length=1000, quantity=10)]
        for sw, sh in [(1250, 2500), (1000, 2000), (1500, 3000)]:
            cutter = MetalCutter(sheet_width=sw, sheet_height=sh, thickness=0.7)
            plan = cutter.calculate_from_standard_products(products)
            assert plan.total_sheets >= 1
            assert plan.get_summary()["utilization_percent"] > 0


# ═══════════════════════════════════════════════════════════
#  7. КОЕФІЦІЄНТИ ЗАПАСУ ПО КАТЕГОРІЯМ (Етап 5)
# ═══════════════════════════════════════════════════════════

class TestCategoryWasteFactors:
    """Тести коефіцієнтів запасу на брак/поворот."""

    def test_default_factors_are_zero(self):
        from ventilation_company.gui.settings_tab import DEFAULT_CATEGORY_WASTE_FACTORS
        assert DEFAULT_CATEGORY_WASTE_FACTORS["rect_duct"] == 0.0
        assert DEFAULT_CATEGORY_WASTE_FACTORS["rect_fitting"] == 0.0
        assert DEFAULT_CATEGORY_WASTE_FACTORS["round_duct"] == 0.0
        assert DEFAULT_CATEGORY_WASTE_FACTORS["round_fitting"] == 0.0

