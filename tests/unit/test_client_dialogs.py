"""Тести CRM-діалогів (async-завантаження через FunctionWorker)."""

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


CLIENT = {
    "id": 7,
    "name": "ТОВ «Тест-Клієнт»",
    "contact_person": "Іван",
    "status": "Активний",
}

CARD_DATA = {
    "projects": [
        {
            "id": 1,
            "project_number": "PRJ-001",
            "name": "Вентиляція офісу",
            "status": "в роботі",
            "customer_price": 50000.0,
            "discounted_price": 0,
        }
    ],
    "payments": [
        {
            "id": 1,
            "date": "2026-09-01",
            "amount": 20000.0,
            "currency": "UAH",
            "type": "вхідний",
        },
        {
            "id": 2,
            "date": "2026-09-05",
            "amount": 5000.0,
            "currency": "UAH",
            "type": "вихідний",
        },
    ],
    "interactions": [
        {
            "id": 1,
            "date": "2026-09-10",
            "type": "дзвінок",
            "subject": "Узгодження",
            "result": "ок",
            "next_action": "Відвантаження",
            "next_action_date": "2099-01-01",
        }
    ],
}

HISTORY_INTERACTIONS = [
    {
        "id": 1,
        "date": "2026-09-10",
        "type": "зустріч",
        "subject": "Старт",
        "result": "домовились",
        "next_action": "Рахунок",
        "next_action_date": "2026-09-20",
        "description": "деталі",
    },
    {
        "id": 2,
        "date": "2026-09-15",
        "type": "дзвінок",
        "subject": "Уточнення",
        "result": "ок",
        "next_action": "",
        "next_action_date": None,
        "description": "",
    },
]

HISTORY_PAYMENTS = [
    {
        "id": 1,
        "date": "2026-09-01",
        "amount": 12000.0,
        "currency": "UAH",
        "type": "вхідний",
        "purpose": "аванс",
        "project_name": "PRJ-001",
        "notes": "",
    }
]


def _wait_worker(qapp, dlg, iterations=500):
    for _ in range(iterations):
        qapp.processEvents()
        if dlg._worker is None:
            return True
        # Коротка пауза віддає GIL worker-потоку — інакше тісний цикл
        # processEvents може його голодувати (флакі на повному наборі).
        time.sleep(0.001)
    return False


class TestClientCardDialog:
    def test_async_load_populates_widgets(self, qapp, monkeypatch):
        from ventilation_company.gui_pyside6.client_card_dialog import ClientCardDialog

        monkeypatch.setattr(ClientCardDialog, "_fetch_data", lambda self: CARD_DATA)
        dlg = ClientCardDialog(dict(CLIENT))
        assert _wait_worker(qapp, dlg), "worker завис"

        assert dlg.table_projects.rowCount() == 1
        assert dlg.table_projects.item(0, 1).text() == "PRJ-001"
        # 1 взаємодія; «наступна дія» у майбутньому (2099) — показано
        assert dlg.lbl_interactions.text() == "1"
        assert "2" in dlg.lbl_payments.text()  # 2 оплати
        # Фінансова підсумка: проєкти 50000, вхідні оплати 20000
        assert "50,000.00" in dlg.lbl_projects_total.text()
        assert "20,000.00" in dlg.lbl_payments_total.text()
        assert "30,000.00" in dlg.lbl_balance.text()
        dlg.close()

    def test_fetch_error_reported(self, qapp, monkeypatch):
        from ventilation_company.gui_pyside6.client_card_dialog import ClientCardDialog

        def _boom(self):
            raise RuntimeError("DB недоступна")

        monkeypatch.setattr(ClientCardDialog, "_fetch_data", _boom)
        dlg = ClientCardDialog(dict(CLIENT))
        assert _wait_worker(qapp, dlg)
        dlg.close()

    def test_reload_uses_worker(self, qapp, monkeypatch):
        from ventilation_company.gui_pyside6.client_card_dialog import ClientCardDialog

        monkeypatch.setattr(ClientCardDialog, "_fetch_data", lambda self: CARD_DATA)
        dlg = ClientCardDialog(dict(CLIENT))
        assert _wait_worker(qapp, dlg)
        dlg._start_load()
        assert _wait_worker(qapp, dlg)
        assert dlg.table_projects.rowCount() == 1
        dlg.close()


class TestClientHistoryDialog:
    def test_async_load_populates_tables(self, qapp, monkeypatch):
        from ventilation_company.gui_pyside6.client_history_dialog import ClientHistoryDialog

        monkeypatch.setattr(
            ClientHistoryDialog,
            "_fetch_data",
            lambda self: {
                "interactions": list(HISTORY_INTERACTIONS),
                "payments": list(HISTORY_PAYMENTS),
            },
        )
        dlg = ClientHistoryDialog(7, "ТОВ «Тест-Клієнт»")
        assert _wait_worker(qapp, dlg), "worker завис"

        assert dlg.table_interactions.rowCount() == 2
        assert dlg.table_payments.rowCount() == 1
        assert dlg._interactions[0]["subject"] == "Старт"
        assert dlg._payments[0]["amount"] == 12000.0
        dlg.close()

    def test_reload_after_changes(self, qapp, monkeypatch):
        from ventilation_company.gui_pyside6.client_history_dialog import ClientHistoryDialog

        state = {"payments": list(HISTORY_PAYMENTS)}

        def _fetch(self):
            return {"interactions": [], "payments": list(state["payments"])}

        monkeypatch.setattr(ClientHistoryDialog, "_fetch_data", _fetch)
        dlg = ClientHistoryDialog(7, "Клієнт")
        assert _wait_worker(qapp, dlg)
        assert dlg.table_payments.rowCount() == 1

        # Імітація доданої оплати: повторний запуск worker'а підтягує її
        state["payments"].append(
            {
                "id": 2,
                "date": "2026-09-20",
                "amount": 3000.0,
                "currency": "UAH",
                "type": "вхідний",
                "purpose": "доплата",
                "project_name": "",
                "notes": "",
            }
        )
        dlg._start_load()
        assert _wait_worker(qapp, dlg)
        assert dlg.table_payments.rowCount() == 2
        dlg.close()

    def test_fetch_error_reported(self, qapp, monkeypatch):
        from ventilation_company.gui_pyside6.client_history_dialog import ClientHistoryDialog

        def _boom(self):
            raise RuntimeError("DB недоступна")

        monkeypatch.setattr(ClientHistoryDialog, "_fetch_data", _boom)
        dlg = ClientHistoryDialog(7, "Клієнт")
        assert _wait_worker(qapp, dlg)
        assert dlg._interactions == []
        dlg.close()
