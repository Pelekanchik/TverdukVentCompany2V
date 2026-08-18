"""Інтеграція standard_products з metal_cutting (Етап 4).

Конвертує вироби (StandardProduct) у деталі для розкрою (Detail),
використовуючи точні розміри заготовки (blank_area) з урахуванням
припусків з manufacturing_settings.json.
"""

from __future__ import annotations

import math

from ventilation_company.manufacturing_params import get_params, seam_allowance_for_thickness
from ventilation_company.metal_cutting import Detail
from ventilation_company.standard_products import (
    RectCap,
    RectDuct,
    RectElbow,
    RectFlange,
    RectTee,
    RectTransition,
    RoundCap,
    RoundDuct,
    RoundElbow,
    RoundFlange,
    RoundTee,
    RoundTransition,
    StandardProduct,
)


def product_to_detail(product: StandardProduct) -> Detail | None:
    """Конвертувати виріб у деталь для розкрою з точними розмірами заготовки.

    Припуски (cut, bend, seam) вже враховані в розмірах — тому
    Detail створюється з cut_allowance=0 і bend_allowance=0.
    """
    w_mm, h_mm = _get_blank_dimensions(product)
    if w_mm <= 0 or h_mm <= 0:
        return None
    return Detail(
        name=product.name,
        width=w_mm,
        height=h_mm,
        quantity=product.quantity,
        product_type=product.product_type,
        cut_allowance=0,  # припуски вже в w_mm / h_mm
        bend_allowance=0,
    )


def products_to_details(products: list[StandardProduct]) -> list[Detail]:
    """Конвертувати список виробів у деталі для розкрою."""
    details = []
    for p in products:
        d = product_to_detail(p)
        if d:
            details.append(d)
    return details


# ═══════════════════════════════════════════════════════════
# BLANK DIMENSIONS (точні розміри заготовок в мм)
# ═══════════════════════════════════════════════════════════

def _get_blank_dimensions(product: StandardProduct) -> tuple[float, float]:
    """Повертає (width_mm, height_mm) заготовки для розкрою."""
    if isinstance(product, RectDuct):
        return _rect_duct_blank(product)
    elif isinstance(product, RoundDuct):
        return _round_duct_blank(product)
    elif isinstance(product, RectElbow):
        return _rect_elbow_blank(product)
    elif isinstance(product, RoundElbow):
        return _round_elbow_blank(product)
    elif isinstance(product, RectFlange):
        return _rect_flange_blank(product)
    elif isinstance(product, RoundFlange):
        return _round_flange_blank(product)
    elif isinstance(product, RectTee):
        return _rect_tee_blank(product)
    elif isinstance(product, RoundTee):
        return _round_tee_blank(product)
    elif isinstance(product, RectTransition):
        return _rect_transition_blank(product)
    elif isinstance(product, RoundTransition):
        return _round_transition_blank(product)
    elif isinstance(product, RectCap):
        return _rect_cap_blank(product)
    elif isinstance(product, RoundCap):
        return _round_cap_blank(product)
    else:
        # Fallback: наближено з blank_area
        return _fallback_blank(product)


def _rect_duct_blank(p: RectDuct) -> tuple[float, float]:
    params = get_params(p._category)
    t = p._thickness_float()
    seam_mm = seam_allowance_for_thickness(params.seam_allowance_mm, t, factor=20.0)
    cut_mm = params.cut_allowance_mm
    w_mm = 2 * (p.width + p.height) + seam_mm
    h_mm = p.length + 2 * cut_mm
    return w_mm, h_mm


def _round_duct_blank(p: RoundDuct) -> tuple[float, float]:
    params = get_params(p._category)
    d_mm = p.width
    l_mm = p.length
    cut_mm = params.cut_allowance_mm
    if params.helix_angle_deg > 0:
        helix_rad = math.radians(params.helix_angle_deg)
        strip_width_mm = math.pi * d_mm / math.cos(helix_rad)
    else:
        t = p._thickness_float()
        seam_mm = seam_allowance_for_thickness(20.0, t, factor=15.0)
        strip_width_mm = math.pi * d_mm + seam_mm
    strip_length_mm = l_mm + 2 * cut_mm
    return strip_width_mm, strip_length_mm


def _rect_elbow_blank(p: RectElbow) -> tuple[float, float]:
    params = get_params(p._category)
    t = p._thickness_float()
    w_mm = p.width
    h_mm = p.height
    r_mm = p.radius
    angle_rad = math.radians(p.angle)
    seam_mm = seam_allowance_for_thickness(params.seam_allowance_mm, t, factor=20.0)
    cut_mm = params.cut_allowance_mm
    bend_mm = params.bend_allowance_mm
    blank_width = 2 * (w_mm + h_mm) + seam_mm
    mean_r = r_mm + h_mm / 2
    arc = mean_r * angle_rad
    blank_length = p.top_extension + p.bottom_extension + arc + 2 * cut_mm + bend_mm
    return blank_width, blank_length


def _round_elbow_blank(p: RoundElbow) -> tuple[float, float]:
    params = get_params(p._category)
    d_mm = p.width
    r_mm = p.radius
    angle_rad = math.radians(p.angle)
    strip_width = math.pi * d_mm
    mean_r = r_mm + d_mm / 2
    arc = mean_r * angle_rad
    total_len = p.top_extension + p.bottom_extension + arc + 2 * params.cut_allowance_mm + params.bend_allowance_mm
    return strip_width, total_len


def _rect_flange_blank(p: RectFlange) -> tuple[float, float]:
    params = get_params(p._category)
    w_mm, h_mm, p_mm = p.width, p.height, p.profile
    seam, cut = params.seam_allowance_mm, params.cut_allowance_mm
    bw = w_mm + 2 * p_mm + seam + 2 * cut
    bh = h_mm + 2 * p_mm + seam + 2 * cut
    return bw, bh


def _round_flange_blank(p: RoundFlange) -> tuple[float, float]:
    params = get_params(p._category)
    d_mm, p_mm = p.width, p.profile
    seam, cut = params.seam_allowance_mm, params.cut_allowance_mm
    outer = d_mm + 2 * p_mm + seam + 2 * cut
    return outer, outer  # квадратна заготовка під круглий фланець


def _rect_tee_blank(p: RectTee) -> tuple[float, float]:
    # Трійник — складна розгортка, наближення
    params = get_params(p._category)
    t = p._thickness_float()
    base = p.calculate_surface_area()
    seam = seam_allowance_for_thickness(params.seam_allowance_mm, t, factor=20.0)
    factor = 1 + (seam * 2 + params.cut_allowance_mm * 4) / (p.width + p.height + 1)
    blank_m2 = base * factor
    area_mm2 = blank_m2 * 1_000_000
    # Наближено: ширина = периметр основного + відгалуження
    w_mm = max(2 * (p.width + p.height), 2 * (p.branch_width + p.branch_height)) + seam * 2
    h_mm = area_mm2 / w_mm if w_mm > 0 else 0
    return w_mm, h_mm


def _round_tee_blank(p: RoundTee) -> tuple[float, float]:
    params = get_params(p._category)
    base = p.calculate_surface_area()
    factor = 1 + (params.cut_allowance_mm * 3 + params.bend_allowance_mm) / (p.width + 1) * 0.01
    blank_m2 = base * max(factor, 1.05)
    area_mm2 = blank_m2 * 1_000_000
    # Наближено: квадратна заготовка
    side = math.sqrt(area_mm2)
    return side, side


def _rect_transition_blank(p: RectTransition) -> tuple[float, float]:
    params = get_params(p._category)
    t = p._thickness_float()
    base = p.calculate_surface_area()
    seam = seam_allowance_for_thickness(params.seam_allowance_mm, t, factor=20.0)
    factor = 1 + (seam + params.cut_allowance_mm * 2 + params.bend_allowance_mm) / (p.width + p.height + 1)
    blank_m2 = base * factor
    area_mm2 = blank_m2 * 1_000_000
    p1 = 2 * (p.width + p.height)
    p2 = 2 * (p.end_width + p.end_height)
    w_mm = max(p1, p2) + seam * 2
    h_mm = area_mm2 / w_mm if w_mm > 0 else 0
    return w_mm, h_mm


def _round_transition_blank(p: RoundTransition) -> tuple[float, float]:
    params = get_params(p._category)
    base = p.calculate_surface_area()
    factor = 1 + (params.cut_allowance_mm * 2 + params.bend_allowance_mm) / (p.width + 1) * 0.01
    blank_m2 = base * max(factor, 1.03)
    area_mm2 = blank_m2 * 1_000_000
    side = math.sqrt(area_mm2)
    return side, side


def _rect_cap_blank(p: RectCap) -> tuple[float, float]:
    params = get_params(p._category)
    w_mm, h_mm, p_mm = p.width, p.height, p.profile
    seam, cut = params.seam_allowance_mm, params.cut_allowance_mm
    bw = w_mm + 2 * p_mm + seam + 2 * cut
    bh = h_mm + 2 * p_mm + seam + 2 * cut
    return bw, bh


def _round_cap_blank(p: RoundCap) -> tuple[float, float]:
    params = get_params(p._category)
    d_mm = p.width
    depth = p.depth
    seam, cut = params.seam_allowance_mm, params.cut_allowance_mm
    # Розгортка: коло + бокова поверхня
    bw = math.pi * d_mm + seam + 2 * cut
    bh = d_mm / 2 + depth + seam + 2 * cut
    return bw, bh


def _fallback_blank(p: StandardProduct) -> tuple[float, float]:
    if p.blank_area <= 0:
        return 0.0, 0.0
    area_mm2 = p.blank_area * 1_000_000
    h = math.sqrt(area_mm2 / 2)
    w = area_mm2 / h
    return w, h
