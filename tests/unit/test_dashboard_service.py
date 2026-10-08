"""Тести сервісу дашборду (services/dashboard_service.py)."""

from datetime import datetime

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
