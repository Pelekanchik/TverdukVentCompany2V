"""Репозиторій для документів проєкту (ProjectDocument).

CRUD + фільтрація по проєкту та типу.
"""

from typing import List

from ventilation_company.database.db import get_db
from ventilation_company.database.models.project_document import ProjectDocument


class ProjectDocumentRepository:
    """CRUD для документів проєкту."""

    @staticmethod
    def create(project_id: int, doc_type: str, filename: str, content: bytes) -> dict:
        with get_db() as session:
            doc = ProjectDocument(
                project_id=project_id,
                doc_type=doc_type,
                filename=filename,
                content=content,
                file_size=len(content),
            )
            session.add(doc)
            session.flush()
            session.refresh(doc)
            session.commit()
            return {
                "id": doc.id,
                "project_id": doc.project_id,
                "doc_type": doc.doc_type,
                "filename": doc.filename,
                "file_size": doc.file_size,
                "created_at": doc.created_at,
            }

    @staticmethod
    def get_by_project(project_id: int, doc_type: str = None) -> List[dict]:
        with get_db() as session:
            q = session.query(ProjectDocument).filter(ProjectDocument.project_id == project_id)
            if doc_type:
                q = q.filter(ProjectDocument.doc_type == doc_type)
            docs = q.order_by(ProjectDocument.created_at.desc()).all()
            return [{
                "id": d.id,
                "project_id": d.project_id,
                "doc_type": d.doc_type,
                "filename": d.filename,
                "file_size": d.file_size,
                "created_at": d.created_at,
            } for d in docs]

    @staticmethod
    def get_by_id(doc_id: int) -> dict | None:
        with get_db() as session:
            doc = session.query(ProjectDocument).filter(ProjectDocument.id == doc_id).first()
            if not doc:
                return None
            return {
                "id": doc.id,
                "project_id": doc.project_id,
                "doc_type": doc.doc_type,
                "filename": doc.filename,
                "content": doc.content,
                "file_size": doc.file_size,
                "created_at": doc.created_at,
            }

    @staticmethod
    def delete(doc_id: int) -> bool:
        with get_db() as session:
            doc = session.query(ProjectDocument).filter(ProjectDocument.id == doc_id).first()
            if not doc:
                return False
            session.delete(doc)
            session.commit()
            return True
