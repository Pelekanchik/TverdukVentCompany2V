#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "ventilation_company", "auth", "service.py")

with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

# Знаходимо _orm_to_user і замінюємо isoformat на універсальну функцію
pattern = r'(    def _orm_to_user\(self, orm\):.*?return User\()'
match = re.search(pattern, txt, re.DOTALL)

if match:
    # Замінюємо isoformat() на _fmt()
    txt = re.sub(
        r'(\w+)\.isoformat\(\) if \1 else None',
        r'_fmt(\1)',
        txt
    )
    # Додаємо helper функцію на початок методу
    old_method = '    def _orm_to_user(self, orm):\n        """Конвертувати ORM-запис у User."""'
    new_method = '''    def _orm_to_user(self, orm):
        """Конвертувати ORM-запис у User."""
        def _fmt(dt):
            if dt is None:
                return None
            if hasattr(dt, 'isoformat'):
                return dt.isoformat()
            return str(dt)'''
    
    txt = txt.replace(old_method, new_method)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    print("✅ auth/service.py виправлено")
else:
    print("⚠️  _orm_to_user не знайдено")

print("\nТепер запустіть:  python main.py")
input("\nНатисніть Enter...")