#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys

# Знаходимо папку PostgreSQL
possible_paths = [
    r"C:\Program Files\PostgreSQL\16\bin",
    r"C:\Program Files\PostgreSQL\15\bin",
    r"C:\Program Files\PostgreSQL\14\bin",
    r"C:\Program Files\PostgreSQL\13\bin",
]

postgres_bin = None
for p in possible_paths:
    if os.path.exists(p):
        postgres_bin = p
        break

if postgres_bin is None:
    print("❌ PostgreSQL не знайдено у стандартних папках")
    print("   Перевірте, чи встановлено PostgreSQL")
    input("Enter...")
    sys.exit(1)

print(f"✅ Знайдено: {postgres_bin}")

# Додаємо у PATH для поточної сесії
os.environ["PATH"] = postgres_bin + ";" + os.environ.get("PATH", "")
print("✅ Додано у PATH для поточної сесії")

# Перевіримо
import subprocess
try:
    result = subprocess.run(["psql", "--version"], capture_output=True, text=True)
    print("✅ PostgreSQL працює:", result.stdout.strip())
except FileNotFoundError:
    print("❌ Все ще не знайдено")
    sys.exit(1)

# Зберігаємо PATH у файл для наступних запусків
with open("postgres_path.txt", "w") as f:
    f.write(postgres_bin)
print("✅ Шлях збережено у postgres_path.txt")

print("\nТепер запустіть:  python setup_postgres.py")
input("\nНатисніть Enter...")