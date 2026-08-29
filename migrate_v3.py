#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))

# Встановлюємо pandas
print("⬇️  Встановлення pandas...")
subprocess.run([os.sys.executable, "-m", "pip", "install", "pandas"], capture_output=True)
print("✅ pandas готовий")

import pandas as pd
import sqlite3

SQLITE_PATH = os.path.join(BASE, "data", "company.db")
PG_URL = "postgresql://vent:vent123@localhost/ventcompany"

if not os.path.exists(SQLITE_PATH):
    print("❌ База не знайдена")
    input("Enter...")
    exit(1)

print("=" * 60)
print("  МІГРАЦІЯ SQLite → PostgreSQL (v3 — pandas)")
print("=" * 60)

# Підключення
sqlite_conn = sqlite3.connect(SQLITE_PATH)
pg_engine = __import__('sqlalchemy').create_engine(PG_URL)

# Список таблиць
tables = pd.read_sql_query(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
    sqlite_conn
)['name'].tolist()

print(f"\n📋 Таблиць: {len(tables)}")

migrated = 0
skipped = []

for table in tables:
    try:
        # Читаємо з SQLite
        df = pd.read_sql_query(f"SELECT * FROM {table}", sqlite_conn)
        if df.empty:
            print(f"   ⏭️  {table} — порожня")
            continue
        
        # Видаляємо стару таблицю з PostgreSQL (якщо є)
        pg_engine.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
        
        # Записуємо у PostgreSQL
        df.to_sql(table, pg_engine, if_exists='replace', index=False)
        
        print(f"   ✅ {table} — {len(df)} рядків")
        migrated += len(df)
        
    except Exception as e:
        print(f"   ⚠️  {table} — {str(e)[:50]}")
        skipped.append(table)

sqlite_conn.close()

print("\n" + "=" * 60)
print(f"✅ Перенесено: {migrated} записів")
if skipped:
    print(f"⚠️  Пропущено: {', '.join(skipped)}")
print("=" * 60)
print("\nЗапустіть:  python main.py")
print("=" * 60)
input("\nНатисніть Enter...")