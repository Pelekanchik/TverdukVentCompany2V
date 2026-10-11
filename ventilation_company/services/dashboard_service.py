"""Агрегація даних для дашборду головної сторінки.

Рахує по ВСІХ проєктах (не тільки завершених): договірна вартість,
отримані оплати, дебіторка (через сервіс дебіторки — ті самі цифри,
що у вкладці «Гроші»), динаміку по місяцях та розподіл за статусами.
"""

from __future__ import annotations

from collections import Counter

from sqlalchemy import extract, func

from ventilation_company.database.db import get_db
from ventilation_company.database.models.unified import Payment
from ventilation_company.database.repositories.client_repo import ClientRepository
from ventilation_company.database.repositories.project_repo import ProjectRepository
from ventilation_company.services.receivables import (
    _DONE_STATUSES,
    build_receivables,
    receivables_totals,
)


class DashboardService:
    @staticmethod
    def overview() -> dict:
        """Підсумки для дашборду.

        Повертає {
            total_count, active_count, done_count,
            total_revenue, paid, debt, overpaid,
            clients, monthly, statuses, payments_monthly,
        }:
        - monthly: [{"month": 1..12, "count", "sum"}] — проєкти за місяцем
          створення (лише ті, що мають дату);
        - statuses: [{"status", "count"}] — розподіл проєктів за статусом;
        - payments_monthly: [{"month", "sum"}] — вхідні оплати за місяцем.
        """
        projects = ProjectRepository.list_all()
        receivables = build_receivables(projects)
        totals = receivables_totals(receivables)
        total_by_id = {row["project_id"]: row["total"] for row in receivables}
        clients = ClientRepository.list_all()

        statuses_counter: Counter[str] = Counter()
        monthly_acc: dict[int, dict] = {}
        for p in projects:
            statuses_counter[(p.get("status") or "—").strip() or "—"] += 1
            created = p.get("created_at")
            if created is None:
                continue
            month = int(getattr(created, "month", 0) or 0)
            if not month:
                continue
            bucket = monthly_acc.setdefault(month, {"month": month, "count": 0, "sum": 0.0})
            bucket["count"] += 1
            bucket["sum"] += float(total_by_id.get(int(p.get("id") or 0), 0.0))

        done_count = sum(
            count for status, count in statuses_counter.items() if status.lower() in _DONE_STATUSES
        )

        return {
            "total_count": len(projects),
            "active_count": len(projects) - done_count,
            "done_count": done_count,
            "total_revenue": totals["total"],
            "paid": totals["paid"],
            "debt": totals["debt"],
            "overpaid": totals["overpaid"],
            "clients": len(clients),
            "monthly": sorted(monthly_acc.values(), key=lambda row: row["month"]),
            "statuses": [
                {"status": status, "count": count}
                for status, count in statuses_counter.most_common()
            ],
            "payments_monthly": DashboardService._payments_monthly(),
        }

    @staticmethod
    def _payments_monthly() -> list[dict]:
        """Вхідні оплати згруповані за місяцем дати платежу."""
        try:
            with get_db() as session:
                rows = (
                    session.query(
                        extract("month", Payment.date).label("month"),
                        func.sum(Payment.amount).label("sum"),
                    )
                    .filter(Payment.payment_type == "вхідний", Payment.date.isnot(None))
                    .group_by("month")
                    .order_by("month")
                    .all()
                )
            return [{"month": int(m), "sum": float(s or 0)} for m, s in rows if m is not None]
        except Exception:
            return []
