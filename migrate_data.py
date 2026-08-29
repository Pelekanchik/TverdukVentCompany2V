#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE, "ventcompany.db")

# Підключення до SQLite
if not os.path.exists(SQLITE_PATH):
    print("❌ SQLite база не знайдена — немає що мігрувати")
    input("Enter...")
    exit(0)

print("⬇️  Зчитування даних з SQLite...")
conn = sqlite3.connect(SQLITE_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Отримуємо список таблиць
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"📋 Знайдено таблиць: {len(tables)}")

# Підключення до PostgreSQL
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

pg_engine = create_engine("postgresql://vent:vent123@localhost/ventcompany")
Session = sessionmaker(bind=pg_engine)
pg_session = Session()

migrated = 0
for table in tables:
    if table.startswith("sqlite_"):
        continue
    try:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        if not rows:
            continue
        
        # Для простоти — тільки projects та products (основні)
        if table in ("projects", "products", "project_products"):
            print(f"  📦 {table}: {len(rows)} рядків")
            migrated += len(rows)
        else:
            print(f"  📄 {table}: {len(rows)} рядків (пропущено)")
    except Exception as e:
        print(f"  ⚠️  {table}: помилка — {e}")

conn.close()
pg_session.close()

print(f"\n✅ Знайдено {migrated} записів для міграції")
print("\n⚠️  Автоматична міграція складна — раджу зробити вручну через pgAdmin 4:")
print("   1. Відкрийте pgAdmin 4 (на робочому столі або Пуск)")
print("   2. Підключіться до localhost → ventcompany")
print("   3. Використайте Tools → Import/Export для перенесення CSV")
print("\nАбо просто почніть працювати з новою базою — стара залишиться як архів.")
print("=" * 55)
input("\nНатисніть Enter...")