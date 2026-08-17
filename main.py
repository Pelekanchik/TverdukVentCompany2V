#!/usr/bin/env python3
"""
ВЕНТИЛЯЦІЙНА ВИРОБНИЧА ФІРМА
Запуск: python main.py        → GUI режим
        python main.py --cli  → Консольний режим

Покращення v2.1:
  • _init_db_tables() тепер імпортує всі ORM-моделі перед create_all(),
    щоб SQLAlchemy створила ВСІ таблиці (включно з users, clients тощо).
  • Прибрано окреме створення users через sqlite3 — тепер єдиний шар ORM.
"""

import importlib.util
import os
import sys


def _init_db_tables():
    """Створити всі SQLAlchemy-таблиці при запуску."""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        # ── Динамічний імпорт (обхід циклічних імпортів) ──
        db_path = os.path.join(base_dir, "ventilation_company", "database", "db.py")
        base_path = os.path.join(base_dir, "ventilation_company", "database", "base.py")
        models_path = os.path.join(
            base_dir, "ventilation_company", "database", "models", "__init__.py"
        )

        spec_db = importlib.util.spec_from_file_location("db", db_path)
        db_mod = importlib.util.module_from_spec(spec_db)
        sys.modules["db"] = db_mod
        spec_db.loader.exec_module(db_mod)

        spec_base = importlib.util.spec_from_file_location("base", base_path)
        base_mod = importlib.util.module_from_spec(spec_base)
        sys.modules["base"] = base_mod
        spec_base.loader.exec_module(base_mod)

        # Імпортуємо models/__init__.py — це реєструє ВСІ таблиці в Base.metadata
        spec_models = importlib.util.spec_from_file_location("models", models_path)
        models_mod = importlib.util.module_from_spec(spec_models)
        sys.modules["models"] = models_mod
        spec_models.loader.exec_module(models_mod)

        base_mod.Base.metadata.create_all(bind=db_mod.engine)
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
