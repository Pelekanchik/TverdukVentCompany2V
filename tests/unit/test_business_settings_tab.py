"""GUI-тести вкладки бізнес-налаштувань (settings_business_tab)."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


class _FakeUser:
    def __init__(self, role):
        self.role = role


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class TestBusinessSettingsTab:
    def _make_tab(self, qapp, monkeypatch, tmp_path, role):
        from ventilation_company.services import business_settings as bs_module

        # Одиночка з тимчасовим файлом: усі get_instance() всередині вкладки
        # отримають цей самий ізольований екземпляр.
        monkeypatch.setattr(bs_module.BusinessSettings, "_instance", None)
        bs_module.BusinessSettings.get_instance(str(tmp_path / "business_settings.json"))
        from ventilation_company.gui_pyside6.settings_business_tab import (
            BusinessSettingsTab,
        )

        return BusinessSettingsTab(current_user=_FakeUser(role))

    def test_director_can_edit(self, qapp, monkeypatch, tmp_path):
        tab = self._make_tab(qapp, monkeypatch, tmp_path, "director")
        assert tab.can_edit is True
        assert tab.spin_vat.isEnabled()
        assert tab.tbl_components.isEnabled()
        assert tab.tbl_positions.rowCount() > 0

    def test_viewer_readonly(self, qapp, monkeypatch, tmp_path):
        tab = self._make_tab(qapp, monkeypatch, tmp_path, "перегляд")
        assert tab.can_edit is False
        assert not tab.spin_vat.isEnabled()
        assert not tab.tbl_components.isEnabled()

    def test_load_fills_tables(self, qapp, monkeypatch, tmp_path):
        tab = self._make_tab(qapp, monkeypatch, tmp_path, "admin")
        # Комплектуючі, типові роботи та посади за замовчуванням мають бути завантажені
        assert tab.tbl_components.rowCount() > 0
        assert tab.tbl_works.rowCount() > 0
        assert tab.tbl_positions.rowCount() > 0
        assert tab.tbl_materials.rowCount() > 0
        first_key = tab.tbl_components.item(0, 0).text()
        assert first_key

    def test_save_roundtrip(self, qapp, monkeypatch, tmp_path):
        from ventilation_company.services import business_settings as bs_module
        from ventilation_company.services.business_settings import BusinessSettings

        tab = self._make_tab(qapp, monkeypatch, tmp_path, "admin")
        tab.spin_vat.setValue(9.5)
        assert tab.save() is True

        bs_module.BusinessSettings._instance = None
        s = BusinessSettings.get_instance(str(tmp_path / "business_settings.json"))
        assert s.get_vat_rate() == 9.5

    def test_viewer_save_is_noop(self, qapp, monkeypatch, tmp_path):
        tab = self._make_tab(qapp, monkeypatch, tmp_path, "перегляд")
        assert tab.save() is False

    def test_company_fields_roundtrip(self, qapp, monkeypatch, tmp_path):
        """Реквізити фірми зберігаються через вкладку та повертаються у генератори."""
        from ventilation_company.services import business_settings as bs_module
        from ventilation_company.services.business_settings import BusinessSettings

        tab = self._make_tab(qapp, monkeypatch, tmp_path, "admin")
        assert tab.company_edits["name"].isEnabled()
        tab.company_edits["name"].setText("ПП «ВентБуд»")
        tab.company_edits["edrpou"].setText("98765432")
        tab.company_edits["city"].setText("м. Львів")
        assert tab.save() is True

        bs_module.BusinessSettings._instance = None
        s = BusinessSettings.get_instance(str(tmp_path / "business_settings.json"))
        company = s.get_company()
        assert company["name"] == "ПП «ВентБуд»"
        assert company["edrpou"] == "98765432"
        assert company["city"] == "м. Львів"
        # Незаповнені поля — дефолтні.
        assert company["phone"] == "+38 (044) 123-45-67"
