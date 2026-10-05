"""ORM-модель історії закупівельних цін (v2.9).

Записується при затвердженні заявки на матеріали; використовується
для підказки останніх цен у діалозі заявки.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ventilation_company.database.base import Base


class PurchasePrice(Base):
    __tablename__ = "purchase_prices"

    __table_args__ = (Index("idx_purchase_prices_name", "item_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    price: Mapped[float] = mapped_column(Float, nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)
