"""Підключення до БД (PostgreSQL) з пулом з'єднань та конфігурацією через env.

Використання:
    from ventilation_company.database.db import get_db, engine
    with get_db() as session:
        ...
"""

import os
import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "postgresql://vent:vent123@localhost:5432/ventcompany"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_recycle=POOL_RECYCLE,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)


@contextmanager
def get_db():
    """Контекстний менеджер для сесії БД. Автоматично commit/rollback/close."""
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
    """Зворотна сумісність: повертає raw PostgreSQL connection.

    Раніше це був sqlite3.connect(). Тепер — raw psycopg2 connection.
    Якщо ви використовуєте цю функцію — краще перейдіть на SQLAlchemy ORM.
    """
    import warnings
    warnings.warn(
        "get_calc_db() застаріло. Використовуйте get_db() або SQLAlchemy ORM.",
        DeprecationWarning,
        stacklevel=2
    )
    return engine.raw_connection()
