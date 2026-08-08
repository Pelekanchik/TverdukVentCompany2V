"""ORM-моделі для продуктів/виробів (калькулятор)."""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ventilation_company.database.base import Base


class ProductType(Base):
    __tablename__ = "product_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    icon: Mapped[str | None] = mapped_column(String, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)

    subtypes: Mapped[list[ProductSubtype]] = relationship(
        back_populates="product_type", cascade="all, delete-orphan"
    )


class ProductSubtype(Base):
    __tablename__ = "product_subtypes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_type_id: Mapped[int] = mapped_column(ForeignKey("product_types.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    formula: Mapped[str] = mapped_column(String, nullable=False)
    shape_type: Mapped[str] = mapped_column(String, default="round")
    flange_perimeter_formula: Mapped[str | None] = mapped_column(String, nullable=True)
    waste_factor: Mapped[float] = mapped_column(Float, default=1.18)
    labor_norm: Mapped[float] = mapped_column(Float, default=0.5)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, default=1)

    product_type: Mapped[ProductType] = relationship(back_populates="subtypes")
    size_ranges: Mapped[list[SizeRange]] = relationship(
        back_populates="subtype", cascade="all, delete-orphan"
    )


class SizeRange(Base):
    __tablename__ = "size_ranges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subtype_id: Mapped[int] = mapped_column(ForeignKey("product_subtypes.id"))
    param_name: Mapped[str] = mapped_column(String, nullable=False)
    param_label: Mapped[str] = mapped_column(String, nullable=False)
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    step: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String, default="мм")
    values_json: Mapped[str | None] = mapped_column(String, nullable=True)

    subtype: Mapped[ProductSubtype] = relationship(back_populates="size_ranges")
