"""Тести сервісного шару.

Запуск:  pytest tests/test_services.py -v
"""

import pytest

from ventilation_company.services.product_validator import ProductValidator, ValidationError
from ventilation_company.services.product_builder import ProductBuilder
from ventilation_company.standard_products import (
    MaterialType, Thickness, RectDuct, RoundDuct, RectFlange,
)


class TestProductValidator:
    """Тести валідації."""

    def test_valid_input(self):
        result = ProductValidator.validate(
            width="400", height="200", length="1000",
            quantity="5",
        )
        assert result == {"width": 400.0, "height": 200.0, "length": 1000.0, "quantity": 5}

    def test_comma_decimal(self):
        result = ProductValidator.validate(width="400,5", height="200", length="0", quantity="1")
        assert result["width"] == 400.5

    def test_negative_value(self):
        with pytest.raises(ValidationError) as exc:
            ProductValidator.validate(width="-100", height="200", length="1000", quantity="1")
        assert "від'ємним" in str(exc.value)

    def test_zero_quantity(self):
        with pytest.raises(ValidationError) as exc:
            ProductValidator.validate(width="400", height="200", length="1000", quantity="0")
        assert "більше 0" in str(exc.value)

    def test_invalid_number(self):
        with pytest.raises(ValidationError) as exc:
            ProductValidator.validate(width="abc", height="200", length="1000", quantity="1")
        assert "числом" in str(exc.value)

    def test_hidden_fields(self):
        """Якщо поле приховане, його значення = width."""
        result = ProductValidator.validate(
            width="400", height="999", length="1000",
            quantity="1", height_visible=False,
        )
        assert result["height"] == 400.0  # = width, бо height приховане


class TestProductBuilder:
    """Тести фабрики виробів."""

    def test_build_rect_duct(self):
        product = ProductBuilder.build(
            ptype="rect_duct", selected_name="Повітропровід прямокутний",
            width=400, height=200, length=1000,
            material_str="оцинкована сталь", thickness_str="0.7",
            quantity=2, profile=30.0,
        )
        assert isinstance(product, RectDuct)
        assert product.width == 400
        assert product.quantity == 2
        assert product.material == MaterialType.GALVANIZED
        assert product.thickness == Thickness.T0_7

    def test_build_round_duct(self):
        product = ProductBuilder.build(
            ptype="round_duct", selected_name="Повітропровід круглий",
            width=315, height=315, length=1000,
            material_str="нержавіюча сталь", thickness_str="1.0",
            quantity=1, profile=30.0,
        )
        assert isinstance(product, RoundDuct)
        assert product.material == MaterialType.STAINLESS
        assert product.thickness == Thickness.T1_0

    def test_build_rect_flange(self):
        product = ProductBuilder.build(
            ptype="rect_flange", selected_name="Фланець прямокутний",
            width=400, height=200, length=0,
            material_str="оцинкована сталь", thickness_str="0.7",
            quantity=4, profile=30.0,
        )
        assert isinstance(product, RectFlange)
        assert product.quantity == 4

    def test_build_unknown_type(self):
        product = ProductBuilder.build(
            ptype="unknown_type", selected_name="???",
            width=100, height=100, length=100,
            material_str="оцинкована сталь", thickness_str="0.7",
            quantity=1, profile=30.0,
        )
        assert product is None

    def test_build_flange_for_duct(self):
        flange = ProductBuilder.build_flange(
            ptype="rect_duct", w=400, h=200,
            thickness=Thickness.T0_7,
            material=MaterialType.GALVANIZED,
            flange_qty=2, profile=30.0,
        )
        assert isinstance(flange, RectFlange)
        assert flange.quantity == 2

    def test_resolve_material(self):
        assert ProductBuilder.resolve_material("оцинкована сталь") == MaterialType.GALVANIZED
        assert ProductBuilder.resolve_material("нержавіюча сталь") == MaterialType.STAINLESS
        assert ProductBuilder.resolve_material("алюміній") == MaterialType.ALUMINUM
        assert ProductBuilder.resolve_material("неіснуючий") == MaterialType.GALVANIZED

    def test_resolve_thickness(self):
        assert ProductBuilder.resolve_thickness("0.5") == Thickness.T0_5
        assert ProductBuilder.resolve_thickness("2.0") == Thickness.T2_0
        assert ProductBuilder.resolve_thickness("99") == Thickness.T0_7  # default
