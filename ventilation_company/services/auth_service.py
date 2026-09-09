"""Temporary GUI facade over canonical auth service.

Canonical auth:
- ventilation_company.auth.service.auth
- ventilation_company.auth.permissions
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ventilation_company.auth.password_policy import hash_password, verify_password
from ventilation_company.auth.permissions import (
    TAB_PERMISSIONS,
    Role,
    can_manage_users,
    has_permission,
    role_permissions,
)
from ventilation_company.auth.service import auth as canonical_auth

VALID_ROLES = [role.value for role in Role]


@dataclass
class AuthUser:
    """Авторизований користувач (датаклас для GUI)."""

    id: int
    username: str
    full_name: str
    role: str
    is_active: bool

    def can_edit(self) -> bool:
        return any(p.value.endswith(".edit") for p in role_permissions(self.role))

    def can_delete(self) -> bool:
        return any(p.value.endswith(".delete") for p in role_permissions(self.role))

    def can_manage_users(self) -> bool:
        return can_manage_users(self.role)

    def allowed_tabs(self) -> list[str]:
        return [
            tab
            for tab, permission in TAB_PERMISSIONS.items()
            if has_permission(self.role, permission)
        ]

    def has_tab_access(self, tab_name: str) -> bool:
        return has_permission(self.role, TAB_PERMISSIONS.get(tab_name, ""))


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

    @classmethod
    def create_user(
        cls, username: str, password: str, full_name: str, role: Role | str = Role.MONTER
    ):
        return canonical_auth.create_user(
            username=username, password=password, full_name=full_name, role=role
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
