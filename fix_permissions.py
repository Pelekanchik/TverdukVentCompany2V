#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))

# Читаємо шлях до PostgreSQL
with open("postgres_path.txt", "r") as f:
    pg_bin = f.read().strip()

os.environ["PATH"] = pg_bin + ";" + os.environ.get("PATH", "")

# Даємо права користувачу vent на схему public
commands = [
    'GRANT ALL ON SCHEMA public TO vent;',
    'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO vent;',
    'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO vent;',
    'ALTER DATABASE ventcompany OWNER TO vent;',
]

print("🔧 Налаштування прав для користувача 'vent'...")
for cmd in commands:
    result = subprocess.run(
        ["psql", "-U", "postgres", "-d", "ventcompany", "-c", cmd],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"✅ {cmd.strip()}")
    else:
        print(f"⚠️  {result.stderr.strip()}")

print("\nТепер запустіть:  python main.py")
input("\nНатисніть Enter...")