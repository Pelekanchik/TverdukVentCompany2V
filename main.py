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
    """Створити/оновити всі SQLAlchemy-таблиці при запуску.

    Спочатку пробуємо Alembic (міграції), якщо не вдалось — fallback на create_all().
    Перед міграціями автоматично створюється резервна копія БД.
    """
    from ventilation_company.utils.logging_config import setup_logging
    from ventilation_company.utils.backup import create_backup, cleanup_old_backups

    logger = setup_logging()

    # Бекап перед будь-якими змінами
    create_backup()
    cleanup_old_backups(keep=10)

    try:
        # Спробуємо Alembic спочатку
        import subprocess
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            logger.info("[DB] Міграції Alembic застосовано")
            return
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.warning("Alembic не знайдено або таймаут, використовуємо create_all()")

    # Fallback: створити таблиці напряму
    try:
        import ventilation_company.database.models
        from ventilation_company.database.base import Base
        from ventilation_company.database.db import engine
        Base.metadata.create_all(bind=engine)
        logger.info("[DB] Таблиці SQLAlchemy створено/оновлено (без Alembic)")
    except Exception as e:
        logger.error("[DB] Помилка SQLAlchemy: %s", e)


def run_gui():
    """Функція для запуску GUI."""
    _init_db_tables()

    try:
        from ventilation_company.gui.main_window import main as gui_main
        gui_main()
    except ImportError as e:
        from ventilation_company.utils.logging_config import get_logger
        log = get_logger("main")
        log.error("Помилка запуску GUI: %s", e)
        log.info("Спробуйте: pip install tk")
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
