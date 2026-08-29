"""Підключення до БД (PostgreSQL)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

DATABASE_URL = "postgresql://vent:vent123@localhost/ventcompany"
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)

def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def get_calc_db():
    import sqlite3
    from ventilation_company.config import DB_PATH
    return sqlite3.connect(DB_PATH)
