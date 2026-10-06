"""Тести власного вибору дати (MonthPickerDialog + DatePicker)."""

import pytest
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QPushButton

from ventilation_company.gui_pyside6.calendar_picker import DatePicker, MonthPickerDialog


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestMonthPickerDialog:
    def test_initial_month_and_year(self, qapp):
        dlg = MonthPickerDialog(QDate(2026, 10, 9))
        assert dlg.combo_month.currentIndex() == 9  # жовтень
        assert dlg.spin_year.value() == 2026

    def test_grid_has_42_day_buttons(self, qapp):
        dlg = MonthPickerDialog(QDate(2026, 10, 9))
        buttons = dlg.findChildren(QPushButton)
        # 42 дні + ◀ + ▶
        assert len(buttons) == 44

    def test_shift_month_forward(self, qapp):
        dlg = MonthPickerDialog(QDate(2026, 12, 15))
        dlg._shift_month(1)
        assert dlg.combo_month.currentIndex() == 0  # січень
        assert dlg.spin_year.value() == 2027

    def test_shift_month_backward(self, qapp):
        dlg = MonthPickerDialog(QDate(2026, 1, 15))
        dlg._shift_month(-1)
        assert dlg.combo_month.currentIndex() == 11  # грудень
        assert dlg.spin_year.value() == 2025

    def test_pick_day_sets_selected_and_accepts(self, qapp):
        dlg = MonthPickerDialog(QDate(2026, 10, 9))
        dlg._pick(QDate(2026, 10, 20))
        assert dlg.selected_date == QDate(2026, 10, 20)
        assert dlg.result() == MonthPickerDialog.DialogCode.Accepted

    def test_default_date_is_today(self, qapp):
        dlg = MonthPickerDialog()
        assert dlg.combo_month.currentIndex() == QDate.currentDate().month() - 1
        assert dlg.spin_year.value() == QDate.currentDate().year()


class TestDatePicker:
    def test_api_compatible_with_qdate_edit(self, qapp):
        picker = DatePicker(QDate(2026, 10, 9))
        assert picker.date() == QDate(2026, 10, 9)
        picker.setDate(QDate(2027, 3, 1))
        assert picker.date() == QDate(2027, 3, 1)

    def test_default_date_is_today(self, qapp):
        picker = DatePicker()
        assert picker.date() == QDate.currentDate()

    def test_set_enabled_toggles_children(self, qapp):
        picker = DatePicker()
        picker.setEnabled(False)
        assert not picker.edit.isEnabled()
        assert not picker.btn.isEnabled()
        picker.setEnabled(True)
        assert picker.edit.isEnabled()
        assert picker.btn.isEnabled()
