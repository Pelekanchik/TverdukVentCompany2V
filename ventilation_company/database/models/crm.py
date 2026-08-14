"""ORM-моделі для CRM (клієнти, взаємодії, платежі, нагадування)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ventilation_company.database.base import Base

if TYPE_CHECKING:
    pass


class Client(Base):
    """Картка клієнта."""
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    company_type: Mapped[str | None] = mapped_column(String, nullable=True)  # ФОП, ТОВ, ПП...
    edrpou: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="client", cascade="all, delete-orphan", order_by="Interaction.date.desc()"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="client", cascade="all, delete-orphan", order_by="Payment.date.desc()"
    )
    projects: Mapped[list["ClientProject"]] = relationship(
        back_populates="client", cascade="all, delete-orphan", order_by="ClientProject.start_date.desc()"
    )
    reminders: Mapped[list["WarrantyReminder"]] = relationship(
        back_populates="client", cascade="all, delete-orphan", order_by="WarrantyReminder.reminder_date.asc()"
    )

    def __repr__(self) -> str:
        return f"<Client {self.name}>"


class Interaction(Base):
    """Взаємодія з клієнтом (дзвінок, зустріч, лист, замітка)."""
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    interaction_type: Mapped[str] = mapped_column(String, default="дзвінок")  # дзвінок, зустріч, лист, замітка, email
    subject: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(String, nullable=True)  # позитив, негатив, у процесі
    next_action: Mapped[str | None] = mapped_column(String, nullable=True)
    next_action_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)

    client: Mapped["Client"] = relationship(back_populates="interactions")


class Payment(Base):
    """Платіж від/до клієнта."""
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String, default="UAH")
    payment_type: Mapped[str] = mapped_column(String, default="вхідний")  # вхідний, вихідний
    purpose: Mapped[str | None] = mapped_column(String, nullable=True)
    project_name: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    client: Mapped["Client"] = relationship(back_populates="payments")


class ClientProject(Base):
    """Проєкт клієнта (історія замовлень)."""
    __tablename__ = "client_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    project_name: Mapped[str] = mapped_column(String, nullable=False)
    project_number: Mapped[str | None] = mapped_column(String, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="в роботі")  # в роботі, завершено, гарантія, закрито
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    warranty_months: Mapped[int] = mapped_column(Integer, default=24)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    client: Mapped["Client"] = relationship(back_populates="projects")


class WarrantyReminder(Base):
    """Нагадування про гарантійне обслуговування."""
    __tablename__ = "warranty_reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    client_project_id: Mapped[int | None] = mapped_column(ForeignKey("client_projects.id"), nullable=True)
    project_name: Mapped[str] = mapped_column(String, nullable=False)
    reminder_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_completed: Mapped[bool] = mapped_column(default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    client: Mapped["Client"] = relationship(back_populates="reminders")
