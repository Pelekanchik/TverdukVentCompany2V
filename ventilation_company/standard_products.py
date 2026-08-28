"""Стандартні вироби для вентиляційних систем — Етапи 1+2+3.

Покращення:
  • Розділено 3 площі: surface_area, blank_area, material_area.
  • Параметри виробництва з manufacturing_settings.json (KIM, припуски).
  • Ціноутворення через CostEngine (material_area × ціна + blank_area × робота + ПДВ).

Зворотна сумісність:
  • MaterialType і Thickness — Enum.
  • metal_area → property = surface_area.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import ClassVar

from ventilation_company.calculations.cost_engine import CostEngine
from ventilation_company.manufacturing_params import (
    ProductCategory,
    get_labor_rate,
    get_material_price,
    get_params,
    seam_allowance_for_thickness,
)
from ventilation_company.utils.logging_config import get_logger

_logger = get_logger("products")


# ═══════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════

class MaterialType(Enum):
    GALVANIZED = "оцинкована сталь"
    STAINLESS = "нержавіюча сталь"
    ALUMINUM = "алюміній"


class Thickness(Enum):
    T0_5 = 0.5
    T0_7 = 0.7
    T0_9 = 0.9
    T1_0 = 1.0
    T1_2 = 1.2
    T1_5 = 1.5
    T2_0 = 2.0


_MATERIAL_TYPE_MAP: dict[str, str] = {
    "оцинкована сталь": "оцинкована сталь",
    "нержавіюча сталь": "нержавіюча сталь",
    "алюміній": "алюміній",
    "galvanized": "оцинкована сталь",
    "stainless": "нержавіюча сталь",
    "aluminum": "алюміній",
}


def _normalize_material(material_value: MaterialType | str) -> str:
    if isinstance(material_value, MaterialType):
        return material_value.value
    lowered = str(material_value).lower().strip()
    return _MATERIAL_TYPE_MAP.get(lowered, lowered)


def _normalize_thickness(thickness_value: Thickness | float) -> float:
    if isinstance(thickness_value, Thickness):
        return thickness_value.value
    return float(thickness_value)


# ═══════════════════════════════════════════════════════════
# БАЗОВИЙ КЛАС
# ═══════════════════════════════════════════════════════════

@dataclass
class StandardProduct:
    """Базовий клас виробу вентиляції з покращеним розрахунком площ."""

    name: str
    product_type: str = ""
    width: float = 0
    height: float = 0
    length: float = 0
    thickness: Thickness | float = field(default=Thickness.T0_7)
    material: MaterialType | str = field(default=MaterialType.GALVANIZED)
    quantity: int = 1
    has_flanges: bool = False
    flange_count: int = 0
    flange_price: Decimal = Decimal("0")
    profile: float = 30.0
    notes: str = ""

    surface_area: float = field(init=False)
    blank_area: float = field(init=False)
    material_area: float = field(init=False)
    weight: float = field(init=False)
    unit_price: Decimal = Decimal("0")
    total_price: Decimal = Decimal("0")

    _category: ClassVar[ProductCategory] = ProductCategory.RECT_DUCT
    _cost_engine: ClassVar = CostEngine()

    def __post_init__(self):
        if not self.product_type:
            self.product_type = self.name
        self.surface_area = self.calculate_surface_area()
        self.blank_area = self.calculate_blank_area()
        self.material_area = self.calculate_material_area()
        self.weight = self.calculate_weight()
        if self.unit_price == 0:
            self.unit_price = Decimal(str(self.calculate_price()))
        self.total_price = self.unit_price * self.quantity

    # ── Зворотна сумісність ──

    @property
    def metal_area(self) -> float:
        return self.surface_area

    def calculate_metal_area(self) -> float:
        return self.calculate_surface_area()

    def _material_str(self) -> str:
        return _normalize_material(self.material)

    def _thickness_float(self) -> float:
        return _normalize_thickness(self.thickness)

    # ── Площі ──

    def calculate_surface_area(self) -> float:
        return 0.0

    def calculate_blank_area(self) -> float:
        return self.surface_area

    def calculate_material_area(self) -> float:
        params = get_params(self._category)
        kim_eff = params.effective_kim()
        if kim_eff <= 0:
            return self.blank_area
        return self.blank_area / kim_eff

    # ── Вага ──

    def calculate_weight(self) -> float:
        density = 7850
        material_str = self._material_str()
        if "нержав" in material_str:
            density = 7900
        elif "алюм" in material_str:
            density = 2700
        t = self._thickness_float()
        return self.blank_area * (t / 1000) * density

    # ── Ціна (Етап 3: через CostEngine) ──

    def calculate_price(self) -> float:
        """Розрахунок ціни через CostEngine (синхронізовано з pricing_settings.json)."""
        try:
            breakdown = self._cost_engine.calculate(
                product_type=self.product_type,
                material_name=self._material_str(),
                thickness_mm=self._thickness_float(),
                surface_area_m2=self.surface_area,
                blank_area_m2=self.blank_area,
                material_area_m2=self.material_area,
                quantity=1,  # unit price
                flange_count=self.flange_count,
                flange_price=float(self.flange_price),
            )
            return breakdown.final_price
        except Exception as e:
            _logger.warning("CostEngine failed: %s, fallback to legacy pricing", e)
            return self._legacy_calculate_price()

    def recalculate_price(self) -> float:
        """
        Перерахувати ціну з актуальними ставками з pricing_settings.json.
        Використовувати при завантаженні проєкту або зміні налаштувань.
        """
        self.unit_price = Decimal(str(self.calculate_price()))
        self.total_price = self.unit_price * self.quantity
        return float(self.unit_price)

    def recalculate_price(self) -> float:
        """
        Перерахувати ціну з актуальними ставками з pricing_settings.json.
        Використовувати при завантаженні проєкту або зміні налаштувань.
        """
        self.unit_price = Decimal(str(self.calculate_price()))
        self.total_price = self.unit_price * self.quantity
        return float(self.unit_price)

    def get_cost_breakdown(self):
        """Отримати детальний розбив собівартості (CostBreakdown)."""
        return self._cost_engine.calculate(
            product_type=self.product_type,
            material_name=self._material_str(),
            thickness_mm=self._thickness_float(),
            surface_area_m2=self.surface_area,
            blank_area_m2=self.blank_area,
            material_area_m2=self.material_area,
            quantity=self.quantity,
            flange_count=self.flange_count,
            flange_price=float(self.flange_price),
        )

    def _legacy_calculate_price(self) -> float:
        """Fallback старий розрахунок (якщо CostEngine недоступний)."""
        material_key = self._material_str()
        t = self._thickness_float()
        material_price = get_material_price(material_key, t)
        material_cost = self.material_area * material_price
        labor = get_labor_rate(self.product_type.lower().strip())
        rate_per_m2 = labor.get("rate_per_m2", 100.0)
        difficulty = labor.get("difficulty_percent", 0.0)
        labor_cost = self.blank_area * rate_per_m2 * (1 + difficulty / 100)
        flange_cost = self.flange_count * float(self.flange_price) if self.has_flanges else 0.0
        return round(material_cost + labor_cost + flange_cost, 2)

    # ── Серіалізація ──

    def to_dict(self) -> dict:
        data = {
            "name": self.name,
            "product_type": self.product_type,
            "width": self.width,
            "height": self.height,
            "length": self.length,
            "thickness": self._thickness_float(),
            "material": self._material_str(),
            "quantity": self.quantity,
            "surface_area_m2": round(self.surface_area, 4),
            "blank_area_m2": round(self.blank_area, 4),
            "material_area_m2": round(self.material_area, 4),
            "metal_area_m2": round(self.metal_area, 4),
            "weight_kg": round(self.weight, 4),
            "has_flanges": self.has_flanges,
            "flange_count": self.flange_count,
            "flange_price": self.flange_price,
            "profile": self.profile,
            "unit_price": str(self.unit_price),
            "total_price": str(self.total_price),
            "notes": self.notes,
        }
        for field_name in [
            "branch_width", "branch_height", "branch_length",
            "branch_diameter", "branch_offset", "end_width",
            "end_height", "end_diameter", "angle", "radius",
            "top_extension", "bottom_extension",
            "segments", "depth", "border", "bolt_count",
            "bolt_diameter", "bolt_spacing", "fabric_type",
        ]:
            if hasattr(self, field_name):
                data[field_name] = getattr(self, field_name)
        if hasattr(self, "_dynamic_params"):
            data.update(self._dynamic_params)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "StandardProduct":
        raw_material = data.get("material", "оцинкована сталь")
        material = MaterialType.GALVANIZED
        for m in MaterialType:
            if m.value == raw_material:
                material = m
                break
        raw_thickness = data.get("thickness", 0.7)
        thickness = Thickness.T0_7
        for th in Thickness:
            if abs(th.value - raw_thickness) < 0.01:
                thickness = th
                break

        # Конвертуємо ціни в Decimal для коректної арифметики
        def _to_decimal(val):
            if isinstance(val, Decimal):
                return val
            if isinstance(val, (int, float)):
                return Decimal(str(val))
            if isinstance(val, str):
                return Decimal(val)
            return Decimal("0")

        return cls(
            name=data.get("name", ""),
            product_type=data.get("product_type", data.get("type", "")),
            width=data.get("width", 0),
            height=data.get("height", 0),
            length=data.get("length", 0),
            thickness=thickness,
            material=material,
            quantity=data.get("quantity", 1),
            has_flanges=data.get("has_flanges", False),
            flange_count=data.get("flange_count", 0),
            flange_price=_to_decimal(data.get("flange_price", 0)),
            profile=data.get("profile", 30.0),
            unit_price=_to_decimal(data.get("unit_price", 0)),
            total_price=_to_decimal(data.get("total_price", 0)),
            notes=data.get("notes", ""),
        )


# ═══════════════════════════════════════════════════════════
# ПРЯМОКУТНИЙ ПОВІТРОПРОВІД
# ═══════════════════════════════════════════════════════════

@dataclass
class RectDuct(StandardProduct):
    _category = ProductCategory.RECT_DUCT

    def calculate_surface_area(self) -> float:
        w = self.width / 1000
        h = self.height / 1000
        l = self.length / 1000
        return 2 * (w + h) * l

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        t = self._thickness_float()
        seam_mm = seam_allowance_for_thickness(params.seam_allowance_mm, t, factor=20.0)
        cut_mm = params.cut_allowance_mm
        w_mm, h_mm, l_mm = self.width, self.height, self.length
        unfolded_width_mm = 2 * (w_mm + h_mm) + seam_mm
        unfolded_length_mm = l_mm + 2 * cut_mm
        blank_m2 = (unfolded_width_mm * unfolded_length_mm) / 1_000_000
        if params.stiffener_rule.enabled:
            threshold = params.stiffener_rule.threshold_mm
            count = params.stiffener_rule.count_per_side
            profile = params.stiffener_rule.profile_mm
            extra = 0.0
            if w_mm > threshold:
                extra += count * 2 * (h_mm / 1000) * (profile / 1000)
            if h_mm > threshold:
                extra += count * 2 * (w_mm / 1000) * (profile / 1000)
            blank_m2 += extra
        return blank_m2


# ═══════════════════════════════════════════════════════════
# КРУГЛИЙ ПОВІТРОПРОВІД
# ═══════════════════════════════════════════════════════════

@dataclass
class RoundDuct(StandardProduct):
    _category = ProductCategory.ROUND_DUCT

    def calculate_surface_area(self) -> float:
        d = self.width / 1000
        l = self.length / 1000
        return math.pi * d * l

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        d_mm = self.width
        l_mm = self.length
        cut_mm = params.cut_allowance_mm
        if params.helix_angle_deg > 0:
            helix_rad = math.radians(params.helix_angle_deg)
            strip_width_mm = math.pi * d_mm / math.cos(helix_rad)
        else:
            t = self._thickness_float()
            seam_mm = seam_allowance_for_thickness(20.0, t, factor=15.0)
            strip_width_mm = math.pi * d_mm + seam_mm
        strip_length_mm = l_mm + 2 * cut_mm
        blank_m2 = (strip_width_mm * strip_length_mm) / 1_000_000
        if params.stiffener_rule.enabled:
            threshold = params.stiffener_rule.threshold_mm
            count = params.stiffener_rule.count_per_side
            profile = params.stiffener_rule.profile_mm
            if d_mm > threshold:
                ring_length = math.pi * d_mm
                ring_count = count * max(1, int(l_mm / 1000))
                blank_m2 += ring_count * (ring_length * profile) / 1_000_000
        return blank_m2


# ═══════════════════════════════════════════════════════════
# КОЛІНА
# ═══════════════════════════════════════════════════════════

@dataclass
class RectElbow(StandardProduct):
    _category = ProductCategory.RECT_ELBOW
    angle: float = 90
    radius: float = 50
    top_extension: float = 100
    bottom_extension: float = 100

    def calculate_surface_area(self) -> float:
        w = self.width / 1000
        h = self.height / 1000
        r = self.radius / 1000
        angle_rad = math.radians(self.angle)
        top_ext = self.top_extension / 1000
        bottom_ext = self.bottom_extension / 1000
        perimeter = 2 * (w + h)
        straight = perimeter * (top_ext + bottom_ext)
        mean_r = r + h / 2
        arc = mean_r * angle_rad
        bend = perimeter * arc
        return straight + bend

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        t = self._thickness_float()
        w_mm = self.width
        h_mm = self.height
        r_mm = self.radius
        angle_rad = math.radians(self.angle)
        seam_mm = seam_allowance_for_thickness(params.seam_allowance_mm, t, factor=20.0)
        cut_mm = params.cut_allowance_mm
        bend_mm = params.bend_allowance_mm
        unfolded_width = 2 * (w_mm + h_mm) + seam_mm
        mean_r = r_mm + h_mm / 2
        arc = mean_r * angle_rad
        total_len = self.top_extension + self.bottom_extension + arc + 2 * cut_mm + bend_mm
        return (unfolded_width * total_len) / 1_000_000


@dataclass
class RoundElbow(StandardProduct):
    _category = ProductCategory.ROUND_ELBOW
    angle: float = 90
    radius: float = 50
    top_extension: float = 100
    bottom_extension: float = 100

    def calculate_surface_area(self) -> float:
        d = self.width / 1000
        r = self.radius / 1000
        angle_rad = math.radians(self.angle)
        top_ext = self.top_extension / 1000
        bottom_ext = self.bottom_extension / 1000
        straight = math.pi * d * (top_ext + bottom_ext)
        mean_r = r + d / 2
        arc = mean_r * angle_rad
        bend = math.pi * d * arc
        return straight + bend

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        d_mm = self.width
        r_mm = self.radius
        angle_rad = math.radians(self.angle)
        strip_width = math.pi * d_mm
        mean_r = r_mm + d_mm / 2
        arc = mean_r * angle_rad
        total_len = self.top_extension + self.bottom_extension + arc + 2 * params.cut_allowance_mm + params.bend_allowance_mm
        return (strip_width * total_len) / 1_000_000


# ═══════════════════════════════════════════════════════════
# ІНШІ ВИРОБИ
# ═══════════════════════════════════════════════════════════

@dataclass
class RectFlange(StandardProduct):
    _category = ProductCategory.RECT_FLANGE
    bolt_count: int = 0

    def calculate_surface_area(self) -> float:
        w = self.width / 1000
        h = self.height / 1000
        border = self.profile / 1000
        return (w + 2 * border) * (h + 2 * border)

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        w_mm, h_mm, p_mm = self.width, self.height, self.profile
        seam, cut = params.seam_allowance_mm, params.cut_allowance_mm
        bw = w_mm + 2 * p_mm + seam + 2 * cut
        bh = h_mm + 2 * p_mm + seam + 2 * cut
        total = (bw * bh) / 1_000_000
        if self.bolt_count > 0:
            bd = getattr(self, "bolt_diameter", 8)
            total -= self.bolt_count * math.pi * (bd / 1000 / 2) ** 2
        return total


@dataclass
class RoundFlange(StandardProduct):
    _category = ProductCategory.ROUND_FLANGE
    bolt_count: int = 0

    def calculate_surface_area(self) -> float:
        d = self.width / 1000
        border = self.profile / 1000
        return math.pi * ((d + 2 * border) / 2) ** 2

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        d_mm, p_mm = self.width, self.profile
        seam, cut = params.seam_allowance_mm, params.cut_allowance_mm
        outer = d_mm + 2 * p_mm + seam + 2 * cut
        total = math.pi * (outer / 2) ** 2 / 1_000_000
        if self.bolt_count > 0:
            bd = getattr(self, "bolt_diameter", 8)
            total -= self.bolt_count * math.pi * (bd / 1000 / 2) ** 2
        return total


@dataclass
class RectTee(StandardProduct):
    _category = ProductCategory.RECT_TEE
    branch_width: float = 200
    branch_height: float = 200
    branch_length: float = 400
    branch_offset: float = 300

    def calculate_surface_area(self) -> float:
        w = self.width / 1000
        h = self.height / 1000
        l = self.length / 1000
        bw = self.branch_width / 1000
        bh = self.branch_height / 1000
        bl = self.branch_length / 1000
        return 2 * (w + h) * l + 2 * (bw + bh) * bl

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        t = self._thickness_float()
        base = self.calculate_surface_area()
        seam = seam_allowance_for_thickness(params.seam_allowance_mm, t, factor=20.0)
        factor = 1 + (seam * 2 + params.cut_allowance_mm * 4) / (self.width + self.height + 1)
        return base * factor


@dataclass
class RoundTee(StandardProduct):
    _category = ProductCategory.ROUND_TEE
    branch_diameter: float = 200
    branch_length: float = 400
    branch_offset: float = 300

    def calculate_surface_area(self) -> float:
        d = self.width / 1000
        l = self.length / 1000
        bd = self.branch_diameter / 1000
        bl = self.branch_length / 1000
        return math.pi * d * l + math.pi * bd * bl

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        base = self.calculate_surface_area()
        factor = 1 + (params.cut_allowance_mm * 3 + params.bend_allowance_mm) / (self.width + 1) * 0.01
        return base * max(factor, 1.05)


@dataclass
class RectTransition(StandardProduct):
    _category = ProductCategory.RECT_TRANSITION
    end_width: float = 300
    end_height: float = 150

    def calculate_surface_area(self) -> float:
        w1 = self.width / 1000
        h1 = self.height / 1000
        w2 = self.end_width / 1000
        h2 = self.end_height / 1000
        l = self.length / 1000
        return 2 * ((w1 + w2) / 2 + (h1 + h2) / 2) * l

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        t = self._thickness_float()
        base = self.calculate_surface_area()
        seam = seam_allowance_for_thickness(params.seam_allowance_mm, t, factor=20.0)
        factor = 1 + (seam + params.cut_allowance_mm * 2 + params.bend_allowance_mm) / (self.width + self.height + 1)
        return base * factor


@dataclass
class RoundTransition(StandardProduct):
    _category = ProductCategory.ROUND_TRANSITION
    end_diameter: float = 300

    def calculate_surface_area(self) -> float:
        d1 = self.width / 1000
        d2 = self.end_diameter / 1000
        l = self.length / 1000
        return math.pi * ((d1 + d2) / 2) * l

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        base = self.calculate_surface_area()
        factor = 1 + (params.cut_allowance_mm * 2 + params.bend_allowance_mm) / (self.width + 1) * 0.01
        return base * max(factor, 1.03)


@dataclass
class RectCap(StandardProduct):
    _category = ProductCategory.RECT_CAP

    def calculate_surface_area(self) -> float:
        w = self.width / 1000
        h = self.height / 1000
        border = self.profile / 1000
        return (w + 2 * border) * (h + 2 * border)

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        base = self.calculate_surface_area()
        factor = 1 + (params.seam_allowance_mm + params.cut_allowance_mm * 2) / (self.width + self.height + 1)
        return base * factor


@dataclass
class RoundCap(StandardProduct):
    _category = ProductCategory.ROUND_CAP
    depth: float = 30

    def calculate_surface_area(self) -> float:
        d = self.width / 1000
        depth = self.depth / 1000
        return math.pi * (d / 2) ** 2 + math.pi * d * depth

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        base = self.calculate_surface_area()
        factor = 1 + (params.seam_allowance_mm + params.cut_allowance_mm * 2) / (self.width + 1) * 0.01
        return base * max(factor, 1.02)


@dataclass
class FlexibleConnector(StandardProduct):
    _category = ProductCategory.FLEXIBLE
    fabric_type: str = "поліестер"

    def calculate_surface_area(self) -> float:
        w = self.width / 1000
        h = self.height / 1000
        l = self.length / 1000
        return 2 * (w + h) * l

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        base = self.calculate_surface_area()
        factor = 1 + params.cut_allowance_mm * 2 / (self.length + 1) * 0.01
        return base * max(factor, 1.01)

    def calculate_price(self) -> float:
        fabric_prices = {"поліестер": 80.0, "склотканина": 150.0, "ПВХ": 120.0}
        price_per_m2 = fabric_prices.get(self.fabric_type, 80.0)
        return self.metal_area * price_per_m2

    def __post_init__(self):
        super().__post_init__()
        self.unit_price = float(self.unit_price)
        self.total_price = float(self.total_price)


# ═══════════════════════════════════════════════════════════
# БІБЛІОТЕКА
# ═══════════════════════════════════════════════════════════

@dataclass
class ProductLibrary:
    products: list = field(default_factory=list)

    def add(self, product: StandardProduct):
        self.products.append(product)

    def remove(self, index: int):
        if 0 <= index < len(self.products):
            del self.products[index]

    def clear(self):
        self.products.clear()

    def get_total_surface_area(self) -> float:
        return sum(float(p.surface_area) * p.quantity for p in self.products)

    def get_total_blank_area(self) -> float:
        return sum(float(p.blank_area) * p.quantity for p in self.products)

    def get_total_material_area(self) -> float:
        return sum(float(p.material_area) * p.quantity for p in self.products)

    def get_total_metal_area(self) -> float:
        return self.get_total_surface_area()

    def get_total_weight(self) -> float:
        return sum(float(p.weight) * p.quantity for p in self.products)

    def get_total_price(self) -> float:
        return sum(float(p.total_price) for p in self.products)

    def get_specification(self) -> list[dict]:
        from collections import defaultdict
        grouped = defaultdict(lambda: {"quantity": 0, "products": []})
        for p in self.products:
            key = (p.product_type, p.width, p.height, p.length, p._thickness_float(), p._material_str())
            grouped[key]["quantity"] += p.quantity
            grouped[key]["products"].append(p)
        result = []
        for key, data in grouped.items():
            p = data["products"][0]
            result.append({
                "name": p.name,
                "product_type": p.product_type,
                "width": p.width,
                "height": p.height,
                "length": p.length,
                "thickness": p._thickness_float(),
                "material": p._material_str(),
                "quantity": data["quantity"],
                "surface_area_m2": round(p.surface_area, 4),
                "blank_area_m2": round(p.blank_area, 4),
                "material_area_m2": round(p.material_area, 4),
                "metal_area_m2": round(p.metal_area, 4),
                "weight_kg": round(p.weight, 4),
                "unit_price": round(float(p.unit_price), 2),
                "total_price": round(float(p.unit_price) * data["quantity"], 2),
            })
        return result

    def to_dict(self) -> list[dict]:
        return [p.to_dict() for p in self.products]

    def from_dict(self, data: list[dict]):
        self.products = [StandardProduct.from_dict(p) for p in data]

    def __len__(self):
        return len(self.products)


# ═══════════════════════════════════════════════════════════
# ХЕЛПЕРИ / ФАБРИКИ
# ═══════════════════════════════════════════════════════════

def _resolve_thickness(thickness: float | Thickness) -> Thickness:
    if isinstance(thickness, Thickness):
        return thickness
    for th in Thickness:
        if abs(th.value - thickness) < 0.01:
            return th
    return Thickness.T0_7


def _resolve_material(material: str | MaterialType) -> MaterialType:
    if isinstance(material, MaterialType):
        return material
    for m in MaterialType:
        if m.value == material:
            return m
    return MaterialType.GALVANIZED


def make_rect_duct(
    width: float, height: float, length: float,
    thickness: float | Thickness = 0.7,
    material: str | MaterialType = "оцинкована сталь",
    quantity: int = 1,
) -> RectDuct:
    thick = _resolve_thickness(thickness)
    mat = _resolve_material(material)
    return RectDuct(
        name=f"Повітропровід {width:.0f}×{height:.0f}×{length:.0f}",
        product_type="повітропровід прямокутний",
        width=width, height=height, length=length,
        thickness=thick, material=mat, quantity=quantity,
    )


def make_round_duct(
    diameter: float, length: float,
    thickness: float | Thickness = 0.7,
    material: str | MaterialType = "оцинкована сталь",
    quantity: int = 1,
) -> RoundDuct:
    thick = _resolve_thickness(thickness)
    mat = _resolve_material(material)
    return RoundDuct(
        name=f"Повітропровід Ø{diameter:.0f}×{length:.0f}",
        product_type="повітропровід круглий",
        width=diameter, height=diameter, length=length,
        thickness=thick, material=mat, quantity=quantity,
    )
