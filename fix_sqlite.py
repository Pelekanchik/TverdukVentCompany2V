"""Патч: переключення VentCompany на SQLite.

Запуск:
    python fix_sqlite.py
"""

import os

BASE = os.path.dirname(os.path.abspath(__file__))

# 1. Перезаписуємо .env
env_path = os.path.join(BASE, ".env")
with open(env_path, "w", encoding="utf-8") as f:
    f.write("""DATABASE_URL=sqlite:///data/company.db
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_FULL_NAME=Administrator
""")
print("✅ .env оновлено → SQLite")

# 2. Перезаписуємо db.py
db_path = os.path.join(BASE, "ventilation_company", "database", "db.py")
db_code = """"""Підключення до БД (SQLite)."""

import os
import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "company.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)


@contextmanager
def get_db():
    """Контекстний менеджер для сесії БД."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_db_connection() -> bool:
    """Перевіряє чи доступна БД."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Помилка підключення до БД: {e}")
        return False


def get_calc_db():
    """Зворотна сумісність."""
    import sqlite3
    return sqlite3.connect(DB_PATH)
"""

with open(db_path, "w", encoding="utf-8") as f:
    f.write(db_code)
print("✅ db.py оновлено → SQLite")

# 3. Перезаписуємо migrations/env.py
env_py_path = os.path.join(BASE, "migrations", "env.py")
env_py_code = """"""Alembic env.py для SQLite."""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ventilation_company.database.base import Base
from ventilation_company.database.db import DATABASE_URL
from ventilation_company.database.models import *

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""

with open(env_py_path, "w", encoding="utf-8") as f:
    f.write(env_py_code)
print("✅ migrations/env.py оновлено → SQLite")

print("\n🎉 Готово! Тепер запускай: python main.py")
