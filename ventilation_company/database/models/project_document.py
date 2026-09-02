"""Модель документа проєкту (зберігання в PostgreSQL як bytea).

Таблиця: project_documents
  • id — PK
  • project_id — FK на projects
  • doc_type — тип (spec, calc, metal, order)
  • filename — ім'я файлу
  • content — бінарні дані Excel (LargeBinary)
  • file_size — розмір у байтах
  • created_at — дата створення
"""

from datetime import datetime
from sqlalchemy import Integer, String, LargeBinary, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ventilation_company.database.base import Base


class ProjectDocument(Base):
    __tablename__ = "project_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False)  # spec, calc, metal, order
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
