"""Тести кнопки «В Telegram» у вкладці розкрою."""

import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets", reason="потрібен Qt")
QApplication = QtWidgets.QApplication


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def _make_tab(
    qapp, monkeypatch, tmp_path, *, plan_ready: bool, token: str = "tok", chat: str = "1"
):
    from ventilation_company.gui_pyside6 import telegram_send

    monkeypatch.setattr(telegram_send, "cloud_backup_preferences", lambda: (True, token, chat))
    sent: list[tuple] = []

    def fake_send(token_, chat_, file_path, caption=""):
        sent.append((token_, chat_, file_path, caption))
        return True

    monkeypatch.setattr(telegram_send, "send_telegram_document", fake_send)

    from ventilation_company.gui_pyside6 import cutting_tab

    tab = cutting_tab.CuttingTab()
    if plan_ready:
        tab._plan = _make_plan()
    return tab, sent


def _make_plan():
    from types import SimpleNamespace

    detail = SimpleNamespace(name="Повітропровід 400×200×500")
    sheet = SimpleNamespace(
        width=1250,
        height=2500,
        placed_details=[
            SimpleNamespace(x=0, y=0, width=1204, height=510, rotated=False, detail=detail),
        ],
    )
    return SimpleNamespace(
        sheets=[sheet],
        get_summary=lambda: {
            "total_sheets": 1,
            "utilization_percent": 80.0,
            "waste_percent": 20.0,
            "used_area_m2": 5.0,
        },
    )


def test_send_telegram_without_plan_warns(qapp, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    tab, sent = _make_tab(qapp, monkeypatch, tmp_path, plan_ready=False)
    tab._on_send_telegram()
    assert sent == []  # нічого не відправлено


def test_send_telegram_without_token_warns(qapp, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    tab, sent = _make_tab(qapp, monkeypatch, tmp_path, plan_ready=True, token="")
    tab._on_send_telegram()
    assert sent == []


def test_send_telegram_ok(qapp, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: None))
    tab, sent = _make_tab(qapp, monkeypatch, tmp_path, plan_ready=True)
    tab._on_send_telegram()
    # чекаємо завершення фонового потоку
    if tab._tg_doc_worker is not None:
        tab._tg_doc_worker.wait(5000)
    assert len(sent) == 1
    token_, chat_, file_path, caption = sent[0]
    assert token_ == "tok" and chat_ == "1"
    assert file_path.endswith(".pdf")
    assert "План розкрою" in caption
