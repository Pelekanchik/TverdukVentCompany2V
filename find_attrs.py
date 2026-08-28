#!/usr/bin/env python3
"""Знаходить правильні атрибути класів."""

import sys
sys.path.insert(0, r"C:\Users\Admin\Desktop\TverdukVentCompany2V")

# 1. ProjectDatabase — як закрити з'єднання
from ventilation_company.db_integration import ProjectDatabase
db = ProjectDatabase("data/company.db")

print("=" * 50)
print("ProjectDatabase — пошук engine/session:")
print("=" * 50)

for attr in ["_session_factory", "_get_connection", "engine", "_engine", "session", "_session", "connection", "_connection"]:
    if hasattr(db, attr):
        val = getattr(db, attr)
        print(f"  ✅ {attr} = {type(val).__name__}")
        if hasattr(val, 'dispose'):
            print(f"     → має dispose()")
        if hasattr(val, 'close'):
            print(f"     → має close()")
    else:
        print(f"  ❌ {attr} — немає")

# 2. RoundDuct — правильне ім'я поля діаметра
from ventilation_company.standard_products import make_round_duct, MaterialType
duct = make_round_duct(200, 1000, 0.7, MaterialType.GALVANIZED)

print("\n" + "=" * 50)
print("RoundDuct — всі атрибути (не методи):")
print("=" * 50)

for attr in sorted(dir(duct)):
    if attr.startswith("_"):
        continue
    val = getattr(duct, attr, None)
    if not callable(val):
        print(f"  {attr} = {val}")

# 3. Thickness Enum
from ventilation_company.standard_products import Thickness
print("\n" + "=" * 50)
print("Thickness Enum:")
print("=" * 50)
for t in Thickness:
    print(f"  {t.name} = {t.value}")