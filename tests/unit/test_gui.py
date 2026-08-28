"""Тести GUI-компонентів."""

import pytest
import tkinter as tk


class TestPresetDialog:
    """Тести діалогу пресетів."""

    def test_dialog_import(self):
        """Імпорт діалогу не падає."""
        from ventilation_company.gui.preset_dialog import PresetDialog
        assert PresetDialog is not None


class TestProductsTab:
    """Тести вкладки виробів."""

    def test_library_creation(self):
        """Бібліотека створюється порожньою."""
        from ventilation_company.standard_products import ProductLibrary
        lib = ProductLibrary()
        assert len(lib.products) == 0

    def test_add_product_increases_count(self):
        """Додавання виробу збільшує кількість."""
        from ventilation_company.standard_products import ProductLibrary, make_rect_duct
        from ventilation_company.standard_products import MaterialType

        lib = ProductLibrary()
        lib.add(make_rect_duct(100, 50, 500, 0.7, MaterialType.GALVANIZED))
        assert len(lib.products) == 1


class TestSettingsTab:
    """Тести налаштувань."""

    def test_pricing_settings_singleton(self):
        """PricingSettings — singleton."""
        from ventilation_company.gui.settings_tab import PricingSettings
        s1 = PricingSettings.get_instance()
        s2 = PricingSettings.get_instance()
        assert s1 is s2

    def test_labor_rate_structure(self, default_settings):
        """Структура ставки зарплати."""
        info = default_settings.get_labor_rate("повітропровід прямокутний")
        assert "rate_per_m2" in info
        assert "difficulty_percent" in info
        assert isinstance(info["rate_per_m2"], (int, float))
        assert isinstance(info["difficulty_percent"], (int, float))

    def test_material_price_positive(self, default_settings):
        """Ціна матеріалу додатна."""
        price = default_settings.get_material_price("оцинкована сталь", "0.7")
        assert price > 0
