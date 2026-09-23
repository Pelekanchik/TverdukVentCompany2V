"""Project repository."""

from __future__ import annotations

from ventilation_company.database.db import get_db
from ventilation_company.database.models.project import Project


def _to_dict(project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "project_number": project.project_number,
        "client": project.client,
        "client_id": project.client_id,
        "address": project.address,
        "status": project.status,
        "priority": project.priority,
        "progress": project.progress,
        "start_date": project.start_date,
        "deadline": project.deadline,
        "completed_date": project.completed_date,
        "cost_price": project.cost_price,
        "customer_price": project.customer_price,
        "discounted_price": project.discounted_price,
        "profit": project.profit,
        "margin_percent": project.margin_percent,
        "notes": project.notes,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


class ProjectRepository:
    @staticmethod
    def list_all() -> list[dict]:
        with get_db() as session:
            projects = session.query(Project).order_by(Project.created_at.desc()).all()
            return [_to_dict(p) for p in projects]

    @staticmethod
    def get(project_id: int) -> dict | None:
        with get_db() as session:
            project = session.get(Project, project_id)
            return _to_dict(project) if project else None

    @staticmethod
    def create(data: dict) -> dict:
        with get_db() as session:
            project = Project(
                name=data.get("name"),
                project_number=data.get("project_number"),
                client=data.get("client"),
                client_id=data.get("client_id"),
                address=data.get("address"),
                status=data.get("status") or "Новий",
                priority=data.get("priority") or "Середній",
                progress=data.get("progress") or 0,
                start_date=data.get("start_date"),
                deadline=data.get("deadline"),
                completed_date=data.get("completed_date"),
                cost_price=data.get("cost_price") or 0,
                customer_price=data.get("customer_price") or 0,
                discounted_price=data.get("discounted_price") or 0,
                profit=data.get("profit") or 0,
                margin_percent=data.get("margin_percent") or 0,
                notes=data.get("notes"),
            )
            session.add(project)
            session.commit()
            session.refresh(project)
            return _to_dict(project)

    @staticmethod
    def update(project_id: int, data: dict) -> dict | None:
        with get_db() as session:
            project = session.get(Project, project_id)
            if not project:
                return None
            fields = {
                "name",
                "project_number",
                "client",
                "client_id",
                "address",
                "status",
                "priority",
                "progress",
                "start_date",
                "deadline",
                "completed_date",
                "cost_price",
                "customer_price",
                "discounted_price",
                "profit",
                "margin_percent",
                "notes",
            }
            for key in fields:
                if key in data:
                    setattr(project, key, data[key])
            session.commit()
            session.refresh(project)
            return _to_dict(project)

    @staticmethod
    def delete(project_id: int) -> bool:
        with get_db() as session:
            project = session.get(Project, project_id)
            if not project:
                return False
            session.delete(project)
            session.commit()
            return True
