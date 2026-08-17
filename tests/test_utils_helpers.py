"""Тести для модуля helpers."""

import json
from datetime import datetime
import os
import tempfile

import pytest

from ventilation_company.utils.helpers import (
    calculate_area,
    calculate_duct_area,
    calculate_rect_duct_area,
    format_currency,
    format_date,
    load_json,
    save_json,
)


class TestFormatCurrency:
    """Тести форматування валюти."""

    def test_basic(self):
        result = format_currency(1500.5)
        assert "1,500.50" in result
        assert "hrn" in result

    def test_zero(self):
        result = format_currency(0)
        assert "0.00" in result

    def test_thousands(self):
        result = format_currency(1500000.0)
        assert "1,500,000.00" in result


class TestFormatDate:
    """Тести форматування дати."""

    def test_default_format(self):

        result = format_date(datetime(2026, 8, 10))
        assert result == "10.08.2026"

    def test_custom_format(self):

        result = format_date(datetime(2026, 8, 10), fmt="%Y-%m-%d")
        assert result == "2026-08-10"

    def test_none_uses_today(self):
        result = format_date()
        assert len(result) > 0


class TestSaveAndLoadJson:
    """Тести збереження/завантаження JSON."""

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.json")
            data = {"name": "Тест", "value": 42, "nested": {"key": "val"}}
            save_json(data, filepath)
            assert os.path.exists(filepath)
            loaded = load_json(filepath)
            assert loaded["name"] == "Тест"
            assert loaded["value"] == 42
            assert loaded["nested"]["key"] == "val"

    def test_save_creates_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "sub", "dir", "test.json")
            save_json({"test": 1}, filepath)
            assert os.path.exists(filepath)


class TestCalculateArea:
    """Тести розрахунку площі."""

    def test_rectangle(self):
        assert calculate_area(10, 5) == 50

    def test_square(self):
        assert calculate_area(4, 4) == 16

    def test_zero(self):
        assert calculate_area(0, 5) == 0


class TestCalculateDuctArea:
    """Тести розрахунку площі круглого повітропроводу."""

    def test_round_duct(self):
        import math

        result = calculate_duct_area(160, 1000)
        expected = math.pi * 160 * 1000
        assert abs(result - expected) < 0.001

    def test_zero_diameter(self):
        assert calculate_duct_area(0, 1000) == 0

    def test_zero_length(self):
        assert calculate_duct_area(160, 0) == 0


class TestCalculateRectDuctArea:
    """Тести розрахунку площі прямокутного повітропроводу."""

    def test_rect_duct(self):
        result = calculate_rect_duct_area(400, 200, 1000)
        expected = 2 * (400 + 200) * 1000
        assert result == expected

    def test_zero_dimensions(self):
        # Примітка: функція не перевіряє на 0, просто рахує формулу
        assert calculate_rect_duct_area(0, 200, 1000) == 400000  # 2*(0+200)*1000
        assert calculate_rect_duct_area(400, 0, 1000) == 800000  # 2*(400+0)*1000
