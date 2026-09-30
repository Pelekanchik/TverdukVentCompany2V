"""Тести діалогу картки проєкту (async-завантаження через FunctionWorker)."""

import time

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _no_modal_message_boxes(monkeypatch):
    """У headless-CI модальні QMessageBox блокують цикл подій — замінюємо на no-op."""
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(
        "PySide6.QtWidgets.QMessageBox.critical", staticmethod(lambda *a, **k: None)
    )
    monkeypatch.setattr(
        "PySide6.QtWidgets.QMessageBox.information", staticmethod(lambda *a, **k: None)
    )


FAKE_DATA = {
    "project": {
        "id": 1,
        "name": "Тестовий проєкт",
        "project_number": "PRJ-2026-001",
        "client": "ТОВ «Клієнт»",
        "status": "в роботі",
        "created_at": "2026-09-27 10:00",
        "cost_price": 5000.0,
        "customer_price": 8000.0,
        "discounted_price": 0,
        "works_total": 1000.0,
        "plus_expenses_total": 0.0,
        "minus_expenses_total": 500.0,
        "paid_total": 4000.0,
    },
    "products": [
        {
            "id": 1,
            "name": "Повітропровід",
            "product_type": "повітропровід прямокутний",
            "width": 400,
            "height": 200,
            "length": 1000,
            "material": "оцинкована сталь",
            "quantity": 2,
            "cost_price": 1000.0,
            "unit_price": 1500.0,
            "discounted_price": 0,
            "total_price": 3000.0,
        }
    ],
    "documents": [],
    "works": [
        {
            "id": 1,
            "work_name": "Монтаж",
            "quantity": 1.0,
            "unit": "шт",
            "unit_price": 1000.0,
            "total_price": 1000.0,
        }
    ],
    "expenses": [],
    "drawings": [],
    "payments": [
        {
            "id": 1,
            "date": "2026-09-27",
            "type": "вхідний",
            "amount": 4000,
            "purpose": "",
            "notes": "",
        }
    ],
}


def _wait_worker(qapp, dlg, iterations=500):
    for _ in range(iterations):
        qapp.processEvents()
        if dlg._worker is None:
            return True
        # Коротка пауза віддає GIL worker-потоку — інакше тісний цикл
        # processEvents може його голодувати (флакі на повному наборі).
        time.sleep(0.001)
    return False


class TestProjectCardDialog:
    def test_async_load_populates_tabs(self, qapp, monkeypatch):
        from ventilation_company.gui_pyside6.project_card_dialog import ProjectCardDialog

        monkeypatch.setattr(ProjectCardDialog, "_fetch_data", lambda self: FAKE_DATA)
        dlg = ProjectCardDialog(1)
        assert _wait_worker(qapp, dlg), "worker завис"

        assert dlg._project_data["name"] == "Тестовий проєкт"
        assert "Тестовий проєкт" in dlg.lbl_title.text()
        assert dlg.products_model.rowCount() == 1
        assert dlg.works_model.rowCount() == 1
        assert dlg.payments_table.rowCount() == 1
        # Поле інформації заповнене
        assert dlg._info_labels["name"].text() == "Тестовий проєкт"
        assert "5,000.00" in dlg._info_labels["cost_price"].text()
        dlg.close()

    def test_missing_project_shows_warning(self, qapp, monkeypatch):
        from ventilation_company.gui_pyside6.project_card_dialog import ProjectCardDialog

        monkeypatch.setattr(ProjectCardDialog, "_fetch_data", lambda self: {"project": None})
        dlg = ProjectCardDialog(999)
        assert _wait_worker(qapp, dlg)
        assert dlg._project_data == {}
        dlg.close()

    def test_fetch_error_reported(self, qapp, monkeypatch):
        from ventilation_company.gui_pyside6.project_card_dialog import ProjectCardDialog

        def _boom(self):
            raise RuntimeError("DB недоступна")

        monkeypatch.setattr(ProjectCardDialog, "_fetch_data", _boom)
        dlg = ProjectCardDialog(1)
        assert _wait_worker(qapp, dlg)
        assert dlg._project_data == {}
        dlg.close()

    def test_reload_uses_worker(self, qapp, monkeypatch):
        from ventilation_company.gui_pyside6.project_card_dialog import ProjectCardDialog

        monkeypatch.setattr(ProjectCardDialog, "_fetch_data", lambda self: FAKE_DATA)
        dlg = ProjectCardDialog(1)
        assert _wait_worker(qapp, dlg)
        dlg._reload_all()
        assert _wait_worker(qapp, dlg)
        assert dlg._project_data["name"] == "Тестовий проєкт"
        dlg.close()

    def test_payments_summary_panel(self, qapp, monkeypatch):
        """Панель підсумку: вартість = ціна + роботи; сплачено/залишок/% коректні."""
        from ventilation_company.gui_pyside6.project_card_dialog import ProjectCardDialog

        monkeypatch.setattr(ProjectCardDialog, "_fetch_data", lambda self: FAKE_DATA)
        dlg = ProjectCardDialog(1)
        assert _wait_worker(qapp, dlg)
        # Вартість: customer_price 8000 + works_total 1000 = 9000; сплачено 4000.
        assert "9,000.00" in dlg.lbl_pay_price.text()
        assert "4,000.00" in dlg.lbl_pay_paid.text()
        assert "5,000.00" in dlg.lbl_pay_left.text()
        assert dlg.lbl_pay_percent.text() == "44 %"
        assert dlg.progress_pay.value() == 44
        dlg.close()
