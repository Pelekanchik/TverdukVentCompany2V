"""Модуль автентифікації та авторизації VentCompany."""

from ventilation_company.auth.permissions import (
    ROLE_LABELS,
    ROLE_PERMISSIONS,
    TAB_PERMISSIONS,
    Role,
    get_role_label,
    has_permission,
)
from ventilation_company.auth.service import AuthService, auth

__all__ = [
    "Role",
    "ROLE_PERMISSIONS",
    "ROLE_LABELS",
    "TAB_PERMISSIONS",
    "has_permission",
    "get_role_label",
    "AuthService",
    "auth",
]
