#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text, inspect

BASE = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE, "data", "company.db")
PG_URL = "postgresql://vent:vent123@localhost/ventcompany"

print("=" * 60)
print("  ЧИСТИЙ ПЕРЕХІД НА PostgreSQL")
print("=" * 60)

# 1. Підключення
pg_engine = create_engine(PG_URL)
sqlite_conn = sqlite3.connect(SQLITE_PATH)

# 2. ОЧИЩЕННЯ: видаляємо ВСІ таблиці з PostgreSQL
print("\n🗑️  Очищення старих таблиць...")
with pg_engine.connect() as conn:
    conn.execute(text("DROP SCHEMA public CASCADE"))
    conn.execute(text("CREATE SCHEMA public"))
    conn.execute(text("GRANT ALL ON SCHEMA public TO vent"))
    conn.commit()
print("✅ База очищена")

# 3. Створюємо таблиці через SQLAlchemy (правильні типи)
print("\n📐 Створення таблиць через SQLAlchemy...")
from ventilation_company.database.models import Base
Base.metadata.create_all(bind=pg_engine)
print("✅ Таблиці створено з правильними типами")

# 4. Міграція даних
print("\n📦 Міграція даних...")
tables = pd.read_sql_query(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
    sqlite_conn
)['name'].tolist()

migrated = 0
for table in tables:
    if table == "alembic_version":
        continue
    
    try:
        df = pd.read_sql_query(f'SELECT * FROM "{table}"', sqlite_conn)
        if df.empty:
            continue
        
        # Вставляємо дані (таблиця вже існує з правильними типами)
        df.to_sql(table, pg_engine, if_exists='append', index=False, method='multi')
        print(f"   ✅ {table} — {len(df)} рядків")
        migrated += len(df)
    except Exception as e:
        print(f"   ⚠️  {table} — {str(e)[:50]}")

sqlite_conn.close()

# 5. Виправляємо db_integration.py — ТІЛЬКИ PostgreSQL
print("\n🔧 Виправлення db_integration.py...")
db_path = os.path.join(BASE, "ventilation_company", "db_integration.py")
with open(db_path, "r", encoding="utf-8") as f:
    txt = f.read()

# to_char для PostgreSQL (жорстко, без сумісності)
txt = txt.replace('func.strftime("%Y-%m", ClientProject.end_date)', "func.to_char(ClientProject.end_date, 'YYYY-MM')")
txt = txt.replace('func.strftime("%Y-%m", ClientProject.start_date)', "func.to_char(ClientProject.start_date, 'YYYY-MM')")
txt = txt.replace('self._month_format(ClientProject.end_date)', "func.to_char(ClientProject.end_date, 'YYYY-MM')")
txt = txt.replace('self._month_format(ClientProject.start_date)', "func.to_char(ClientProject.start_date, 'YYYY-MM')")

# Виправляємо since для PostgreSQL (дата, не рядок)
txt = txt.replace('ClientProject.end_date >= since.strftime("%Y-%m") + "-01"', "ClientProject.end_date >= since")
txt = txt.replace('ClientProject.start_date >= since', "ClientProject.start_date >= since")

with open(db_path, "w", encoding="utf-8") as f:
    f.write(txt)
print("✅ db_integration.py — to_char для PostgreSQL")

# 6. Виправляємо db.py на PostgreSQL
db_py_path = os.path.join(BASE, "ventilation_company", "database", "db.py")
with open(db_py_path, "w", encoding="utf-8") as f:
    f.write('''"""Підключення до БД (PostgreSQL)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

DATABASE_URL = "postgresql://vent:vent123@localhost/ventcompany"
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)

def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def get_calc_db():
    import sqlite3
    from ventilation_company.config import DB_PATH
    return sqlite3.connect(DB_PATH)
''')
print("✅ db.py — PostgreSQL")

# 7. Чистимо кеш
for root, dirs, files in os.walk(BASE):
    for d in list(dirs):
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d))
            dirs.remove(d)
print("🗑️  Кеш очищено")

print("\n" + "=" * 60)
print(f"✅ ГОТОВО! Перенесено {migrated} записів")
print("=" * 60)
print("\nЗапустіть:  python main.py")
print("=" * 60)
input("\nНатисніть Enter...")