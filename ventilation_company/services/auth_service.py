"""Сервіс авторизації та автентифікації.

Ролі:
  admin      — повний доступ, управління користувачами
  manager    — проєкти, клієнти, ціни, прайси
  engineer   — розкрій, специфікації, 3D-моделі, розрахунки
  master     — виробництво, статуси, відвантаження
  accountant — собівартість, прибуток, звіти, зарплати
  viewer     — тільки перегляд (без редагування)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import bcrypt

from ventilation_company.database.db import get_db
from ventilation_company.database.models.user import UserORM

logger = logging.getLogger(__name__)

ROLE_PERMISSIONS = {
    "admin":      {"tabs": "*", "edit": True, "delete": True, "manage_users": True},
    "manager":    {"tabs": ["products", "specification", "price_list", "clients", "projects"], "edit": True, "delete": False, "manage_users": False},
    "engineer":   {"tabs": ["products", "specification", "cutting", "freecad", "projects"], "edit": True, "delete": False, "manage_users": False},
    "master":     {"tabs": ["projects", "specification", "cutting"], "edit": True, "delete": False, "manage_users": False},
    "accountant": {"tabs": ["price_list", "projects", "settings"], "edit": True, "delete": False, "manage_users": False},
    "viewer":     {"tabs": "*", "edit": False, "delete": False, "manage_users": False},
}

VALID_ROLES = set(ROLE_PERMISSIONS.keys())


@dataclass
class AuthUser:
    """Авторизований користувач (датаклас для GUI)."""
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool

    def can_edit(self) -> bool:
        return ROLE_PERMISSIONS.get(self.role, {}).get("edit", False)

    def can_delete(self) -> bool:
        return ROLE_PERMISSIONS.get(self.role, {}).get("delete", False)

    def can_manage_users(self) -> bool:
        return ROLE_PERMISSIONS.get(self.role, {}).get("manage_users", False)

    def allowed_tabs(self):
        return ROLE_PERMISSIONS.get(self.role, {}).get("tabs", [])

    def has_tab_access(self, tab_name: str) -> bool:
        tabs = self.allowed_tabs()
        if tabs == "*":
            return True
        return tab_name in tabs


class AuthService:
    _current_user: Optional[AuthUser] = None

    @classmethod
    def hash_password(cls, plain_password: str) -> str:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )

    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional[AuthUser]:
        with get_db() as session:
            user = session.query(UserORM).filter(
                UserORM.username == username,
                UserORM.is_active == 1
            ).first()

            if not user or not cls.verify_password(password, user.password_hash):
                return None

            user.last_login = datetime.now()
            session.commit()

            auth_user = AuthUser(
                id=user.id,
                username=user.username,
                full_name=user.full_name,
                role=user.role,
                is_active=bool(user.is_active)
            )
            cls._current_user = auth_user
            return auth_user

    @classmethod
    def get_current_user(cls) -> Optional[AuthUser]:
        return cls._current_user

    @classmethod
    def logout(cls) -> None:
        cls._current_user = None

    @classmethod
    def require_role(cls, *roles: str) -> bool:
        user = cls._current_user
        if not user:
            return False
        return user.role in roles
