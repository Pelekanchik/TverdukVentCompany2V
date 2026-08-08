"""ORM-модель для розрахунків."""

from __future__ import annotations

# ДОДАТИ на початок файлу (після імпортів sqlalchemy):
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ventilation_company.database.base import Base

if TYPE_CHECKING:
    from ventilation_company.database.models.project import Project


class Calculation(Base):
    __tablename__ = "calculations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    calculation_type: Mapped[str | None] = mapped_column(String, nullable=True)
    materials_cost: Mapped[float] = mapped_column(Float, default=0)
    components_cost: Mapped[float] = mapped_column(Float, default=0)
    works_cost: Mapped[float] = mapped_column(Float, default=0)
    overhead_cost: Mapped[float] = mapped_column(Float, default=0)
    total_cost: Mapped[float] = mapped_column(Float, default=0)
    markup_amount: Mapped[float] = mapped_column(Float, default=0)
    vat_amount: Mapped[float] = mapped_column(Float, default=0)
    final_price: Mapped[float] = mapped_column(Float, default=0)
    profit: Mapped[float] = mapped_column(Float, default=0)
    calculated_at: Mapped[str | None] = mapped_column(String, nullable=True)

    project: Mapped[Project] = relationship(back_populates="calculations")
