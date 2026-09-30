"""GUI-тести вкладки «Гроші» (дебіторка)."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

ROWS = [
    {
        "project_id": 1,
        "project_number": "ПР-1",
        "name": "Проєкт А",
        "client": "ТОВ «А»",
        "status": "в роботі",
        "total": 9500.0,
        "paid": 4000.0,
        "balance": 5500.0,
        "percent": 42.1,
        "overpaid": False,
        "payments_count": 1,
        "last_payment": "2026-09-01",
    },
    {
        "project_id": 2,
        "project_number": "ПР-2",
        "name": "Проєкт Б",
        "client": "ТОВ «Б»",
        "status": "здано",
        "total": 2000.0,
        "paid": 2500.0,
        "balance": -500.0,
        "percent": 100.0,
        "overpaid": True,
        "payments_count": 2,
        "last_payment": "2026-09-20",
    },
    {
        "project_id": 3,
        "project_number": "ПР-3",
        "name": "Проєкт В",
        "client": "ТОВ «В»",
        "status": "draft",
        "total": 3000.0,
        "paid": 0.0,
        "balance": 3000.0,
        "percent": 0.0,
        "overpaid": False,
        "payments_count": 0,
        "last_payment": "",
    },
]


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _stub_receivables(monkeypatch):
    """Не читаємо реальну базу у тестах."""
    monkeypatch.setattr(
        "ventilation_company.gui_pyside6.money_tab.build_receivables", lambda: list(ROWS)
    )


class TestMoneyTab:
    def _make_tab(self, qapp):
        from ventilation_company.gui_pyside6.money_tab import MoneyTab

        return MoneyTab()

    def test_loads_rows_and_summary(self, qapp):
        tab = self._make_tab(qapp)
        assert tab.table.rowCount() == 3
        assert tab.lbl_projects.text() == "3"
        assert "14,500.00" in tab.lbl_total.text()  # 9500 + 2000 + 3000
        assert "6,500.00" in tab.lbl_paid.text()  # 4000 + 2500
        assert "8,500.00" in tab.lbl_debt.text()  # 5500 + 0 + 3000
        assert "500.00" in tab.lbl_overpaid.text()  # переплата по проєкту Б

    def test_filter_debt(self, qapp):
        tab = self._make_tab(qapp)
        tab.combo_filter.setCurrentText("Борг")
        assert tab.table.rowCount() == 2  # А і В

    def test_filter_overpaid(self, qapp):
        tab = self._make_tab(qapp)
        tab.combo_filter.setCurrentText("Переплата")
        assert tab.table.rowCount() == 1

    def test_filter_no_payments(self, qapp):
        tab = self._make_tab(qapp)
        tab.combo_filter.setCurrentText("Без оплат")
        assert tab.table.rowCount() == 1

    def test_search_by_client(self, qapp):
        tab = self._make_tab(qapp)
        tab.edit_search.setText("това")
        assert tab.table.rowCount() == 0
        tab.edit_search.setText("тОВ «б»")
        assert tab.table.rowCount() == 1

    def test_filter_and_search_combine(self, qapp):
        tab = self._make_tab(qapp)
        tab.combo_filter.setCurrentText("Борг")
        tab.edit_search.setText("Проєкт В")
        assert tab.table.rowCount() == 1
