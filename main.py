#!/usr/bin/env python3
"""
ВЕНТИЛЯЦІЙНА ВИРОБНИЧА ФІРМА
Запуск: python main.py        → GUI режим
        python main.py --cli  → Консольний режим
"""

import os
import subprocess  # ← ВИПРАВЛЕННЯ: додано імпорт
import sys


def _init_db_tables():
    """Створити/оновити всі SQLAlchemy-таблиці при запуску.

    Спочатку пробуємо Alembic (міграції), якщо не вдалось — fallback на create_all().
    """
    from ventilation_company.utils.logging_config import setup_logging
    from ventilation_company.utils.backup import create_backup, cleanup_old_backups

    logger = setup_logging()
    create_backup()
    cleanup_old_backups(keep=10)

    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        if result.returncode == 0:
            logger.info("[DB] Міграції Alembic застосовано")
            return
        else:
            logger.warning("[DB] Alembic stderr: %s", result.stderr)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.warning("Alembic недоступний або таймаут: %s", e)

    try:
        import ventilation_company.database.models
        from ventilation_company.database.base import Base
        from ventilation_company.database.db import engine
        Base.metadata.create_all(bind=engine)
        logger.info("[DB] Таблиці SQLAlchemy створено/оновлено (без Alembic)")
    except Exception as e:
        logger.error("[DB] Помилка SQLAlchemy create_all: %s", e)


def run_gui():
    _init_db_tables()
    try:
        from ventilation_company.gui.main_window import main as gui_main
        gui_main()
    except ImportError as e:
        from ventilation_company.utils.logging_config import get_logger
        log = get_logger("main")
        log.error("Помилка запуску GUI: %s", e)
        raise


def run_cli():
    _init_db_tables()
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
