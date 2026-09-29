"""Репозиторій для креслень проєкту (ProjectDrawing).

CRUD + фільтрація по проєкту. Файли зберігаються на диску,
у БД — лише посилання (шлях).
"""

from ventilation_company.database.db import get_db
from ventilation_company.database.models.project_drawing import ProjectDrawing
from ventilation_company.services.audit_service import log_action


class ProjectDrawingRepository:
    """CRUD для креслень проєкту."""

    @staticmethod
    def create(
        project_id: int,
        filename: str,
        file_path: str,
        drawing_type: str = "креслення",
        notes: str = "",
    ) -> dict:
        with get_db() as session:
            drawing = ProjectDrawing(
                project_id=project_id,
                filename=filename,
                file_path=file_path,
                drawing_type=drawing_type,
                notes=notes,
            )
            session.add(drawing)
            session.flush()
            session.refresh(drawing)
            session.commit()
            log_action(
                "drawing.create",
                entity_type="drawing",
                entity_id=drawing.id,
                details={
                    "project_id": drawing.project_id,
                    "filename": drawing.filename,
                    "drawing_type": drawing.drawing_type,
                },
            )
            return {
                "id": drawing.id,
                "project_id": drawing.project_id,
                "filename": drawing.filename,
                "file_path": drawing.file_path,
                "drawing_type": drawing.drawing_type,
                "notes": drawing.notes,
                "created_at": drawing.created_at,
            }

    @staticmethod
    def get_by_project(project_id: int) -> list[dict]:
        with get_db() as session:
            drawings = (
                session.query(ProjectDrawing)
                .filter(ProjectDrawing.project_id == project_id)
                .order_by(ProjectDrawing.created_at.desc())
                .all()
            )
            return [
                {
                    "id": d.id,
                    "project_id": d.project_id,
                    "filename": d.filename,
                    "file_path": d.file_path,
                    "drawing_type": d.drawing_type,
                    "notes": d.notes,
                    "created_at": d.created_at,
                }
                for d in drawings
            ]

    @staticmethod
    def delete(drawing_id: int) -> None:
        with get_db() as session:
            drawing = session.get(ProjectDrawing, drawing_id)
            if drawing:
                session.delete(drawing)
                session.commit()
                log_action(
                    "drawing.delete",
                    entity_type="drawing",
                    entity_id=drawing_id,
                    details={"filename": drawing.filename},
                )
