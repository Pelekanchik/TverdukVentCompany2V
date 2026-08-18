"""Тести для стандартних виробів (standard_products)."""

import math

import pytest

from ventilation_company.standard_products import (
    FlexibleConnector,
    MaterialType,
    ProductLibrary,
    RectCap,
    RectDuct,
    RectElbow,
    RectFlange,
    RectTee,
    RectTransition,
    RoundCap,
    RoundDuct,
    RoundElbow,
    RoundFlange,
    RoundTee,
    RoundTransition,
    StandardProduct,
    Thickness,
    make_rect_duct,
    make_round_duct,
)


class TestMaterialType:
    """Тести типів матеріалів."""

    def test_values(self):
        assert MaterialType.GALVANIZED.value == "оцинкована сталь"
        assert MaterialType.STAINLESS.value == "нержавіюча сталь"
        assert MaterialType.ALUMINUM.value == "алюміній"


class TestThickness:
    """Тести товщин."""

    def test_values(self):
        assert Thickness.T0_5.value == 0.5
        assert Thickness.T0_7.value == 0.7
        assert Thickness.T1_0.value == 1.0
        assert Thickness.T2_0.value == 2.0


class TestStandardProduct:
    """Тести базового класу виробу."""

    def test_creation(self):
        p = StandardProduct(name="Тест", width=400, height=200, length=1000)
        assert p.name == "Тест"
        assert p.metal_area >= 0
        assert p.weight >= 0
        assert p.unit_price >= 0
        assert p.total_price >= 0

    def test_calculate_weight(self):
        p = StandardProduct(name="Тест", width=400, height=200, length=1000, thickness=Thickness.T1_0)
        expected_weight = p.metal_area * (1.0 / 1000) * 7850
        assert abs(p.weight - expected_weight) < 0.001

    def test_to_dict(self):
        p = StandardProduct(name="Тест", width=400, height=200, length=1000)
        d = p.to_dict()
        assert d["name"] == "Тест"
        assert "metal_area_m2" in d
        assert "weight_kg" in d

    def test_from_dict(self):
        data = {
            "name": "Відновлений",
            "width": 500,
            "height": 300,
            "length": 1000,
            "thickness": 0.7,
            "material": "оцинкована сталь",
            "quantity": 3,
        }
        p = StandardProduct.from_dict(data)
        assert p.name == "Відновлений"
        assert p.quantity == 3

    def test_default_material(self):
        p = StandardProduct(name="Тест")
        assert p.material == MaterialType.GALVANIZED

    def test_default_thickness(self):
        p = StandardProduct(name="Тест")
        assert p.thickness == Thickness.T0_7


class TestRectDuct:
    """Тести прямокутного повітропроводу."""

    def test_metal_area(self):
        d = RectDuct(name="ПП", width=400, height=200, length=1000)
        w, h, l = 0.4, 0.2, 1.0
        expected = 2 * (w + h) * l
        assert abs(d.metal_area - expected) < 0.001

    def test_total_price(self):
        d = RectDuct(name="ПП", width=400, height=200, length=1000, quantity=3)
        assert d.total_price == d.unit_price * 3


class TestRoundDuct:
    """Тести круглого повітропроводу."""

    def test_metal_area(self):
        d = RoundDuct(name="КП", width=250, length=1000)
        expected = math.pi * 0.25 * 1.0
        assert abs(d.metal_area - expected) < 0.001


class TestRectFlange:
    """Тести прямокутного фланця."""

    def test_metal_area(self):
        f = RectFlange(name="Фланець", width=400, height=200, profile=30)
        border = 0.03
        expected = (0.4 + 2 * border) * (0.2 + 2 * border)
        assert abs(f.metal_area - expected) < 0.001


class TestRoundFlange:
    """Тести круглого фланця."""

    def test_metal_area(self):
        f = RoundFlange(name="Фланець", width=250, profile=30)
        border = 0.03
        outer_d = 0.25 + 2 * border
        expected = math.pi * (outer_d / 2) ** 2
        assert abs(f.metal_area - expected) < 0.001


class TestRectTee:
    """Тести прямокутного трійника."""

    def test_metal_area(self):
        t = RectTee(name="Трійник", width=400, height=200, length=500, branch_width=200, branch_height=150, branch_length=400)
        w, h, l = 0.4, 0.2, 0.5
        bw, bh, bl = 0.2, 0.15, 0.4
        expected = 2 * (w + h) * l + 2 * (bw + bh) * bl
        assert abs(t.metal_area - expected) < 0.001


class TestRoundTee:
    """Тести круглого трійника."""

    def test_metal_area(self):
        t = RoundTee(name="Трійник", width=250, length=500, branch_diameter=150, branch_length=400)
        expected = math.pi * 0.25 * 0.5 + math.pi * 0.15 * 0.4
        assert abs(t.metal_area - expected) < 0.001


class TestRectTransition:
    """Тести прямокутного переходу."""

    def test_metal_area(self):
        t = RectTransition(name="Перехід", width=400, height=200, length=300, end_width=300, end_height=150)
        w1, h1, w2, h2, l = 0.4, 0.2, 0.3, 0.15, 0.3
        avg_p = 2 * ((w1 + w2) / 2 + (h1 + h2) / 2)
        expected = avg_p * l
        assert abs(t.metal_area - expected) < 0.001


class TestRoundTransition:
    """Тести круглого переходу."""

    def test_metal_area(self):
        t = RoundTransition(name="Перехід", width=250, length=300, end_diameter=200)
        avg_d = (0.25 + 0.2) / 2
        expected = math.pi * avg_d * 0.3
        assert abs(t.metal_area - expected) < 0.001


class TestRectElbow:
    """Тести прямокутного коліна (відповідно до CAMduct)."""

    def test_metal_area_90_no_extensions(self):
        """Коліно 90° без подовжень — тільки зігнута частина."""
        e = RectElbow(name="Коліно", width=400, height=200, angle=90, radius=50,
                      top_extension=0, bottom_extension=0)
        w, h, r = 0.4, 0.2, 0.05
        angle_rad = math.radians(90)
        mean_r = r + h / 2          # середній радіус = r + H/2
        arc = mean_r * angle_rad
        perimeter = 2 * (w + h)
        expected = perimeter * arc  # тільки зігнута частина
        assert abs(e.metal_area - expected) < 0.001

    def test_metal_area_90_with_extensions(self):
        """Коліно 90° з подовженнями 100мм — як у CAMduct (A=400,B=200,F=50,D=100,E=100)."""
        e = RectElbow(name="Коліно", width=400, height=200, angle=90, radius=50,
                      top_extension=100, bottom_extension=100)
        w, h, r = 0.4, 0.2, 0.05
        angle_rad = math.radians(90)
        mean_r = r + h / 2
        arc = mean_r * angle_rad
        perimeter = 2 * (w + h)
        # зігнута частина + прямі подовження
        expected = perimeter * arc + perimeter * 0.2
        assert abs(e.metal_area - expected) < 0.001

    def test_metal_area_45_degrees(self):
        """Коліно 45° з подовженнями."""
        e = RectElbow(name="Коліно", width=400, height=200, angle=45, radius=50,
                      top_extension=100, bottom_extension=100)
        w, h, r = 0.4, 0.2, 0.05
        angle_rad = math.radians(45)
        mean_r = r + h / 2
        arc = mean_r * angle_rad
        perimeter = 2 * (w + h)
        expected = perimeter * arc + perimeter * 0.2
        assert abs(e.metal_area - expected) < 0.001


class TestRoundElbow:
    """Тести круглого коліна (відповідно до CAMduct)."""

    def test_metal_area_90_no_extensions(self):
        """Коліно 90° без подовжень — тільки зігнута частина."""
        e = RoundElbow(name="Коліно", width=250, angle=90, radius=50,
                       top_extension=0, bottom_extension=0)
        d, r = 0.25, 0.05
        angle_rad = math.radians(90)
        mean_r = r + d / 2          # середній радіус = r + D/2
        arc = mean_r * angle_rad
        expected = math.pi * d * arc
        assert abs(e.metal_area - expected) < 0.001

    def test_metal_area_90_with_extensions(self):
        """Коліно 90° з подовженнями 100мм."""
        e = RoundElbow(name="Коліно", width=250, angle=90, radius=50,
                       top_extension=100, bottom_extension=100)
        d, r = 0.25, 0.05
        angle_rad = math.radians(90)
        mean_r = r + d / 2
        arc = mean_r * angle_rad
        expected = math.pi * d * arc + math.pi * d * 0.2
        assert abs(e.metal_area - expected) < 0.001

    def test_metal_area_45_degrees(self):
        """Коліно 45° з подовженнями."""
        e = RoundElbow(name="Коліно", width=250, angle=45, radius=50,
                       top_extension=100, bottom_extension=100)
        d, r = 0.25, 0.05
        angle_rad = math.radians(45)
        mean_r = r + d / 2
        arc = mean_r * angle_rad
        expected = math.pi * d * arc + math.pi * d * 0.2
        assert abs(e.metal_area - expected) < 0.001


class TestRectCap:
    """Тести прямокутної заглушки."""

    def test_metal_area(self):
        c = RectCap(name="Заглушка", width=400, height=200, profile=30)
        border = 0.03
        expected = (0.4 + 2 * border) * (0.2 + 2 * border)
        assert abs(c.metal_area - expected) < 0.001


class TestRoundCap:
    """Тести круглої заглушки."""

    def test_metal_area(self):
        c = RoundCap(name="Заглушка", width=250, depth=30)
        d, depth = 0.25, 0.03
        base = math.pi * (d / 2) ** 2
        side = math.pi * d * depth
        expected = base + side
        assert abs(c.metal_area - expected) < 0.001


class TestFlexibleConnector:
    """Тести гнучкої вставки."""

    def test_metal_area(self):
        f = FlexibleConnector(name="Вставка", width=400, height=200, length=200)
        w, h, l = 0.4, 0.2, 0.2
        expected = 2 * (w + h) * l
        assert abs(f.metal_area - expected) < 0.001

    def test_calculate_price_polyester(self):
        f = FlexibleConnector(name="Вставка", width=400, height=200, length=200, fabric_type="поліестер", quantity=2)
        # unit_price = metal_area * fabric_price (за 1 шт)
        # total_price = unit_price * quantity
        expected = f.metal_area * 80.0 * 2
        assert abs(f.total_price - expected) < 0.01

    def test_calculate_price_glass(self):
        f = FlexibleConnector(name="Вставка", width=400, height=200, length=200, fabric_type="склотканина", quantity=1)
        expected = f.metal_area * 150.0
        assert abs(f.total_price - expected) < 0.01


class TestProductLibrary:
    """Тести бібліотеки виробів."""

    def test_empty_library(self):
        lib = ProductLibrary()
        assert len(lib) == 0
        assert lib.get_total_metal_area() == 0
        assert lib.get_total_weight() == 0
        assert lib.get_total_price() == 0

    def test_add_and_remove(self):
        lib = ProductLibrary()
        d = RectDuct(name="ПП", width=400, height=200, length=1000)
        lib.add(d)
        assert len(lib) == 1
        lib.remove(0)
        assert len(lib) == 0

    def test_clear(self):
        lib = ProductLibrary()
        lib.add(RectDuct(name="П1", width=400, height=200, length=1000))
        lib.add(RoundDuct(name="П2", width=250, length=1000))
        lib.clear()
        assert len(lib) == 0

    def test_get_total_metal_area(self):
        lib = ProductLibrary()
        lib.add(RectDuct(name="П1", width=400, height=200, length=1000, quantity=2))
        lib.add(RoundDuct(name="П2", width=250, length=1000, quantity=3))
        expected = lib.products[0].metal_area * 2 + lib.products[1].metal_area * 3
        assert abs(lib.get_total_metal_area() - expected) < 0.001

    def test_get_specification(self):
        lib = ProductLibrary()
        lib.add(RectDuct(name="ПП 400×200", width=400, height=200, length=1000, quantity=2))
        lib.add(RectDuct(name="ПП 400×200", width=400, height=200, length=1000, quantity=3))
        spec = lib.get_specification()
        assert len(spec) == 1  # згруповано
        assert spec[0]["quantity"] == 5

    def test_to_dict(self):
        lib = ProductLibrary()
        lib.add(RectDuct(name="ПП", width=400, height=200, length=1000))
        data = lib.to_dict()
        assert len(data) == 1
        assert data[0]["name"] == "ПП"

    def test_from_dict(self):
        lib = ProductLibrary()
        data = [
            {"name": "ПП", "width": 400, "height": 200, "length": 1000, "thickness": 0.7, "material": "оцинкована сталь"},
        ]
        lib.from_dict(data)
        assert len(lib) == 1
        assert lib.products[0].name == "ПП"


class TestFactoryMethods:
    """Тести фабричних методів."""

    def test_make_rect_duct(self):
        d = make_rect_duct(400, 200, 1000, thickness=0.7)
        assert isinstance(d, RectDuct)
        assert d.width == 400
        assert d.height == 200
        assert d.length == 1000
        assert "400×200×1000" in d.name

    def test_make_round_duct(self):
        d = make_round_duct(250, 1000, thickness=1.0)
        assert isinstance(d, RoundDuct)
        assert d.width == 250
        assert d.length == 1000
        assert d.thickness == Thickness.T1_0
        assert "Ø250×1000" in d.name
