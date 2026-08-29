#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "ventilation_company", "auth", "service.py")

with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

# Замінюємо isoformat() на універсальну функцію
old = '''    def _orm_to_user(self, orm):
        """Конвертувати ORM-запис у User."""
        return User(
            id=orm.id,
            username=orm.username,
            display_name=orm.display_name,
            role=orm.role,
            email=orm.email,
            phone=orm.phone,
            is_active=orm.is_active,
            created_at=orm.created_at.isoformat() if orm.created_at else None,
            last_login=orm.last_login.isoformat() if orm.last_login else None,
        )'''

new = '''    def _orm_to_user(self, orm):
        """Конвертувати ORM-запис у User."""
        def _fmt(dt):
            if dt is None:
                return None
            if hasattr(dt, 'isoformat'):
                return dt.isoformat()
            return str(dt)
        return User(
            id=orm.id,
            username=orm.username,
            display_name=orm.display_name,
            role=orm.role,
            email=orm.email,
            phone=orm.phone,
            is_active=orm.is_active,
            created_at=_fmt(orm.created_at),
            last_login=_fmt(orm.last_login),
        )'''

if old in txt:
    txt = txt.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    print("✅ auth/service.py виправлено — тепер обробляє і рядки, і datetime")
else:
    print("⚠️  Блок не знайдено")

print("\nТепер запустіть:  python main.py")
input("\nНатисніть Enter...")