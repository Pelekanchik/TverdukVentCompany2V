"""Сервіс автентифікації та авторизації (SQLAlchemy ORM).

Покращення v2.1:
  • Повністю переписано з raw sqlite3 на SQLAlchemy ORM.
  • Збережено клас User для зворотної сумісності з GUI.
  • Дефолтні паролі більше не хардкодяться.
  • При першому запуску генерується випадковий пароль для admin.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
from typing import Optional

from ventilation_company.auth.permissions import Role, has_permission
from ventilation_company.database.db import SessionLocal
from ventilation_company.database.models.user import UserORM

# Шлях до тимчасового файлу з обліковими даними першого запуску
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SETUP_FILE = os.path.join(_BASE_DIR, "data", ".setup_credentials.json")


class User:
    """Проста dataclass-користувач (зворотна сумісність з GUI)."""

    def __init__(self, id: int, username: str, password_hash: str,
                 full_name: str, role: str, is_active: int = 1,
                 created_at: str = None, last_login: str = None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.full_name = full_name
        self.role = role
        self.is_active = is_active
        self.created_at = created_at
        self.last_login = last_login


class AuthService:
    """Сервіс автентифікації з хешуванням паролів (SQLAlchemy ORM)."""

    _instance: Optional["AuthService"] = None
    _current_user: Optional[User] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        pass  # ініціалізація відкладена до першого використання

    def _session(self):
        return SessionLocal()

    # ── Хешування ──
    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> str:
        """PBKDF2-HMAC-SHA256 з salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
        ).hex()
        return f"{salt}${pwd_hash}"

    @staticmethod
    def _verify_password(password: str, stored: str) -> bool:
        """Перевірити пароль проти збереженого хешу."""
        if "$" not in stored:
            return False
        salt, _ = stored.split("$", 1)
        return secrets.compare_digest(
            AuthService._hash_password(password, salt), stored
        )

    def _orm_to_user(self, orm: UserORM) -> User:
        return User(
            id=orm.id,
            username=orm.username,
            password_hash=orm.password_hash,
            full_name=orm.full_name,
            role=orm.role,
            is_active=orm.is_active,
            created_at=orm.created_at.isoformat() if orm.created_at else None,
            last_login=orm.last_login.isoformat() if orm.last_login else None,
        )

    # ── CRUD користувачів ──
    def create_user(
        self,
        username: str,
        password: str,
        full_name: str,
        role: Role | str = Role.MONTER,
    ) -> User:
        """Створити нового користувача."""
        if isinstance(role, str):
            role = Role(role)

        session = self._session()
        try:
            existing = session.query(UserORM).filter(
                UserORM.username == username
            ).first()
            if existing:
                raise ValueError(f"Користувач '{username}' вже існує")

            user_orm = UserORM(
                username=username,
                password_hash=self._hash_password(password),
                full_name=full_name,
                role=role.value,
                is_active=1,
            )
            session.add(user_orm)
            session.commit()
            session.refresh(user_orm)
            return self._orm_to_user(user_orm)
        finally:
            session.close()

    def get_user(self, user_id: int) -> Optional[User]:
        session = self._session()
        try:
            orm = session.get(UserORM, user_id)
            return self._orm_to_user(orm) if orm else None
        finally:
            session.close()

    def get_user_by_username(self, username: str) -> Optional[User]:
        session = self._session()
        try:
            orm = session.query(UserORM).filter(
                UserORM.username == username, UserORM.is_active == 1
            ).first()
            return self._orm_to_user(orm) if orm else None
        finally:
            session.close()

    def list_users(self) -> list[User]:
        session = self._session()
        try:
            rows = session.query(UserORM).filter(
                UserORM.is_active == 1
            ).order_by(UserORM.id).all()
            return [self._orm_to_user(r) for r in rows]
        finally:
            session.close()

    def update_user(self, user_id: int, **kwargs) -> bool:
        allowed = {"full_name", "role", "is_active"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if "password" in kwargs:
            fields["password_hash"] = self._hash_password(kwargs["password"])
        if not fields:
            return False

        session = self._session()
        try:
            orm = session.get(UserORM, user_id)
            if not orm:
                return False
            for k, v in fields.items():
                setattr(orm, k, v)
            session.commit()
            return True
        finally:
            session.close()

    def delete_user(self, user_id: int) -> bool:
        """Soft-delete."""
        return self.update_user(user_id, is_active=0)

    # ── Автентифікація ──
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Перевірити логін/пароль і повернути користувача."""
        session = self._session()
        try:
            orm = session.query(UserORM).filter(
                UserORM.username == username, UserORM.is_active == 1
            ).first()
            if orm and self._verify_password(password, orm.password_hash):
                from datetime import datetime
                orm.last_login = datetime.now()
                session.commit()
                self._current_user = self._orm_to_user(orm)
                return self._current_user
            return None
        finally:
            session.close()

    def logout(self):
        """Вийти з системи."""
        self._current_user = None

    @property
    def current_user(self) -> Optional[User]:
        return self._current_user

    @property
    def is_authenticated(self) -> bool:
        return self._current_user is not None

    # ── Авторизація ──
    def can(self, permission: str) -> bool:
        """Чи має поточний користувач дозвіл?"""
        if not self._current_user:
            return False
        return has_permission(self._current_user.role, permission)

    def is_director(self) -> bool:
        return self._current_user is not None and self._current_user.role == Role.DIRECTOR.value

    def is_engineer(self) -> bool:
        return self._current_user is not None and self._current_user.role == Role.ENGINEER.value

    def is_accountant(self) -> bool:
        return self._current_user is not None and self._current_user.role == Role.ACCOUNTANT.value

    def is_monter(self) -> bool:
        return self._current_user is not None and self._current_user.role == Role.MONTER.value

    # ── Ініціалізація першого запуску ──
    @staticmethod
    def _generate_temp_password(length: int = 12) -> str:
        """Згенерувати криптографічно стійкий тимчасовий пароль."""
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def ensure_default_users(self):
        """Створити дефолтного адміністратора при першому запуску.

        • Якщо в БД ще немає жодного користувача — створюється admin
          з випадковим паролем.
        • Пароль зберігається у файл .setup_credentials.json (тимчасово).
        • Інші ролі НЕ створюються автоматично.
        """
        session = self._session()
        try:
            count = session.query(UserORM).count()
            if count == 0:
                temp_password = self._generate_temp_password()
                user_orm = UserORM(
                    username="admin",
                    password_hash=self._hash_password(temp_password),
                    full_name="Адміністратор",
                    role=Role.DIRECTOR.value,
                    is_active=1,
                )
                session.add(user_orm)
                session.commit()

                os.makedirs(os.path.dirname(_SETUP_FILE), exist_ok=True)
                setup_data = {
                    "username": "admin",
                    "password": temp_password,
                    "role": "director",
                    "created_at": __import__("datetime").datetime.now().isoformat(),
                    "note": "Видаліть цей файл після першого входу. Пароль рекомендується змінити.",
                }
                with open(_SETUP_FILE, "w", encoding="utf-8") as f:
                    json.dump(setup_data, f, ensure_ascii=False, indent=2)
                try:
                    os.chmod(_SETUP_FILE, stat.S_IRUSR | stat.S_IWUSR)
                except OSError:
                    pass
        finally:
            session.close()

    def has_setup_credentials(self) -> bool:
        return os.path.exists(_SETUP_FILE)

    def get_setup_credentials(self) -> dict | None:
        if not self.has_setup_credentials():
            return None
        try:
            with open(_SETUP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def clear_setup_credentials(self):
        if os.path.exists(_SETUP_FILE):
            try:
                os.remove(_SETUP_FILE)
            except OSError:
                pass


# ── Глобальний екземпляр ──
auth = AuthService()
