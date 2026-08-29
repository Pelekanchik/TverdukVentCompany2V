#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "ventilation_company", "auth", "service.py")

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Замінюємо кожен рядок з isoformat
new_lines = []
for i, line in enumerate(lines, 1):
    if ".isoformat()" in line and "orm." in line:
        # Замінюємо: orm.xxx.isoformat() if orm.xxx else None
        # На: (orm.xxx.isoformat() if hasattr(orm.xxx, 'isoformat') else str(orm.xxx)) if orm.xxx else None
        import re
        line = re.sub(
            r'(orm\.\w+)\.isoformat\(\) if \1 else None',
            r'(\1.isoformat() if hasattr(\1, "isoformat") else str(\1)) if \1 else None',
            line
        )
        print(f"   ✅ Рядок {i}: виправлено isoformat")
    new_lines.append(line)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("\nТепер запустіть:  python main.py")
input("\nНатисніть Enter...")