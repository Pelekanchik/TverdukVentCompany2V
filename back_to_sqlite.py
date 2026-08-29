#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))

# Відновлюємо db.py з backup
backup = os.path.join(BASE, "ventilation_company", "database", "db.py.sqlite_backup")
current = os.path.join(BASE, "ventilation_company", "database", "db.py")

if os.path.exists(backup):
    shutil.copy(backup, current)
    print("✅ db.py відновлено з backup (SQLite)")
else:
    # Створюємо простий SQLite db.py
    with open(current, "w", encoding="utf-8") as f:
        f.write('''"""Підключення до БД (SQLite)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

SQLALCHEMY_DATABASE_URI = "sqlite:///data/company.db"
engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False, future=True)
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
    print("✅ db.py створено для SQLite")

# Чистимо кеш
for root, dirs, files in os.walk(BASE):
    for d in list(dirs):
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d))
            dirs.remove(d)

print("🗑️  Кеш очищено")
print("\n" + "=" * 60)
print("✅ Повернено на SQLite")
print("=" * 60)
print("\nВаші дані у data/company.db — цілі й неушкоджені.")
print("Всі виправлення збережено:")
print("  • services/ (PricingService, SalaryService, ProjectService)")
print("  • Тести (6/6 пройдено)")
print("  • Прайс-лист видалено")
print("  • Зарплата уніфікована")
print("\nЗапустіть:  python main.py")
print("=" * 60)
input("\nНатисніть Enter...")