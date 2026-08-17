"""ORM-модель користувачів (раніше raw sqlite3)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ventilation_company.database.base import Base


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="monter")
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
