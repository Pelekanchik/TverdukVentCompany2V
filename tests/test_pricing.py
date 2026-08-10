"""Розширені тести для PricingEngine."""

import pytest

from ventilation_company.calculations.pricing import PricingEngine


class TestPricingEngineCostPlus:
    """Тести методу Cost-plus."""

    def test_basic(self):
        engine = PricingEngine(base_cost=10000, markup_percent=30)
        result = engine.cost_plus_pricing()
        assert result["method"] == "cost_plus"
        assert result["base_cost"] == 10000
        assert result["markup_percent"] == 30
        assert result["markup_amount"] == 3000.0
        assert result["price_without_vat"] == 13000.0
        assert result["vat_percent"] == 20
        assert result["vat_amount"] == 2600.0
        assert result["final_price"] == 15600.0

    def test_zero_markup(self):
        engine = PricingEngine(base_cost=10000, markup_percent=0)
        result = engine.cost_plus_pricing()
        assert result["markup_amount"] == 0
        assert result["price_without_vat"] == 10000.0

    def test_custom_markup(self):
        engine = PricingEngine(base_cost=5000, markup_percent=50)
        result = engine.cost_plus_pricing()
        assert result["markup_amount"] == 2500.0
        assert result["price_without_vat"] == 7500.0
        assert result["final_price"] == 9000.0

    def test_default_markup(self):
        engine = PricingEngine(base_cost=10000)
        result = engine.cost_plus_pricing()
        assert result["markup_percent"] == 30.0


class TestPricingEngineCompetitive:
    """Тести конкурентного методу."""

    def test_basic(self):
        engine = PricingEngine(base_cost=10000)
        result = engine.competitive_pricing(competitor_price=15000)
        assert result["method"] == "competitive"
        assert result["competitor_price"] == 15000
        assert result["recommended_price_without_vat"] >= 11000  # min 10% above cost

    def test_competitor_too_low(self):
        engine = PricingEngine(base_cost=10000)
        result = engine.competitive_pricing(competitor_price=5000)
        # Має бути мінімум 10% над собівартістю
        assert result["recommended_price_without_vat"] >= 11000

    def test_high_competitor(self):
        engine = PricingEngine(base_cost=10000)
        result = engine.competitive_pricing(competitor_price=50000)
        assert result["recommended_price_without_vat"] == 47500.0  # 95% of competitor


class TestPricingEngineValueBased:
    """Тести методу на основі цінності."""

    def test_basic(self):
        engine = PricingEngine(base_cost=10000)
        result = engine.value_based_pricing(client_value=50000)
        assert result["method"] == "value_based"
        assert result["client_value"] == 50000
        assert result["price_without_vat"] >= 11500  # min 15% above cost

    def test_low_client_value(self):
        engine = PricingEngine(base_cost=10000)
        result = engine.value_based_pricing(client_value=15000)
        # max 60% of client_value = 9000, але min 11500
        assert result["price_without_vat"] >= 11500

    def test_high_client_value(self):
        engine = PricingEngine(base_cost=10000)
        result = engine.value_based_pricing(client_value=200000)
        # capped at base_cost * 2.5 = 25000
        assert result["price_without_vat"] <= 25000


class TestPricingEngineCompareMethods:
    """Тести порівняння методів."""

    def test_all_methods_present(self):
        engine = PricingEngine(base_cost=10000)
        results = engine.compare_methods(competitor_price=15000, client_value=50000)
        assert "cost_plus" in results
        assert "competitive" in results
        assert "value_based" in results

    def test_compare_methods_types(self):
        engine = PricingEngine(base_cost=10000)
        results = engine.compare_methods()
        assert results["cost_plus"]["method"] == "cost_plus"
        assert results["competitive"]["method"] == "competitive"
        assert results["value_based"]["method"] == "value_based"

    def test_compare_methods_final_prices(self):
        engine = PricingEngine(base_cost=10000)
        results = engine.compare_methods()
        assert results["cost_plus"]["final_price"] == 15600.0
        assert "final_price" in results["competitive"]
        assert "final_price" in results["value_based"]


class TestPricingEngineEdgeCases:
    """Граничні випадки."""

    def test_zero_base_cost(self):
        engine = PricingEngine(base_cost=0, markup_percent=30)
        result = engine.cost_plus_pricing()
        assert result["final_price"] == 0

    def test_negative_base_cost(self):
        engine = PricingEngine(base_cost=-1000, markup_percent=30)
        result = engine.cost_plus_pricing()
        assert result["markup_amount"] == -300.0

    def test_very_high_markup(self):
        engine = PricingEngine(base_cost=1000, markup_percent=500)
        result = engine.cost_plus_pricing()
        assert result["markup_amount"] == 5000.0
        assert result["final_price"] == 7200.0

    def test_float_precision(self):
        engine = PricingEngine(base_cost=9999.99, markup_percent=33.33)
        result = engine.cost_plus_pricing()
        assert isinstance(result["markup_amount"], float)
        assert isinstance(result["final_price"], float)
