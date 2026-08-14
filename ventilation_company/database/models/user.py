"""ORM-модель користувача системи."""

from datetime import datetime

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

# ═══ ОБХІД database/__init__.py ═══
import importlib.util
import os
_base_path = os.path.join(os.path.dirname(__file__), "..", "base.py")
_spec = importlib.util.spec_from_file_location("base", _base_path)
_base_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base_mod)
Base = _base_mod.Base
# ═══════════════════════════════════


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="monter")
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(
        String, default=lambda: datetime.now().isoformat()
    )
    last_login: Mapped[str | None] = mapped_column(String, nullable=True)
