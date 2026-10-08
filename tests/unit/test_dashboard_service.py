"""Тести сервісу дашборду (services/dashboard_service.py)."""

from datetime import datetime

import pytest

from ventilation_company.services import dashboard_service
from ventilation_company.services.dashboard_service import DashboardService


def _stub_dashboard(monkeypatch, projects, rec_rows, totals, clients):
    monkeypatch.setattr(
        dashboard_service.ProjectRepository, "list_all", staticmethod(lambda: projects)
    )
    monkeypatch.setattr(dashboard_service, "build_receivables", lambda p: rec_rows)
    monkeypatch.setattr(dashboard_service, "receivables_totals", lambda r: totals)
    monkeypatch.setattr(
        dashboard_service.ClientRepository, "list_all", staticmethod(lambda: clients)
    )
    monkeypatch.setattr(DashboardService, "_payments_monthly", staticmethod(lambda: []))


class TestPaymentsMonthly:
    def test_groups_incoming_by_month(self, monkeypatch):
        class _Query:
            def filter(self, *a, **kw):
                return self

            def group_by(self, *a):
                return self

            def order_by(self, *a):
                return self

            def all(self):
                return [(9, 15000.0), (10, 7000.0)]

        class _Session:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def query(self, *a):
                return _Query()

        monkeypatch.setattr(dashboard_service, "get_db", lambda: _Session())
        result = DashboardService._payments_monthly()
        assert result == [{"month": 9, "sum": 15000.0}, {"month": 10, "sum": 7000.0}]

    def test_returns_empty_on_db_error(self, monkeypatch):
        def boom():
            raise RuntimeError("БД недоступна")

        monkeypatch.setattr(dashboard_service, "get_db", boom)
        assert DashboardService._payments_monthly() == []


class TestOverview:
    def test_empty_database(self, monkeypatch):
        _stub_dashboard(monkeypatch, [], [], {"total": 0, "paid": 0, "debt": 0, "overpaid": 0}, [])
        stats = DashboardService.overview()
        assert stats["total_count"] == 0
        assert stats["active_count"] == 0
        assert stats["done_count"] == 0
        assert stats["monthly"] == []
        assert stats["statuses"] == []

    def test_counts_and_statuses(self, monkeypatch):
        projects = [
            {"id": 1, "status": "draft", "created_at": datetime(2026, 9, 5)},
            {"id": 2, "status": "Завершено", "created_at": datetime(2026, 9, 20)},
            {"id": 3, "status": "в роботі", "created_at": None},
        ]
        _stub_dashboard(
            monkeypatch,
            projects,
            rec_rows=[],
            totals={"total": 0, "paid": 0, "debt": 0, "overpaid": 0},
            clients=[{"id": 1}, {"id": 2}],
        )
        stats = DashboardService.overview()
        assert stats["total_count"] == 3
        assert stats["done_count"] == 1
        assert stats["active_count"] == 2
        assert stats["clients"] == 2
        statuses = {row["status"]: row["count"] for row in stats["statuses"]}
        assert statuses == {"draft": 1, "Завершено": 1, "в роботі": 1}

    def test_monthly_aggregation_uses_receivables_total(self, monkeypatch):
        projects = [
            {"id": 1, "status": "draft", "created_at": datetime(2026, 9, 5)},
            {"id": 2, "status": "draft", "created_at": datetime(2026, 9, 25)},
            {"id": 3, "status": "draft", "created_at": datetime(2026, 10, 1)},
        ]
        rec_rows = [
            {"project_id": 1, "total": 10000.0},
            {"project_id": 2, "total": 5000.0},
            {"project_id": 3, "total": 7000.0},
        ]
        _stub_dashboard(
            monkeypatch,
            projects,
            rec_rows=rec_rows,
            totals={"total": 22000, "paid": 1000, "debt": 21000, "overpaid": 0},
            clients=[],
        )
        stats = DashboardService.overview()
        monthly = {row["month"]: row for row in stats["monthly"]}
        assert monthly[9]["count"] == 2
        assert monthly[9]["sum"] == 15000.0
        assert monthly[10]["count"] == 1
        assert monthly[10]["sum"] == 7000.0
        assert stats["total_revenue"] == 22000
        assert stats["paid"] == 1000
        assert stats["debt"] == 21000

    def test_done_statuses_case_insensitive(self, monkeypatch):
        projects = [
            {"id": 1, "status": "COMPLETED", "created_at": None},
            {"id": 2, "status": "Виконано", "created_at": None},
            {"id": 3, "status": "draft", "created_at": None},
        ]
        _stub_dashboard(
            monkeypatch,
            projects,
            rec_rows=[],
            totals={"total": 0, "paid": 0, "debt": 0, "overpaid": 0},
            clients=[],
        )
        stats = DashboardService.overview()
        assert stats["done_count"] == 2
        assert stats["active_count"] == 1


# ── Автооновлення вкладки дашборду ──


@pytest.fixture
def qapp():
    """Власна фікстура QApplication (pytest-qt у CI не встановлено)."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    return app


def test_dashboard_timer_active_and_interval(qapp, monkeypatch):
    """Таймер автооновлення існує, активний і спрацьовує раз на хвилину."""
    from ventilation_company.gui_pyside6.dashboard_tab import DashboardTab

    monkeypatch.setattr(dashboard_service.ProjectRepository, "list_all", staticmethod(lambda: []))
    monkeypatch.setattr(dashboard_service.ClientRepository, "list_all", staticmethod(lambda: []))
    tab = DashboardTab()
    assert tab._timer.isActive()
    assert tab._timer.interval() == DashboardTab.REFRESH_INTERVAL_MS == 60_000


def test_dashboard_timer_skips_hidden_tab(qapp, monkeypatch):
    """Коли вкладка невидима, таймер не перечитує дані."""
    from ventilation_company.gui_pyside6.dashboard_tab import DashboardTab

    calls = []
    monkeypatch.setattr(DashboardService, "overview", staticmethod(lambda: calls.append(1) or {}))
    tab = DashboardTab()
    tab.refresh = lambda: calls.append("refresh")  # type: ignore[method-assign]
    calls.clear()  # скидаємо початкове refresh() з __init__
    tab.hide()
    assert not tab.isVisible()
    tab._on_timer()
    assert calls == []  # прихована вкладка — оновлення немає
    tab.show()
    tab._on_timer()
    assert calls == ["refresh"]
