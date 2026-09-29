"""Тести зв'язування бізнес-налаштувань із карткою проєкту."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from ventilation_company.gui_pyside6.project_card_dialog import (
    ComponentPickerDialog,
    WorkEditDialog,
)
from ventilation_company.services import business_settings as bs_module
from ventilation_company.services.business_settings import BusinessSettings


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def business_settings(tmp_path, monkeypatch):
    filepath = str(tmp_path / "business_settings.json")
    monkeypatch.setattr(bs_module.BusinessSettings, "_instance", None)
    settings = BusinessSettings.get_instance(filepath)
    yield settings
    monkeypatch.setattr(bs_module.BusinessSettings, "_instance", None)


class TestWorkEditDialogWorkRates:
    def test_work_list_loaded(self, qapp, business_settings):
        dlg = WorkEditDialog(project_id=1)
        keys = [dlg.combo_work.itemData(i) for i in range(dlg.combo_work.count())]
        assert keys[0] is None  # «— Вручну —»
        assert "монтаж_повітропроводів" in keys
        assert "доставка" in keys
        assert "виїзд_на_замір" in keys

    def test_selecting_work_fills_fields(self, qapp, business_settings):
        dlg = WorkEditDialog(project_id=1)
        idx = dlg.combo_work.findData("монтаж_повітропроводів")
        assert idx > 0
        dlg.combo_work.setCurrentIndex(idx)
        assert dlg.edit_name.text() == "монтаж повітропроводів"
        assert dlg.edit_unit.text() == "м2"
        assert dlg.spin_price.value() == pytest.approx(280.0)

    def test_manual_item_does_not_touch_fields(self, qapp, business_settings):
        dlg = WorkEditDialog(project_id=1)
        dlg.edit_name.setText("Ручна робота")
        dlg.spin_price.setValue(123.0)
        dlg.combo_work.setCurrentIndex(0)
        assert dlg.edit_name.text() == "Ручна робота"
        assert dlg.spin_price.value() == 123.0

    def test_edit_mode_preselects_matching_work(self, qapp, business_settings):
        dlg = WorkEditDialog(project_id=1, work_data={"work_name": "доставка", "quantity": 2})
        assert dlg.combo_work.currentData() == "доставка"
        # Ціна з роботи, а не з довідника (сигнали заблоковані при преселекті)
        assert dlg.spin_price.value() == 0


class TestComponentPickerDialog:
    def test_lists_components_with_prices(self, qapp, business_settings):
        dlg = ComponentPickerDialog()
        assert dlg.table.rowCount() == len(business_settings.components)
        first_key = dlg._keys[0]
        display = dlg.table.item(0, 0).text()
        assert display == first_key.replace("_", " ")

    def test_get_data_returns_expense_fields(self, qapp, business_settings):
        dlg = ComponentPickerDialog()
        idx = dlg._keys.index("фільтр_грубої_очистки")
        dlg.table.selectRow(idx)
        dlg.spin_qty.setValue(3)
        data = dlg.get_data()
        assert data is not None
        assert data["expense_name"] == "фільтр грубої очистки"
        assert data["quantity"] == 3
        assert data["unit_price"] == pytest.approx(1200.0)
        assert data["total_price"] == pytest.approx(3600.0)
        assert data["direction"] == "minus"

    def test_get_data_none_when_no_components(self, qapp, business_settings, tmp_path):
        """Без комплектуючих у налаштуваннях діалог повертає None."""
        filepath = tmp_path / "empty_settings.json"
        filepath.write_text('{"components": {}}', encoding="utf-8")
        bs_module.BusinessSettings._instance = None
        BusinessSettings.get_instance(str(filepath))
        dlg = ComponentPickerDialog()
        assert dlg.table.rowCount() == 0
        assert dlg.get_data() is None
        bs_module.BusinessSettings._instance = None
