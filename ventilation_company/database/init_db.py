"""Ініціалізація бази даних PostgreSQL.

Запуск:
    python -m ventilation_company.database.init_db
"""

import os
import sys
import logging
import subprocess
from datetime import datetime

from dotenv import load_dotenv

# Завантажуємо .env з кореня проєкту
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

from ventilation_company.database.db import engine, check_db_connection
from ventilation_company.database.base import Base
from ventilation_company.database.models import *
from ventilation_company.auth.service import auth
from sqlalchemy.orm import Session


def create_tables():
    """Створити всі таблиці через SQLAlchemy."""
    logger.info("Створення таблиць...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Таблиці створено")
    except Exception as e:
        logger.error(f"❌ Помилка створення таблиць: {e}")
        raise


def stamp_alembic():
    """Позначити поточну БД як мігровану (створити alembic_version)."""
    logger.info("Налаштування Alembic...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "stamp", "head"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_root,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            logger.info("✅ Alembic: поточна версія позначена як head")
        else:
            logger.warning(f"⚠️ Alembic stamp: {result.stderr}")
    except Exception as e:
        logger.warning(f"⚠️ Alembic stamp не вдалося: {e}")


def create_default_admin():
    """Створити адміністратора з .env або випадковим паролем."""
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    admin_full_name = os.getenv("ADMIN_FULL_NAME", "Адміністратор")

    try:
        with Session(engine) as session:
            from ventilation_company.database.models.user import UserORM
            existing = session.query(UserORM).filter(
                UserORM.username == admin_username
            ).first()

            if existing:
                logger.info(f"Адміністратор '{admin_username}' вже існує")
                return

            # Використовуємо існуючий auth service
            user = auth.create_user(
                username=admin_username,
                password=admin_password,
                full_name=admin_full_name,
                role="director",
            )
            logger.info(f"✅ Створено адміністратора: {user.username} (роль: {user.role})")
            logger.warning(f"⚠️  Пароль: '{admin_password}' — ЗМІНІТЬ ПІСЛЯ ПЕРШОГО ВХОДУ!")
    except Exception as e:
        logger.error(f"❌ Помилка створення адміна: {e}")
        raise


def main():
    logger.info("=" * 50)
    logger.info("Ініціалізація VentCompany PostgreSQL")
    logger.info("=" * 50)

    logger.info("Перевірка підключення до PostgreSQL...")
    if not check_db_connection():
        logger.error("❌ Не вдалося підключитися до PostgreSQL")
        logger.error("Переконайтесь що:")
        logger.error("  1. PostgreSQL запущено (Services → postgresql-x64-16)")
        logger.error("  2. База 'ventcompany' створена")
        logger.error("  3. Файл .env налаштований правильно")
        sys.exit(1)
    logger.info("✅ Підключення успішне")

    create_tables()
    stamp_alembic()
    create_default_admin()

    logger.info("=" * 50)
    logger.info("✅ Ініціалізація завершена!")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
