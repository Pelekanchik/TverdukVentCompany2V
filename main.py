#!/usr/bin/env python3
"""
ВЕНТИЛЯЦІЙНА ВИРОБНИЧА ФІРМА
Запуск: python main.py        → GUI режим
        python main.py --cli  → Консольний режим

Покращення v2.1:
  • _init_db_tables() тепер використовує звичайний import замість
    динамічного importlib, щоб уникнути дублювання Base.metadata.
  • Прибрано окреме створення users через sqlite3 — тепер єдиний шар ORM.
"""

import os
import sys


def _init_db_tables():
    """Створити всі SQLAlchemy-таблиці при запуску."""
    try:
        # Імпортуємо моделі — це реєструє всі таблиці в Base.metadata
        import ventilation_company.database.models
        from ventilation_company.database.base import Base
        from ventilation_company.database.db import engine
        Base.metadata.create_all(bind=engine)
        print("[DB] Таблиці SQLAlchemy створено/оновлено")
    except Exception as e:
        print(f"[DB] Попередження SQLAlchemy: {e}")


def run_gui():
    """Функція для запуску GUI."""
    _init_db_tables()

    try:
        from ventilation_company.gui.main_window import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"Помилка запуску GUI: {e}")
        print("Спробуйте: pip install tk")
        raise


def run_cli():
    """Функція для запуску CLI."""
    try:
        from ventilation_company.main_cli import main as cli_main
    except ImportError:
        from main_cli import main as cli_main
    cli_main()


if __name__ == "__main__":
    if "--cli" in sys.argv or "-c" in sys.argv:
        run_cli()
    else:
        run_gui()
