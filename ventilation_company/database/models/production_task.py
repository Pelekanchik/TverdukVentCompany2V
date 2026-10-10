"""Модель завдання виробництва (черга цеху).

Таблиця: production_tasks
  • id — PK
  • project_id — FK на projects
  • product_name — назва виробу (з project_products)
  • quantity — кількість
  • priority — пріоритет (терміново / високий / звичайний / низький)
  • status — в черзі / в роботі / готово
  • planned_start — планова дата початку
  • planned_end — плановий термін здачі
  • notes — примітка
  • created_at / updated_at — службові мітки
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ventilation_company.database.base import Base


class ProductionTask(Base):
    __tablename__ = "production_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    priority: Mapped[str] = mapped_column(String(50), default="звичайний")
    status: Mapped[str] = mapped_column(String(50), default="в черзі")
    planned_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    planned_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
