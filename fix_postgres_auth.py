#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))

# Читаємо шлях до PostgreSQL
with open("postgres_path.txt", "r") as f:
    pg_bin = f.read().strip()

pg_dir = os.path.dirname(pg_bin)  # C:\Program Files\PostgreSQL\18
data_dir = os.path.join(pg_dir, "data")
hba_path = os.path.join(data_dir, "pg_hba.conf")

print(f"Шлях до pg_hba.conf: {hba_path}")

if not os.path.exists(hba_path):
    print("❌ Файл не знайдено")
    input("Enter...")
    exit(1)

# Backup
shutil.copy(hba_path, hba_path + ".backup")
print("✅ Backup створено")

# Читаємо і змінюємо
with open(hba_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
changed = False
for line in lines:
    # Змінюємо md5/password на trust для локальних підключень
    if line.strip().startswith("host") and "127.0.0.1" in line:
        if "trust" not in line:
            new_lines.append("host    all             all             127.0.0.1/32            trust\n")
            changed = True
            continue
    if line.strip().startswith("host") and "::1" in line:
        if "trust" not in line:
            new_lines.append("host    all             all             ::1/128                 trust\n")
            changed = True
            continue
    new_lines.append(line)

if changed:
    with open(hba_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("✅ Автентифікація змінена на trust (без пароля для локальних)")
else:
    print("✅ Вже налаштовано trust")

# Перезапускаємо PostgreSQL
print("\nПерезапуск PostgreSQL...")
try:
    subprocess.run(["pg_ctl", "restart", "-D", data_dir], check=True, capture_output=True)
    print("✅ PostgreSQL перезапущено")
except Exception as e:
    print(f"⚠️  Не вдалося перезапустити: {e}")
    print("   Перезапустіть комп'ютер або службу PostgreSQL вручну")

print("\nТепер запустіть:  python setup_postgres.py")
print("Пароль запитувати НЕ буде.")
input("\nНатисніть Enter...")
