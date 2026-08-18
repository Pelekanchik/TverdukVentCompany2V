"""Стандартні вироби для вентиляційних систем — Етап 1.

Покращення:
  • Розділено 3 площі: surface_area (поверхня), blank_area (заготовка),
    material_area (з урахуванням KIM та відходів).
  • calculate_weight() тепер рахує від blank_area (реальна заготовка).
  • calculate_price() підтягує ціни з pricing_settings.json.
  • Додано технологічні припуски (замок, різ, згин) через manufacturing_params.
  • Перероблено формули для RectDuct, RoundDuct, RectElbow, RoundElbow.

Зворотна сумісність:
  • MaterialType і Thickness залишено Enum (для старого коду).
  • Поле metal_area → property, що повертає surface_area.
  • Метод calculate_metal_area() → делегує calculate_surface_area().
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import ClassVar

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
# ENUMS (зворотна сумісність)
# ═══════════════════════════════════════════════════════════

class MaterialType(Enum):
    """Тип матеріалу."""

    GALVANIZED = "оцинкована сталь"
    STAINLESS = "нержавіюча сталь"
    ALUMINUM = "алюміній"


class Thickness(Enum):
    """Товщина металу, мм."""

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
    """Нормалізувати назву матеріалу в строку для pricing_settings.json."""
    if isinstance(material_value, MaterialType):
        return material_value.value
    lowered = str(material_value).lower().strip()
    return _MATERIAL_TYPE_MAP.get(lowered, lowered)


def _normalize_thickness(thickness_value: Thickness | float) -> float:
    """Нормалізувати товщину в float."""
    if isinstance(thickness_value, Thickness):
        return thickness_value.value
    return float(thickness_value)


# ═══════════════════════════════════════════════════════════
# БАЗОВИЙ КЛАС
# ═══════════════════════════════════════════════════════════

@dataclass
class StandardProduct:
    """Базовий клас виробу вентиляції з покращеним розрахунком площ."""

    # ── Ідентифікація ──
    name: str
    product_type: str = ""

    # ── Розміри (мм) ──
    width: float = 0
    height: float = 0
    length: float = 0

    # ── Матеріал ──
    # Типи залишено гнучкими (Enum | str / float) для зворотної сумісності
    thickness: Thickness | float = field(default=Thickness.T0_7)
    material: MaterialType | str = field(default=MaterialType.GALVANIZED)

    # ── Кількість ──
    quantity: int = 1

    # ── Фланці ──
    has_flanges: bool = False
    flange_count: int = 0
    flange_price: Decimal = Decimal("0")
    profile: float = 30.0

    # ── Нотатки ──
    notes: str = ""

    # ── Обчислювані поля (init=False) ──
    surface_area: float = field(init=False)     # площа поверхні готового виробу, м²
    blank_area: float = field(init=False)       # площа листової заготовки з припусками, м²
    material_area: float = field(init=False)    # blank_area / KIM (реальні витрати металу), м²
    weight: float = field(init=False)           # вага, кг
    unit_price: Decimal = Decimal("0")          # ціна за шт
    total_price: Decimal = Decimal("0")         # ціна × кількість

    # ── Категорія для manufacturing_params ──
    _category: ClassVar[ProductCategory] = ProductCategory.RECT_DUCT

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

    # ── ЗВОРОТНЯ СУМІСНІСТЬ ──

    @property
    def metal_area(self) -> float:
        """Псевдонім для surface_area (для старого коду)."""
        return self.surface_area

    def calculate_metal_area(self) -> float:
        """Псевдонім для calculate_surface_area() (для старого коду)."""
        return self.calculate_surface_area()

    def _material_str(self) -> str:
        """Нормалізована строка матеріалу."""
        return _normalize_material(self.material)

    def _thickness_float(self) -> float:
        """Нормалізована товщина як float."""
        return _normalize_thickness(self.thickness)

    # ── РОЗРАХУНОК ПЛОЩ ──

    def calculate_surface_area(self) -> float:
        """Площа поверхні готового виробу (м²) — для покриття, ізоляції."""
        return 0.0

    def calculate_blank_area(self) -> float:
        """Площа листової заготовки з технологічними припусками (м²).

        Це площа металу, який реально потрібно розкроїти,
        з урахуванням замка, припусків на різ, ребер жорсткості.
        """
        return self.surface_area

    def calculate_material_area(self) -> float:
        """Реальна площа матеріалу з урахуванням KIM та відходів (м²).

        material_area = blank_area / KIM_effective
        Це те, скільки металу фактично витрачається.
        """
        params = get_params(self._category)
        kim_eff = params.effective_kim()
        if kim_eff <= 0:
            return self.blank_area
        return self.blank_area / kim_eff

    # ── ВАГА ──

    def calculate_weight(self) -> float:
        """Вага виробу, кг — рахується від площі заготовки."""
        density = 7850  # кг/м³ для сталі
        material_str = self._material_str()
        if "нержав" in material_str:
            density = 7900
        elif "алюм" in material_str:
            density = 2700
        t = self._thickness_float()
        return self.blank_area * (t / 1000) * density

    # ── ЦІНА ──

    def calculate_price(self) -> float:
        """Розрахунок ціни виробу з цінами з pricing_settings.json."""
        # 1. Ціна матеріалу
        material_key = self._material_str()
        t = self._thickness_float()
        material_price = get_material_price(material_key, t)
        material_cost = self.material_area * material_price

        # 2. Вартість роботи
        labor = get_labor_rate(self.product_type.lower().strip())
        rate_per_m2 = labor.get("rate_per_m2", 100.0)
        difficulty = labor.get("difficulty_percent", 0.0)
        labor_cost = self.blank_area * rate_per_m2 * (1 + difficulty / 100)

        # 3. Фланці
        flange_cost = 0.0
        if self.has_flanges:
            flange_cost = self.flange_count * float(self.flange_price)

        total = material_cost + labor_cost + flange_cost

        _logger.debug(
            "[%s] mat=%.3f×%.1f=%.2f | labor=%.2f | flanges=%.2f | total=%.2f",
            self.name,
            self.material_area,
            material_price,
            material_cost,
            labor_cost,
            flange_cost,
            total,
        )
        return round(total, 2)

    # ── СЕРІАЛІЗАЦІЯ ──

    def to_dict(self) -> dict:
        """Конвертувати у словник для серіалізації."""
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
            "metal_area_m2": round(self.metal_area, 4),  # backward compat
            "weight_kg": round(self.weight, 4),
            "has_flanges": self.has_flanges,
            "flange_count": self.flange_count,
            "flange_price": self.flange_price,
            "profile": self.profile,
            "unit_price": str(self.unit_price),
            "total_price": str(self.total_price),
            "notes": self.notes,
        }
        # Додаємо специфічні поля підкласів
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
        """Створити виріб зі словника."""
        # Відновлюємо Enum зі строк/чисел для зворотної сумісності
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
            flange_price=data.get("flange_price", 0),
            profile=data.get("profile", 30.0),
            unit_price=data.get("unit_price", 0),
            total_price=data.get("total_price", 0),
            notes=data.get("notes", ""),
        )


# ═══════════════════════════════════════════════════════════
# ПРЯМОКУТНИЙ ПОВІТРОПРОВІД
# ═══════════════════════════════════════════════════════════

@dataclass
class RectDuct(StandardProduct):
    """Прямокутний повітропровід.

    Розгортка: периметр перерізу + замок (подвійний фальц).
    Довжина заготовки = довжина виробу + 2×припуск на різ.
    """

    _category = ProductCategory.RECT_DUCT

    def calculate_surface_area(self) -> float:
        """Площа поверхні готового виробу."""
        w = self.width / 1000
        h = self.height / 1000
        l = self.length / 1000
        return 2 * (w + h) * l

    def calculate_blank_area(self) -> float:
        """Площа заготовки з припусками на замок і різ."""
        params = get_params(self._category)
        t = self._thickness_float()

        # Припуск на замок залежить від товщини
        seam_mm = seam_allowance_for_thickness(
            params.seam_allowance_mm, t, factor=20.0
        )
        cut_mm = params.cut_allowance_mm

        w_mm = self.width
        h_mm = self.height
        l_mm = self.length

        # Розгорнута ширина = периметр + замок
        unfolded_width_mm = 2 * (w_mm + h_mm) + seam_mm
        # Довжина заготовки
        unfolded_length_mm = l_mm + 2 * cut_mm

        blank_m2 = (unfolded_width_mm * unfolded_length_mm) / 1_000_000

        # Ребра жорсткості
        if params.stiffener_rule:
            threshold_mm, count_per_side, profile_mm = params.stiffener_rule
            stiffener_area_m2 = 0.0
            # По ширині
            if w_mm > threshold_mm:
                stiffener_area_m2 += count_per_side * 2 * (h_mm / 1000) * (profile_mm / 1000)
            # По висоті
            if h_mm > threshold_mm:
                stiffener_area_m2 += count_per_side * 2 * (w_mm / 1000) * (profile_mm / 1000)
            blank_m2 += stiffener_area_m2

        return blank_m2


# ═══════════════════════════════════════════════════════════
# КРУГЛИЙ ПОВІТРОПРОВІД
# ═══════════════════════════════════════════════════════════

@dataclass
class RoundDuct(StandardProduct):
    """Круглий повітропровід (спірально-навивний).

    Заготовка — смуга металу, що навивається спіраллю.
    Ширина смуги = π·D / cos(helix_angle).
    """

    _category = ProductCategory.ROUND_DUCT

    def calculate_surface_area(self) -> float:
        """Площа поверхні готового виробу."""
        d = self.width / 1000  # діаметр, м
        l = self.length / 1000
        return math.pi * d * l

    def calculate_blank_area(self) -> float:
        """Площа заготовки — смуга для спіральної навивки."""
        params = get_params(self._category)
        d_mm = self.width
        l_mm = self.length
        cut_mm = params.cut_allowance_mm

        if params.helix_angle_deg > 0:
            # Спіральна навивка
            helix_rad = math.radians(params.helix_angle_deg)
            strip_width_mm = math.pi * d_mm / math.cos(helix_rad)
        else:
            # Замкова труба — ширина = π·D + замок
            t = self._thickness_float()
            seam_mm = seam_allowance_for_thickness(20.0, t, factor=15.0)
            strip_width_mm = math.pi * d_mm + seam_mm

        strip_length_mm = l_mm + 2 * cut_mm
        blank_m2 = (strip_width_mm * strip_length_mm) / 1_000_000

        # Ребра жорсткості
        if params.stiffener_rule:
            threshold_mm, count_per_side, profile_mm = params.stiffener_rule
            if d_mm > threshold_mm:
                # Ребро — кільце навколо труби
                ring_length_mm = math.pi * d_mm
                ring_count = count_per_side * max(1, int(l_mm / 1000))
                stiffener_m2 = ring_count * (ring_length_mm * profile_mm) / 1_000_000
                blank_m2 += stiffener_m2

        return blank_m2


# ═══════════════════════════════════════════════════════════
# ПРЯМОКУТНЕ КОЛІНО (ВІДВІД)
# ═══════════════════════════════════════════════════════════

@dataclass
class RectElbow(StandardProduct):
    """Прямокутне коліно з подовженнями.

    Параметри (як у CAMduct):
      • width  (A) — ширина перерізу, мм
      • height (B) — глибина (висота) перерізу, мм
      • angle  (C) — кут згину, °
      • radius (F) — внутрішній радіус горловини, мм
      • top_extension    (D) — верхнє подовження, мм
      • bottom_extension (E) — нижнє подовження, мм

    Площа поверхні (готова):
      S = 2·(W+H)·[(top+bottom) + (r + H/2)·α]

    Площа заготовки — збільшена на припуски згину та замок.
    """

    _category = ProductCategory.RECT_ELBOW

    angle: float = 90
    radius: float = 50          # внутрішній радіус горловини (F), мм
    top_extension: float = 100    # верхнє подовження (D), мм
    bottom_extension: float = 100 # нижнє подовження (E), мм

    def calculate_surface_area(self) -> float:
        """Площа поверхні готового коліна."""
        w = self.width / 1000
        h = self.height / 1000
        r = self.radius / 1000
        angle_rad = math.radians(self.angle)
        top_ext = self.top_extension / 1000
        bottom_ext = self.bottom_extension / 1000

        perimeter = 2 * (w + h)
        straight_area = perimeter * (top_ext + bottom_ext)
        mean_radius = r + h / 2
        arc_length = mean_radius * angle_rad
        bend_area = perimeter * arc_length

        return straight_area + bend_area

    def calculate_blank_area(self) -> float:
        """Площа заготовки коліна з припусками."""
        params = get_params(self._category)
        t = self._thickness_float()
        w_mm = self.width
        h_mm = self.height
        r_mm = self.radius
        angle_rad = math.radians(self.angle)
        top_mm = self.top_extension
        bottom_mm = self.bottom_extension

        # Припуски
        seam_mm = seam_allowance_for_thickness(
            params.seam_allowance_mm, t, factor=20.0
        )
        cut_mm = params.cut_allowance_mm
        bend_mm = params.bend_allowance_mm

        # Периметр заготовки (з замком)
        unfolded_width_mm = 2 * (w_mm + h_mm) + seam_mm

        # Довжина заготовки = подовження + дуга + припуски
        mean_r_mm = r_mm + h_mm / 2
        arc_mm = mean_r_mm * angle_rad
        total_length_mm = top_mm + bottom_mm + arc_mm + 2 * cut_mm + bend_mm

        return (unfolded_width_mm * total_length_mm) / 1_000_000


# ═══════════════════════════════════════════════════════════
# КРУГЛЕ КОЛІНО (ВІДВІД)
# ═══════════════════════════════════════════════════════════

@dataclass
class RoundElbow(StandardProduct):
    """Кругле коліно з подовженнями.

    Параметри:
      • width  — діаметр труби, мм
      • angle  — кут згину, °
      • radius — внутрішній радіус горловини, мм
      • top_extension    — верхнє подовження, мм
      • bottom_extension — нижнє подовження, мм
    """

    _category = ProductCategory.ROUND_ELBOW

    angle: float = 90
    radius: float = 50
    top_extension: float = 100
    bottom_extension: float = 100

    def calculate_surface_area(self) -> float:
        """Площа поверхні готового коліна."""
        d = self.width / 1000
        r = self.radius / 1000
        angle_rad = math.radians(self.angle)
        top_ext = self.top_extension / 1000
        bottom_ext = self.bottom_extension / 1000

        straight_area = math.pi * d * (top_ext + bottom_ext)
        mean_radius = r + d / 2
        arc_length = mean_radius * angle_rad
        bend_area = math.pi * d * arc_length

        return straight_area + bend_area

    def calculate_blank_area(self) -> float:
        """Площа заготовки — смуга для гнутого коліна."""
        params = get_params(self._category)
        d_mm = self.width
        r_mm = self.radius
        angle_rad = math.radians(self.angle)
        top_mm = self.top_extension
        bottom_mm = self.bottom_extension

        cut_mm = params.cut_allowance_mm
        bend_mm = params.bend_allowance_mm

        # Ширина смуги = π·D (окружність)
        strip_width_mm = math.pi * d_mm

        # Довжина смуги
        mean_r_mm = r_mm + d_mm / 2
        arc_mm = mean_r_mm * angle_rad
        total_length_mm = top_mm + bottom_mm + arc_mm + 2 * cut_mm + bend_mm

        return (strip_width_mm * total_length_mm) / 1_000_000


# ═══════════════════════════════════════════════════════════
# ІНШІ ВИРОБИ (залишено для сумісності, формули базові)
# ═══════════════════════════════════════════════════════════

@dataclass
class RectFlange(StandardProduct):
    """Прямокутний фланець."""

    _category = ProductCategory.RECT_FLANGE

    def calculate_surface_area(self) -> float:
        w = self.width / 1000
        h = self.height / 1000
        border = self.profile / 1000
        return (w + 2 * border) * (h + 2 * border)

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        w_mm = self.width
        h_mm = self.height
        p_mm = self.profile
        seam_mm = params.seam_allowance_mm
        cut_mm = params.cut_allowance_mm
        blank_w = w_mm + 2 * p_mm + seam_mm + 2 * cut_mm
        blank_h = h_mm + 2 * p_mm + seam_mm + 2 * cut_mm
        total = (blank_w * blank_h) / 1_000_000
        # Віднімаємо площу отворів (приблизно)
        if hasattr(self, "bolt_count") and self.bolt_count > 0:
            bolt_d = getattr(self, "bolt_diameter", 8)
            bolt_area = self.bolt_count * math.pi * (bolt_d / 1000 / 2) ** 2
            total -= bolt_area
        return total


@dataclass
class RoundFlange(StandardProduct):
    """Круглий фланець."""

    _category = ProductCategory.ROUND_FLANGE

    def calculate_surface_area(self) -> float:
        d = self.width / 1000
        border = self.profile / 1000
        outer_d = d + 2 * border
        return math.pi * (outer_d / 2) ** 2

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        d_mm = self.width
        p_mm = self.profile
        seam_mm = params.seam_allowance_mm
        cut_mm = params.cut_allowance_mm
        outer_d = d_mm + 2 * p_mm + seam_mm + 2 * cut_mm
        total = math.pi * (outer_d / 2) ** 2 / 1_000_000
        if hasattr(self, "bolt_count") and self.bolt_count > 0:
            bolt_d = getattr(self, "bolt_diameter", 8)
            total -= self.bolt_count * math.pi * (bolt_d / 1000 / 2) ** 2
        return total


@dataclass
class RectTee(StandardProduct):
    """Прямокутний трійник."""

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
        main_area = 2 * (w + h) * l
        branch_area = 2 * (bw + bh) * bl
        return main_area + branch_area

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        t = self._thickness_float()
        # Трійник — складна деталь, blank ≈ surface + припуски
        base = self.calculate_surface_area()
        seam_mm = seam_allowance_for_thickness(
            params.seam_allowance_mm, t, factor=20.0
        )
        cut_mm = params.cut_allowance_mm
        # Наближено: збільшуємо на припуски (~10% + seam/cut)
        factor = 1 + (seam_mm * 2 + cut_mm * 4) / (self.width + self.height + 1)
        return base * factor


@dataclass
class RoundTee(StandardProduct):
    """Круглий трійник."""

    _category = ProductCategory.ROUND_TEE

    branch_diameter: float = 200
    branch_length: float = 400
    branch_offset: float = 300

    def calculate_surface_area(self) -> float:
        d = self.width / 1000
        l = self.length / 1000
        bd = self.branch_diameter / 1000
        bl = self.branch_length / 1000
        main_area = math.pi * d * l
        branch_area = math.pi * bd * bl
        return main_area + branch_area

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        base = self.calculate_surface_area()
        cut_mm = params.cut_allowance_mm
        bend_mm = params.bend_allowance_mm
        factor = 1 + (cut_mm * 3 + bend_mm) / (self.width + 1) * 0.01
        return base * max(factor, 1.05)


@dataclass
class RectTransition(StandardProduct):
    """Прямокутний перехід."""

    _category = ProductCategory.RECT_TRANSITION

    end_width: float = 300
    end_height: float = 150

    def calculate_surface_area(self) -> float:
        w1 = self.width / 1000
        h1 = self.height / 1000
        w2 = self.end_width / 1000
        h2 = self.end_height / 1000
        l = self.length / 1000
        avg_perimeter = 2 * ((w1 + w2) / 2 + (h1 + h2) / 2)
        return avg_perimeter * l

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        t = self._thickness_float()
        base = self.calculate_surface_area()
        seam_mm = seam_allowance_for_thickness(
            params.seam_allowance_mm, t, factor=20.0
        )
        cut_mm = params.cut_allowance_mm
        bend_mm = params.bend_allowance_mm
        factor = 1 + (seam_mm + cut_mm * 2 + bend_mm) / (self.width + self.height + 1)
        return base * factor


@dataclass
class RoundTransition(StandardProduct):
    """Круглий перехід (конус)."""

    _category = ProductCategory.ROUND_TRANSITION

    end_diameter: float = 300

    def calculate_surface_area(self) -> float:
        d1 = self.width / 1000
        d2 = self.end_diameter / 1000
        l = self.length / 1000
        avg_d = (d1 + d2) / 2
        return math.pi * avg_d * l

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        base = self.calculate_surface_area()
        cut_mm = params.cut_allowance_mm
        bend_mm = params.bend_allowance_mm
        factor = 1 + (cut_mm * 2 + bend_mm) / (self.width + 1) * 0.01
        return base * max(factor, 1.03)


@dataclass
class RectCap(StandardProduct):
    """Прямокутна заглушка."""

    _category = ProductCategory.RECT_CAP

    def calculate_surface_area(self) -> float:
        w = self.width / 1000
        h = self.height / 1000
        border = self.profile / 1000
        return (w + 2 * border) * (h + 2 * border)

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        base = self.calculate_surface_area()
        seam_mm = params.seam_allowance_mm
        cut_mm = params.cut_allowance_mm
        factor = 1 + (seam_mm + cut_mm * 2) / (self.width + self.height + 1)
        return base * factor


@dataclass
class RoundCap(StandardProduct):
    """Кругла заглушка."""

    _category = ProductCategory.ROUND_CAP

    depth: float = 30

    def calculate_surface_area(self) -> float:
        d = self.width / 1000
        depth = self.depth / 1000
        base_area = math.pi * (d / 2) ** 2
        side_area = math.pi * d * depth
        return base_area + side_area

    def calculate_blank_area(self) -> float:
        params = get_params(self._category)
        base = self.calculate_surface_area()
        seam_mm = params.seam_allowance_mm
        cut_mm = params.cut_allowance_mm
        factor = 1 + (seam_mm + cut_mm * 2) / (self.width + 1) * 0.01
        return base * max(factor, 1.02)


@dataclass
class FlexibleConnector(StandardProduct):
    """Гнучка вставка."""

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
        cut_mm = params.cut_allowance_mm
        factor = 1 + cut_mm * 2 / (self.length + 1) * 0.01
        return base * max(factor, 1.01)

    def calculate_price(self) -> float:
        """Спеціальна ціна для гнучкої вставки (тканина, не метал).

        Зворотна сумісність: старий код мав баг подвійного множення на quantity.
        calculate_price() множить на quantity, і __post_init__ знову множить.
        """
        fabric_prices = {"поліестер": 80.0, "склотканина": 150.0, "ПВХ": 120.0}
        price_per_m2 = fabric_prices.get(self.fabric_type, 80.0)
        # Старий код використовував metal_area (surface_area), не blank_area
        return self.metal_area * price_per_m2 * self.quantity

    def __post_init__(self):
        super().__post_init__()
        # Зворотна сумісність: старий код використовував float, не Decimal
        self.unit_price = float(self.unit_price)
        self.total_price = float(self.total_price)


# ═══════════════════════════════════════════════════════════
# БІБЛІОТЕКА ВИРОБІВ
# ═══════════════════════════════════════════════════════════

@dataclass
class ProductLibrary:
    """Бібліотека виробів."""

    products: list = field(default_factory=list)

    def add(self, product: StandardProduct):
        self.products.append(product)

    def remove(self, index: int):
        if 0 <= index < len(self.products):
            del self.products[index]

    def clear(self):
        self.products.clear()

    def get_total_surface_area(self) -> float:
        """Загальна площа поверхні (для покриття/ізоляції)."""
        return sum(p.surface_area * p.quantity for p in self.products)

    def get_total_blank_area(self) -> float:
        """Загальна площа заготовок (для розкрою)."""
        return sum(p.blank_area * p.quantity for p in self.products)

    def get_total_material_area(self) -> float:
        """Загальна площа матеріалу з KIM (для собівартості)."""
        return sum(p.material_area * p.quantity for p in self.products)

    # ── Зворотна сумісність ──
    def get_total_metal_area(self) -> float:
        """Псевдонім для get_total_surface_area() (старий код)."""
        return self.get_total_surface_area()

    def get_total_weight(self) -> float:
        return sum(p.weight * p.quantity for p in self.products)

    def get_total_price(self) -> float:
        return sum(p.total_price for p in self.products)

    def get_specification(self) -> list[dict]:
        """Отримати згруповану специфікацію."""
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
                "metal_area_m2": round(p.metal_area, 4),  # backward compat
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
# ХЕЛПЕРИ ДЛЯ ФАБРИЧНИХ МЕТОДІВ
# ═══════════════════════════════════════════════════════════

def _resolve_thickness(thickness: float | Thickness) -> Thickness:
    """Конвертувати float у Thickness Enum для зворотної сумісності."""
    if isinstance(thickness, Thickness):
        return thickness
    for th in Thickness:
        if abs(th.value - thickness) < 0.01:
            return th
    return Thickness.T0_7


def _resolve_material(material: str | MaterialType) -> MaterialType:
    """Конвертувати строку у MaterialType Enum для зворотної сумісності."""
    if isinstance(material, MaterialType):
        return material
    for m in MaterialType:
        if m.value == material:
            return m
    return MaterialType.GALVANIZED


# ═══════════════════════════════════════════════════════════
# ФАБРИЧНІ МЕТОДИ
# ═══════════════════════════════════════════════════════════

def make_rect_duct(
    width: float,
    height: float,
    length: float,
    thickness: float | Thickness = 0.7,
    material: str | MaterialType = "оцинкована сталь",
    quantity: int = 1,
) -> RectDuct:
    """Фабричний метод для прямокутного повітропроводу."""
    thick = _resolve_thickness(thickness)
    mat = _resolve_material(material)
    return RectDuct(
        name=f"Повітропровід {width:.0f}×{height:.0f}×{length:.0f}",
        product_type="повітропровід прямокутний",
        width=width,
        height=height,
        length=length,
        thickness=thick,
        material=mat,
        quantity=quantity,
    )


def make_round_duct(
    diameter: float,
    length: float,
    thickness: float | Thickness = 0.7,
    material: str | MaterialType = "оцинкована сталь",
    quantity: int = 1,
) -> RoundDuct:
    """Фабричний метод для круглого повітропроводу."""
    thick = _resolve_thickness(thickness)
    mat = _resolve_material(material)
    return RoundDuct(
        name=f"Повітропровід Ø{diameter:.0f}×{length:.0f}",
        product_type="повітропровід круглий",
        width=diameter,
        height=diameter,
        length=length,
        thickness=thick,
        material=mat,
        quantity=quantity,
    )
