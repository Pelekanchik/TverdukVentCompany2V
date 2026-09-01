"""Повне налаштування PostgreSQL для VentCompany.

Запуск:
    python setup_postgres_full.py

Що робить:
    1. Питає пароль адміна PostgreSQL (postgres)
    2. Створює/оновлює користувача 'vent'
    3. Створює таблиці в базі 'ventcompany'
    4. Оновлює .env
    5. Перевіряє результат
"""

import sys
import subprocess

def install_package(pkg):
    """Встановлює пакет, якщо його немає."""
    try:
        __import__(pkg)
    except ImportError:
        print(f"Встановлюємо {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

install_package("psycopg2-binary")
install_package("sqlalchemy")
install_package("python-dotenv")

import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine, inspect, text
import os

BASE = os.path.dirname(os.path.abspath(__file__))
DB_NAME = "ventcompany"
DB_USER = "vent"
DB_PASS = "vent123"
DB_HOST = "localhost"
DB_PORT = "5432"

print("=" * 60)
print("  НАЛАШТУВАННЯ PostgreSQL для VentCompany")
print("=" * 60)

# Крок 1: Питаємо пароль адміна
print("\n[1/5] Введіть пароль адміністратора PostgreSQL (користувач 'postgres'):")
print("        (той пароль, який ви вказали при встановленні PostgreSQL)")
admin_password = input("Пароль: ").strip()

if not admin_password:
    print("❌ Пароль не може бути порожнім!")
    sys.exit(1)

# Крок 2: Підключаємося як postgres і налаштовуємо
print("\n[2/5] Підключення до PostgreSQL як адміністратор...")
try:
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database="postgres",
        user="postgres",
        password=admin_password
    )
    conn.autocommit = True
    cur = conn.cursor()
    print("  ✅ Підключення успішне")
except Exception as e:
    print(f"  ❌ Помилка підключення: {e}")
    print("  Перевірте:")
    print("    - Чи запущений PostgreSQL (services.msc)")
    print("    - Чи правильний пароль")
    print("    - Чи порт 5432 не зайнятий")
    sys.exit(1)

# Створюємо базу (якщо немає)
print("\n[3/5] Створення бази 'ventcompany'...")
cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
if not cur.fetchone():
    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
    print("  ✅ База створена")
else:
    print("  ℹ️  База вже існує")

# Створюємо/оновлюємо користувача vent
print("\n[4/5] Налаштування користувача 'vent'...")
cur.execute(f"SELECT 1 FROM pg_roles WHERE rolname = '{DB_USER}'")
if not cur.fetchone():
    cur.execute(sql.SQL("CREATE USER {} WITH PASSWORD %s").format(sql.Identifier(DB_USER)), (DB_PASS,))
    print("  ✅ Користувач 'vent' створений")
else:
    cur.execute(sql.SQL("ALTER USER {} WITH PASSWORD %s").format(sql.Identifier(DB_USER)), (DB_PASS,))
    print("  ℹ️  Користувач 'vent' оновлений")

# Даємо права
cur.execute(sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
    sql.Identifier(DB_NAME), sql.Identifier(DB_USER)
))
cur.execute(sql.SQL("ALTER DATABASE {} OWNER TO {}").format(
    sql.Identifier(DB_NAME), sql.Identifier(DB_USER)
))
print("  ✅ Права надані")

cur.close()
conn.close()

# Крок 5: Створення таблиць через SQLAlchemy
print("\n[5/5] Створення таблиць...")

database_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

try:
    sys.path.insert(0, BASE)
    from ventilation_company.database.db import engine, check_db_connection
    from ventilation_company.database.base import Base
    from ventilation_company.database.models import *

    # Перевизначаємо engine з правильним URL
    from sqlalchemy import create_engine
    engine = create_engine(database_url, echo=False, future=True)

    if not check_db_connection():
        raise Exception("Не вдалося підключитися")

    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"  ✅ Таблиці створено: {len(tables)} шт.")
    for t in sorted(tables):
        print(f"     • {t}")

except Exception as e:
    print(f"  ❌ Помилка створення таблиць: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Крок 6: Оновлюємо .env
print("\n[6/6] Оновлення .env...")
env_path = os.path.join(BASE, ".env")
with open(env_path, "w", encoding="utf-8") as f:
    f.write(f"""DATABASE_URL={database_url}
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_FULL_NAME=Administrator
""")
print("  ✅ .env оновлено")

print("\n" + "=" * 60)
print("  ✅ НАЛАШТУВАННЯ ЗАВЕРШЕНО!")
print("=" * 60)
print("\n  Запускайте програму:")
print("    python main.py")
print("\n  Логін: admin")
print("  Пароль: admin123")
