"""Ініціалізація бази даних PostgreSQL.

Запуск:
    python -m ventilation_company.database.init_db
"""

import os
import sys
import logging
from datetime import datetime

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

from ventilation_company.database.db import engine, check_db_connection
from ventilation_company.database.base import Base
from ventilation_company.database.models import *
from ventilation_company.services.auth_service import AuthService
from ventilation_company.database.repositories.user_repo import UserRepository
from sqlalchemy.orm import Session


def create_tables():
    logger.info("Створення таблиць...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Таблиці створено")


def create_default_admin():
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    admin_full_name = os.getenv("ADMIN_FULL_NAME", "Адміністратор")

    with Session(engine) as session:
        repo = UserRepository(session)
        existing = repo.get_by_username(admin_username)
        if existing:
            logger.info(f"Адміністратор '{admin_username}' вже існує")
            return

        admin = repo.create(
            username=admin_username,
            password=admin_password,
            full_name=admin_full_name,
            role="admin",
            is_active=True
        )
        logger.info(f"✅ Створено адміністратора: {admin.username} (роль: {admin.role})")
        logger.warning(f"⚠️  Пароль: '{admin_password}' — ЗМІНІТЬ ПІСЛЯ ПЕРШОГО ВХОДУ!")


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
        logger.error("  3. Користувач 'vent' має права")
        logger.error("  4. Файл .env налаштований правильно")
        sys.exit(1)
    logger.info("✅ Підключення успішне")

    create_tables()
    create_default_admin()

    logger.info("=" * 50)
    logger.info("✅ Ініціалізація завершена!")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
