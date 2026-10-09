"""Тести Telegram-сповіщень: сервіс звіту про проєкт + GUI-хелпер відправки файлів."""

import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets", reason="потрібен Qt")
QApplication = QtWidgets.QApplication
QMessageBox = QtWidgets.QMessageBox


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


# ── Сервіс project_notifications ──


def test_build_text_contains_project_and_client():
    from ventilation_company.services.project_notifications import build_project_created_text

    text = build_project_created_text(
        {
            "name": "Вентиляція кафе",
            "project_number": "PRJ-1",
            "status": "Новий",
            "customer_price": 150000,
            "discounted_price": 140000,
            "cost_price": 100000,
            "profit": 40000,
            "client": "ТОВ «Вент» (0501234567)",
        }
    )
    assert "🆕" in text
    assert "Вентиляція кафе" in text
    assert "PRJ-1" in text
    assert "140 000.00 ₴" in text  # ціна зі знижкою пріоритетна
    assert "50 000.00 ₴" not in text  # customer_price без знижки не дублюється
    assert "ТОВ «Вент»" in text
    assert "(0501234567)" not in text  # телефон з display-рядка обрізано


def test_notify_project_created_without_bot(monkeypatch):
    from ventilation_company.services import project_notifications

    monkeypatch.setattr(project_notifications, "cloud_backup_preferences", lambda: (False, "", ""))
    assert project_notifications.notify_project_created({"name": "X"}) is False


def test_notify_project_created_sends_message(monkeypatch):
    from ventilation_company.services import project_notifications

    monkeypatch.setattr(
        project_notifications, "cloud_backup_preferences", lambda: (True, "tok", "42")
    )
    sent: list[tuple] = []
    monkeypatch.setattr(
        project_notifications,
        "send_telegram_message",
        lambda token, chat, text: sent.append((token, chat, text)) or True,
    )
    ok = project_notifications.notify_project_created(
        {"name": "Вентиляція", "project_number": "P-9"}
    )
    assert ok is True
    assert sent and sent[0][0] == "tok" and sent[0][1] == "42"
    assert "Вентиляція" in sent[0][2]


def test_send_telegram_message_uses_sendmessage_api(monkeypatch):
    """Функція send_telegram_message ходить на /sendMessage з urlencoded-тілом."""
    from ventilation_company.utils import cloud_backup

    captured: dict = {}

    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        captured["body"] = req.data
        return _Resp()

    monkeypatch.setattr(cloud_backup.urlrequest, "urlopen", fake_urlopen)
    assert cloud_backup.send_telegram_message("TOK", "7", "Привіт") is True
    assert captured["url"].endswith("/botTOK/sendMessage")
    body = captured["body"].decode()
    from urllib.parse import parse_qs

    fields = parse_qs(body)
    assert fields["chat_id"] == ["7"]
    assert fields["text"] == ["Привіт"]


# ── GUI-хелпер telegram_send ──


def test_helper_warns_without_bot(qapp, monkeypatch):
    from ventilation_company.gui_pyside6 import telegram_send

    monkeypatch.setattr(telegram_send, "cloud_backup_preferences", lambda: (False, "", ""))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    parent = QtWidgets.QWidget()
    assert telegram_send.send_document_telegram(parent, "x.pdf", "cap") is False
    assert not hasattr(parent, "_tg_doc_worker")


def test_helper_sends_file_in_background(qapp, monkeypatch, tmp_path):
    from ventilation_company.gui_pyside6 import telegram_send

    monkeypatch.setattr(telegram_send, "cloud_backup_preferences", lambda: (True, "tok", "1"))
    sent: list[tuple] = []
    monkeypatch.setattr(
        telegram_send,
        "send_telegram_document",
        lambda token, chat, path, caption="": sent.append((token, chat, path, caption)) or True,
    )
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: None))

    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")
    parent = QtWidgets.QWidget()
    assert telegram_send.send_document_telegram(parent, str(pdf), "Підпис") is True
    worker = parent._tg_doc_worker
    assert worker is not None
    worker.wait(5000)
    assert len(sent) == 1
    assert sent[0][:3] == ("tok", "1", str(pdf))
    assert sent[0][3] == "Підпис"
