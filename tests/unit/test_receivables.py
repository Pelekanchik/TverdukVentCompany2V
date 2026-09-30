"""Тести сервісу дебіторки (services/receivables.py)."""

import pytest

from ventilation_company.services import receivables
from ventilation_company.services.receivables import (
    build_receivables,
    payment_summary,
    receivables_totals,
)


class TestPaymentSummary:
    def test_empty(self):
        s = payment_summary([], 9000)
        assert s["paid"] == 0.0
        assert s["balance"] == 9000.0
        assert s["percent"] == 0.0
        assert s["overpaid"] is False

    def test_incoming_minus_refund(self):
        payments = [
            {"amount": 5000, "type": "вхідний"},
            {"amount": 1000, "type": "вихідний"},
        ]
        s = payment_summary(payments, 9000)
        assert s["paid"] == 4000.0
        assert s["balance"] == 5000.0
        assert s["percent"] == 44.4

    def test_full_payment(self):
        s = payment_summary([{"amount": 9000}], 9000)
        assert s["balance"] == 0.0
        assert s["percent"] == 100.0
        assert s["overpaid"] is False

    def test_overpayment_capped(self):
        s = payment_summary([{"amount": 10000}], 9000)
        assert s["overpaid"] is True
        assert s["percent"] == 100.0

    def test_zero_price_no_division_error(self):
        s = payment_summary([{"amount": 1000}], 0)
        assert s["percent"] == 0.0


@pytest.fixture
def stub_repos(monkeypatch):
    """Ізольовані репозиторії з фіксованими даними."""
    projects = [
        {
            "id": 1,
            "project_number": "ПР-1",
            "name": "Проєкт А",
            "client": "ТОВ «А»",
            "status": "в роботі",
        },
        {
            "id": 2,
            "project_number": "ПР-2",
            "name": "Проєкт Б",
            "client": "ТОВ «Б»",
            "status": "здано",
        },
    ]
    data = {
        1: {
            "products": [
                {"discounted_price": 0, "total_price": 8000.0},
            ],
            "works": [{"total_price": 1000.0}],
            "expenses": [
                {"total_price": 500.0, "direction": "plus"},
                {"total_price": 300.0, "direction": "minus"},
            ],
            "payments": [
                {"date": "2026-09-01", "type": "вхідний", "amount": 4000},
            ],
        },
        2: {
            "products": [],
            "works": [{"total_price": 2000.0}],
            "expenses": [],
            "payments": [
                {"date": "2026-08-15", "type": "вхідний", "amount": 3000},
                {"date": "2026-09-20", "type": "вихідний", "amount": 500},
            ],
        },
    }
    monkeypatch.setattr(receivables.ProjectRepository, "list_all", staticmethod(lambda: projects))
    monkeypatch.setattr(
        receivables.ProductRepository,
        "get_all",
        staticmethod(lambda project_id: data[project_id]["products"]),
    )
    monkeypatch.setattr(
        receivables.ProjectWorkRepository,
        "get_all",
        staticmethod(lambda project_id: data[project_id]["works"]),
    )
    monkeypatch.setattr(
        receivables.ProjectExpenseRepository,
        "get_all",
        staticmethod(lambda project_id: data[project_id]["expenses"]),
    )
    monkeypatch.setattr(
        receivables.PaymentRepository,
        "list_by_project",
        staticmethod(lambda project_id: data[project_id]["payments"]),
    )
    return projects


class TestBuildReceivables:
    def test_rows_content(self, stub_repos):
        rows = build_receivables()
        assert len(rows) == 2

        a = next(r for r in rows if r["project_id"] == 1)
        # 8000 (виробі) + 1000 (роботи) + 500 (plus-витрати) = 9500
        assert a["total"] == 9500.0
        assert a["paid"] == 4000.0
        assert a["balance"] == 5500.0
        assert a["last_payment"] == "2026-09-01"
        assert a["payments_count"] == 1

        b = next(r for r in rows if r["project_id"] == 2)
        # 2000 роботи; сплачено 3000 - 500 повернення = 2500 → переплата 500
        assert b["total"] == 2000.0
        assert b["paid"] == 2500.0
        assert b["overpaid"] is True

    def test_sorting_debt_first(self, stub_repos):
        rows = build_receivables()
        # Проєкт з боргом (А) — перед проєктом із переплатою (Б).
        assert rows[0]["project_id"] == 1
        assert rows[1]["project_id"] == 2

    def test_explicit_projects_argument(self, stub_repos):
        rows = build_receivables(
            [{"id": 1, "project_number": "ПР-1", "name": "X", "client": "", "status": ""}]
        )
        assert len(rows) == 1
        assert rows[0]["project_id"] == 1


class TestReceivablesTotals:
    def test_totals(self):
        rows = [
            {"total": 1000.0, "paid": 400.0, "balance": 600.0, "overpaid": False},
            {"total": 2000.0, "paid": 2500.0, "balance": -500.0, "overpaid": True},
        ]
        t = receivables_totals(rows)
        assert t["projects"] == 2
        assert t["total"] == 3000.0
        assert t["paid"] == 2900.0
        assert t["debt"] == 600.0
        assert t["overpaid"] == 500.0
