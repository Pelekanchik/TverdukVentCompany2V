"""Система ролей та дозволів VentCompany.

Ролі:
  • director   — повний доступ (все)
  • engineer   — проєкти, вироби, специфікації, розкрій, 3D, аеродинаміка
  • accountant — фінанси, ціни, налаштування, CRM, дашборд
  • monter     — тільки свої проєкти (призначені), специфікації, розкрій
"""

from enum import Enum


class Role(str, Enum):
    DIRECTOR = "director"
    ENGINEER = "engineer"
    ACCOUNTANT = "accountant"
    MONTER = "monter"


# ── Дозволи (permission = "дія_об'єкт") ──
# Формат: <дія>_<об'єкт>
# Дії: view, edit, create, delete, export
# Об'єкти: products, specification, cutting, project_3d, settings,
#          price_list, metal_prices, production, materials,
#          aerodynamics, crm, dashboard, projects, users

ROLE_PERMISSIONS: dict[Role, list[str]] = {
    Role.DIRECTOR: ["*"],  # wildcard — все дозволено

    Role.ENGINEER: [
        # Вироби
        "view_products", "create_products", "edit_products", "delete_products",
        # Специфікація
        "view_specification", "create_specification", "edit_specification", "export_specification",
        # Розкрій
        "view_cutting", "create_cutting", "edit_cutting",
        # 3D
        "view_project_3d", "create_project_3d", "export_project_3d",
        # Проєкти
        "view_projects", "create_projects", "edit_projects",
        # Аеродинаміка
        "view_aerodynamics",
        # Прайс-лист (тільки перегляд)
        "view_price_list",
        # Матеріали (тільки перегляд)
        "view_materials",
        # Виробництво (тільки перегляд)
        "view_production",
        # CRM (тільки перегляд клієнтів)
        "view_crm",
        # Дашборд
        "view_dashboard",
    ],

    Role.ACCOUNTANT: [
        # Фінанси та ціноутворення
        "view_settings", "edit_settings",
        "view_price_list", "edit_price_list", "export_price_list",
        "view_metal_prices", "edit_metal_prices",
        # CRM
        "view_crm", "edit_crm",
        # Дашборд
        "view_dashboard",
        # Виробництво (тільки перегляд для звітів)
        "view_production",
        "view_materials",
        # Проєкти (тільки перегляд фінансової частини)
        "view_projects",
        # Специфікація (перегляд)
        "view_specification",
        # Експорт звітів
        "export_specification", "export_price_list",
    ],

    Role.MONTER: [
        # Тільки свої проєкти (фільтрується в AuthService)
        "view_projects",
        # Специфікація своїх проєктів
        "view_specification",
        # Розкрій своїх проєктів
        "view_cutting",
        # 3D перегляд
        "view_project_3d",
        # Матеріали (тільки перегляд для своїх)
        "view_materials",
        # Виробництво (тільки перегляд для своїх)
        "view_production",
    ],
}


# ── Відображення ролей для GUI ──
ROLE_LABELS: dict[Role, str] = {
    Role.DIRECTOR: "Директор",
    Role.ENGINEER: "Інженер",
    Role.ACCOUNTANT: "Бухгалтер",
    Role.MONTER: "Монтажник",
}


# ── Вкладки та необхідні дозволи ──
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
}


def has_permission(role: Role | str, permission: str) -> bool:
    """Перевірити, чи має роль вказаний дозвіл."""
    if isinstance(role, str):
        role = Role(role)
    perms = ROLE_PERMISSIONS.get(role, [])
    return "*" in perms or permission in perms


def get_role_label(role: Role | str) -> str:
    """Отримати людську назву ролі."""
    if isinstance(role, str):
        role = Role(role)
    return ROLE_LABELS.get(role, role.value)
