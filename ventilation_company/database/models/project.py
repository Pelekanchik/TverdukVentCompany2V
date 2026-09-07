"""ORM-моделі для проєктів (оновлені v2.3).

Додано:
  • ProjectExpense — додаткові витрати проєкту
  • discounted_price (v2.2)
  • Relationships для works, expenses
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index, Integer, Numeric, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ventilation_company.database.base import Base

if TYPE_CHECKING:
    from ventilation_company.database.models.unified import (
        ProjectProduct, Specification, CuttingPlan,
    )


class Project(Base):
    __tablename__ = "projects"

    __table_args__ = (
        Index("idx_project_number", "project_number"),
        Index("idx_project_client", "client"),
        Index("idx_project_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    client: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    ventilation_type: Mapped[str | None] = mapped_column(String, nullable=True)
    air_flow: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="draft")
    total_area: Mapped[float] = mapped_column(Float, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Фінансові поля
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    drawing_path: Mapped[str | None] = mapped_column(String, nullable=True)
    customer_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discounted_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)   # ← v2.2
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    salary_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    assigned_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    components: Mapped[list["ProjectComponent"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    materials: Mapped[list["ProjectMaterial"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    works: Mapped[list["ProjectWork"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    expenses: Mapped[list["ProjectExpense"]] = relationship(   # ← v2.3 НОВЕ
        back_populates="project", cascade="all, delete-orphan"
    )
    calculations: Mapped[list["Calculation"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    project_products: Mapped[list["ProjectProduct"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    specifications: Mapped[list["Specification"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    cutting_plans: Mapped[list["CuttingPlan"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectComponent(Base):
    __tablename__ = "project_components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    component_name: Mapped[str | None] = mapped_column(String, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="components")


class ProjectMaterial(Base):
    __tablename__ = "project_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    material_name: Mapped[str | None] = mapped_column(String, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="materials")


class ProjectWork(Base):
    __tablename__ = "project_works"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    work_name: Mapped[str | None] = mapped_column(String, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="works")


class ProjectExpense(Base):   # ← v2.3 НОВЕ
    __tablename__ = "project_expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    expense_name: Mapped[str | None] = mapped_column(String, nullable=True)
    quantity: Mapped[float] = mapped_column(Float, default=1)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)

    project: Mapped["Project"] = relationship(back_populates="expenses")
