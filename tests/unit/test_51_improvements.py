"""Тести покращень 5.1: Telegram-сповіщення, PDF-звіти, перегляд креслень, етикетки."""

from datetime import datetime, timedelta
from types import SimpleNamespace


def test_payment_text_without_project_id_has_no_balance():
    """Без project_id рядки залишку не додаються і текст будується без помилок."""
    from ventilation_company.services.project_notifications import build_payment_received_text

    text = build_payment_received_text(
        {
            "amount": 5000,
            "project_name": "Касова оплата",
            "type": "вхідний",
            "date": "2026-10-10",
        }
    )
    assert "5 000.00 ₴" in text
    assert "Оплачено за проєктом" not in text
    assert "Залишок до сплати" not in text


def test_payment_text_with_unknown_project_id_still_works():
    """project_id, за яким не вдалося порахувати (немає БД/проєкту), не ламає текст."""
    from ventilation_company.services.project_notifications import (
        _project_payment_context,
        build_payment_received_text,
    )

    payment = {"amount": 100, "project_id": 999999999}
    # контекст не рахується — але і виняток не підіймається
    _project_payment_context(payment)
    text = build_payment_received_text(payment)
    assert "100.00 ₴" in text


def test_status_changed_text():
    from ventilation_company.services.project_notifications import build_status_changed_text

    text = build_status_changed_text(
        {"name": "Вентиляція ТЦ", "project_number": "П-15"}, "Новий", "В роботі"
    )
    assert "Вентиляція ТЦ" in text
    assert "П-15" in text
    assert "Новий" in text and "В роботі" in text


def test_notify_status_changed_skips_same_or_missing(monkeypatch):
    from ventilation_company.services import project_notifications

    # однакові статуси — без відправки, навіть із налаштованим ботом
    assert project_notifications.notify_project_status_changed({}, "В роботі", "В роботі") is False
    assert project_notifications.notify_project_status_changed({}, "", "") is False
    # бот не налаштовано — False
    monkeypatch.setattr(project_notifications, "cloud_backup_preferences", lambda: (False, "", ""))
    assert project_notifications.notify_project_status_changed({}, "Новий", "В роботі") is False


def test_notify_status_changed_sends(monkeypatch):
    from ventilation_company.services import project_notifications

    monkeypatch.setattr(
        project_notifications, "cloud_backup_preferences", lambda: (True, "tok", "42")
    )
    sent: list[str] = []
    monkeypatch.setattr(
        project_notifications,
        "send_telegram_message",
        lambda token, chat, text: sent.append(text) or True,
    )
    ok = project_notifications.notify_project_status_changed(
        {"name": "Вентиляція ТЦ"}, "Новий", "В роботі"
    )
    assert ok is True and sent and "В роботі" in sent[0]


def _patch_repos(monkeypatch, projects):
    """Підставити фейкові репозиторії для check_stuck_projects."""
    from ventilation_company.database.repositories import (
        app_settings_repository,
        project_repo,
    )

    class FakeSettings:
        def get(self, key, default):
            return default

    class FakeProjectRepo:
        @staticmethod
        def list_all():
            return projects

    monkeypatch.setattr(app_settings_repository, "AppSettingsRepository", FakeSettings)
    monkeypatch.setattr(project_repo, "ProjectRepository", FakeProjectRepo)


def test_check_stuck_projects_sends_digest(monkeypatch):
    from ventilation_company.services import project_notifications

    old = (datetime.now() - timedelta(days=30)).isoformat()
    projects = [
        {"name": "Старий проєкт", "status": "В роботі", "updated_at": old},
        {"name": "Завершений", "status": "Закрито", "updated_at": old},  # ігнорується
        {
            "name": "Свіжий",
            "status": "Новий",
            "updated_at": datetime.now().isoformat(),
        },  # не завислий
    ]
    _patch_repos(monkeypatch, projects)
    monkeypatch.setattr(
        project_notifications, "cloud_backup_preferences", lambda: (True, "tok", "42")
    )
    sent: list[str] = []
    monkeypatch.setattr(
        project_notifications,
        "send_telegram_message",
        lambda token, chat, text: sent.append(text) or True,
    )
    assert project_notifications.check_stuck_projects() is True
    assert len(sent) == 1
    assert "Старий проєкт" in sent[0]
    assert "Завершений" not in sent[0]
    assert "Свіжий" not in sent[0]


def test_check_stuck_projects_no_stuck(monkeypatch):
    from ventilation_company.services import project_notifications

    fresh = {"name": "Активний", "status": "В роботі", "updated_at": datetime.now().isoformat()}
    _patch_repos(monkeypatch, [fresh])
    monkeypatch.setattr(
        project_notifications, "cloud_backup_preferences", lambda: (True, "tok", "42")
    )
    assert project_notifications.check_stuck_projects() is False


def test_check_stuck_projects_without_bot(monkeypatch):
    from ventilation_company.services import project_notifications

    _patch_repos(monkeypatch, [])
    monkeypatch.setattr(project_notifications, "cloud_backup_preferences", lambda: (False, "", ""))
    assert project_notifications.check_stuck_projects() is False


def _dashboard_stats():
    return {
        "total_count": 12,
        "active_count": 7,
        "total_revenue": 1_500_000.0,
        "paid": 900_000.0,
        "debt": 600_000.0,
        "clients": 5,
        "done_count": 5,
        "overpaid": 0.0,
        "monthly": [{"month": 9, "count": 3, "sum": 450000.0}],
        "payments_monthly": [{"month": 9, "sum": 300000.0}],
        "statuses": [{"status": "В роботі", "count": 4}, {"status": "Закрито", "count": 5}],
    }


def test_dashboard_pdf_created(tmp_path):
    from ventilation_company.dashboard_pdf_generator import generate_dashboard_pdf

    out = tmp_path / "dashboard.pdf"
    result = generate_dashboard_pdf(_dashboard_stats(), str(out))
    assert result == str(out)
    data = out.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 3000


def _labels_plan():
    detail = SimpleNamespace(name="Відвод 400×200 90°")
    sheet = SimpleNamespace(
        width=1250,
        height=2500,
        placed_details=[
            SimpleNamespace(x=0, y=0, width=404, height=210, rotated=False, detail=detail)
            for _ in range(3)
        ],
    )
    return SimpleNamespace(sheets=[sheet, sheet])  # 6 деталей, 2 листи


def test_labels_pdf_created(tmp_path):
    from ventilation_company.cutting_labels_generator import generate_labels_pdf

    out = tmp_path / "labels.pdf"
    result = generate_labels_pdf(
        _labels_plan(),
        str(out),
        meta={"material": "Оцинкована сталь", "thickness": "0.7", "sheet_size": "1250×2500"},
    )
    assert result == str(out)
    data = out.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 3000  # QR-коди на місці


def test_labels_collect_all_sheets():
    from ventilation_company.cutting_labels_generator import _LabelsPDF

    pdf = _LabelsPDF(_labels_plan(), meta={})
    labels = pdf._collect_labels()
    assert len(labels) == 6  # 3 деталі × 2 листи, суцільна нумерація
    assert [lb["num"] for lb in labels] == [1, 2, 3, 4, 5, 6]


def _preview_stub(drawing):
    """Мінімальний об'єкт із методами міксіна для тесту попереднього перегляду."""
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QLabel

    from ventilation_company.gui_pyside6.project_card_docs_mixin import ProjectCardDocsMixin

    class _Stub(SimpleNamespace):
        def _set_preview_message(self, text):
            self._drawing_preview.setPixmap(QPixmap())
            self._drawing_preview.setText(text)

    obj = _Stub()
    obj._drawing_preview = QLabel()
    obj._selected_drawing = lambda: drawing
    obj._PREVIEW_IMAGES = ProjectCardDocsMixin._PREVIEW_IMAGES
    return obj


def test_drawing_preview_no_selection(qapp):
    from ventilation_company.gui_pyside6.project_card_docs_mixin import ProjectCardDocsMixin

    obj = _preview_stub(None)
    ProjectCardDocsMixin._update_drawing_preview(obj)
    assert "Оберіть креслення" in obj._drawing_preview.text()


def test_drawing_preview_missing_file(qapp):
    from ventilation_company.gui_pyside6.project_card_docs_mixin import ProjectCardDocsMixin

    obj = _preview_stub({"file_path": "C:\\no_such_file_12345.dwg"})
    ProjectCardDocsMixin._update_drawing_preview(obj)
    assert "не знайдено" in obj._drawing_preview.text()


def test_drawing_preview_unsupported_ext(qapp):
    import os
    import tempfile

    from ventilation_company.gui_pyside6.project_card_docs_mixin import ProjectCardDocsMixin

    # існуючий файл із форматом без попереднього перегляду
    with tempfile.NamedTemporaryFile(suffix=".dwg", delete=False) as f:
        f.write(b"dummy")
        path = f.name
    try:
        obj = _preview_stub({"file_path": path})
        ProjectCardDocsMixin._update_drawing_preview(obj)
        assert "недоступний" in obj._drawing_preview.text()
    finally:
        os.unlink(path)
