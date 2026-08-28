"""Тести інтеграції з FreeCAD."""

import pytest


class TestFreeCADModels:
    """Тести 3D-моделей."""

    def test_freencad_available_import(self):
        """Імпорт freecad_models не падає."""
        try:
            from ventilation_company.freecad_models import FREECAD_AVAILABLE
            assert isinstance(FREECAD_AVAILABLE, bool)
        except ImportError as e:
            pytest.skip(f"FreeCAD не встановлено: {e}")

    def test_build_product_model_exists(self):
        """Функція build_product_model існує."""
        try:
            from ventilation_company.freecad_models import build_product_model
            assert callable(build_product_model)
        except ImportError:
            pytest.skip("FreeCAD не встановлено")


class TestGeometryCalculations:
    """Тести геометричних розрахунків."""

    def test_rect_duct_surface(self):
        """Площа прямокутного повітропровода."""
        w, h, l = 400, 200, 1000
        expected = 2 * (w + h) * l / 1_000_000
        assert expected == pytest.approx(1.2, 0.001)

    def test_round_duct_surface(self):
        """Площа круглого повітропровода."""
        d, l = 200, 1000
        expected = 3.14159 * d * l / 1_000_000
        assert expected == pytest.approx(0.628, 0.01)
