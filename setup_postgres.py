#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
path_file = os.path.join(BASE_DIR, "postgres_path.txt")
if os.path.exists(path_file):
    with open(path_file, "r") as f:
        pg_path = f.read().strip()
    if pg_path:
        os.environ["PATH"] = pg_path + ";" + os.environ.get("PATH", "")



BASE = os.path.dirname(os.path.abspath(__file__))

print("=" * 60)
print("  ВСТАНОВЛЕННЯ PostgreSQL для VentCompany")
print("=" * 60)
print("\n1. Завантажте PostgreSQL: https://www.postgresql.org/download/windows/")
print("2. Встановіть з паролем 'vent123' (або своїм)")
print("3. Під час встановлення залиште галочку 'pgAdmin 4'")
print("\nПісля встановлення натисніть Enter...")
input()

# Перевіримо, чи встановлено
print("\nПеревірка встановлення...")
try:
    result = subprocess.run(["psql", "--version"], capture_output=True, text=True)
    print("✅ PostgreSQL знайдено:", result.stdout.strip())
except FileNotFoundError:
    print("❌ PostgreSQL НЕ знайдено у PATH")
    print("   Додайте C:\\Program Files\\PostgreSQL\\16\\bin у PATH")
    print("   або перезапустіть комп'ютер після встановлення")
    input("\nEnter...")
    sys.exit(1)

# Створюємо базу
print("\nСтворення бази 'ventcompany'...")
try:
    subprocess.run([
        "psql", "-U", "postgres", "-c",
        "CREATE DATABASE ventcompany;"
    ], check=True)
    print("✅ База 'ventcompany' створена")
except subprocess.CalledProcessError:
    print("⚠️  База можливо вже існує — це нормально")

# Створюємо користувача
print("\nСтворення користувача 'vent'...")
try:
    subprocess.run([
        "psql", "-U", "postgres", "-c",
        "CREATE USER vent WITH PASSWORD 'vent123';"
    ], check=True)
    subprocess.run([
        "psql", "-U", "postgres", "-c",
        "GRANT ALL PRIVILEGES ON DATABASE ventcompany TO vent;"
    ], check=True)
    print("✅ Користувач 'vent' створений")
except subprocess.CalledProcessError:
    print("⚠️  Користувач можливо вже існує — це нормально")

print("\n" + "=" * 60)
print("✅ PostgreSQL готовий!")
print("=" * 60)
print("\nНаступний крок: змінити config.py на PostgreSQL")
print("  DATABASE_URL = 'postgresql://vent:vent123@localhost/ventcompany'")
print("=" * 60)
input("\nНатисніть Enter...")