"""Авто-оновлення схеми БД: додавання відсутніх колонок.

Використовується як fallback, коли Alembic-міграції ще не застосовані
або коли БД створена до додавання нових полів у модель.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text

from ventilation_company.database.base import Base
from ventilation_company.database.db import engine

_logger = logging.getLogger("auto_migrate")


def _sqlite_type(col_type) -> str:
    """Отримати SQLite-тип для SQLAlchemy-типу."""
    from sqlalchemy import (
        Boolean, DateTime, Float, Integer, Numeric, String, Text,
    )

    if isinstance(col_type, (String,)):
        return f"VARCHAR({col_type.length or 255})"
    if isinstance(col_type, (Text,)):
        return "TEXT"
    if isinstance(col_type, (Integer,)):
        return "INTEGER"
    if isinstance(col_type, (Float, Numeric)):
        return "FLOAT"
    if isinstance(col_type, (DateTime,)):
        return "DATETIME"
    if isinstance(col_type, (Boolean,)):
        return "BOOLEAN"
    # За замовчуванням — TEXT
    return "TEXT"


def auto_add_missing_columns() -> None:
    """Автоматично додати відсутні колонки до існуючих таблиць SQLite."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            # Таблиці створюються через create_all, тут пропускаємо
            continue

        existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
        missing = [col for col in table.columns if col.name not in existing_cols]

        for col in missing:
            # Для SQLite: не можна додати NOT NULL без DEFAULT
            sqlite_type = _sqlite_type(col.type)
            nullable = "NULL" if col.nullable else "NULL"  # SQLite fallback
            default = ""

            # Якщо колонка має default — використовуємо його
            if col.default is not None and hasattr(col.default, "arg"):
                arg = col.default.arg
                if isinstance(arg, str):
                    default = f" DEFAULT '{arg}'"
                else:
                    default = f" DEFAULT {arg}"

            sql = (
                f'ALTER TABLE "{table_name}" '
                f'ADD COLUMN "{col.name}" {sqlite_type}{default} {nullable}'
            )
            try:
                with engine.connect() as conn:
                    conn.execute(text(sql))
                    conn.commit()
                _logger.info(
                    "[auto_migrate] Додано колонку %s.%s (%s)",
                    table_name, col.name, sqlite_type,
                )
            except Exception as exc:
                _logger.warning(
                    "[auto_migrate] Не вдалося додати %s.%s: %s",
                    table_name, col.name, exc,
                )
