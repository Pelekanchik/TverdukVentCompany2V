"""Тести вкладки «Ціноутворення»: вставка цін з Excel, експорт CSV."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMessageBox

from ventilation_company.gui_pyside6.pricing_tab import (
    MetalPricesTab,
    metal_prices_to_csv,
    parse_price_grid,
)

THICKNESSES = ["0.5", "0.7", "0.9", "1.0", "1.2", "1.5", "2.0"]


@pytest.fixture(scope="module")
def qapp():
    """Власна фікстура QApplication (pytest-qt у CI не встановлено)."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestParsePriceGrid:
    def test_tsv_with_dots_and_commas(self):
        text = "Оцинкована сталь\t450.50\t520,75\t600\nНержавіюча сталь\t1200\t1350\t1500"
        data, skipped = parse_price_grid(text, THICKNESSES)
        assert skipped == 0
        assert data["Оцинкована сталь"] == {"0.5": 450.5, "0.7": 520.75, "0.9": 600.0}
        assert data["Нержавіюча сталь"]["0.5"] == 1200.0

    def test_semicolon_separator_and_spaces(self):
        text = "Алюміній; 800 ;900"
        data, skipped = parse_price_grid(text, THICKNESSES)
        assert data["Алюміній"] == {"0.5": 800.0, "0.7": 900.0}

    def test_invalid_cells_counted_as_skipped(self):
        text = "Оцинкована сталь\t450\tabc\t600"
        data, skipped = parse_price_grid(text, THICKNESSES)
        assert skipped == 1
        assert data["Оцинкована сталь"] == {"0.5": 450.0, "0.9": 600.0}

    def test_empty_text_gives_empty_data(self):
        data, skipped = parse_price_grid("", THICKNESSES)
        assert data == {}
        assert skipped == 0


class TestMetalPricesToCsv:
    def test_csv_roundtrip(self, qapp):
        tab = MetalPricesTab({"material_prices": {}, "labor_rates": {}})
        csv_text = metal_prices_to_csv(tab.model, THICKNESSES)
        lines = csv_text.splitlines()
        assert lines[0] == "Матеріал;" + ";".join(THICKNESSES)
        assert len(lines) == 4  # заголовок + 3 матеріали
        # Зворотний розбір дає ті ж ціни (0.00)
        data, skipped = parse_price_grid("\n".join(lines[1:]), THICKNESSES)
        assert skipped == 0
        assert data["оцинкована сталь"]["0.5"] == 0.0


class TestPasteFromExcel:
    def test_paste_applies_prices_case_insensitive_materials(self, qapp, monkeypatch):
        monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
        tab = MetalPricesTab({"material_prices": {}, "labor_rates": {}})
        QGuiApplication.clipboard().setText(
            "ОЦИНКОВАНА СТАЛЬ\t450.50\t520,75\nнержавіюча сталь\t1200\t1350"
        )
        tab._on_paste()
        assert tab.model.item(0, 1).text() == "450.50"
        assert tab.model.item(0, 2).text() == "520.75"
        assert tab.model.item(1, 1).text() == "1200.00"
        # Алюміній не був у буфері — лишився 0.00
        assert tab.model.item(2, 1).text() == "0.00"

    def test_paste_empty_clipboard_warns(self, qapp, monkeypatch):
        called = {"info": False}
        monkeypatch.setattr(
            QMessageBox,
            "information",
            staticmethod(lambda *a, **k: called.update(info=True)),
        )
        tab = MetalPricesTab({"material_prices": {}, "labor_rates": {}})
        QGuiApplication.clipboard().setText("")
        tab._on_paste()
        assert called["info"]


class TestAlignmentAndProtection:
    def test_material_name_not_editable_and_prices_right_aligned(self, qapp):
        from PySide6.QtCore import Qt

        tab = MetalPricesTab({"material_prices": {}, "labor_rates": {}})
        name_item = tab.model.item(0, 0)
        assert not name_item.flags() & Qt.ItemFlag.ItemIsEditable
        price_item = tab.model.item(0, 1)
        assert price_item.textAlignment() & Qt.AlignmentFlag.AlignRight
