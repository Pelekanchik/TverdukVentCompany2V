"""Temporary GUI facade over canonical auth service.

Новий канонічний auth знаходиться у:

- `ventilation_company.auth.service`
- `ventilation_company.auth.permissions`

Цей модуль лишено тільки для зворотної сумісності з PySide6 GUI.
Нові місця в коді мають імпортувати канонічний `auth`, `Role`, `has_permission`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ventilation_company.auth.password_policy import hash_password, verify_password
from ventilation_company.auth.permissions import Role
from ventilation_company.auth.service import auth as canonical_auth

# ── Temporary compatibility mapping for GUI tabs ──
# TODO: migrate GUI to canonical permissions and remove this mapping.
ROLE_PERMISSIONS = {
    "admin": {
        "tabs": "*",
        "edit": True,
        "delete": True,
        "manage_users": True,
    },
    "director": {
        "tabs": "*",
        "edit": True,
        "delete": True,
        "manage_users": True,
    },
    "manager": {
        "tabs": ["products", "specification", "price_list", "clients", "projects"],
        "edit": True,
        "delete": False,
        "manage_users": False,
    },
    "engineer": {
        "tabs": ["products", "specification", "cutting", "freecad", "projects"],
        "edit": True,
        "delete": False,
        "manage_users": False,
    },
    "master": {
        "tabs": ["projects", "specification", "cutting"],
        "edit": True,
        "delete": False,
        "manage_users": False,
    },
    "monter": {
        "tabs": ["projects", "specification", "cutting"],
        "edit": True,
        "delete": False,
        "manage_users": False,
    },
    "accountant": {
        "tabs": ["price_list", "projects", "settings"],
        "edit": True,
        "delete": False,
        "manage_users": False,
    },
    "viewer": {
        "tabs": "*",
        "edit": False,
        "delete": False,
        "manage_users": False,
    },
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
    """Facade: delegates auth to canonical auth service."""

    _current_user: Optional[AuthUser] = None

    @staticmethod
    def _to_gui_user(user) -> Optional[AuthUser]:
        if user is None:
            return None
        return AuthUser(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_active=bool(user.is_active),
        )

    @classmethod
    def hash_password(cls, plain_password: str) -> str:
        return hash_password(plain_password)

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        return verify_password(plain_password, hashed_password)

    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional[AuthUser]:
        user = canonical_auth.authenticate(username, password)
        gui_user = cls._to_gui_user(user)
        cls._current_user = gui_user
        return gui_user

    @classmethod
    def get_current_user(cls) -> Optional[AuthUser]:
        return cls._current_user

    @classmethod
    def logout(cls) -> None:
        canonical_auth.logout()
        cls._current_user = None

    @classmethod
    def require_role(cls, *roles: str) -> bool:
        user = cls._current_user
        if not user:
            return False
        return user.role in roles

    # ── Compatibility CRUD delegated to canonical auth ──
    @classmethod
    def create_user(
        cls, username: str, password: str, full_name: str, role: Role | str = Role.MONTER
    ):
        return canonical_auth.create_user(
            username=username,
            password=password,
            full_name=full_name,
            role=role,
        )

    @classmethod
    def list_users(cls):
        return canonical_auth.list_users()

    @classmethod
    def get_user(cls, user_id: int):
        return canonical_auth.get_user(user_id)

    @classmethod
    def get_user_by_username(cls, username: str):
        return canonical_auth.get_user_by_username(username)

    @classmethod
    def update_user(cls, user_id: int, **kwargs) -> bool:
        return canonical_auth.update_user(user_id, **kwargs)

    @classmethod
    def delete_user(cls, user_id: int) -> bool:
        return canonical_auth.delete_user(user_id)
