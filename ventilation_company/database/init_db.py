"""Ініціалізація бази даних PostgreSQL.

Запуск:
    python -m ventilation_company.database.init_db

Безпека:
    • Якщо ADMIN_PASSWORD у .env не заданий або слабкий — генерується випадковий пароль.
    • Облікові дані першого запуску зберігаються локально у data/.setup_credentials.json.
    • Файл .env і data/.setup_credentials.json не мають потрапляти в Git.
"""

import os
import sys
import json
import stat
import secrets
import string
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

from ventilation_company.database.db import engine, check_db_connection
from ventilation_company.database.base import Base
from ventilation_company.database.models import *  # noqa: F401,F403 - реєстрація моделей
from ventilation_company.auth.service import auth
from ventilation_company.auth.password_policy import validate_password
from sqlalchemy.orm import Session


def _generate_strong_password(length: int = 16) -> str:
    """Згенерувати пароль, який точно проходить політику."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        result = validate_password(password)
        if result.valid and result.strength in {"medium", "strong"}:
            return password


def _write_setup_credentials(username: str, password: str, role: str) -> Path:
    creds_path = project_root / "data" / ".setup_credentials.json"
    creds_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "username": username,
        "password": password,
        "role": role,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "note": "Локальний файл. Видаліть його після першого входу та змініть пароль.",
    }
    creds_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(creds_path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return creds_path


def create_tables():
    logger.info("Створення таблиць...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Таблиці створено")
    except Exception as e:
        logger.error(f"❌ Помилка створення таблиць: {e}")
        raise


def stamp_alembic():
    logger.info("Налаштування Alembic...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "stamp", "head"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(project_root),
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
    admin_username = os.getenv("ADMIN_USERNAME", "admin").strip() or "admin"
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
    admin_full_name = os.getenv("ADMIN_FULL_NAME", "Адміністратор").strip() or "Адміністратор"

    if admin_password:
        check = validate_password(admin_password)
        if not check.valid:
            logger.error("❌ ADMIN_PASSWORD з .env не відповідає політиці паролів:")
            for err in check.errors:
                logger.error(f"   - {err}")
            logger.error("Виправте .env або залиште ADMIN_PASSWORD порожнім для генерації випадкового пароля.")
            raise SystemExit(2)

    with Session(engine) as session:
        from ventilation_company.database.models.user import UserORM
        existing = session.query(UserORM).filter(UserORM.username == admin_username).first()
        if existing:
            logger.info(f"Адміністратор '{admin_username}' вже існує")
            return

    generated = False
    if not admin_password:
        admin_password = _generate_strong_password()
        generated = True

    user = auth.create_user(
        username=admin_username,
        password=admin_password,
        full_name=admin_full_name,
        role="director",
    )
    logger.info(f"✅ Створено адміністратора: {user.username} (роль: {user.role})")

    if generated:
        creds_path = _write_setup_credentials(user.username, admin_password, user.role)
        logger.warning("⚠️  Згенеровано випадковий пароль адміністратора.")
        logger.warning(f"⚠️  Облікові дані збережено локально: {creds_path}")
        logger.warning("⚠️  Видаліть цей файл після першого входу та обов'язково змініть пароль.")
    else:
        logger.warning("⚠️  Використано ADMIN_PASSWORD з .env. Переконайтесь, що .env не в Git.")


def main():
    logger.info("=" * 50)
    logger.info("Ініціалізація VentCompany PostgreSQL")
    logger.info("=" * 50)

    logger.info("Перевірка підключення до PostgreSQL...")
    if not check_db_connection():
        logger.error("❌ Не вдалося підключитися до PostgreSQL")
        logger.error("Переконайтесь що:")
        logger.error("  1. PostgreSQL запущено")
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
