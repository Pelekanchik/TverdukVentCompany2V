"""Скидання пароля адміністратора."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ventilation_company.auth.service import auth
from ventilation_company.database.db import SessionLocal
from ventilation_company.database.models.user import UserORM

NEW_PASSWORD = "admin123"  # Змініть на свій пароль

session = SessionLocal()
try:
    admin = session.query(UserORM).filter(UserORM.username == "admin").first()
    if admin:
        admin.password_hash = auth._hash_password(NEW_PASSWORD)
        session.commit()
        print(f"✅ Пароль admin змінено на: {NEW_PASSWORD}")
    else:
        # Створюємо admin, якщо його немає
        from ventilation_company.auth.permissions import Role
        admin = UserORM(
            username="admin",
            password_hash=auth._hash_password(NEW_PASSWORD),
            full_name="Адміністратор",
            role=Role.DIRECTOR.value,
            is_active=1,
        )
        session.add(admin)
        session.commit()
        print(f"✅ Створено admin з паролем: {NEW_PASSWORD}")
finally:
    session.close()