#!/usr/bin/env python3
"""
ВЕНТИЛЯЦІЙНА ВИРОБНИЧА ФІРМА
Запуск: python main.py        → GUI режим
        python main.py --cli  → Консольний режим
"""

import importlib.util
import os
import sys


def _init_db_tables():
    """Створити SQLAlchemy-таблиці (обхід багнутого database/__init__.py)."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path_mod = os.path.join(base_dir, "ventilation_company", "database", "db.py")
        base_path = os.path.join(base_dir, "ventilation_company", "database", "base.py")

        spec_db = importlib.util.spec_from_file_location("db", db_path_mod)
        db_mod = importlib.util.module_from_spec(spec_db)
        spec_db.loader.exec_module(db_mod)

        spec_base = importlib.util.spec_from_file_location("base", base_path)
        base_mod = importlib.util.module_from_spec(spec_base)
        spec_base.loader.exec_module(base_mod)

        base_mod.Base.metadata.create_all(bind=db_mod.engine)
        print("[DB] Таблиці SQLAlchemy створено/оновлено")
    except Exception as e:
        print(f"[DB] Попередження SQLAlchemy: {e}")

    # Таблиця users створюється автоматично в AuthService.__init__()
    # (ventilation_company/auth/service.py — sqlite3 напряму)


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
