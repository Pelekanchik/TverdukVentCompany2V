"""VentCompany — PySide6 версія.

Запуск:
    python main_pyside6.py
"""

import sys
import os
import subprocess

# Додаємо корінь проєкту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _init_db_tables():
    """Ініціалізація БД: Alembic → create_all fallback."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        if result.returncode == 0:
            print("[DB] Міграції Alembic застосовано")
            return
        else:
            print(f"[DB] Alembic warning: {result.stderr}")
    except Exception as e:
        print(f"[DB] Alembic недоступний: {e}")

    # Fallback
    try:
        import ventilation_company.database.models
        from ventilation_company.database.base import Base
        from ventilation_company.database.db import engine
        Base.metadata.create_all(bind=engine)
        print("[DB] Таблиці створено через SQLAlchemy")
    except Exception as e:
        print(f"[DB] Помилка створення таблиць: {e}")


if __name__ == "__main__":
    _init_db_tables()
    from ventilation_company.gui_pyside6.main_window import run_app
    run_app()
