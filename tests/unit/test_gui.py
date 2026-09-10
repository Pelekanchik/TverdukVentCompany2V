"""Non-GUI regression tests for settings/products."""


class TestProductsLibrary:
    def test_library_creation(self):
        from ventilation_company.standard_products import ProductLibrary

        lib = ProductLibrary()
        assert len(lib.products) == 0

    def test_add_product_increases_count(self):
        from ventilation_company.standard_products import (
            MaterialType,
            ProductLibrary,
            make_rect_duct,
        )

        lib = ProductLibrary()
        lib.add(make_rect_duct(100, 50, 500, 0.7, MaterialType.GALVANIZED))
        assert len(lib.products) == 1


class TestPricingSettings:
    def test_pricing_settings_singleton(self):
        from ventilation_company.services.pricing_settings import PricingSettings

        s1 = PricingSettings.get_instance()
        s2 = PricingSettings.get_instance()
        assert s1 is s2

    def test_labor_rate_structure(self, default_settings):
        info = default_settings.get_labor_rate("повітропровід прямокутний")
        assert "rate_per_m2" in info
        assert "difficulty_percent" in info
        assert isinstance(info["rate_per_m2"], (int, float))
        assert isinstance(info["difficulty_percent"], (int, float))

    def test_material_price_positive(self, default_settings):
        price = default_settings.get_material_price("оцинкована сталь", "0.7")
        assert price > 0
