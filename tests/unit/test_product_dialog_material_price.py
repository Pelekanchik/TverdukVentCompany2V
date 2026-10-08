"""Тести автопідтягування цін на метал у діалозі виробу."""

import math

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from ventilation_company.gui_pyside6.product_dialog import SCHEMAS, calc_surface_area


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


CUSTOM_PRICES = {
    "оцинкована сталь": {"0.5": "450", "0.7": 580, "1.0": 750},
    "нержавіюча сталь": {"0.5": 950, "1.5": "1 600,00"},
    "мідь": {"0.8": 2100},
}


class _PricingStub:
    material_prices = CUSTOM_PRICES
    markup_categories = {
        "Стандартна": 30.0,
        "Преміум": 40.0,
        "Економ": 20.0,
        "Спецзамовлення": 50.0,
    }

    def reload(self):
        return None


@pytest.fixture(autouse=True)
def _stub_pricing(monkeypatch):
    monkeypatch.setattr(
        "ventilation_company.services.pricing_settings.PricingSettings.get_instance",
        staticmethod(lambda: _PricingStub()),
    )


def _make_dialog(monkeypatch, data=None):
    from ventilation_company.gui_pyside6.product_dialog import ProductDialog

    return ProductDialog(data or {})


def _items(combo):
    return [combo.itemText(i) for i in range(combo.count())]


class TestMaterialAutoPrice:
    def test_combos_populated_from_pricing(self, qapp, monkeypatch):
        dlg = _make_dialog(monkeypatch)
        assert _items(dlg.combo_material) == [
            "Оцинкована сталь",
            "Нержавіюча сталь",
            "Мідь",
        ]
        assert _items(dlg.combo_thickness) == ["0.5", "0.7", "1.0"]
        dlg.close()

    def test_label_shows_price_from_settings(self, qapp, monkeypatch):
        dlg = _make_dialog(monkeypatch)
        dlg.combo_thickness.setCurrentText("0.7")
        assert "580" in dlg.lbl_metal_price.text()
        dlg.close()

    def test_string_price_parsed(self, qapp, monkeypatch):
        dlg = _make_dialog(monkeypatch)
        dlg.combo_material.setCurrentText("Нержавіюча сталь")
        dlg.combo_thickness.setCurrentText("1.5")
        assert "1,600.00" in dlg.lbl_metal_price.text()
        dlg.close()

    def test_material_change_keeps_thickness(self, qapp, monkeypatch):
        dlg = _make_dialog(monkeypatch, {"material": "Оцинкована сталь", "thickness": 0.7})
        assert dlg.combo_thickness.currentText() == "0.7"
        dlg.combo_material.setCurrentText("Нержавіюча сталь")
        # 0.7 у нержавійки немає → дефолт 0.7 не підходить → перший доступний
        assert dlg.combo_thickness.currentText() == "0.5"
        dlg.close()

    def test_unknown_material_price_warns(self, qapp, monkeypatch):
        dlg = _make_dialog(monkeypatch, {"material": "Титан", "thickness": 0.5})
        assert "Титан" in _items(dlg.combo_material)
        assert "не знайдено" in dlg.lbl_metal_price.text()
        dlg.close()

    def test_thickness_change_triggers_recalc(self, qapp, monkeypatch):
        dlg = _make_dialog(monkeypatch)
        calls = {"n": 0}
        monkeypatch.setattr(dlg, "_on_calc", lambda: calls.__setitem__("n", calls["n"] + 1))
        dlg._calc_result = object()  # імітуємо виконаний розрахунок
        dlg.combo_thickness.setCurrentText("1.0")
        assert calls["n"] >= 1
        dlg.close()

    def test_no_recalc_before_first_calc(self, qapp, monkeypatch):
        dlg = _make_dialog(monkeypatch)
        calls = {"n": 0}
        monkeypatch.setattr(dlg, "_on_calc", lambda: calls.__setitem__("n", calls["n"] + 1))
        dlg.combo_thickness.setCurrentText("1.0")
        assert calls["n"] == 0
        dlg.close()


# ── Нові типи виробів (v2.12): формули площі та схеми ──


class TestNewProductTypesArea:
    """Формули площі металу для нових типів деталей."""

    def test_round_grille(self):
        # π·d²/4 · 1.2
        assert calc_surface_area("Решітка кругла", 300, 0, 0) == pytest.approx(
            math.pi * 300 * 300 / 4 * 1.2 / 1_000_000, abs=1e-9
        )

    def test_rect_grille(self):
        assert calc_surface_area("Решітка прямокутна", 400, 200, 0) == pytest.approx(
            400 * 200 * 1.2 / 1_000_000, abs=1e-9
        )

    def test_diffuser(self):
        assert calc_surface_area("Дифузор круглий", 250, 0, 0) == pytest.approx(
            math.pi * 250 * 250 / 4 * 1.3 / 1_000_000, abs=1e-9
        )

    def test_round_spigot(self):
        assert calc_surface_area("Раструб круглий", 200, 0, 500) == pytest.approx(
            math.pi * 200 * 500 / 1_000_000, abs=1e-9
        )

    def test_round_damper_with_length(self):
        area = calc_surface_area("Зворотний клапан круглий", 250, 0, 150)
        expected = math.pi * 250 * 250 / 4 * 1.5 / 1_000_000 + math.pi * 250 * 150 / 1_000_000
        assert area == pytest.approx(expected, abs=1e-9)

    def test_rect_cross(self):
        assert calc_surface_area("Хрестовина прямокутна", 400, 200, 0) == pytest.approx(
            2 * (400 + 200) * 400 * 2.2 / 1_000_000, abs=1e-9
        )

    def test_saddle_with_branch(self):
        area = calc_surface_area(
            "Відгалуження кругле 45°", 315, 0, 0, branch_width=160, branch_length=250
        )
        expected = math.pi * 315 * 315 * 1.2 / 1_000_000 + math.pi * 160 * 250 / 1_000_000
        assert area == pytest.approx(expected, abs=1e-9)


class TestNewProductTypesInSchemaList:
    """Нові типи присутні у списку та мають опис у діалозі."""

    def test_new_types_in_schemas(self):
        for pt in (
            "Решітка кругла",
            "Решітка прямокутна",
            "Дифузор круглий",
            "Раструб круглий",
            "Раструб прямокутний",
            "Зворотний клапан круглий",
            "Зворотний клапан прямокутний",
            "Хрестовина кругла",
            "Хрестовина прямокутна",
            "Відгалуження кругле 45°",
        ):
            assert pt in SCHEMAS

    def test_labor_rates_defaults(self):
        from ventilation_company.services.pricing_settings import DEFAULT_LABOR_RATES

        assert "решітка кругла" in DEFAULT_LABOR_RATES
        assert "зворотний клапан круглий" in DEFAULT_LABOR_RATES
        assert "відгалуження кругле 45°" in DEFAULT_LABOR_RATES
