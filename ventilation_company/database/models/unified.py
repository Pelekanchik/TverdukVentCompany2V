"""Єдині ORM-моделі для таблиць, раніше створених через raw sqlite3.

Покращення v2.1:
  • Усі таблиці з db_integration.py перенесено на SQLAlchemy ORM.
  • Зворотна сумісність: назви таблиць і колонок збігаються з sqlite3-версією.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Float, ForeignKey, Index, Integer, Numeric, String, Text, DateTime, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ventilation_company.database.base import Base

if TYPE_CHECKING:
    from ventilation_company.database.models.project import Project


class ProjectProduct(Base):
    """Вироби в проєкті (раніше project_products у sqlite3)."""
    __tablename__ = "project_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    product_type: Mapped[str | None] = mapped_column(String, nullable=True)
    width: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    length: Mapped[float | None] = mapped_column(Float, nullable=True)
    thickness: Mapped[float | None] = mapped_column(Float, nullable=True)
    material: Mapped[str | None] = mapped_column(String, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    metal_area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    blank_area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    material_area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )

    project: Mapped["Project"] = relationship(back_populates="project_products")


class Specification(Base):
    """Специфікації проєкту."""
    __tablename__ = "specifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    format: Mapped[str] = mapped_column(String, default="json")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    total_items: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)  # кг — float OK
    total_area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)  # м² — float OK
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )

    project: Mapped["Project"] = relationship(back_populates="specifications")


class CuttingPlan(Base):
    """Плани розкрою."""
    __tablename__ = "cutting_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    sheet_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    sheet_height: Mapped[float | None] = mapped_column(Float, nullable=True)
    thickness: Mapped[float | None] = mapped_column(Float, nullable=True)
    material: Mapped[str | None] = mapped_column(String, nullable=True)
    sheets_required: Mapped[int | None] = mapped_column(Integer, nullable=True)
    utilization_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    waste_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    plan_data: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )

    project: Mapped["Project"] = relationship(back_populates="cutting_plans")


class StandardProductLibrary(Base):
    """Бібліотека стандартних виробів."""
    __tablename__ = "standard_products_library"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    product_type: Mapped[str] = mapped_column(String, nullable=False)
    width: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    length: Mapped[float | None] = mapped_column(Float, nullable=True)
    thickness: Mapped[float | None] = mapped_column(Float, nullable=True)
    material: Mapped[str | None] = mapped_column(String, nullable=True)
    default_quantity: Mapped[int] = mapped_column(Integer, default=1)
    parameters: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )


class MaterialPrice(Base):
    """Ціни на матеріали."""
    __tablename__ = "material_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material: Mapped[str] = mapped_column(String, nullable=False)
    thickness: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_per_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_per_m2: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String, default="UAH")
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


class Client(Base):
    """Клієнти."""
    __tablename__ = "clients"

    __table_args__ = (
        Index("idx_client_name", "name"),
        Index("idx_client_edrpou", "edrpou"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    company_type: Mapped[str | None] = mapped_column(String, nullable=True)
    edrpou: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )

    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    projects: Mapped[list["ClientProject"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    warranty_reminders: Mapped[list["WarrantyReminder"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )


class Interaction(Base):
    """Взаємодії з клієнтами."""
    __tablename__ = "interactions"

    __table_args__ = (
        Index("idx_interaction_client", "client_id"),
        Index("idx_interaction_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
    date: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )
    interaction_type: Mapped[str] = mapped_column(String, default="дзвінок")
    subject: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(String, nullable=True)
    next_action_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)

    client: Mapped["Client"] = relationship(back_populates="interactions")


class Payment(Base):
    """Платежі."""
    __tablename__ = "payments"

    __table_args__ = (
        Index("idx_payment_client", "client_id"),
        Index("idx_payment_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
    date: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )
    amount: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String, default="UAH")
    payment_type: Mapped[str] = mapped_column(String, default="вхідний")
    purpose: Mapped[str | None] = mapped_column(String, nullable=True)
    project_name: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    client: Mapped["Client"] = relationship(back_populates="payments")


class ClientProject(Base):
    """Проєкти клієнта (окремі від внутрішніх проєктів)."""
    __tablename__ = "client_projects"

    __table_args__ = (
        Index("idx_cp_client", "client_id"),
        Index("idx_cp_status", "status"),
        Index("idx_cp_start", "start_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
    project_name: Mapped[str] = mapped_column(String, nullable=False)
    project_number: Mapped[str | None] = mapped_column(String, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="в роботі")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    warranty_months: Mapped[int] = mapped_column(Integer, default=24)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    client: Mapped["Client"] = relationship(back_populates="projects")


class WarrantyReminder(Base):
    """Нагадування про гарантію."""
    __tablename__ = "warranty_reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
    client_project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    project_name: Mapped[str] = mapped_column(String, nullable=False)
    reminder_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_completed: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    client: Mapped["Client"] = relationship(back_populates="warranty_reminders")
