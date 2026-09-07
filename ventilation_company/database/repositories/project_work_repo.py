"""Репозиторій для робіт проєкту (ProjectWork) — v2.3."""

from typing import List
from ventilation_company.database.db import get_db
from ventilation_company.database.models.project import ProjectWork


def _work_to_dict(work: ProjectWork) -> dict:
    return {
        "id": work.id,
        "project_id": work.project_id,
        "work_name": work.work_name or "—",
        "quantity": float(work.quantity or 1),
        "unit": work.unit or "шт",
        "unit_price": float(work.unit_price or 0),
        "total_price": float(work.total_price or 0),
    }


class ProjectWorkRepository:
    @staticmethod
    def get_all(project_id: int) -> List[dict]:
        with get_db() as session:
            items = session.query(ProjectWork).filter(ProjectWork.project_id == project_id).order_by(ProjectWork.id).all()
            return [_work_to_dict(i) for i in items]

    @staticmethod
    def create(data: dict) -> dict:
        with get_db() as session:
            qty = data.get("quantity", 1)
            unit_price = data.get("unit_price", 0)
            work = ProjectWork(
                project_id=data["project_id"],
                work_name=data.get("work_name", ""),
                quantity=qty,
                unit=data.get("unit", "шт"),
                unit_price=unit_price,
                total_price=qty * unit_price,
            )
            session.add(work)
            session.flush()
            session.refresh(work)
            session.commit()
            return _work_to_dict(work)

    @staticmethod
    def update(work_id: int, data: dict) -> bool:
        with get_db() as session:
            work = session.query(ProjectWork).filter(ProjectWork.id == work_id).first()
            if not work:
                return False
            for key, value in data.items():
                if hasattr(work, key):
                    setattr(work, key, value)
            # Перерахунок total_price
            work.total_price = (work.quantity or 1) * (work.unit_price or 0)
            session.commit()
            return True

    @staticmethod
    def delete(work_id: int) -> bool:
        with get_db() as session:
            work = session.query(ProjectWork).filter(ProjectWork.id == work_id).first()
            if not work:
                return False
            session.delete(work)
            session.commit()
            return True
