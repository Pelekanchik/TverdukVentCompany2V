"""ORM-моделі для калькулятора виробів."""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ventilation_company.database.base import Base


class CalcMaterial(Base):
    __tablename__ = "calc_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    grade: Mapped[str | None] = mapped_column(String, nullable=True)
    thickness: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String, default="мм")
    price_per_m2: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    waste_factor: Mapped[float] = mapped_column(Float, default=1.18)
    is_active: Mapped[int] = mapped_column(Integer, default=1)


class SubtypeMaterial(Base):
    __tablename__ = "subtype_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subtype_id: Mapped[int] = mapped_column(ForeignKey("product_subtypes.id"))
    material_id: Mapped[int] = mapped_column(ForeignKey("calc_materials.id"))
    is_default: Mapped[int] = mapped_column(Integer, default=0)


class CalcCalculation(Base):
    __tablename__ = "calc_calculations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_name: Mapped[str | None] = mapped_column(String, nullable=True)
    client_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    markup_percent: Mapped[float] = mapped_column(Float, default=30)
    overhead_percent: Mapped[float] = mapped_column(Float, default=15)
    labor_mode: Mapped[str] = mapped_column(String, default="hour")
    total_cost: Mapped[float] = mapped_column(Float, default=0)
    sale_price: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String, default="draft")
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)

    items: Mapped[list[CalcItem]] = relationship(
        back_populates="calculation", cascade="all, delete-orphan"
    )


class CalcItem(Base):
    __tablename__ = "calc_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    calculation_id: Mapped[int] = mapped_column(ForeignKey("calc_calculations.id"))
    subtype_id: Mapped[int] = mapped_column(Integer, nullable=False)
    material_id: Mapped[int] = mapped_column(Integer, nullable=False)
    size_params: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    area_m2: Mapped[float] = mapped_column(Float, default=0)
    material_cost: Mapped[float] = mapped_column(Float, default=0)
    flange_cost: Mapped[float] = mapped_column(Float, default=0)
    labor_cost: Mapped[float] = mapped_column(Float, default=0)
    overhead_cost: Mapped[float] = mapped_column(Float, default=0)
    total_cost: Mapped[float] = mapped_column(Float, default=0)
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    total_price: Mapped[float] = mapped_column(Float, default=0)

    calculation: Mapped[CalcCalculation] = relationship(back_populates="items")


class OverheadItem(Base):
    __tablename__ = "overhead_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, default="fixed")
    value: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, default=1)


class CalcSetting(Base):
    __tablename__ = "calc_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str | None] = mapped_column(String, nullable=True)
