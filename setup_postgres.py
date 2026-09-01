"""
🐘 VentCompany PostgreSQL Setup — Автоматичний інсталятор v2

Запуск: python setup_postgres.py
"""

import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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
    deps = [
        ("psycopg2", "psycopg2-binary"),
        ("dotenv", "python-dotenv"),
        ("bcrypt", "bcrypt"),
        ("alembic", "alembic"),
    ]
    for mod, name in deps:
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


def create_env():
    write_file(os.path.join(BASE_DIR, ".env"), '''# PostgreSQL конфігурація VentCompany
DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/ventcompany

# Налаштування пулу з'єднань
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=3600

# Перший адміністратор (створюється автоматично)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_FULL_NAME=Адміністратор
''')


def create_alembic_ini():
    write_file(os.path.join(BASE_DIR, "alembic.ini"), '''# Alembic конфігурація для VentCompany (PostgreSQL)

[alembic]
script_location = migrations
prepend_sys_path = .
version_path_separator = os

sqlalchemy.url = postgresql://postgres:postgres123@localhost:5432/ventcompany

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


def create_migrations_structure():
    """Створити структуру міграцій з initial ревізією."""
    # README (обов'язковий для Alembic)
    readme_path = os.path.join(MIGRATIONS_DIR, "README")
    if not os.path.exists(readme_path):
        write_file(readme_path, "Generic single-database configuration.\n")

    # script.py.mako (шаблон)
    mako_path = os.path.join(MIGRATIONS_DIR, "script.py.mako")
    if not os.path.exists(mako_path):
        write_file(mako_path, '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
''')

    # versions папка
    versions_dir = os.path.join(MIGRATIONS_DIR, "versions")
    os.makedirs(versions_dir, exist_ok=True)

    # initial міграція (якщо ще немає)
    initial_path = os.path.join(versions_dir, "001_initial.py")
    if not os.path.exists(initial_path):
        write_file(initial_path, '''"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2026-09-01 15:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
''')
        print("  ✅ Створено initial міграцію 001_initial.py")


def update_requirements():
    print_header("Крок 4: Оновлення requirements.txt")
    req_path = os.path.join(BASE_DIR, "requirements.txt")
    additions = [
        "psycopg2-binary>=2.9.9",
        "python-dotenv>=1.0.0",
        "bcrypt>=4.0.0",
    ]

    existing = ""
    if os.path.exists(req_path):
        with open(req_path, "r", encoding="utf-8") as f:
            existing = f.read()

    added = []
    for dep in additions:
        pkg = dep.split(">=")[0]
        if pkg not in existing:
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
    print("                        PostgreSQL + Auth Setup v2\n")

    if not check_dependencies():
        print("\n  ⛔ Встановіть залежності і запустіть знову.")
        input("  Натисніть Enter для виходу...")
        sys.exit(1)

    print_header("Крок 2: Створення файлів конфігурації")
    create_env()
    create_alembic_ini()
    create_migrations_env()
    create_migrations_structure()

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
        print("     4. Для нових міграцій: alembic revision --autogenerate -m \"опис\"")
    else:
        print("  ⚠️  Файли створено, але init_db не вдалося запустити.")
        print("     Спробуйте вручну: python -m ventilation_company.database.init_db")
    print("=" * 55)
    input("\n  Натисніть Enter для виходу...")


if __name__ == "__main__":
    main()
