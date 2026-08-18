"""Централізовані параметри виробництва (Етап 2).

Завантажує налаштування з data/manufacturing_settings.json (KIM, припуски, ребра)
та data/pricing_settings.json (ціни матеріалів, тарифи робіт).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ventilation_company.utils.logging_config import get_logger

_logger = get_logger("manufacturing_params")

_SETTINGS_PATH = Path(__file__).parent.parent / "data" / "manufacturing_settings.json"
_PRICING_PATH = Path(__file__).parent.parent / "data" / "pricing_settings.json"


# ═══════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════

class ProductCategory(Enum):
    RECT_DUCT = "rect_duct"
    ROUND_DUCT = "round_duct"
    RECT_ELBOW = "rect_elbow"
    ROUND_ELBOW = "round_elbow"
    RECT_FLANGE = "rect_flange"
    ROUND_FLANGE = "round_flange"
    RECT_TEE = "rect_tee"
    ROUND_TEE = "round_tee"
    RECT_TRANSITION = "rect_transition"
    ROUND_TRANSITION = "round_transition"
    RECT_CAP = "rect_cap"
    ROUND_CAP = "round_cap"
    FLEXIBLE = "flexible"


# ═══════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True)
class StiffenerRule:
    enabled: bool = False
    threshold_mm: float = 0.0
    count_per_side: int = 0
    profile_mm: float = 0.0


@dataclass(frozen=True)
class ManufacturingParams:
    """Параметри виробництва для категорії виробу."""

    kim: float = 1.0
    seam_allowance_mm: float = 20.0
    cut_allowance_mm: float = 5.0
    bend_allowance_mm: float = 3.0
    helix_angle_deg: float = 0.0
    stiffener_rule: StiffenerRule = StiffenerRule()

    def effective_kim(self) -> float:
        """Коефіцієнт використання матеріалу (KIM).

        Повертає 0…1.  КIM=0.85 означає, що на 1 м² заготовки
        потрібно 1/0.85 = 1.176 м² листа.
        """
        if self.kim <= 0 or self.kim > 1.0:
            return 1.0
        return self.kim


# ═══════════════════════════════════════════════════════════
# ЗАВАНТАЖЕННЯ НАЛАШТУВАНЬ
# ═══════════════════════════════════════════════════════════

_settings_cache: dict[str, Any] | None = None
_pricing_cache: dict[str, Any] | None = None


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        _logger.error("Не вдалося завантажити %s: %s", path, exc)
        return {}


def _settings() -> dict[str, Any]:
    global _settings_cache
    if _settings_cache is None:
        raw = _load_json(_SETTINGS_PATH)
        _settings_cache = raw.get("categories", {})
    return _settings_cache


def _pricing() -> dict[str, Any]:
    global _pricing_cache
    if _pricing_cache is None:
        _pricing_cache = _load_json(_PRICING_PATH)
    return _pricing_cache


def clear_cache() -> None:
    """Скинути кеш налаштувань (для тестів / після оновлення JSON)."""
    global _settings_cache, _pricing_cache
    _settings_cache = None
    _pricing_cache = None


def _build_params(raw: dict[str, Any]) -> ManufacturingParams:
    stiff = raw.get("stiffener_rule", {})
    return ManufacturingParams(
        kim=raw.get("kim", 1.0),
        seam_allowance_mm=raw.get("seam_allowance_mm", 20.0),
        cut_allowance_mm=raw.get("cut_allowance_mm", 5.0),
        bend_allowance_mm=raw.get("bend_allowance_mm", 3.0),
        helix_angle_deg=raw.get("helix_angle_deg", 0.0),
        stiffener_rule=StiffenerRule(
            enabled=stiff.get("enabled", False),
            threshold_mm=stiff.get("threshold_mm", 0.0),
            count_per_side=stiff.get("count_per_side", 0),
            profile_mm=stiff.get("profile_mm", 0.0),
        ),
    )


def get_params(category: ProductCategory) -> ManufacturingParams:
    """Отримати параметри виробництва для категорії."""
    raw = _settings().get(category.value, {})
    return _build_params(raw)


def get_all_params() -> dict[ProductCategory, ManufacturingParams]:
    """Отримати всі параметри виробництва."""
    return {cat: get_params(cat) for cat in ProductCategory}


# ═══════════════════════════════════════════════════════════
# ЦІНИ / ТАРИФИ (з pricing_settings.json)
# ═══════════════════════════════════════════════════════════

def get_material_price(material_name: str, thickness_mm: float) -> float:
    """Ціна матеріалу за м² для заданої товщини.

    Args:
        material_name: "оцинкована сталь", "нержавіюча сталь", "алюміній"
        thickness_mm: 0.5, 0.7, 0.9, 1.0, 1.2, 1.5, 2.0

    Returns:
        Ціна за м² грн (або 0.0 якщо не знайдено).
    """
    pricing = _pricing()
    materials = pricing.get("material_prices", {})
    prices = materials.get(material_name, {})
    # prices — dict {str(thickness): price}
    key = str(thickness_mm)
    if key in prices:
        return float(prices[key])
    # fallback до найближчої товщини
    try:
        thicknesses = sorted(float(k) for k in prices.keys())
        if not thicknesses:
            return 0.0
        closest = min(thicknesses, key=lambda t: abs(t - thickness_mm))
        return float(prices[str(closest)])
    except Exception:
        _logger.warning("Не знайдено ціну для %s товщ %.1f", material_name, thickness_mm)
        return 0.0


def get_labor_rate(product_type: str) -> dict[str, float]:
    """Отримати тариф роботи для типу виробу.

    Returns:
        {"rate_per_m2": float, "difficulty_percent": float}
    """
    pricing = _pricing()
    labor = pricing.get("labor_rates", {})
    pt = product_type.lower().strip()
    data = labor.get(pt, {"rate_per_m2": 100.0, "difficulty_percent": 0.0})
    return {
        "rate_per_m2": float(data.get("rate_per_m2", 100.0)),
        "difficulty_percent": float(data.get("difficulty_percent", 0.0)),
    }


# ═══════════════════════════════════════════════════════════
# УТИЛІТИ
# ═══════════════════════════════════════════════════════════

def seam_allowance_for_thickness(
    base_mm: float, thickness_mm: float, factor: float = 20.0
) -> float:
    """Розрахунок припуску на замок з урахуванням товщини.

    При товщині > 1.0 мм припуск збільшується.
    """
    if thickness_mm > 1.0:
        return base_mm + (thickness_mm - 1.0) * factor
    return base_mm


# ═══════════════════════════════════════════════════════════
# GUI-READY API
# ═══════════════════════════════════════════════════════════

def update_category(category: ProductCategory, params: ManufacturingParams) -> None:
    """Оновити параметри категорії в JSON-файлі (для GUI-налаштувань)."""
    settings = _load_json(_SETTINGS_PATH)
    if "categories" not in settings:
        settings["categories"] = {}
    settings["categories"][category.value] = {
        "kim": params.kim,
        "seam_allowance_mm": params.seam_allowance_mm,
        "cut_allowance_mm": params.cut_allowance_mm,
        "bend_allowance_mm": params.bend_allowance_mm,
        "helix_angle_deg": params.helix_angle_deg,
        "stiffener_rule": {
            "enabled": params.stiffener_rule.enabled,
            "threshold_mm": params.stiffener_rule.threshold_mm,
            "count_per_side": params.stiffener_rule.count_per_side,
            "profile_mm": params.stiffener_rule.profile_mm,
        },
    }
    try:
        with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        clear_cache()
        _logger.info("Оновлено параметри для %s", category.value)
    except OSError as exc:
        _logger.error("Не вдалося зберегти %s: %s", _SETTINGS_PATH, exc)


def validate_settings() -> list[str]:
    """Валідація налаштувань — повертає список помилок (порожній = ОК)."""
    errors: list[str] = []
    for cat in ProductCategory:
        p = get_params(cat)
        if p.kim <= 0 or p.kim > 1.0:
            errors.append(f"{cat.value}: KIM поза діапазоном (0…1]: {p.kim}")
        if p.seam_allowance_mm < 0:
            errors.append(f"{cat.value}: seam_allowance_mm < 0")
        if p.cut_allowance_mm < 0:
            errors.append(f"{cat.value}: cut_allowance_mm < 0")
        if p.bend_allowance_mm < 0:
            errors.append(f"{cat.value}: bend_allowance_mm < 0")
    return errors
