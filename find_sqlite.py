#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))

print("🔍 Пошук SQLite бази...\n")

found = []
for root, dirs, files in os.walk(BASE):
    for f in files:
        if f.endswith(".db") or f.endswith(".sqlite") or f.endswith(".sqlite3"):
            full = os.path.join(root, f)
            size = os.path.getsize(full)
            found.append((full, size))

if found:
    for path, size in found:
        print(f"✅ {path} ({size:,} байт)")
else:
    print("❌ SQLite база не знайдена")
    print("   Можливо, вона у папці AppData або іншому місці")

print("\n" + "=" * 55)
input("\nНатисніть Enter...")