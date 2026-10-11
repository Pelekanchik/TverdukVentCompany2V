"""Тести PricingSettings.get_material_price (пошук ціни металу)."""

import json

import pytest

from ventilation_company.services import pricing_settings as ps_module
from ventilation_company.services.pricing_settings import PricingSettings


@pytest.fixture
def pricing(tmp_path, monkeypatch):
    """Ізольований екземпляр PricingSettings у тимчасовому файлі."""
    filepath = str(tmp_path / "pricing_settings.json")
    monkeypatch.setattr(ps_module.PricingSettings, "_instance", None)
    settings = PricingSettings.get_instance(filepath)
    yield settings
    monkeypatch.setattr(ps_module.PricingSettings, "_instance", None)


class TestGetMaterialPrice:
    def test_exact_match(self, pricing):
        pricing.material_prices = {"оцинкована сталь": {"0.5": 450.0}}
        pricing.save()
        assert pricing.get_material_price("оцинкована сталь", 0.5) == 450.0

    def test_case_insensitive_material(self, pricing):
        """«Оцинкована сталь» (як у виробі) знаходить «оцинкована сталь» (як у прайсі)."""
        pricing.material_prices = {"оцинкована сталь": {"0.5": 450.0}}
        pricing.save()
        assert pricing.get_material_price("Оцинкована сталь", 0.5) == 450.0
        assert pricing.get_material_price("ОЦИНКОВАНА СТАЛЬ", 0.5) == 450.0

    def test_thickness_formats(self, pricing):
        """0.5 = «0.50» = «0,5» — усі формати товщини еквівалентні."""
        pricing.material_prices = {"оцинкована сталь": {"0.5": 450.0}}
        pricing.save()
        assert pricing.get_material_price("оцинкована сталь", "0.50") == 450.0
        assert pricing.get_material_price("оцинкована сталь", "0,5") == 450.0

    def test_integer_thickness(self, pricing):
        """Товщина 1 (int) знаходить ключ «1.0»."""
        pricing.material_prices = {"оцинкована сталь": {"1.0": 750.0}}
        pricing.save()
        assert pricing.get_material_price("оцинкована сталь", 1) == 750.0

    def test_unknown_returns_default(self, pricing):
        pricing.material_prices = {"оцинкована сталь": {"0.5": 450.0}}
        pricing.save()
        assert pricing.get_material_price("мідь", 0.5) == 55.0  # дефолт
        assert pricing.get_material_price("оцинкована сталь", 3.0) == 55.0

    def test_unknown_returns_custom_default(self, pricing):
        pricing.material_prices = {}
        pricing.save()
        assert pricing.get_material_price("мідь", 0.5, default=0) == 0.0

    def test_string_price_value(self, pricing):
        """Ціна, збережена рядком («450»), конвертується у float."""
        pricing.material_prices = {"оцинкована сталь": {"0.5": "450"}}
        pricing.save()
        assert pricing.get_material_price("Оцинкована сталь", 0.5) == 450.0

    def test_loaded_from_file(self, pricing, tmp_path):
        """Реальний файл (як у користувача): малі літери, ціна float."""
        filepath = tmp_path / "pricing_settings.json"
        filepath.write_text(
            json.dumps({"material_prices": {"оцинкована сталь": {"0.5": 450.0}}}),
            encoding="utf-8",
        )
        pricing._last_modified = 0  # примусово перечитати
        assert pricing.get_material_price("Оцинкована сталь", 0.5) == 450.0
