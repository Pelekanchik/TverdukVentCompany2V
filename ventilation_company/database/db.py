"""Підключення до БД (PostgreSQL) з пулом з'єднань та конфігурацією через env.

Engine створюється ліниво — при першому зверненні до engine / SessionLocal /
db_session, а не на імпорті модуля. Якщо DATABASE_URL не налаштований
(заглушка CHANGE_ME), перша спроба використання дає зрозумілу помилку.

Використання:
    from ventilation_company.database.db import get_db, engine
    with get_db() as session:
        ...
"""

import logging
import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker

from ventilation_company.paths import APP_ROOT

# === Source + PyInstaller-safe .env loading ===
_candidate_envs = [
    Path.cwd() / ".env",
    APP_ROOT / ".env",
    Path(__file__).resolve().parents[3] / ".env",
]
for _env_path in _candidate_envs:
    if _env_path.exists():
        try:
            load_dotenv(dotenv_path=_env_path, override=True, encoding="utf-8")
        except UnicodeDecodeError:
            load_dotenv(dotenv_path=_env_path, override=True, encoding="cp1251")
        break
else:
    load_dotenv(override=True, encoding="utf-8")
# ===============================================

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "postgresql://CHANGE_ME:CHANGE_ME@localhost:5432/ventcompany"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))


class DatabaseConfigurationError(RuntimeError):
    """DATABASE_URL не налаштований або містить заглушку."""


def _validate_database_url(url: str) -> None:
    if "CHANGE_ME" in url:
        raise DatabaseConfigurationError(
            "DATABASE_URL не налаштований.\n\n"
            "Створіть файл .env у корені проєкту з рядком:\n"
            "  DATABASE_URL=postgresql://КОРИСТУВАЧ:ПАРОЛЬ@localhost:5432/ventcompany\n\n"
            "Або запустіть: python setup_postgres.py"
        )


# ── Лінива ініціалізація engine ──
_engine = None
_SessionLocal = None
_db_session = None


def _init_engine() -> None:
    """Створити engine і фабрику сесій (один раз, при першому використанні)."""
    global _engine, _SessionLocal, _db_session
    if _engine is not None:
        return
    _validate_database_url(DATABASE_URL)
    _engine = create_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_recycle=POOL_RECYCLE,
    )
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    _db_session = scoped_session(_SessionLocal)
    logger.info("PostgreSQL engine ініціалізовано: %s", DATABASE_URL.split("@")[-1])


def get_session_local():
    """Ліниво повернути фабрику сесій (ініціалізує engine при першому виклику).

    Навідміну від ``from db import SessionLocal``, цей виклик не спрацьовує
    на імпорті модуля — лише коли сесію справді потрібно відкрити.
    """
    _init_engine()
    return _SessionLocal


def get_engine():
    """Ліниво повернути engine (ініціалізує при першому виклику)."""
    _init_engine()
    return _engine


def __getattr__(name: str):
    """PEP 562: лінивий доступ до engine / SessionLocal / db_session."""
    if name in ("engine", "SessionLocal", "db_session"):
        _init_engine()
        return {"engine": _engine, "SessionLocal": _SessionLocal, "db_session": _db_session}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


@contextmanager
def get_db():
    """Контекстний менеджер для сесії БД. Автоматично commit/rollback/close."""
    _init_engine()
    session = _SessionLocal()
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
        _init_engine()
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Помилка підключення до БД: {e}")
        return False


def get_calc_db():
    """Зворотна сумісність: повертає raw PostgreSQL connection."""
    import warnings

    warnings.warn(
        "get_calc_db() застаріло. Використовуйте get_db() або SQLAlchemy ORM.",
        DeprecationWarning,
        stacklevel=2,
    )
    _init_engine()
    return _engine.raw_connection()
