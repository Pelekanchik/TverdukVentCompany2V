"""Тести стандартних виробів та бібліотеки."""

import pytest
from ventilation_company.standard_products import (
    make_rect_duct,
    make_round_duct,
    MaterialType,
    ProductLibrary,
)


class TestRectDuct:
    """Тести прямокутних повітропроводів."""

    def test_creation(self):
        """Створення прямокутного повітропровода."""
        duct = make_rect_duct(400, 200, 1000, 0.7, MaterialType.GALVANIZED)
        assert duct.width == 400
        assert duct.height == 200
        assert duct.length == 1000
        assert duct.thickness.value == 0.7

    def test_surface_area(self):
        """Площа поверхні: 2*(w+h)*l / 1e6."""
        duct = make_rect_duct(400, 200, 1000, 0.7, MaterialType.GALVANIZED)
        expected = 2 * (400 + 200) * 1000 / 1_000_000
        assert duct.surface_area == pytest.approx(expected, 0.001)

    def test_blank_area(self):
        """Площа заготовки з припуском."""
        duct = make_rect_duct(400, 200, 1000, 0.7, MaterialType.GALVANIZED)
        assert duct.blank_area > duct.surface_area

    def test_weight_positive(self):
        """Вага має бути додатною."""
        duct = make_rect_duct(100, 50, 500, 0.5, MaterialType.GALVANIZED)
        assert duct.weight > 0

    def test_to_dict_roundtrip(self):
        """Серіалізація."""
        duct = make_rect_duct(300, 150, 800, 0.7, MaterialType.GALVANIZED)
        data = duct.to_dict()
        assert data["width"] == 300
        assert data["product_type"] == "повітропровід прямокутний"


class TestRoundDuct:
    """Тести круглих повітропроводів."""

    def test_creation(self):
        """Створення круглого повітропровода."""
        duct = make_round_duct(200, 1000, 0.7, MaterialType.GALVANIZED)
        # У круглого повітропровода diameter === width
        assert duct.width == 200
        assert duct.length == 1000

    def test_surface_area(self):
        """Площа поверхні: π*d*l / 1e6."""
        duct = make_round_duct(200, 1000, 0.7, MaterialType.GALVANIZED)
        expected = 3.14159 * 200 * 1000 / 1_000_000
        assert duct.surface_area == pytest.approx(expected, 0.01)


class TestProductLibrary:
    """Тести бібліотеки виробів."""

    def test_add_product(self):
        """Додавання виробу в бібліотеку."""
        lib = ProductLibrary()
        duct = make_rect_duct(400, 200, 1000, 0.7, MaterialType.GALVANIZED)
        lib.add(duct)
        assert len(lib.products) == 1

    def test_total_weight(self):
        """Загальна вага бібліотеки."""
        lib = ProductLibrary()
        lib.add(make_rect_duct(400, 200, 1000, 0.7, MaterialType.GALVANIZED))
        lib.add(make_rect_duct(150, 80, 500, 0.5, MaterialType.GALVANIZED))
        assert lib.get_total_weight() > 0

    def test_to_dict(self):
        """Експорт бібліотеки в словник."""
        lib = ProductLibrary()
        lib.add(make_rect_duct(400, 200, 1000, 0.7, MaterialType.GALVANIZED))
        data = lib.to_dict()
        assert len(data) == 1
        assert data[0]["width"] == 400


class TestMaterialTypes:
    """Тести типів матеріалів."""

    def test_galvanized(self):
        """Оцинкована сталь."""
        assert MaterialType.GALVANIZED.value == "оцинкована сталь"

    def test_stainless(self):
        """Нержавіюча сталь."""
        assert MaterialType.STAINLESS.value == "нержавіюча сталь"

    def test_aluminum(self):
        """Алюміній."""
        assert MaterialType.ALUMINUM.value == "алюміній"
