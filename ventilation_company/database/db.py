"""Підключення до БД та сесії."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from ventilation_company.config import DB_PATH

# Створюємо директорію, якщо немає
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# SQLAlchemy engine
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,  # True для дебагу SQL-запитів
    future=True,
)

# Фабрика сесій
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Scoped session для потокобезпеки (GUI + фонові задачі)
db_session = scoped_session(SessionLocal)


def get_db():
    """Генератор сесій для використання з context managers."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
