#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess

def find_postgres():
    """Знайти psql.exe у Program Files."""
    base_paths = [
        r"C:\Program Files\PostgreSQL",
        r"C:\Program Files (x86)\PostgreSQL",
    ]
    
    for base in base_paths:
        if not os.path.exists(base):
            continue
        for version in os.listdir(base):
            bin_path = os.path.join(base, version, "bin")
            psql_path = os.path.join(bin_path, "psql.exe")
            if os.path.exists(psql_path):
                return bin_path
    return None

path = find_postgres()
if path:
    print(f"✅ Знайдено: {path}")
    # Додаємо у PATH
    os.environ["PATH"] = path + ";" + os.environ.get("PATH", "")
    # Перевіримо
    result = subprocess.run(["psql", "--version"], capture_output=True, text=True)
    print("✅ PostgreSQL:", result.stdout.strip())
    # Зберігаємо
    with open("postgres_path.txt", "w") as f:
        f.write(path)
    print("\nТепер запустіть:  python setup_postgres.py")
else:
    print("❌ PostgreSQL НЕ знайдено")
    print("   Можливі причини:")
    print("   1. Встановлення ще триває — зачекайте і спробуйте знову")
    print("   2. Встановлено у нестандартну папку")
    print("   3. Встановлення не завершилося успішно")
    print("\n   Спробуйте знайти вручну:")
    print('   Відкрийте C:\\ і пошукайте "psql.exe"')

input("\nНатисніть Enter...")