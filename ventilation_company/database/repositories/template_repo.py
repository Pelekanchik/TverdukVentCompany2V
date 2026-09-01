"""
Репозиторій для роботи з шаблонами розрахунків (PostgreSQL / SQLAlchemy ORM).
"""

import json
from datetime import datetime

from ventilation_company.database.db import get_db
from ventilation_company.database.models.calc_template import CalcTemplate


class TemplateRepo:
    """CRUD для calc_templates через SQLAlchemy ORM."""

    @staticmethod
    def get_all() -> list[dict]:
        with get_db() as session:
            rows = session.query(CalcTemplate).order_by(CalcTemplate.name).all()
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "items_data": r.items_data,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]

    @staticmethod
    def get_by_id(template_id: int) -> dict | None:
        with get_db() as session:
            row = session.query(CalcTemplate).filter(CalcTemplate.id == template_id).first()
            if row is None:
                return None
            return {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "items_data": row.items_data,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }

    @staticmethod
    def add(name: str, description: str = "", items_data: list[dict] = None) -> int:
        with get_db() as session:
            tmpl = CalcTemplate(
                name=name,
                description=description,
                items_data=json.dumps(items_data or []),
                created_at=datetime.utcnow(),
            )
            session.add(tmpl)
            session.flush()
            return tmpl.id

    @staticmethod
    def update(template_id: int, **kwargs) -> None:
        allowed = {"name", "description", "items_data"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        if "items_data" in fields:
            fields["items_data"] = json.dumps(fields["items_data"])

        with get_db() as session:
            tmpl = session.query(CalcTemplate).filter(CalcTemplate.id == template_id).first()
            if tmpl:
                for k, v in fields.items():
                    setattr(tmpl, k, v)

    @staticmethod
    def delete(template_id: int) -> None:
        with get_db() as session:
            tmpl = session.query(CalcTemplate).filter(CalcTemplate.id == template_id).first()
            if tmpl:
                session.delete(tmpl)
