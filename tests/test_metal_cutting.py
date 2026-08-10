"""Тести для модуля розкрою металу (metal_cutting)."""

import math

import pytest

from ventilation_company.metal_cutting import (
    CuttingPlan,
    Detail,
    MetalCutter,
    PlacedDetail,
    Sheet,
    SheetSize,
    calculate_sheet_cutting,
    estimate_metal_needed,
)


class TestDetail:
    """Тести для деталі."""

    def test_creation(self):
        d = Detail(name="Панель", width=500, height=300, quantity=2)
        assert d.name == "Панель"
        assert d.width == 500
        assert d.height == 300
        assert d.quantity == 2

    def test_total_width_with_allowance(self):
        d = Detail(name="Тест", width=500, height=300, cut_allowance=2.0)
        assert d.total_width == 504.0  # 500 + 2*2

    def test_total_height_with_allowance(self):
        d = Detail(name="Тест", width=500, height=300, cut_allowance=2.0, bend_allowance=3.0)
        assert d.total_height == 310.0  # 300 + 2*2 + 2*3

    def test_area(self):
        d = Detail(name="Тест", width=1000, height=500, cut_allowance=0, bend_allowance=0)
        assert d.area == 0.5  # (1000*500)/1_000_000

    def test_total_area(self):
        d = Detail(name="Тест", width=1000, height=500, quantity=3, cut_allowance=0, bend_allowance=0)
        assert d.total_area == 1.5


class TestSheet:
    """Тести для листа металу."""

    def test_creation(self):
        s = Sheet(width=1250, height=2500, thickness=0.7)
        assert s.width == 1250
        assert s.height == 2500
        assert s.thickness == 0.7
        assert len(s.free_rectangles) == 1

    def test_total_area(self):
        s = Sheet(width=1250, height=2500, thickness=0.7)
        assert s.total_area == 3.125  # (1250*2500)/1_000_000

    def test_place_detail_success(self):
        s = Sheet(width=1250, height=2500, thickness=0.7)
        d = Detail(name="Панель", width=500, height=300, cut_allowance=0, bend_allowance=0)
        result = s.place_detail(d, 0, 0)
        assert result is True
        assert len(s.placed_details) == 1

    def test_place_detail_out_of_bounds(self):
        s = Sheet(width=100, height=100, thickness=0.7)
        d = Detail(name="Велика", width=200, height=200, cut_allowance=0, bend_allowance=0)
        result = s.place_detail(d, 0, 0)
        assert result is False

    def test_place_detail_overlap(self):
        s = Sheet(width=1250, height=2500, thickness=0.7)
        d1 = Detail(name="П1", width=500, height=300, cut_allowance=0, bend_allowance=0)
        d2 = Detail(name="П2", width=500, height=300, cut_allowance=0, bend_allowance=0)
        s.place_detail(d1, 0, 0)
        result = s.place_detail(d2, 100, 100)
        assert result is False  # перетин

    def test_utilization(self):
        s = Sheet(width=1000, height=1000, thickness=0.7)
        d = Detail(name="Панель", width=500, height=500, cut_allowance=0, bend_allowance=0)
        s.place_detail(d, 0, 0)
        assert s.utilization == 0.25  # 500*500 / 1000*1000

    def test_find_best_position(self):
        s = Sheet(width=1250, height=2500, thickness=0.7)
        d = Detail(name="Панель", width=500, height=300, cut_allowance=0, bend_allowance=0)
        pos = s.find_best_position(d)
        assert pos is not None
        x, y, rotated = pos
        assert x == 0
        assert y == 0
        assert rotated is False

    def test_find_best_position_with_rotation(self):
        s = Sheet(width=300, height=500, thickness=0.7)
        d = Detail(name="Панель", width=400, height=200, cut_allowance=0, bend_allowance=0)
        # 400×200 не вміщується без повороту (300×500), але 200×400 — вміщується
        pos = s.find_best_position(d)
        assert pos is not None
        x, y, rotated = pos
        assert rotated is True


class TestPlacedDetail:
    """Тести для розміщеної деталі."""

    def test_not_rotated(self):
        d = Detail(name="Тест", width=500, height=300, cut_allowance=0, bend_allowance=0)
        pd = PlacedDetail(d, 0, 0, rotated=False)
        assert pd.width == 500
        assert pd.height == 300

    def test_rotated(self):
        d = Detail(name="Тест", width=500, height=300, cut_allowance=0, bend_allowance=0)
        pd = PlacedDetail(d, 0, 0, rotated=True)
        assert pd.width == 300
        assert pd.height == 500


class TestCuttingPlan:
    """Тести для плану розкрою."""

    def test_empty_plan(self):
        plan = CuttingPlan()
        assert plan.total_sheets == 0
        assert plan.total_area == 0
        assert plan.overall_utilization == 0

    def test_plan_with_sheets(self):
        plan = CuttingPlan()
        s1 = Sheet(width=1250, height=2500, thickness=0.7)
        s2 = Sheet(width=1250, height=2500, thickness=0.7)
        plan.sheets = [s1, s2]
        assert plan.total_sheets == 2

    def test_get_summary(self):
        plan = CuttingPlan()
        s = Sheet(width=1000, height=1000, thickness=0.7)
        d = Detail(name="П", width=500, height=500, cut_allowance=0, bend_allowance=0)
        s.place_detail(d, 0, 0)
        plan.sheets = [s]
        summary = plan.get_summary()
        assert summary["total_sheets"] == 1
        assert summary["utilization_percent"] == 25.0
        assert summary["waste_percent"] == 75.0


class TestMetalCutter:
    """Тести для головного класу розкрою."""

    def test_creation(self):
        cutter = MetalCutter(sheet_width=1250, sheet_height=2500, thickness=0.7)
        assert cutter.sheet_width == 1250
        assert cutter.sheet_height == 2500
        assert cutter.thickness == 0.7

    def test_calculate_cutting_single_detail(self):
        cutter = MetalCutter(sheet_width=1250, sheet_height=2500, thickness=0.7)
        details = [Detail(name="Панель", width=500, height=300, quantity=1, cut_allowance=0, bend_allowance=0)]
        plan = cutter.calculate_cutting(details)
        assert plan.total_sheets >= 1
        assert len(plan.unplaced_details) == 0

    def test_calculate_cutting_multiple_details(self):
        cutter = MetalCutter(sheet_width=1250, sheet_height=2500, thickness=0.7)
        details = [
            Detail(name="П1", width=400, height=200, quantity=5, cut_allowance=0, bend_allowance=0),
            Detail(name="П2", width=300, height=150, quantity=10, cut_allowance=0, bend_allowance=0),
        ]
        plan = cutter.calculate_cutting(details)
        assert plan.total_sheets >= 1
        placed_count = sum(len(s.placed_details) for s in plan.sheets)
        assert placed_count == 15  # 5 + 10

    def test_calculate_cutting_with_rotation(self):
        cutter = MetalCutter(sheet_width=500, sheet_height=500, thickness=0.7)
        details = [
            Detail(name="Довга", width=400, height=200, quantity=2, cut_allowance=0, bend_allowance=0),
        ]
        plan = cutter.calculate_cutting(details, allow_rotation=True)
        placed_count = sum(len(s.placed_details) for s in plan.sheets)
        assert placed_count == 2

    def test_calculate_from_products_rect_duct(self):
        cutter = MetalCutter(sheet_width=1250, sheet_height=2500, thickness=0.7)
        products = [
            {"name": "Повітропровід", "product_type": "rect_duct", "width": 400, "height": 200, "length": 1000, "quantity": 2},
        ]
        plan = cutter.calculate_from_products(products)
        assert plan.total_sheets >= 1

    def test_calculate_from_products_round_duct(self):
        cutter = MetalCutter(sheet_width=1250, sheet_height=2500, thickness=0.7)
        products = [
            {"name": "Повітропровід", "product_type": "round_duct", "width": 250, "length": 1000, "quantity": 3},
        ]
        plan = cutter.calculate_from_products(products)
        assert plan.total_sheets >= 1

    def test_create_details_from_products_flange(self):
        cutter = MetalCutter()
        products = [
            {"name": "Фланець", "product_type": "rect_flange", "width": 400, "height": 200, "profile": 30, "quantity": 4},
        ]
        details = cutter.create_details_from_products(products)
        assert len(details) == 1
        assert details[0].quantity == 4

    def test_get_metal_summary(self):
        """Зведена інформація про потребу в металі (баг виправлено)."""
        cutter = MetalCutter(sheet_width=1250, sheet_height=2500, thickness=0.7)
        products = [
            {"name": "Повітропровід", "product_type": "rect_duct", "width": 400, "height": 200, "length": 1000, "quantity": 5},
        ]
        summary = cutter.get_metal_summary(products)
        assert summary["details_count"] == 5
        assert summary["sheets_required"] >= 1
        assert "utilization_percent" in summary
        assert "sheet_size" in summary
        assert "1250×2500" in summary["sheet_size"]

    def test_unplaced_details(self):
        cutter = MetalCutter(sheet_width=100, sheet_height=100, thickness=0.7)
        details = [Detail(name="Велика", width=200, height=200, quantity=1, cut_allowance=0, bend_allowance=0)]
        plan = cutter.calculate_cutting(details)
        assert len(plan.unplaced_details) == 1


class TestSheetSizeEnum:
    """Тести для переліку розмірів листів."""

    def test_standard_sizes(self):
        assert SheetSize.SHEET_1250x2500.value == (1250, 2500)
        assert SheetSize.SHEET_1000x2000.value == (1000, 2000)
        assert SheetSize.SHEET_1500x3000.value == (1500, 3000)


class TestQuickFunctions:
    """Тести швидких функцій."""

    def test_calculate_sheet_cutting(self):
        products = [
            {"name": "П1", "product_type": "rect_duct", "width": 300, "height": 150, "length": 500, "quantity": 2},
        ]
        plan = calculate_sheet_cutting(products)
        assert isinstance(plan, CuttingPlan)

    def test_estimate_metal_needed(self):
        """Оцінка необхідної кількості металу (баг виправлено)."""
        products = [
            {"name": "П1", "product_type": "rect_duct", "width": 300, "height": 150, "length": 500, "quantity": 2},
        ]
        summary = estimate_metal_needed(products)
        assert "details_count" in summary
        assert "sheets_required" in summary
        assert "utilization_percent" in summary
        assert "sheet_size" in summary
        assert "1250×2500" in summary["sheet_size"]
