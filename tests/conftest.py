"""Pytest fixtures for VentCompany tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ventilation_company.database.base import Base


@pytest.fixture(scope="session")
def engine():
    """Create in-memory SQLite engine for tests."""
    return create_engine("sqlite:///:memory:", future=True)


@pytest.fixture(scope="session")
def tables(engine):
    """Create all tables once per test session."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def clean_tables(engine, tables):
    """Clean all tables before each test."""
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f"DELETE FROM {table.name}"))
        conn.commit()
    yield


@pytest.fixture
def db_session(engine, tables):
    """Provide a fresh database session for each test."""
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()
