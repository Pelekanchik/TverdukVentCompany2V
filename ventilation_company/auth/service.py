"""Сервіс автентифікації та авторизації.

Використовує PBKDF2 для хешування паролів та sqlite3 напряму.
Поточний користувач зберігається як singleton.
"""

import hashlib
import os
import secrets
import sqlite3
from typing import Optional

from ventilation_company.auth.permissions import Role, has_permission

# Шлях до БД (та сама, що й у config.py)
_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "company.db"
)


def _get_conn() -> sqlite3.Connection:
    """Підключення до БД."""
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_users_table():
    """Створити таблицю users, якщо її ще немає."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'monter',
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT
            )
        """)
        conn.commit()


class User:
    """Проста dataclass-користувач (без SQLAlchemy)."""

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
    """Сервіс автентифікації з хешуванням паролів (sqlite3)."""

    _instance: Optional["AuthService"] = None
    _current_user: Optional[User] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        _ensure_users_table()

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

    def _row_to_user(self, row: sqlite3.Row) -> User:
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            full_name=row["full_name"],
            role=row["role"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            last_login=row["last_login"],
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

        with _get_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if existing:
                raise ValueError(f"Користувач '{username}' вже існує")

            cur = conn.execute(
                """INSERT INTO users (username, password_hash, full_name, role, is_active)
                   VALUES (?, ?, ?, ?, 1)""",
                (username, self._hash_password(password), full_name, role.value),
            )
            conn.commit()
            return self.get_user(cur.lastrowid)

    def get_user(self, user_id: int) -> Optional[User]:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,)
            ).fetchone()
            return self._row_to_user(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[User]:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? AND is_active = 1", (username,)
            ).fetchone()
            return self._row_to_user(row) if row else None

    def list_users(self) -> list[User]:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM users WHERE is_active = 1 ORDER BY id"
            ).fetchall()
            return [self._row_to_user(r) for r in rows]

    def update_user(self, user_id: int, **kwargs) -> bool:
        allowed = {"full_name", "role", "is_active"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if "password" in kwargs:
            fields["password_hash"] = self._hash_password(kwargs["password"])
        if not fields:
            return False

        sets = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [user_id]

        with _get_conn() as conn:
            conn.execute(f"UPDATE users SET {sets} WHERE id = ?", values)
            conn.commit()
            return True

    def delete_user(self, user_id: int) -> bool:
        """Soft-delete."""
        return self.update_user(user_id, is_active=0)

    # ── Автентифікація ──
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Перевірити логін/пароль і повернути користувача."""
        user = self.get_user_by_username(username)
        if user and self._verify_password(password, user.password_hash):
            from datetime import datetime
            with _get_conn() as conn:
                conn.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (datetime.now().isoformat(), user.id),
                )
                conn.commit()
            self._current_user = user
            return user
        return None

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

    # ── Ініціалізація ──
    def ensure_default_users(self):
        """Створити дефолтних користувачів, якщо таблиця порожня."""
        with _get_conn() as conn:
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM users"
            ).fetchone()["cnt"]

        if count == 0:
            self.create_user("admin", "admin123", "Адміністратор", Role.DIRECTOR)
            self.create_user("engineer", "eng123", "Іван Інженер", Role.ENGINEER)
            self.create_user("accountant", "acc123", "Олена Бухгалтер", Role.ACCOUNTANT)
            self.create_user("monter", "mon123", "Петро Монтажник", Role.MONTER)
            print("[AUTH] Створено дефолтних користувачів:")
            print("  admin / admin123      (Директор)")
            print("  engineer / eng123     (Інженер)")
            print("  accountant / acc123   (Бухгалтер)")
            print("  monter / mon123       (Монтажник)")


# ── Глобальний екземпляр ──
auth = AuthService()
