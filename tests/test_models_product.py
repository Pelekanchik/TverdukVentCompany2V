"""Тести для моделі Product та PriceHistoryEntry."""

import pytest

from ventilation_company.models.product import PriceHistoryEntry, Product


class TestPriceHistoryEntry:
    """Тести для запису історії цін."""

    def test_creation(self):
        entry = PriceHistoryEntry("10.08.2026", 100.0, 150.0)
        assert entry.date == "10.08.2026"
        assert entry.old_price == 100.0
        assert entry.new_price == 150.0

    def test_diff(self):
        entry = PriceHistoryEntry("10.08.2026", 100.0, 150.0)
        assert entry.diff == 50.0

    def test_diff_negative(self):
        entry = PriceHistoryEntry("10.08.2026", 150.0, 100.0)
        assert entry.diff == -50.0

    def test_to_dict(self):
        entry = PriceHistoryEntry("10.08.2026", 100.0, 150.0)
        d = entry.to_dict()
        assert d["date"] == "10.08.2026"
        assert d["old_price"] == 100.0
        assert d["new_price"] == 150.0

    def test_from_dict(self):
        data = {"date": "10.08.2026", "old_price": 100.0, "new_price": 150.0}
        entry = PriceHistoryEntry.from_dict(data)
        assert entry.date == "10.08.2026"
        assert entry.old_price == 100.0

    def test_repr(self):
        entry = PriceHistoryEntry("10.08.2026", 100.0, 150.0)
        assert "PriceHistoryEntry" in repr(entry)


class TestProduct:
    """Тести для моделі виробу."""

    def test_basic_creation(self):
        p = Product(
            product_id="P001",
            date_added="10.08.2026 12:00",
            name="Повітропровід 400×200",
            price_per_unit=850.0,
            quantity=5,
            length=1000,
            width=400,
            height=200,
            material="оцинкована сталь",
            thickness=0.7,
            category="Труба прямокутна",
        )
        assert p.id == "P001"
        assert p.name == "Повітропровід 400×200"
        assert p.total_price == 4250.0

    def test_total_price_calculation(self):
        p = Product("P002", "10.08.2026", "Тест", price_per_unit=100.0, quantity=3)
        assert p.total_price == 300.0

    def test_date_only(self):
        p = Product("P003", "10.08.2026 14:30", "Тест")
        assert p.date_only == "10.08.2026"

    def test_dimensions_str_round(self):
        p = Product("P004", "10.08.2026", "Тест", diameter=250)
        assert p.dimensions_str == "Ø250.0"

    def test_dimensions_str_rect(self):
        p = Product("P005", "10.08.2026", "Тест", length=1000, width=400, height=200)
        assert "L1000" in p.dimensions_str
        assert "W400" in p.dimensions_str
        assert "H200" in p.dimensions_str

    def test_dimensions_str_empty(self):
        p = Product("P006", "10.08.2026", "Тест")
        assert p.dimensions_str == "—"

    def test_invalid_category_fallback(self):
        p = Product("P007", "10.08.2026", "Тест", category="Невідома категорія")
        assert p.category == "Інше"

    def test_record_price_change(self):
        p = Product("P008", "10.08.2026", "Тест", price_per_unit=100.0)
        p.record_price_change(80.0)
        assert len(p.price_history) == 1
        assert p.price_history[0].old_price == 80.0
        assert p.price_history[0].new_price == 100.0

    def test_price_history_limit(self):
        p = Product("P009", "10.08.2026", "Тест", price_per_unit=100.0)
        for i in range(15):
            p.price_per_unit = 100.0 + i
            p.record_price_change(100.0 + i - 1)
        assert len(p.price_history) == 10

    def test_to_dict_roundtrip(self):
        p = Product(
            product_id="P010",
            date_added="10.08.2026",
            name="Тестовий виріб",
            price_per_unit=500.0,
            quantity=2,
            category="Фасонка",
        )
        p.record_price_change(450.0)
        data = p.to_dict()
        p2 = Product.from_dict(data)
        assert p2.id == p.id
        assert p2.name == p.name
        assert p2.price_per_unit == p.price_per_unit
        assert len(p2.price_history) == len(p.price_history)

    def test_str(self):
        p = Product("P011", "10.08.2026", "Вентилятор", price_per_unit=3500.0)
        assert "Вентилятор" in str(p)
        assert "3500.00" in str(p)

    def test_repr(self):
        p = Product("P012", "10.08.2026", "Тест", price_per_unit=100.0)
        assert "Product" in repr(p)

    def test_material_prices_dict_exists(self):
        assert "оцинкована сталь" in Product.MATERIAL_PRICES
        assert 0.5 in Product.MATERIAL_PRICES["оцинкована сталь"]
        assert Product.MATERIAL_PRICES["оцинкована сталь"][0.5] == 450

    def test_categories_list(self):
        assert "Вентилятор" in Product.CATEGORIES
        assert "Труба прямокутна" in Product.CATEGORIES
        assert len(Product.CATEGORIES) == 9
