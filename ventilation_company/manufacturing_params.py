"""Централізовані виробничі параметри для розрахунку площ заготовок.

Етап 1: Базові припуски, KIM (коефіцієнти використання матеріалу) та
технологічні константи для всіх типів виробів вентиляції.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class ProductCategory(str, Enum):
    """Категорія виробу для визначення KIM та припусків."""

    RECT_DUCT = "rect_duct"           # Прямокутний повітропровід
    ROUND_DUCT = "round_duct"         # Круглий повітропровід
    RECT_ELBOW = "rect_elbow"         # Прямокутне коліно
    ROUND_ELBOW = "round_elbow"       # Кругле коліно
    RECT_TEE = "rect_tee"             # Прямокутний трійник
    ROUND_TEE = "round_tee"           # Круглий трійник
    RECT_TRANSITION = "rect_transition"   # Прямокутний перехід
    ROUND_TRANSITION = "round_transition" # Круглий перехід
    RECT_FLANGE = "rect_flange"       # Прямокутний фланець
    ROUND_FLANGE = "round_flange"     # Круглий фланець
    RECT_CAP = "rect_cap"             # Прямокутна заглушка
    ROUND_CAP = "round_cap"           # Кругла заглушка
    FLEXIBLE = "flexible"             # Гнучка вставка


@dataclass(frozen=True)
class ManufacturingParams:
    """Виробничі параметри для конкретного типу виробу.

    Attributes:
        seam_allowance_mm: Припуск на замок / з'єднання, мм.
            Для прямокутних — залежить від товщини (подвійний фальц).
            Для круглих спіральних — 0 (немає шва).
            Для круглих замкових — фіксований.
        cut_allowance_mm: Припуск на різ з кожного торця, мм.
        bend_allowance_mm: Додатковий припуск на згин (к-т розтягу), мм.
        stiffener_rule: Правило для ребер жорсткості.
            None — не потрібні.
            (side_mm, count_per_side, profile_mm) — якщо сторона > side_mm,
            додати count_per_side ребер профілем profile_mm.
        kim: Коефіцієнт використання матеріалу (0..1).
            Прямі труби ~0.88-0.92, фасонні ~0.55-0.75.
        helix_angle_deg: Кут навивки для спіральних труб, градуси.
            0 — не спіральна.
        waste_percent: Додаткові відходи (логістика, брак), %.
    """

    seam_allowance_mm: float = 0.0
    cut_allowance_mm: float = 2.0
    bend_allowance_mm: float = 0.0
    stiffener_rule: tuple[float, int, float] | None = None
    kim: float = 0.85
    helix_angle_deg: float = 0.0
    waste_percent: float = 2.0

    def effective_kim(self) -> float:
        """KIM з урахуванням додаткових відходів."""
        return self.kim * (1 - self.waste_percent / 100)


# ═══════════════════════════════════════════════════════════
# БАЗОВІ ПАРАМЕТРИ ЗА КАТЕГОРІЯМИ
# ═══════════════════════════════════════════════════════════

_DEFAULT_PARAMS: dict[ProductCategory, ManufacturingParams] = {
    # ── Прямокутний повітропровід ──
    # Замок: подвійний фальц ~15 мм + 20×товщина (стиснення металу)
    # KIM: 0.88 — прямі розкрої, мало відходів
    ProductCategory.RECT_DUCT: ManufacturingParams(
        seam_allowance_mm=15.0,
        cut_allowance_mm=2.0,
        bend_allowance_mm=0.0,
        stiffener_rule=(500.0, 1, 30.0),   # >500 мм → 1 ребро, профіль 30 мм
        kim=0.88,
        helix_angle_deg=0.0,
        waste_percent=2.0,
    ),

    # ── Круглий повітропровід (спірально-навивний) ──
    # Спіральна труба — без поздовжнього шва, KIM найвищий
    ProductCategory.ROUND_DUCT: ManufacturingParams(
        seam_allowance_mm=0.0,
        cut_allowance_mm=5.0,     # Торці обробляються
        bend_allowance_mm=0.0,
        stiffener_rule=(630.0, 1, 25.0),  # >630 мм → ребро жорсткості
        kim=0.92,
        helix_angle_deg=4.0,      # Стандартний кут навивки 3-5°
        waste_percent=1.5,
    ),

    # ── Прямокутне коліно (відвід) ──
    # Сегментне коліно — багато розрізів, KIM низький
    ProductCategory.RECT_ELBOW: ManufacturingParams(
        seam_allowance_mm=20.0,
        cut_allowance_mm=2.0,
        bend_allowance_mm=3.0,    # Корекція на згин (розтяг зовні, стиск всередині)
        stiffener_rule=None,
        kim=0.68,
        helix_angle_deg=0.0,
        waste_percent=4.0,
    ),

    # ── Кругле коліно (гнуте) ──
    # Гнуття на роликах — високі відходи на випробування радіуса
    ProductCategory.ROUND_ELBOW: ManufacturingParams(
        seam_allowance_mm=0.0,
        cut_allowance_mm=2.0,
        bend_allowance_mm=2.5,
        stiffener_rule=None,
        kim=0.72,
        helix_angle_deg=0.0,
        waste_percent=3.0,
    ),

    # ── Прямокутний трійник ──
    # Врізка, розкрій гілки — найбільші відходи
    ProductCategory.RECT_TEE: ManufacturingParams(
        seam_allowance_mm=25.0,
        cut_allowance_mm=2.0,
        bend_allowance_mm=3.0,
        stiffener_rule=None,
        kim=0.62,
        helix_angle_deg=0.0,
        waste_percent=5.0,
    ),

    # ── Круглий трійник ──
    ProductCategory.ROUND_TEE: ManufacturingParams(
        seam_allowance_mm=0.0,
        cut_allowance_mm=2.0,
        bend_allowance_mm=2.0,
        stiffener_rule=None,
        kim=0.65,
        helix_angle_deg=0.0,
        waste_percent=4.0,
    ),

    # ── Прямокутний перехід ──
    ProductCategory.RECT_TRANSITION: ManufacturingParams(
        seam_allowance_mm=20.0,
        cut_allowance_mm=2.0,
        bend_allowance_mm=2.0,
        stiffener_rule=None,
        kim=0.70,
        helix_angle_deg=0.0,
        waste_percent=3.0,
    ),

    # ── Круглий перехід (конус) ──
    ProductCategory.ROUND_TRANSITION: ManufacturingParams(
        seam_allowance_mm=0.0,
        cut_allowance_mm=2.0,
        bend_allowance_mm=1.5,
        stiffener_rule=None,
        kim=0.73,
        helix_angle_deg=0.0,
        waste_percent=3.0,
    ),

    # ── Фланці ──
    ProductCategory.RECT_FLANGE: ManufacturingParams(
        seam_allowance_mm=10.0,
        cut_allowance_mm=1.0,
        bend_allowance_mm=0.0,
        stiffener_rule=None,
        kim=0.78,
        helix_angle_deg=0.0,
        waste_percent=2.0,
    ),
    ProductCategory.ROUND_FLANGE: ManufacturingParams(
        seam_allowance_mm=10.0,
        cut_allowance_mm=1.0,
        bend_allowance_mm=0.0,
        stiffener_rule=None,
        kim=0.80,
        helix_angle_deg=0.0,
        waste_percent=2.0,
    ),

    # ── Заглушки ──
    ProductCategory.RECT_CAP: ManufacturingParams(
        seam_allowance_mm=15.0,
        cut_allowance_mm=1.0,
        bend_allowance_mm=0.0,
        stiffener_rule=None,
        kim=0.82,
        helix_angle_deg=0.0,
        waste_percent=2.0,
    ),
    ProductCategory.ROUND_CAP: ManufacturingParams(
        seam_allowance_mm=10.0,
        cut_allowance_mm=1.0,
        bend_allowance_mm=0.0,
        stiffener_rule=None,
        kim=0.85,
        helix_angle_deg=0.0,
        waste_percent=2.0,
    ),

    # ── Гнучка вставка ──
    ProductCategory.FLEXIBLE: ManufacturingParams(
        seam_allowance_mm=0.0,
        cut_allowance_mm=5.0,
        bend_allowance_mm=0.0,
        stiffener_rule=None,
        kim=0.95,
        helix_angle_deg=0.0,
        waste_percent=1.0,
    ),
}


# ═══════════════════════════════════════════════════════════
# ПУБЛІЧНИЙ API
# ═══════════════════════════════════════════════════════════

def get_params(category: ProductCategory | str) -> ManufacturingParams:
    """Отримати виробничі параметри за категорією.

    Args:
        category: Категорія виробу (enum або строка).

    Returns:
        ManufacturingParams для даної категорії.
        Якщо категорія невідома — повертає дефолтні параметри.
    """
    if isinstance(category, str):
        try:
            category = ProductCategory(category)
        except ValueError:
            return ManufacturingParams()  # дефолт
    return _DEFAULT_PARAMS.get(category, ManufacturingParams())


def seam_allowance_for_thickness(
    base_mm: float, thickness_mm: float, factor: float = 20.0
) -> float:
    """Динамічний припуск на замок залежно від товщини.

    Формула: base_mm + factor * thickness_mm
    Чим товщий метал — тим ширший фальц потрібен.
    """
    return base_mm + factor * thickness_mm


def stiffener_area(
    width_mm: float,
    height_mm: float,
    rule: tuple[float, int, float] | None,
) -> float:
    """Розрахувати додаткову площу ребер жорсткості, м².

    Args:
        width_mm: Ширина перерізу, мм.
        height_mm: Висота перерізу, мм.
        rule: (поріг_мм, кількість_на_сторону, профіль_мм).

    Returns:
        Додаткова площа металу на ребра, м².
    """
    if rule is None:
        return 0.0

    threshold_mm, count_per_side, profile_mm = rule
    total_area_m2 = 0.0

    # Довгі сторони (по height)
    if width_mm > threshold_mm:
        # Ребра йдуть уздовж довжини виробу — тут приблизно, деталі в класі виробу
        # Повертаємо площу одного ребра × кількість
        # Детальний розрахунок робиться в класі виробу
        pass  # делеговано в клас виробу

    return total_area_m2


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

    # Якщо товщина поза діапазоном — беремо крайнє
    if thickness_mm <= available[0][0]:
        return available[0][1]
    if thickness_mm >= available[-1][0]:
        return available[-1][1]

    # Лінійна інтерполяція
    for i in range(len(available) - 1):
        t1, p1 = available[i]
        t2, p2 = available[i + 1]
        if t1 <= thickness_mm <= t2:
            ratio = (thickness_mm - t1) / (t2 - t1)
            return p1 + ratio * (p2 - p1)

    return available[-1][1]


def get_labor_rate(product_type_name: str) -> dict[str, float]:
    """Отримати тариф роботи з pricing_settings.json.

    Returns:
        {"rate_per_m2": float, "difficulty_percent": float}
    """
    global _pricing_cache
    if _pricing_cache is None:
        _pricing_cache = _load_pricing_settings()

    labor = _pricing_cache.get("labor_rates", {})
    return labor.get(product_type_name, {"rate_per_m2": 100.0, "difficulty_percent": 0.0})


def clear_pricing_cache() -> None:
    """Скинути кеш pricing_settings (наприклад, після редагування налаштувань)."""
    global _pricing_cache
    _pricing_cache = None
