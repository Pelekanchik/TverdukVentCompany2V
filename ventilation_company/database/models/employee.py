"""ORM-модель для співробітників."""

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ventilation_company.database.base import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[str | None] = mapped_column(String, nullable=True)
    base_salary: Mapped[float | None] = mapped_column(Float, nullable=True)
    bonus_percent: Mapped[float] = mapped_column(Float, default=0)
    actual_salary: Mapped[float | None] = mapped_column(Float, nullable=True)
    hired_date: Mapped[str | None] = mapped_column(String, nullable=True)
