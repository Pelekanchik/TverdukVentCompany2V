"""Модель креслення проєкту (посилання на зовнішній файл).

На відміну від ProjectDocument (файл зберігається у БД як bytea),
креслення — це посилання на файл на диску (DWG/DXF/PDF, моделі
Revit/FreeCAD), який може бути великим і оновлюватися поза програмою.

Таблиця: project_drawings
  • id — PK
  • project_id — FK на projects
  • filename — ім'я файлу
  • file_path — абсолютний шлях до файлу
  • drawing_type — тип (креслення, модель, деталювання)
  • notes — примітка
  • created_at — дата додавання
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ventilation_company.database.base import Base


class ProjectDrawing(Base):
    __tablename__ = "project_drawings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    drawing_type: Mapped[str] = mapped_column(String(50), nullable=False, default="креслення")
    notes: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
