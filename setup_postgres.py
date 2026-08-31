"""
🐘 VentCompany PostgreSQL Setup — Автоматичний інсталятор

Запуск: python setup_postgres.py
"""

import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VC_DIR = os.path.join(BASE_DIR, "ventilation_company")
DB_DIR = os.path.join(VC_DIR, "database")
REPO_DIR = os.path.join(DB_DIR, "repositories")
SERVICES_DIR = os.path.join(VC_DIR, "services")
MIGRATIONS_DIR = os.path.join(BASE_DIR, "migrations")


def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    rel = os.path.relpath(path, BASE_DIR)
    print(f"  ✅ {rel}")


def print_header(text):
    print("\n" + "=" * 55)
    print(f"  {text}")
    print("=" * 55)


def check_dependencies():
    print_header("Крок 1: Перевірка залежностей")
    missing = []
    for mod, name in [("psycopg2", "psycopg2-binary"), ("dotenv", "python-dotenv"), ("bcrypt", "bcrypt")]:
        try:
            __import__(mod)
            print(f"  ✅ {name} — OK")
        except ImportError:
            missing.append(name)
            print(f"  ❌ {name} — НЕ ЗНАЙДЕНО")
    if missing:
        print(f"\n  ⚠️  Встановіть: pip install {' '.join(missing)}")
        return False
    return True


def create_directories():
    print_header("Крок 2: Створення папок")
    for d in [SERVICES_DIR, REPO_DIR, MIGRATIONS_DIR]:
        os.makedirs(d, exist_ok=True)
        print(f"  📁 {os.path.relpath(d, BASE_DIR)}")


def create_env():
    write_file(os.path.join(BASE_DIR, ".env"), '''# PostgreSQL конфігурація VentCompany
DATABASE_URL=postgresql://vent:vent123@localhost:5432/ventcompany

# Налаштування пулу з'єднань
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=3600

# Перший адміністратор (створюється автоматично)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_FULL_NAME=Адміністратор
''')


def create_db_py():
    write_file(os.path.join(DB_DIR, "db.py"), '''"""Підключення до БД (PostgreSQL) з пулом з'єднань та конфігурацією через env.

Використання:
    from ventilation_company.database.db import get_db, engine
    with get_db() as session:
        ...
"""

import os
import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "postgresql://vent:vent123@localhost:5432/ventcompany"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_recycle=POOL_RECYCLE,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)


@contextmanager
def get_db():
    """Контекстний менеджер для сесії БД. Автоматично commit/rollback/close."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_db_connection() -> bool:
    """Перевіряє чи доступна БД."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Помилка підключення до БД: {e}")
        return False


def get_calc_db():
    """Зворотна сумісність: повертає raw PostgreSQL connection.

    Раніше це був sqlite3.connect(). Тепер — raw psycopg2 connection.
    Якщо ви використовуєте цю функцію — краще перейдіть на SQLAlchemy ORM.
    """
    import warnings
    warnings.warn(
        "get_calc_db() застаріло. Використовуйте get_db() або SQLAlchemy ORM.",
        DeprecationWarning,
        stacklevel=2
    )
    return engine.raw_connection()
''')


def create_auth_service():
    write_file(os.path.join(SERVICES_DIR, "auth_service.py"), '''"""Сервіс авторизації та автентифікації.

Ролі:
  admin      — повний доступ, управління користувачами
  manager    — проєкти, клієнти, ціни, прайси
  engineer   — розкрій, специфікації, 3D-моделі, розрахунки
  master     — виробництво, статуси, відвантаження
  accountant — собівартість, прибуток, звіти, зарплати
  viewer     — тільки перегляд (без редагування)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import bcrypt

from ventilation_company.database.db import get_db
from ventilation_company.database.models.user import UserORM

logger = logging.getLogger(__name__)

ROLE_PERMISSIONS = {
    "admin":      {"tabs": "*", "edit": True, "delete": True, "manage_users": True},
    "manager":    {"tabs": ["products", "specification", "price_list", "clients", "projects"], "edit": True, "delete": False, "manage_users": False},
    "engineer":   {"tabs": ["products", "specification", "cutting", "freecad", "projects"], "edit": True, "delete": False, "manage_users": False},
    "master":     {"tabs": ["projects", "specification", "cutting"], "edit": True, "delete": False, "manage_users": False},
    "accountant": {"tabs": ["price_list", "projects", "settings"], "edit": True, "delete": False, "manage_users": False},
    "viewer":     {"tabs": "*", "edit": False, "delete": False, "manage_users": False},
}

VALID_ROLES = set(ROLE_PERMISSIONS.keys())


@dataclass
class AuthUser:
    """Авторизований користувач (датаклас для GUI)."""
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool

    def can_edit(self) -> bool:
        return ROLE_PERMISSIONS.get(self.role, {}).get("edit", False)

    def can_delete(self) -> bool:
        return ROLE_PERMISSIONS.get(self.role, {}).get("delete", False)

    def can_manage_users(self) -> bool:
        return ROLE_PERMISSIONS.get(self.role, {}).get("manage_users", False)

    def allowed_tabs(self):
        return ROLE_PERMISSIONS.get(self.role, {}).get("tabs", [])

    def has_tab_access(self, tab_name: str) -> bool:
        tabs = self.allowed_tabs()
        if tabs == "*":
            return True
        return tab_name in tabs


class AuthService:
    _current_user: Optional[AuthUser] = None

    @classmethod
    def hash_password(cls, plain_password: str) -> str:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )

    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional[AuthUser]:
        with get_db() as session:
            user = session.query(UserORM).filter(
                UserORM.username == username,
                UserORM.is_active == 1
            ).first()

            if not user or not cls.verify_password(password, user.password_hash):
                return None

            user.last_login = datetime.now()
            session.commit()

            auth_user = AuthUser(
                id=user.id,
                username=user.username,
                full_name=user.full_name,
                role=user.role,
                is_active=bool(user.is_active)
            )
            cls._current_user = auth_user
            return auth_user

    @classmethod
    def get_current_user(cls) -> Optional[AuthUser]:
        return cls._current_user

    @classmethod
    def logout(cls) -> None:
        cls._current_user = None

    @classmethod
    def require_role(cls, *roles: str) -> bool:
        user = cls._current_user
        if not user:
            return False
        return user.role in roles
''')


def create_user_repo():
    write_file(os.path.join(REPO_DIR, "user_repo.py"), '''"""Репозиторій для роботи з користувачами (CRUD + пошук)."""

from __future__ import annotations

from typing import Optional, List

from sqlalchemy.orm import Session

from ventilation_company.database.models.user import UserORM
from ventilation_company.services.auth_service import AuthService


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: int) -> Optional[UserORM]:
        return self.session.query(UserORM).filter(UserORM.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[UserORM]:
        return self.session.query(UserORM).filter(UserORM.username == username).first()

    def get_all(self, active_only: bool = True) -> List[UserORM]:
        query = self.session.query(UserORM)
        if active_only:
            query = query.filter(UserORM.is_active == 1)
        return query.order_by(UserORM.full_name).all()

    def create(self, username: str, password: str, full_name: str,
               role: str = "viewer", is_active: bool = True) -> UserORM:
        if self.get_by_username(username):
            raise ValueError(f"Користувач '{username}' вже існує")

        user = UserORM(
            username=username,
            password_hash=AuthService.hash_password(password),
            full_name=full_name,
            role=role,
            is_active=1 if is_active else 0
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update(self, user_id: int, **kwargs) -> Optional[UserORM]:
        user = self.get_by_id(user_id)
        if not user:
            return None

        if "password" in kwargs:
            kwargs["password_hash"] = AuthService.hash_password(kwargs.pop("password"))

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        self.session.commit()
        self.session.refresh(user)
        return user

    def deactivate(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            return False
        user.is_active = 0
        self.session.commit()
        return True

    def delete(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            return False
        self.session.delete(user)
        self.session.commit()
        return True
''')


def create_init_db():
    write_file(os.path.join(DB_DIR, "init_db.py"), '''"""Ініціалізація бази даних PostgreSQL.

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
''')


def create_alembic_ini():
    write_file(os.path.join(BASE_DIR, "alembic.ini"), '''# Alembic конфігурація для VentCompany (PostgreSQL)

[alembic]
script_location = migrations
prepend_sys_path = .
version_path_separator = os

sqlalchemy.url = postgresql://vent:vent123@localhost:5432/ventcompany

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
''')


def create_migrations_env():
    write_file(os.path.join(MIGRATIONS_DIR, "env.py"), '''"""Alembic env.py для PostgreSQL."""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ventilation_company.database.base import Base
from ventilation_company.database.db import DATABASE_URL
from ventilation_company.database.models import *

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
''')


def update_requirements():
    print_header("Крок 4: Оновлення requirements.txt")
    req_path = os.path.join(BASE_DIR, "requirements.txt")
    additions = ["psycopg2-binary>=2.9.9", "python-dotenv>=1.0.0"]

    existing = ""
    if os.path.exists(req_path):
        with open(req_path, "r", encoding="utf-8") as f:
            existing = f.read()

    added = []
    for dep in additions:
        if dep.split(">=")[0] not in existing:
            added.append(dep)

    if added:
        with open(req_path, "a", encoding="utf-8") as f:
            f.write("\n# PostgreSQL + авторизація\n")
            for dep in added:
                f.write(f"{dep}\n")
        print(f"  ✅ Додано: {', '.join(added)}")
    else:
        print("  ✅ Залежності вже присутні")


def run_init_db():
    print_header("Крок 5: Ініціалізація бази даних")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ventilation_company.database.init_db"],
            cwd=BASE_DIR,
            capture_output=False,
            text=True,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"  ❌ Помилка запуску: {e}")
        return False


def main():
    print("\n")
    print("  ██╗   ██╗███████╗███╗   ██╗████████╗ ██████╗ ██████╗ ███╗   ███╗██████╗")
    print("  ██║   ██║██╔════╝████╗  ██║╚══██╔══╝██╔════╝██╔═══██╗████╗ ████║██╔══██╗")
    print("  ██║   ██║█████╗  ██╔██╗ ██║   ██║   ██║     ██║   ██║██╔████╔██║██████╔╝")
    print("  ╚██╗ ██╔╝██╔══╝  ██║╚██╗██║   ██║   ██║     ██║   ██║██║╚██╔╝██║██╔═══╝")
    print("   ╚████╔╝ ███████╗██║ ╚████║   ██║   ╚██████╗╚██████╔╝██║ ╚═╝ ██║██║")
    print("    ╚═══╝  ╚══════╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝")
    print("                        PostgreSQL + Auth Setup\n")

    if not check_dependencies():
        print("\n  ⛔ Встановіть залежності і запустіть знову.")
        input("  Натисніть Enter для виходу...")
        sys.exit(1)

    create_directories()

    print_header("Крок 3: Створення файлів")
    create_env()
    create_db_py()
    create_auth_service()
    create_user_repo()
    create_init_db()
    create_alembic_ini()
    create_migrations_env()

    update_requirements()
    success = run_init_db()

    print("\n")
    print("=" * 55)
    if success:
        print("  ✅ НАЛАШТУВАННЯ ЗАВЕРШЕНО!")
        print("=" * 55)
        print("\n  📋 Наступні кроки:")
        print("     1. Запустіть програму: python main.py")
        print("     2. Увійдіть як admin / admin123")
        print("     3. ЗМІНІТЬ ПАРОЛЬ АДМІНІСТРАТОРА!")
    else:
        print("  ⚠️  Файли створено, але init_db не вдалося запустити.")
        print("     Спробуйте вручну: python -m ventilation_company.database.init_db")
    print("=" * 55)
    input("\n  Натисніть Enter для виходу...")


if __name__ == "__main__":
    main()
