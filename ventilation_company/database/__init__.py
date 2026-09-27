"""
Модуль роботи з базою даних.

Engine/SessionLocal створюються ліниво (див. ventilation_company.database.db):
імпорт пакета не створює з'єднань і не вимагає налаштованого DATABASE_URL.
"""

from ventilation_company.database.base import Base
from ventilation_company.database.db import get_calc_db, get_db

__all__ = ["Base", "engine", "SessionLocal", "get_db", "db_session", "get_calc_db"]


def __getattr__(name: str):
    """PEP 562: лінивий доступ до engine / SessionLocal / db_session."""
    if name in ("engine", "SessionLocal", "db_session"):
        from ventilation_company.database import db as _db

        return getattr(_db, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
