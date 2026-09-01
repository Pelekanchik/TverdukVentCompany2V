"""Додавання користувача в PostgreSQL."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ventilation_company.database.db import get_db
from ventilation_company.database.models.user import UserORM
import bcrypt

print("=" * 50)
print("  Додавання користувача в PostgreSQL")
print("=" * 50)

username = input("Логін: ").strip()
password = input("Пароль: ").strip()
full_name = input("ПІБ: ").strip()
role = input("Роль (admin/director/manager/engineer/accountant): ").strip() or "director"

password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

with get_db() as session:
    existing = session.query(UserORM).filter(UserORM.username == username).first()
    if existing:
        print(f"❌ Користувач '{username}' вже існує!")
        sys.exit(1)

    user = UserORM(username=username, password_hash=password_hash, full_name=full_name, role=role)
    session.add(user)
    print(f"✅ Користувач '{username}' доданий!")

print("\nЗапускайте: python main.py")
