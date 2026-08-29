#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

# Читаємо шлях до PostgreSQL, якщо є
path_file = os.path.join(BASE, "postgres_path.txt")
if os.path.exists(path_file):
    with open(path_file, "r") as f:
        pg_path = f.read().strip()
    if pg_path and os.path.exists(pg_path):
        os.environ["PATH"] = pg_path + ";" + os.environ.get("PATH", "")
        print(f"✅ PATH оновлено з postgres_path.txt: {pg_path}")

# Тепер запускаємо оригінальний скрипт
import subprocess
try:
    result = subprocess.run(["psql", "--version"], capture_output=True, text=True)
    print("✅ PostgreSQL знайдено:", result.stdout.strip())
except FileNotFoundError:
    print("❌ PostgreSQL все ще не у PATH")
    print("   Перезапустіть комп'ютер або додайте вручну:")
    print(f"   {pg_path if 'pg_path' in dir() else 'C:\\Program Files\\PostgreSQL\\18\\bin'}")
    input("Enter...")
    sys.exit(1)

# Якщо дійшли сюди — все ок, запускаємо setup_postgres.py знову
# Але спочатку виправимо setup_postgres.py, щоб він читав postgres_path.txt
setup_path = os.path.join(BASE, "setup_postgres.py")
with open(setup_path, "r", encoding="utf-8") as f:
    txt = f.read()

# Додаємо читання postgres_path.txt на початок setup_postgres.py
inject = '''import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
path_file = os.path.join(BASE_DIR, "postgres_path.txt")
if os.path.exists(path_file):
    with open(path_file, "r") as f:
        pg_path = f.read().strip()
    if pg_path:
        os.environ["PATH"] = pg_path + ";" + os.environ.get("PATH", "")

'''
if "path_file = os.path.join" not in txt:
    # Вставляємо після перших import
    lines = txt.split("\n")
    import_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("import "):
            import_idx = i + 1
    lines.insert(import_idx, inject)
    txt = "\n".join(lines)
    with open(setup_path, "w", encoding="utf-8") as f:
        f.write(txt)
    print("✅ setup_postgres.py виправлено — тепер читає postgres_path.txt")

print("\nТепер запустіть:  python setup_postgres.py")
input("\nНатисніть Enter...")