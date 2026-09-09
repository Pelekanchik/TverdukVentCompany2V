"""Модель виробів у бібліотеці — v2.4.

Додано поле discounted_price для знижки на окремий виріб.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ventilation_company.database.base import Base


class ProductItem(Base):
    """Виріб у бібліотеці."""

    __tablename__ = "product_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    product_type: Mapped[str] = mapped_column(String, nullable=False)
    width: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    length: Mapped[float | None] = mapped_column(Float, nullable=True)
    thickness: Mapped[float | None] = mapped_column(Float, nullable=True)
    material: Mapped[str | None] = mapped_column(String, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    cost_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    discounted_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)  # ← v2.4 НОВЕ
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )
