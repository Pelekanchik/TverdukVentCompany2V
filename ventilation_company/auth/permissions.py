"""RBAC permissions для VentCompany."""

from enum import Enum


class Permission(str, Enum):
    # Проєкти
    PROJECTS_VIEW = "projects.view"
    PROJECTS_EDIT = "projects.edit"
    PROJECTS_DELETE = "projects.delete"

    # Специфікація / виробництво
    SPEC_VIEW = "specification.view"
    SPEC_EDIT = "specification.edit"
    SPEC_DELETE = "specification.delete"
    PRODUCTION_VIEW = "production.view"
    PRODUCTION_EDIT = "production.edit"

    # Прайс-лист
    PRICE_LIST_VIEW = "price_list.view"
    PRICE_LIST_EDIT = "price_list.edit"
    PRICE_LIST_DELETE = "price_list.delete"

    # CRM
    CRM_VIEW = "crm.view"
    CRM_EDIT = "crm.edit"
    CRM_DELETE = "crm.delete"

    # Налаштування
    SETTINGS_VIEW = "settings.view"
    SETTINGS_EDIT = "settings.edit"

    # Адміністрування
    ADMIN_USERS = "admin.users"
    ADMIN_ROLES = "admin.roles"
    ADMIN_BACKUP = "admin.backup"
    ADMIN_AUDIT = "admin.audit"

    # Продукти
    PRODUCTS_VIEW = "products.view"
    PRODUCTS_EDIT = "products.edit"
    PRODUCTS_DELETE = "products.delete"

    # Документи
    DOCUMENTS_VIEW = "documents.view"
    DOCUMENTS_EDIT = "documents.edit"
    DOCUMENTS_DELETE = "documents.delete"


class Role(str, Enum):
    ADMIN = "admin"
    DIRECTOR = "director"
    MANAGER = "manager"
    ENGINEER = "engineer"
    MASTER = "master"
    ACCOUNTANT = "accountant"
    VIEWER = "viewer"
    MONTER = "monter"


ROLE_LABELS = {
    Role.ADMIN: "Адміністратор",
    Role.DIRECTOR: "Директор",
    Role.MANAGER: "Менеджер",
    Role.ENGINEER: "Інженер",
    Role.MASTER: "Майстер",
    Role.ACCOUNTANT: "Бухгалтер",
    Role.VIEWER: "Тільки перегляд",
    Role.MONTER: "Монтажник",
}

ROLE_PERMISSIONS = {
    Role.ADMIN: set(Permission),
    Role.DIRECTOR: set(Permission),
    Role.MANAGER: {
        Permission.PROJECTS_VIEW,
        Permission.PROJECTS_EDIT,
        Permission.CRM_VIEW,
        Permission.CRM_EDIT,
        Permission.SPEC_VIEW,
        Permission.SPEC_EDIT,
        Permission.PRODUCTS_VIEW,
        Permission.PRODUCTS_EDIT,
        Permission.PRICE_LIST_VIEW,
        Permission.PRICE_LIST_EDIT,
    },
    Role.ENGINEER: {
        Permission.PROJECTS_VIEW,
        Permission.PROJECTS_EDIT,
        Permission.SPEC_VIEW,
        Permission.SPEC_EDIT,
        Permission.PRODUCTION_VIEW,
        Permission.PRODUCTION_EDIT,
        Permission.PRODUCTS_VIEW,
        Permission.PRODUCTS_EDIT,
        Permission.SETTINGS_VIEW,
    },
    Role.MASTER: {
        Permission.PROJECTS_VIEW,
        Permission.SPEC_VIEW,
        Permission.SPEC_EDIT,
        Permission.PRODUCTION_VIEW,
        Permission.PRODUCTION_EDIT,
    },
    Role.ACCOUNTANT: {
        Permission.PROJECTS_VIEW,
        Permission.CRM_VIEW,
        Permission.PRICE_LIST_VIEW,
        Permission.CRM_EDIT,
        Permission.PRICE_LIST_EDIT,
        Permission.PROJECTS_EDIT,
    },
    Role.VIEWER: {
        Permission.SPEC_VIEW,
        Permission.PRODUCTION_VIEW,
        Permission.PRICE_LIST_VIEW,
        Permission.CRM_VIEW,
        Permission.SETTINGS_VIEW,
        Permission.ADMIN_VIEW if hasattr(Permission, "ADMIN_VIEW") else Permission.SETTINGS_VIEW,
        Permission.PRODUCTS_VIEW,
        Permission.PROJECTS_VIEW,
        Permission.DOCUMENTS_VIEW,
    },
    Role.MONTER: {
        Permission.PROJECTS_VIEW,
        Permission.SPEC_VIEW,
        Permission.PRODUCTION_VIEW,
    },
}


def role_permissions(role: Role | str) -> set[Permission]:
    try:
        role = Role(role)
    except ValueError:
        return set()
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: Role | str, permission: Permission | str) -> bool:
    if isinstance(permission, str):
        try:
            permission = Permission(permission)
        except ValueError:
            return False
    return permission in role_permissions(role)


def is_admin(role: Role | str) -> bool:
    try:
        return Role(role) in {Role.ADMIN, Role.DIRECTOR}
    except ValueError:
        return False


def can_manage_users(role: Role | str) -> bool:
    return is_admin(role)
