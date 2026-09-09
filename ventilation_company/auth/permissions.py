"""Система ролей та дозволів VentCompany (оновлена).

Ролі:
  • admin      — повний доступ
  • director   — повний доступ (альтернатива admin)
  • manager    — проєкти, клієнти, ціни, прайси
  • engineer   — розкрій, специфікації, 3D-моделі, розрахунки
  • master     — виробництво, статуси, відвантаження
  • accountant — собівартість, прибуток, звіти, зарплати
  • viewer     — тільки перегляд
  • monter     — монтаж (альтернатива master)
"""

from enum import Enum


class Role(str, Enum):
    DIRECTOR = "director"
    ENGINEER = "engineer"
    ACCOUNTANT = "accountant"
    MONTER = "monter"
    ADMIN = "admin"
    MANAGER = "manager"
    MASTER = "master"
    VIEWER = "viewer"


ROLE_PERMISSIONS: dict[Role, list[str]] = {
    Role.DIRECTOR: ["*"],
    Role.ADMIN: ["*"],

    Role.ENGINEER: [
        "view_products", "create_products", "edit_products", "delete_products",
        "view_specification", "create_specification", "edit_specification", "export_specification",
        "view_cutting", "create_cutting", "edit_cutting",
        "view_project_3d", "create_project_3d", "export_project_3d",
        "view_projects", "create_projects", "edit_projects",
        "view_aerodynamics",
        "view_price_list",
        "view_materials",
        "view_production",
        "view_crm",
        "view_dashboard",
        "view_program_settings",
    ],

    Role.MANAGER: [
        "view_products", "create_products", "edit_products",
        "view_specification", "view_projects", "create_projects", "edit_projects",
        "view_price_list", "edit_price_list", "export_price_list",
        "view_crm", "edit_crm",
        "view_dashboard",
        "view_program_settings",
    ],

    Role.MASTER: [
        "view_projects", "view_specification", "view_cutting",
        "view_materials", "view_production",
        "view_program_settings",
    ],

    Role.ACCOUNTANT: [
        "view_settings", "edit_settings",
        "view_price_list", "edit_price_list", "export_price_list",
        "view_metal_prices", "edit_metal_prices",
        "view_crm", "edit_crm",
        "view_dashboard",
        "view_production",
        "view_materials",
        "view_projects",
        "view_specification",
        "export_specification", "export_price_list",
        "view_program_settings", "edit_program_settings",
    ],

    Role.MONTER: [
        "view_projects",
        "view_specification",
        "view_cutting",
        "view_project_3d",
        "view_materials",
        "view_production",
        "view_program_settings",
    ],

    Role.VIEWER: [
        "view_products", "view_specification", "view_cutting",
        "view_project_3d", "view_projects", "view_price_list",
        "view_materials", "view_production", "view_crm",
        "view_dashboard", "view_program_settings",
    ],
}


ROLE_LABELS: dict[Role, str] = {
    Role.DIRECTOR: "Директор",
    Role.ENGINEER: "Інженер",
    Role.ACCOUNTANT: "Бухгалтер",
    Role.MONTER: "Монтажник",
    Role.ADMIN: "Адміністратор",
    Role.MANAGER: "Менеджер",
    Role.MASTER: "Майстер",
    Role.VIEWER: "Перегляд",
}


TAB_PERMISSIONS: dict[str, list[str]] = {
    "📦 Вироби":       ["view_products"],
    "📋 Специфікація": ["view_specification"],
    "✂️ Розкрій":      ["view_cutting"],
    "🏗️ Проєкти 3D":   ["view_project_3d"],
    "💰 Ціноутворення": ["view_settings"],
    "🏭 Виробництво":  ["view_production"],
    "📦 Матеріали":    ["view_materials"],
    "💨 Аеродинаміка": ["view_aerodynamics"],
    "📊 Дашборд":      ["view_dashboard"],
    "🏷️ Прайс-лист":   ["view_price_list"],
    "👥 CRM":          ["view_crm"],
    "🔧 Ціни на метал": ["view_metal_prices"],
    "⚙️ Налаштування": ["view_program_settings"],
}


def has_permission(role: Role | str, permission: str) -> bool:
    if isinstance(role, str):
        try:
            role = Role(role)
        except ValueError:
            return False
    perms = ROLE_PERMISSIONS.get(role, [])
    return "*" in perms or permission in perms


def get_role_label(role: Role | str) -> str:
    if isinstance(role, str):
        return ROLE_LABELS.get(role, role)
    return ROLE_LABELS.get(role, role.value)
