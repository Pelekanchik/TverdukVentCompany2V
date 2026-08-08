"""Базовий клас SQLAlchemy."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовий клас для всіх ORM-моделей."""

    pass
