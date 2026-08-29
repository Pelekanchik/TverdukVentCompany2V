#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text

BASE = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE, "data", "company.db")
PG_URL = "postgresql://vent:vent123@localhost/ventcompany"

if not os.path.exists(SQLITE_PATH):
    print("❌ База не знайдена")
    input("Enter...")
    exit(1)

print("=" * 60)
print("  МІГРАЦІЯ SQLite → PostgreSQL (final)")
print("=" * 60)

sqlite_conn = sqlite3.connect(SQLITE_PATH)
pg_engine = create_engine(PG_URL)

# Список таблиць
tables = pd.read_sql_query(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
    sqlite_conn
)['name'].tolist()

print(f"\n📋 Таблиць: {len(tables)}")

migrated = 0
skipped = []

for table in tables:
    if table == "alembic_version":
        print(f"   ⏭️  {table} — службова, пропускаємо")
        continue
    
    try:
        df = pd.read_sql_query(f'SELECT * FROM "{table}"', sqlite_conn)
        if df.empty:
            print(f"   ⏭️  {table} — порожня")
            continue
        
        # Видаляємо стару таблицю через connection
        with pg_engine.connect() as conn:
            conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
            conn.commit()
        
        # Записуємо через pandas (replace створить нову)
        df.to_sql(table, pg_engine, if_exists='replace', index=False, method='multi')
        
        print(f"   ✅ {table} — {len(df)} рядків")
        migrated += len(df)
        
    except Exception as e:
        print(f"   ⚠️  {table} — {str(e)[:60]}")
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