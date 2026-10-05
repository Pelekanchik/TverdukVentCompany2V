"""ORM-моделі складу (v2.9).

WarehouseItem — залишки матеріалів на складі.
WarehouseMove — рух (надходження/списання) з прив'язкою до проєкту.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ventilation_company.database.base import Base


class WarehouseItem(Base):
    __tablename__ = "warehouse_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False, default="шт")
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    min_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)

    moves: Mapped[list[WarehouseMove]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="WarehouseMove.id"
    )


class WarehouseMove(Base):
    __tablename__ = "warehouse_moves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("warehouse_items.id", ondelete="CASCADE"), nullable=False
    )
    move_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False, default="in")  # in/out
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)

    item: Mapped[WarehouseItem] = relationship(back_populates="moves")
