"""Dashboard aggregation service."""

from __future__ import annotations

from sqlalchemy import extract, func

from ventilation_company.database.db import get_db
from ventilation_company.database.models.project import Project
from ventilation_company.database.repositories.product_repo import ProductRepository


class DashboardService:
    @staticmethod
    def done_dashboard(done_statuses: list[str]) -> dict:
        with get_db() as session:
            done_projects = session.query(Project).filter(Project.status.in_(done_statuses)).all()
            total_revenue = 0
            total_cost = 0
            for p in done_projects:
                try:
                    products = ProductRepository.get_all(project_id=p.id)
                    for item in products:
                        total_revenue += item.get("total_price", 0)
                        total_cost += item.get("unit_price", 0) * item.get("quantity", 1)
                except Exception:
                    pass

            clients = (
                session.query(Project.client)
                .filter(Project.status.in_(done_statuses), Project.client != None)
                .distinct()
                .count()
            )

            monthly = (
                session.query(
                    extract("month", Project.created_at).label("month"),
                    func.count(Project.id).label("cnt"),
                    func.sum(Project.customer_price).label("sum"),
                )
                .filter(Project.status.in_(done_statuses))
                .group_by("month")
                .order_by("month")
                .all()
            )
            monthly_rows = [
                {"month": int(m), "count": int(c), "sum": float(s or 0)} for m, c, s in monthly
            ]

            return {
                "done_count": len(done_projects),
                "total_revenue": total_revenue,
                "total_cost": total_cost,
                "profit": total_revenue - total_cost,
                "clients": clients,
                "monthly": monthly_rows,
            }
