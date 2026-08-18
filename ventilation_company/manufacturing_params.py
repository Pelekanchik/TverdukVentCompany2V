"""Централізовані виробничі параметри для розрахунку площ заготовок — Етап 2.

Завантажує налаштування з data/manufacturing_settings.json.
Якщо файл відсутній — створює його з дефолтів.
Підтримує збереження, валідацію, GUI-ready методи.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# Шлях до файлу налаштувань
_SETTINGS_PATH = Path(__file__).parent.parent / "data" / "manufacturing_settings.json"


class ProductCategory(str, Enum):
    """Категорія виробу для визначення KIM та припусків."""

    RECT_DUCT = "rect_duct"
    ROUND_DUCT = "round_duct"
    RECT_ELBOW = "rect_elbow"
    ROUND_ELBOW = "round_elbow"
    RECT_TEE = "rect_tee"
    ROUND_TEE = "round_tee"
    RECT_TRANSITION = "rect_transition"
    ROUND_TRANSITION = "round_transition"
    RECT_FLANGE = "rect_flange"
    ROUND_FLANGE = "round_flange"
    RECT_CAP = "rect_cap"
    ROUND_CAP = "round_cap"
    FLEXIBLE = "flexible"


@dataclass(frozen=True)
class StiffenerRule:
    """Правило для ребер жорсткості."""

    enabled: bool = False
    threshold_mm: float = 500.0
    count_per_side: int = 1
    profile_mm: float = 30.0

    @classmethod
    def from_dict(cls, data: dict) -> "StiffenerRule":
        return cls(
            enabled=data.get("enabled", False),
            threshold_mm=data.get("threshold_mm", 500.0),
            count_per_side=data.get("count_per_side", 1),
            profile_mm=data.get("profile_mm", 30.0),
        )

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "threshold_mm": self.threshold_mm,
            "count_per_side": self.count_per_side,
            "profile_mm": self.profile_mm,
        }


@dataclass(frozen=True)
class ManufacturingParams:
    """Виробничі параметри для конкретного типу виробу.

    Attributes:
        name: Назва категорії (англ).
        name_uk: Назва категорії (укр).
        seam_allowance_mm: Припуск на замок / з'єднання, мм.
        cut_allowance_mm: Припуск на різ з кожного торця, мм.
        bend_allowance_mm: Додатковий припуск на згин, мм.
        stiffener_rule: Правило для ребер жорсткості.
        kim: Коефіцієнт використання матеріалу (0..1).
        helix_angle_deg: Кут навивки для спіральних труб, градуси.
        waste_percent: Додаткові відходи (логістика, брак), %.
    """

    name: str = ""
    name_uk: str = ""
    seam_allowance_mm: float = 0.0
    cut_allowance_mm: float = 2.0
    bend_allowance_mm: float = 0.0
    stiffener_rule: StiffenerRule = field(default_factory=lambda: StiffenerRule(enabled=False))
    kim: float = 0.85
    helix_angle_deg: float = 0.0
    waste_percent: float = 2.0

    def effective_kim(self) -> float:
        """KIM з урахуванням додаткових відходів."""
        return self.kim * (1 - self.waste_percent / 100)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "name_uk": self.name_uk,
            "seam_allowance_mm": self.seam_allowance_mm,
            "cut_allowance_mm": self.cut_allowance_mm,
            "bend_allowance_mm": self.bend_allowance_mm,
            "stiffener_rule": self.stiffener_rule.to_dict(),
            "kim": self.kim,
            "helix_angle_deg": self.helix_angle_deg,
            "waste_percent": self.waste_percent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ManufacturingParams":
        return cls(
            name=data.get("name", ""),
            name_uk=data.get("name_uk", ""),
            seam_allowance_mm=data.get("seam_allowance_mm", 0.0),
            cut_allowance_mm=data.get("cut_allowance_mm", 2.0),
            bend_allowance_mm=data.get("bend_allowance_mm", 0.0),
            stiffener_rule=StiffenerRule.from_dict(data.get("stiffener_rule", {})),
            kim=data.get("kim", 0.85),
            helix_angle_deg=data.get("helix_angle_deg", 0.0),
            waste_percent=data.get("waste_percent", 2.0),
        )


# ═══════════════════════════════════════════════════════════
# ЗАВАНТАЖЕННЯ / ЗБЕРЕЖЕННЯ JSON
# ═══════════════════════════════════════════════════════════

_settings_cache: dict[str, Any] | None = None


def _default_settings() -> dict:
    """Дефолтні налаштування (якщо JSON-файл відсутній)."""
    return {
        "_description": "Виробничі параметри для розрахунку площ заготовок.",
        "_version": "2.1.0",
        "material_densities_kg_m3": {
            "сталь_оцинкована": 7850,
            "сталь_нержавіюча": 7900,
            "алюміній": 2700,
        },
        "seam_allowance_formula": {"base_mm": 10.0, "factor_per_mm_thickness": 20.0},
        "categories": {
            cat.value: ManufacturingParams(
                name=cat.value.replace("_", " ").title(),
                name_uk=_uk_name(cat),
            ).to_dict()
            for cat in ProductCategory
        },
    }


def _uk_name(cat: ProductCategory) -> str:
    mapping = {
        ProductCategory.RECT_DUCT: "Прямокутний повітропровід",
        ProductCategory.ROUND_DUCT: "Круглий повітропровід",
        ProductCategory.RECT_ELBOW: "Відвід прямокутний",
        ProductCategory.ROUND_ELBOW: "Відвід круглий",
        ProductCategory.RECT_TEE: "Трійник прямокутний",
        ProductCategory.ROUND_TEE: "Трійник круглий",
        ProductCategory.RECT_TRANSITION: "Перехід прямокутний",
        ProductCategory.ROUND_TRANSITION: "Перехід круглий",
        ProductCategory.RECT_FLANGE: "Фланець прямокутний",
        ProductCategory.ROUND_FLANGE: "Фланець круглий",
        ProductCategory.RECT_CAP: "Заглушка прямокутна",
        ProductCategory.ROUND_CAP: "Заглушка кругла",
        ProductCategory.FLEXIBLE: "Гнучка вставка",
    }
    return mapping.get(cat, cat.value)


def load_settings(force_reload: bool = False) -> dict:
    """Завантажити налаштування з JSON-файлу.

    Args:
        force_reload: Якщо True — перечитати файл з диска.

    Returns:
        Словник із повними налаштуваннями.
    """
    global _settings_cache
    if _settings_cache is not None and not force_reload:
        return _settings_cache

    if _SETTINGS_PATH.exists():
        try:
            with open(_SETTINGS_PATH, encoding="utf-8") as f:
                data = json.load(f)
            # Валідація: чи є ключ 'categories'
            if "categories" not in data:
                data = _default_settings()
                save_settings(data)
            _settings_cache = data
            return data
        except (json.JSONDecodeError, OSError):
            pass

    # Файл відсутній або пошкоджений — створюємо дефолт
    data = _default_settings()
    save_settings(data)
    _settings_cache = data
    return data


def save_settings(data: dict | None = None) -> None:
    """Зберегти налаштування у JSON-файл.

    Args:
        data: Словник налаштувань. Якщо None — зберігає кеш.
    """
    global _settings_cache
    if data is None:
        data = _settings_cache if _settings_cache is not None else _default_settings()
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _settings_cache = data


def get_params(category: ProductCategory | str) -> ManufacturingParams:
    """Отримати виробничі параметри за категорією.

    Args:
        category: Категорія виробу (enum або строка).

    Returns:
        ManufacturingParams для даної категорії.
    """
    settings = load_settings()
    cat_key = category.value if isinstance(category, ProductCategory) else category
    cat_data = settings.get("categories", {}).get(cat_key, {})
    return ManufacturingParams.from_dict(cat_data)


def get_all_params() -> dict[ProductCategory, ManufacturingParams]:
    """Отримати всі параметри для всіх категорій."""
    settings = load_settings()
    cats = settings.get("categories", {})
    result = {}
    for cat in ProductCategory:
        result[cat] = ManufacturingParams.from_dict(cats.get(cat.value, {}))
    return result


def update_category(category: ProductCategory | str, **kwargs) -> ManufacturingParams:
    """Оновити параметри категорії та зберегти у файл.

    GUI-ready: приймає категорію і named-аргументи для оновлення.

    Args:
        category: Категорія для оновлення.
        **kwargs: Поля для оновлення (kim, seam_allowance_mm тощо).

    Returns:
        Оновлені ManufacturingParams.
    """
    settings = load_settings()
    cat_key = category.value if isinstance(category, ProductCategory) else category
    cats = settings.setdefault("categories", {})
    current = ManufacturingParams.from_dict(cats.get(cat_key, {}))

    # Створюємо новий об'єкт з оновленими полями
    current_dict = current.to_dict()
    current_dict.update(kwargs)
    updated = ManufacturingParams.from_dict(current_dict)

    cats[cat_key] = updated.to_dict()
    save_settings(settings)
    return updated


def get_setting(key: str, default: Any = None) -> Any:
    """Отримати глобальне налаштування (наприклад, 'material_densities_kg_m3')."""
    settings = load_settings()
    return settings.get(key, default)


def set_setting(key: str, value: Any) -> None:
    """Встановити глобальне налаштування та зберегти."""
    settings = load_settings()
    settings[key] = value
    save_settings(settings)


def reset_to_defaults() -> None:
    """Скинути всі налаштування до дефолтів."""
    data = _default_settings()
    save_settings(data)


def validate_settings() -> list[str]:
    """Валідувати поточні налаштування.

    Returns:
        Список помилок (порожній, якщо все ок).
    """
    errors = []
    settings = load_settings()
    cats = settings.get("categories", {})

    for cat in ProductCategory:
        data = cats.get(cat.value, {})
        p = ManufacturingParams.from_dict(data)

        if not 0 < p.kim <= 1:
            errors.append(f"{cat.value}: KIM має бути в діапазоні (0, 1], отримано {p.kim}")
        if p.seam_allowance_mm < 0:
            errors.append(f"{cat.value}: seam_allowance_mm не може бути від'ємним")
        if p.cut_allowance_mm < 0:
            errors.append(f"{cat.value}: cut_allowance_mm не може бути від'ємним")
        if p.waste_percent < 0 or p.waste_percent > 50:
            errors.append(f"{cat.value}: waste_percent має бути в [0, 50]")

    return errors


# ═══════════════════════════════════════════════════════════
# ХЕЛПЕРИ (залишено для зворотної сумісності)
# ═══════════════════════════════════════════════════════════

def seam_allowance_for_thickness(base_mm: float, thickness_mm: float, factor: float = 20.0) -> float:
    """Динамічний припуск на замок залежно від товщини.

    Тепер використовує формулу з manufacturing_settings.json, але
    зберігає зворотну сумісність для явних викликів.
    """
    formula = get_setting("seam_allowance_formula", {})
    if formula:
        base = formula.get("base_mm", base_mm)
        f = formula.get("factor_per_mm_thickness", factor)
        return base + f * thickness_mm
    return base_mm + factor * thickness_mm


# ═══════════════════════════════════════════════════════════
# ЦІНИ МАТЕРІАЛІВ З pricing_settings.json
# ═══════════════════════════════════════════════════════════

_PRICING_SETTINGS_PATH = Path(__file__).parent.parent / "data" / "pricing_settings.json"


def _load_pricing_settings() -> dict[str, Any]:
    """Завантажити pricing_settings.json."""
    try:
        with open(_PRICING_SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_pricing_cache: dict[str, Any] | None = None


def get_material_price(material_name: str, thickness_mm: float) -> float:
    """Отримати ціну матеріалу з pricing_settings.json.

    Args:
        material_name: "оцинкована сталь", "нержавіюча сталь", "алюміній".
        thickness_mm: Товщина, мм (0.5, 0.7, ...).

    Returns:
        Ціна за м², грн. Якщо не знайдено — повертає 0.0.
    """
    global _pricing_cache
    if _pricing_cache is None:
        _pricing_cache = _load_pricing_settings()

    prices = _pricing_cache.get("material_prices", {})
    material_prices = prices.get(material_name)
    if not material_prices:
        return 0.0

    # Шукаємо найближчу товщину
    thickness_key = str(thickness_mm)
    if thickness_key in material_prices:
        return float(material_prices[thickness_key])

    # Інтерполяція за найближчими значеннями
    available = sorted(
        [(float(k), float(v)) for k, v in material_prices.items() if k.replace(".", "").isdigit()]
    )
    if not available:
        return 0.0

    if thickness_mm <= available[0][0]:
        return available[0][1]
    if thickness_mm >= available[-1][0]:
        return available[-1][1]

    for i in range(len(available) - 1):
        t1, p1 = available[i]
        t2, p2 = available[i + 1]
        if t1 <= thickness_mm <= t2:
            ratio = (thickness_mm - t1) / (t2 - t1)
            return p1 + ratio * (p2 - p1)

    return available[-1][1]


def get_labor_rate(product_type_name: str) -> dict[str, float]:
    """Отримати тариф роботи з pricing_settings.json."""
    global _pricing_cache
    if _pricing_cache is None:
        _pricing_cache = _load_pricing_settings()

    labor = _pricing_cache.get("labor_rates", {})
    return labor.get(product_type_name, {"rate_per_m2": 100.0, "difficulty_percent": 0.0})


def clear_pricing_cache() -> None:
    """Скинути кеш pricing_settings."""
    global _pricing_cache
    _pricing_cache = None


def clear_settings_cache() -> None:
    """Скинути кеш manufacturing_settings."""
    global _settings_cache
    _settings_cache = None
