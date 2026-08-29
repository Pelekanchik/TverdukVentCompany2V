#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE, "data", "company.db")

if not os.path.exists(SQLITE_PATH):
    print("❌ База не знайдена")
    input("Enter...")
    exit(1)

print("=" * 60)
print("  МІГРАЦІЯ SQLite → PostgreSQL (v2)")
print("=" * 60)

# Підключення до SQLite
sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row
sqlite_cur = sqlite_conn.cursor()

# Підключення до PostgreSQL
from sqlalchemy import create_engine, text

pg_engine = create_engine("postgresql://vent:vent123@localhost/ventcompany")

# Отримуємо список таблиць
sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [row[0] for row in sqlite_cur.fetchall()]
print(f"\n📋 Таблиць у SQLite: {len(tables)}")

migrated = 0
skipped = []

with pg_engine.connect() as pg_conn:
    for table in tables:
        try:
            sqlite_cur.execute(f"SELECT * FROM {table}")
            rows = sqlite_cur.fetchall()
            if not rows:
                print(f"   ⏭️  {table} — порожня")
                continue
            
            # Отримуємо стовпці
            sqlite_cur.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in sqlite_cur.fetchall()]
            col_str = ", ".join([f'"{c}"' for c in columns])
            placeholders = ", ".join([f":{c}" for c in columns])
            
            # Вставляємо batch'ами
            batch_size = 50
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i+batch_size]
                for row in batch:
                    # Створюємо dict параметрів
                    params = {col: row[idx] for idx, col in enumerate(columns)}
                    pg_conn.execute(
                        text(f'INSERT INTO "{table}" ({col_str}) VALUES ({placeholders})'),
                        params
                    )
            
            print(f"   ✅ {table} — {len(rows)} рядків")
            migrated += len(rows)
            
        except Exception as e:
            print(f"   ⚠️  {table} — пропущено ({str(e)[:60]})")
            skipped.append(table)
    
    pg_conn.commit()

sqlite_conn.close()

print("\n" + "=" * 60)
print(f"✅ Перенесено: {migrated} записів")
if skipped:
    print(f"⚠️  Пропущено: {', '.join(skipped)}")
print("=" * 60)
print("\nЗапустіть:  python main.py")
print("=" * 60)
input("\nНатисніть Enter...")