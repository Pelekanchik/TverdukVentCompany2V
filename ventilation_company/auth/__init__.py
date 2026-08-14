"""Модуль автентифікації та авторизації VentCompany."""

from ventilation_company.auth.permissions import (
    Role,
    ROLE_PERMISSIONS,
    ROLE_LABELS,
    TAB_PERMISSIONS,
    has_permission,
    get_role_label,
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
