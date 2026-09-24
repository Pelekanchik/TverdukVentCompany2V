"""Project repository."""

from __future__ import annotations

from datetime import datetime

from ventilation_company.database.db import get_db
from ventilation_company.database.models.project import Project


def _columns() -> set[str]:
    return set(Project.__table__.columns.keys())


def _to_dict(project: Project) -> dict:
    return {key: getattr(project, key, None) for key in _columns()}


class ProjectRepository:
    @staticmethod
    def list_all() -> list[dict]:
        with get_db() as session:
            projects = session.query(Project).order_by(Project.created_at.desc()).all()
            return [_to_dict(p) for p in projects]

    @staticmethod
    def list_by_client(client_id: int) -> list[dict]:
        with get_db() as session:
            projects = (
                session.query(Project)
                .filter(Project.client_id == client_id)
                .order_by(Project.created_at.desc())
                .all()
            )
            return [_to_dict(p) for p in projects]

    @staticmethod
    def get(project_id: int) -> dict | None:
        with get_db() as session:
            project = session.get(Project, project_id)
            return _to_dict(project) if project else None

    @staticmethod
    def create(data: dict) -> dict:
        columns = _columns()
        with get_db() as session:
            project = Project()
            for key, value in data.items():
                if key in columns and value is not None:
                    setattr(project, key, value)
            if "created_at" in columns and getattr(project, "created_at", None) is None:
                project.created_at = datetime.now()
            session.add(project)
            session.commit()
            session.refresh(project)
            return _to_dict(project)

    @staticmethod
    def update(project_id: int, data: dict) -> dict | None:
        columns = _columns()
        with get_db() as session:
            project = session.get(Project, project_id)
            if not project:
                return None
            for key, value in data.items():
                if key in columns:
                    setattr(project, key, value)
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

    @staticmethod
    def delete_cascade(project_id: int) -> bool:
        """Delete project with related documents and products."""
        from ventilation_company.database.models.product_item import ProductItem
        from ventilation_company.database.models.project_document import ProjectDocument

        with get_db() as session:
            project = session.get(Project, project_id)
            if not project:
                return False
            session.query(ProjectDocument).filter(ProjectDocument.project_id == project_id).delete()
            session.query(ProductItem).filter(ProductItem.project_id == project_id).delete()
            session.delete(project)
            session.commit()
            return True
