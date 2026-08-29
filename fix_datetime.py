#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from sqlalchemy import create_engine, text

BASE = os.path.dirname(os.path.abspath(__file__))
PG_URL = "postgresql://vent:vent123@localhost/ventcompany"

pg_engine = create_engine(PG_URL)

tables_to_fix = ["users", "projects", "project_products"]

print("🔧 Виправлення типів datetime у PostgreSQL...\n")

with pg_engine.connect() as conn:
    for table in tables_to_fix:
        for col in ["created_at", "updated_at", "start_date", "end_date"]:
            try:
                # Перевіримо, чи є стовпець
                result = conn.execute(text(f'''
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table}' AND column_name = '{col}'
                '''))
                row = result.fetchone()
                if row and row[1] in ('text', 'character varying'):
                    # Конвертуємо у timestamp
                    conn.execute(text(f'''
                        ALTER TABLE "{table}" 
                        ALTER COLUMN "{col}" TYPE TIMESTAMP 
                        USING "{col}"::TIMESTAMP
                    '''))
                    conn.commit()
                    print(f"   ✅ {table}.{col} → TIMESTAMP")
            except Exception as e:
                print(f"   ⏭️  {table}.{col} — {str(e)[:40]}")

print("\n✅ Готово!")
print("Запустіть:  python main.py")
input("\nНатисніть Enter...")