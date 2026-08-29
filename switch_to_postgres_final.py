#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))

# 1. Встановлюємо psycopg2-binary
print("⬇️  Встановлення psycopg2-binary (драйвер PostgreSQL)...")
result = subprocess.run([os.sys.executable, "-m", "pip", "install", "psycopg2-binary"], capture_output=True, text=True)
if result.returncode == 0:
    print("✅ psycopg2-binary встановлено")
else:
    print("⚠️  Помилка встановлення:", result.stderr)

# 2. Backup db.py
db_path = os.path.join(BASE, "ventilation_company", "database", "db.py")
backup_path = db_path + ".sqlite_backup"
shutil.copy(db_path, backup_path)
print(f"✅ Backup db.py створено: {backup_path}")

# 3. Новий db.py для PostgreSQL
new_db = '''"""Підключення до БД та сесії (PostgreSQL).

Версія v2.2: Перехід з SQLite на PostgreSQL.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# PostgreSQL підключення
DATABASE_URL = "postgresql://vent:vent123@localhost/ventcompany"

# SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # True для дебагу SQL-запитів
    future=True,
)

# Фабрика сесій
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Scoped session для потокобезпеки (GUI + фонові задачі)
db_session = scoped_session(SessionLocal)


def get_db():
    """Генератор сесій для використання з context managers."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_calc_db():
    """Повертає sqlite3 connection для зворотної сумісності (calc_templates)."""
    import sqlite3
    from ventilation_company.config import DB_PATH
    return sqlite3.connect(DB_PATH)
'''

with open(db_path, "w", encoding="utf-8") as f:
    f.write(new_db)
print("✅ db.py оновлено на PostgreSQL")

# 4. Перевіримо підключення
print("\n🔌 Перевірка підключення до PostgreSQL...")
try:
    from sqlalchemy import create_engine
    test_engine = create_engine("postgresql://vent:vent123@localhost/ventcompany")
    conn = test_engine.connect()
    conn.close()
    print("✅ Підключення до PostgreSQL успішне!")
except Exception as e:
    print(f"❌ Помилка підключення: {e}")
    print("   Можливі причини:")
    print("   1. PostgreSQL не запущено (перезапустіть службу)")
    print("   2. База 'ventcompany' не створена (запустіть setup_postgres.py)")
    print("   3. Користувач 'vent' не має прав")

# 5. Чистимо кеш
for root, dirs, files in os.walk(BASE):
    for d in list(dirs):
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d))
            dirs.remove(d)
print("🗑️  Кеш очищено")

print("\n" + "=" * 60)
print("✅ ГОТОВО!")
print("=" * 60)
print("\nТепер запустіть:  python main.py")
print("Програма використовуватиме PostgreSQL.")
print("\nЯкщо щось не так — відновіть backup:")
print("   copy ventilation_company\\database\\db.py.sqlite_backup ventilation_company\\database\\db.py")
print("=" * 60)
input("\nНатисніть Enter...")