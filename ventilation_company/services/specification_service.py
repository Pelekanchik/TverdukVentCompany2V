"""Specification data service."""

from __future__ import annotations

from ventilation_company.database.db import get_db
from ventilation_company.database.models.project import Project
from ventilation_company.database.repositories.product_repo import ProductRepository


class SpecificationService:
    """Data access + formatting helpers for SpecificationTab."""

    @staticmethod
    def load_projects() -> list[dict]:
        with get_db() as session:
            projects = session.query(Project).order_by(Project.created_at.desc()).all()
            return [
                {
                    "id": p.id,
                    "display": f"{p.project_number or '—'} — {p.name or 'Без назви'}",
                }
                for p in projects
            ]

    @staticmethod
    def load_items(project_id: int) -> list[dict]:
        return ProductRepository.get_all(project_id=project_id)

    @staticmethod
    def format_dimensions(item: dict) -> str:
        w = item.get("width", 0) or 0
        h = item.get("height", 0) or 0
        l = item.get("length", 0) or 0

        if h > 0:
            dims = f"{w:.0f}×{h:.0f}"
            if l > 0:
                dims += f" × {l:.0f}"
            return dims

        dims = f"Ø{w:.0f}"
        if l > 0:
            dims += f" × {l:.0f}"
        return dims

    @staticmethod
    def summarize(items: list[dict]) -> dict:
        return {
            "count": len(items),
            "qty": sum(i.get("quantity", 1) for i in items),
            "area": sum((i.get("metal_area_m2") or 0) * (i.get("quantity") or 1) for i in items),
            "weight": sum((i.get("weight_kg") or 0) * (i.get("quantity") or 1) for i in items),
            "total": sum(i.get("total_price", 0) for i in items),
        }
