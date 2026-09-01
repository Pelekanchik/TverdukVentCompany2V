"""Створення таблиць VentCompany у PostgreSQL.

Запуск:
    python create_tables.py
"""

import sys
import os

# Додаємо корінь проєкту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ventilation_company.database.db import engine, check_db_connection, DATABASE_URL
from ventilation_company.database.base import Base
from ventilation_company.database.models import *  # noqa: F401, F403

print(f"Підключення до: {DATABASE_URL}")
print("Перевірка підключення...")

if not check_db_connection():
    print("❌ Не вдалося підключитися до PostgreSQL!")
    print("Перевірте:")
    print("  1. Чи запущений PostgreSQL")
    print("  2. Чи правильний DATABASE_URL у .env")
    print("  3. Чи існує база ventcompany і користувач vent")
    sys.exit(1)

print("✅ Підключення успішне")
print("Створення таблиць...")

try:
    Base.metadata.create_all(bind=engine)
    print("✅ Таблиці створено!")

    # Перевіримо, які таблиці створені
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\nСтворено таблиць: {len(tables)}")
    for t in sorted(tables):
        print(f"  • {t}")

except Exception as e:
    print(f"❌ Помилка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
