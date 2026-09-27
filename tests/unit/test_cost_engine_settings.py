"""Тести узгодженості CostEngine з бізнес-налаштуваннями."""

import pytest

from ventilation_company.services import business_settings as bs_module
from ventilation_company.services.business_settings import BusinessSettings


@pytest.fixture
def business_settings(tmp_path, monkeypatch):
    filepath = str(tmp_path / "business_settings.json")
    monkeypatch.setattr(bs_module.BusinessSettings, "_instance", None)
    settings = BusinessSettings.get_instance(filepath)
    yield settings
    monkeypatch.setattr(bs_module.BusinessSettings, "_instance", None)


class TestCostEngineVat:
    def _calculate(self):
        from ventilation_company.calculations.cost_engine import CostEngine

        engine = CostEngine()
        return engine.calculate(
            product_type="повітропровід прямокутний",
            material_name="Оцинкована сталь",
            thickness_mm=0.7,
            surface_area_m2=1.2,
            blank_area_m2=1.3,
            material_area_m2=1.4,
            quantity=1,
        )

    def test_vat_comes_from_business_settings(self, business_settings):
        business_settings.vat_rate = 7.0
        business_settings.save()
        result = self._calculate()
        assert result.vat_rate == 7.0

    def test_default_vat_is_20(self, business_settings):
        result = self._calculate()
        assert result.vat_rate == 20.0
        expected_vat = result.price_no_vat * 0.20
        assert abs(result.vat_amount - expected_vat) < 0.01

    def test_vat_change_affects_final_price(self, business_settings):
        base = self._calculate()
        business_settings.vat_rate = 0.0
        business_settings.save()
        zero_vat = self._calculate()
        assert zero_vat.vat_amount == 0
        assert zero_vat.final_price == pytest.approx(zero_vat.price_no_vat)
        assert zero_vat.final_price < base.final_price


class TestFlangePrices:
    def test_default_flange_prices(self, business_settings):
        assert business_settings.get_flange_price("P30") == 150.0
        assert business_settings.get_flange_price("P40") == 200.0

    def test_unknown_profile_returns_default(self, business_settings):
        assert business_settings.get_flange_price("P99") == 150.0

    def test_custom_flange_price_persists(self, business_settings, tmp_path):
        business_settings.flange_prices["P30"] = {"ціна": 175.0}
        business_settings.save()
        bs_module.BusinessSettings._instance = None
        reloaded = BusinessSettings.get_instance(str(tmp_path / "business_settings.json"))
        assert reloaded.get_flange_price("P30") == 175.0


class TestMetalDensity:
    def test_density_constant(self):
        from ventilation_company.calculations.cost_engine import METAL_DENSITY_KG_M3

        assert METAL_DENSITY_KG_M3["оцинкована сталь"] == 7850
        assert METAL_DENSITY_KG_M3["нержавіюча сталь"] == 7900
        assert METAL_DENSITY_KG_M3["алюміній"] == 2700
