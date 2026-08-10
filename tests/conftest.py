"""Pytest fixtures for VentCompany tests."""

from __future__ import annotations

import os
import sys
import tempfile
import gc
import time
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Додаємо корінь проекту в шлях
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Підміна відсутнього модуля db_core ──────────────────────
db_core_mock = MagicMock()
db_core_mock.calculate_area = lambda *a, **k: 0
db_core_mock.execute_query = lambda *a, **k: []
db_core_mock.format_size_params = lambda *a, **k: ""
db_core_mock.get_calc_db = lambda *a, **k: None
db_core_mock.get_connection = lambda *a, **k: None
db_core_mock.get_size_labels = lambda *a, **k: {}
db_core_mock.init_database = lambda *a, **k: None
sys.modules["ventilation_company.db_core"] = db_core_mock
# ─────────────────────────────────────────────────────────────

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


@pytest.fixture
def temp_db_path():
    """Provide a temporary database file path.

    На Windows SQLite блокує файл, тому перед видаленням
    треба закрити всі з'єднання.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # Спробуємо видалити кілька разів (Windows може блокувати)
    gc.collect()
    for _ in range(10):
        try:
            if os.path.exists(path):
                os.remove(path)
            break
        except PermissionError:
            time.sleep(0.2)
