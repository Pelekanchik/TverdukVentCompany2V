"""Утиліти для роботи з формулами розрахунку площі металу."""

import math
import re
from typing import Any

from ventilation_company.standard_products import (
    RectDuct, RoundDuct,
    RectFlange, RoundFlange,
    RectTee, RoundTee,
    RectTransition, RoundTransition,
    RectElbow, RoundElbow,
    RectCap, RoundCap,
    FlexibleConnector,
)


def get_custom_formula(product_name: str, formulas: dict[str, str]) -> str:
    """Повертає кастомну формулу для продукту або порожній рядок."""
    return formulas.get(product_name, "")


def parse_formula_params(formula: str) -> list[str]:
    """Витягує параметри з формули (змінні у фігурних дужках)."""
    return re.findall(r"\{(\w+)\}", formula)


def safe_float(value: Any, default: float = 0.0) -> float:
    """Безпечне перетворення в float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def get_extra(extra_vars: dict[str, Any], key: str, default: float = 0.0) -> float:
    """Отримати значення з extra змінних."""
    return safe_float(extra_vars.get(key, default))


def calc_price(product) -> float:
    """Розрахувати ціну продукту (базова ціна 450 грн/м²)."""
    area = product.calculate_metal_area()
    base_price = 450.0
    return round(area * base_price, 2)


def calc_preview_area(
    ptype: str,
    selected_name: str,
    width: float,
    height: float,
    length: float,
    profile: str,
    extra_vars: dict[str, Any],
) -> float:
    """Розрахувати попередню площу металу для продукту."""
    try:
        if ptype == "прямокутна_воздуховод":
            product = RectDuct(width=width, height=height, length=length)
        elif ptype == "кругла_воздуховод":
            product = RoundDuct(diameter=width, length=length)
        elif ptype == "прямокутний_фланець":
            product = RectFlange(width=width, height=height)
        elif ptype == "круглий_фланець":
            product = RoundFlange(diameter=width)
        elif ptype == "прямокутний_трійник":
            w2 = get_extra(extra_vars, "width2", width)
            h2 = get_extra(extra_vars, "height2", height)
            product = RectTee(
                width=width, height=height,
                width2=w2, height2=h2, length=length,
            )
        elif ptype == "круглий_трійник":
            d2 = get_extra(extra_vars, "diameter2", width)
            product = RoundTee(diameter=width, diameter2=d2, length=length)
        elif ptype == "прямокутний_перехід":
            w2 = get_extra(extra_vars, "width2", width)
            h2 = get_extra(extra_vars, "height2", height)
            product = RectTransition(
                width=width, height=height,
                width2=w2, height2=h2, length=length,
            )
        elif ptype == "круглий_перехід":
            d2 = get_extra(extra_vars, "diameter2", width)
            product = RoundTransition(diameter=width, diameter2=d2, length=length)
        elif ptype == "прямокутний_відвід":
            angle = get_extra(extra_vars, "angle", 90)
            product = RectElbow(
                width=width, height=height,
                angle=angle, radius=get_extra(extra_vars, "radius", 0),
            )
        elif ptype == "круглий_відвід":
            angle = get_extra(extra_vars, "angle", 90)
            product = RoundElbow(
                diameter=width, angle=angle,
                radius=get_extra(extra_vars, "radius", 0),
            )
        elif ptype == "прямокутна_заглушка":
            product = RectCap(width=width, height=height)
        elif ptype == "кругла_заглушка":
            product = RoundCap(diameter=width)
        elif ptype == "гнучка_вставка":
            product = FlexibleConnector(
                width=width, height=height, length=length,
                material=profile if profile else "поліестер",
            )
        else:
            return 0.0
        return product.calculate_metal_area()
    except Exception:
        return 0.0
