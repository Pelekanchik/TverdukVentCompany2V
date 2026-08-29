#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE, "data", "company.db")

if not os.path.exists(SQLITE_PATH):
    print("❌ База не знайдена")
    input("Enter...")
    exit(1)

print("=" * 60)
print("  МІГРАЦІЯ SQLite → PostgreSQL")
print("=" * 60)

# Backup
backup_path = SQLITE_PATH + ".backup_" + __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy(SQLITE_PATH, backup_path)
print(f"\n💾 Backup створено: {backup_path}")

# Підключення до SQLite
sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row
sqlite_cur = sqlite_conn.cursor()

# Підключення до PostgreSQL
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

pg_engine = create_engine("postgresql://vent:vent123@localhost/ventcompany")
Session = sessionmaker(bind=pg_engine)
pg_session = Session()

# Отримуємо список таблиць
sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [row[0] for row in sqlite_cur.fetchall()]
print(f"\n📋 Таблиць у SQLite: {len(tables)}")
for t in tables:
    print(f"   • {t}")

# Переносимо таблицю за таблицею
migrated = 0
skipped = []

for table in tables:
    try:
        sqlite_cur.execute(f"SELECT * FROM {table}")
        rows = sqlite_cur.fetchall()
        if not rows:
            print(f"   ⏭️  {table} — порожня")
            continue
        
        # Для ORM таблиць — використовуємо raw SQL INSERT
        # Отримуємо стовпці
        sqlite_cur.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in sqlite_cur.fetchall()]
        col_str = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        
        # Вставляємо batch'ами
        batch_size = 100
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            values = [tuple(row) for row in batch]
            pg_engine.execute(
                f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})",
                values
            )
        
        print(f"   ✅ {table} — {len(rows)} рядків")
        migrated += len(rows)
        
    except Exception as e:
        print(f"   ⚠️  {table} — пропущено ({e})")
        skipped.append(table)

sqlite_conn.close()
pg_session.commit()
pg_session.close()

print("\n" + "=" * 60)
print(f"✅ Перенесено: {migrated} записів")
if skipped:
    print(f"⚠️  Пропущено таблиць: {len(skipped)}")
    for t in skipped:
        print(f"   • {t}")
print("=" * 60)
print("\nТепер запустіть:  python main.py")
print("Ваші проєкти мають бути у PostgreSQL!")
print("=" * 60)
input("\nНатисніть Enter...")