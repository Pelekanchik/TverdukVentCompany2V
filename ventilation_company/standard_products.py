"""Стандартні вироби для вентиляційних систем."""

import copy
import math
from dataclasses import dataclass, field
from decimal import Decimal

from ventilation_company.utils.logging_config import get_logger

_logger = get_logger("products")
from enum import Enum
from typing import Optional


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


@dataclass
class StandardProduct:
    """Базовий клас виробу вентиляції."""
    name: str
    product_type: str = ""
    width: float = 0
    height: float = 0
    length: float = 0
    thickness: Thickness = Thickness.T0_7
    material: MaterialType = MaterialType.GALVANIZED
    quantity: int = 1
    metal_area: float = field(init=False)
    weight: float = field(init=False)
    has_flanges: bool = False
    flange_count: int = 0
    flange_price: Decimal = Decimal("0")
    profile: float = 30.0
    unit_price: Decimal = Decimal("0")
    total_price: Decimal = Decimal("0")
    notes: str = ""

    def __post_init__(self):
        if not self.product_type:
            self.product_type = self.name
        self.metal_area = self.calculate_metal_area()
        self.weight = self.calculate_weight()
        if self.unit_price == 0:
            self.unit_price = self.calculate_price()
        self.total_price = self.unit_price * self.quantity

    def calculate_metal_area(self) -> float:
        """Розрахувати площу металу (м²)."""
        return 0.0

    def calculate_weight(self) -> float:
        """Розрахувати вагу (кг)."""
        density = 7850
        return self.metal_area * (self.thickness.value / 1000) * density

    def calculate_price(self) -> float:
        """Базовий розрахунок ціни."""
        material_prices = {
            MaterialType.GALVANIZED: 120.0,
            MaterialType.STAINLESS: 350.0,
            MaterialType.ALUMINUM: 200.0,
        }
        base_price = self.metal_area * material_prices.get(self.material, 120.0)
        labor_cost = self.metal_area * 50
        if self.has_flanges:
            base_price += self.flange_count * self.flange_price
        return base_price + labor_cost

    def to_dict(self) -> dict:
        """Конвертувати у словник для серіалізації."""
        data = {
            "name": self.name,
            "product_type": self.product_type,
            "width": self.width,
            "height": self.height,
            "length": self.length,
            "thickness": self.thickness.value,
            "material": self.material.value,
            "quantity": self.quantity,
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
        # Додаємо специфічні поля підкласів
        for field_name in ["branch_width", "branch_height", "branch_length",
                           "branch_diameter", "branch_offset", "end_width",
                           "end_height", "end_diameter", "angle", "radius",
                           "top_extension", "bottom_extension",
                           "segments", "depth", "border", "bolt_count",
                           "bolt_diameter", "bolt_spacing", "fabric_type"]:
            if hasattr(self, field_name):
                data[field_name] = getattr(self, field_name)
        if hasattr(self, "_dynamic_params"):
            data.update(self._dynamic_params)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "StandardProduct":
        """Створити виріб зі словника."""
        material = MaterialType.GALVANIZED
        for m in MaterialType:
            if m.value == data.get("material", "оцинкована сталь"):
                material = m
                break
        thickness = Thickness.T0_7
        for t in Thickness:
            if abs(t.value - data.get("thickness", 0.7)) < 0.01:
                thickness = t
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


@dataclass
class RectDuct(StandardProduct):
    """Прямокутний повітропровід."""
    def calculate_metal_area(self) -> float:
        w = self.width / 1000
        h = self.height / 1000
        l = self.length / 1000
        perimeter = 2 * (w + h)
        return perimeter * l


@dataclass
class RoundDuct(StandardProduct):
    """Круглий повітропровід."""
    def calculate_metal_area(self) -> float:
        d = self.width / 1000
        l = self.length / 1000
        return math.pi * d * l


@dataclass
class RectFlange(StandardProduct):
    """Прямокутний фланець."""
    def calculate_metal_area(self) -> float:
        w = self.width / 1000
        h = self.height / 1000
        border = self.profile / 1000
        flange_w = w + 2 * border
        flange_h = h + 2 * border
        return flange_w * flange_h


@dataclass
class RoundFlange(StandardProduct):
    """Круглий фланець."""
    def calculate_metal_area(self) -> float:
        d = self.width / 1000
        border = self.profile / 1000
        outer_d = d + 2 * border
        return math.pi * (outer_d / 2) ** 2


@dataclass
class RectTee(StandardProduct):
    """Прямокутний трійник."""
    branch_width: float = 200
    branch_height: float = 200
    branch_length: float = 400
    branch_offset: float = 300

    def calculate_metal_area(self) -> float:
        w = self.width / 1000
        h = self.height / 1000
        l = self.length / 1000
        bw = self.branch_width / 1000
        bh = self.branch_height / 1000
        bl = self.branch_length / 1000
        main_area = 2 * (w + h) * l
        branch_area = 2 * (bw + bh) * bl
        return main_area + branch_area


@dataclass
class RoundTee(StandardProduct):
    """Круглий трійник."""
    branch_diameter: float = 200
    branch_length: float = 400
    branch_offset: float = 300

    def calculate_metal_area(self) -> float:
        d = self.width / 1000
        l = self.length / 1000
        bd = self.branch_diameter / 1000
        bl = self.branch_length / 1000
        main_area = math.pi * d * l
        branch_area = math.pi * bd * bl
        return main_area + branch_area


@dataclass
class RectTransition(StandardProduct):
    """Прямокутний перехід."""
    end_width: float = 300
    end_height: float = 150

    def calculate_metal_area(self) -> float:
        w1 = self.width / 1000
        h1 = self.height / 1000
        w2 = self.end_width / 1000
        h2 = self.end_height / 1000
        l = self.length / 1000
        avg_perimeter = 2 * ((w1 + w2) / 2 + (h1 + h2) / 2)
        return avg_perimeter * l


@dataclass
class RoundTransition(StandardProduct):
    """Круглий перехід."""
    end_diameter: float = 300

    def calculate_metal_area(self) -> float:
        d1 = self.width / 1000
        d2 = self.end_diameter / 1000
        l = self.length / 1000
        avg_d = (d1 + d2) / 2
        return math.pi * avg_d * l


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

    Формула площі металу:
      S = 2·(W+H)·[(top+bottom) + (r + H/2)·α]
      де W,H,r,top,bottom — в метрах, α — в радіанах.
    """
    angle: float = 90
    radius: float = 50          # внутрішній радіус горловини (F), мм
    top_extension: float = 100    # верхнє подовження (D), мм
    bottom_extension: float = 100 # нижнє подовження (E), мм

    def calculate_metal_area(self) -> float:
        w = self.width / 1000            # ширина, м
        h = self.height / 1000           # висота, м
        r = self.radius / 1000           # внутрішній радіус, м
        angle_rad = math.radians(self.angle)
        top_ext = self.top_extension / 1000
        bottom_ext = self.bottom_extension / 1000

        # Периметр перерізу
        perimeter = 2 * (w + h)

        # Площа прямих подовжень (бічна поверхня прямокутної труби)
        straight_area = perimeter * (top_ext + bottom_ext)

        # Площа зігнутої частини
        # Середній радіус = r + h/2  (ось згину проходить посередині перерізу)
        mean_radius = r + h / 2
        arc_length = mean_radius * angle_rad
        bend_area = perimeter * arc_length

        return straight_area + bend_area


@dataclass
class RoundElbow(StandardProduct):
    """Кругле коліно з подовженнями.

    Параметри (як у CAMduct):
      • width  — діаметр труби, мм
      • angle  — кут згину, °
      • radius — внутрішній радіус горловини, мм
      • top_extension    — верхнє подовження, мм
      • bottom_extension — нижнє подовження, мм

    Формула площі металу:
      S = π·D·[(top+bottom) + (r + D/2)·α]
      де D,r,top,bottom — в метрах, α — в радіанах.
    """
    angle: float = 90
    radius: float = 50          # внутрішній радіус горловини, мм
    top_extension: float = 100    # верхнє подовження, мм
    bottom_extension: float = 100 # нижнє подовження, мм

    def calculate_metal_area(self) -> float:
        d = self.width / 1000            # діаметр, м
        r = self.radius / 1000           # внутрішній радіус, м
        angle_rad = math.radians(self.angle)
        top_ext = self.top_extension / 1000
        bottom_ext = self.bottom_extension / 1000

        # Площа прямих подовжень (бічна поверхня циліндра)
        straight_area = math.pi * d * (top_ext + bottom_ext)

        # Площа зігнутої частини
        # Середній радіус = r + d/2  (ось згину посередині труби)
        mean_radius = r + d / 2
        arc_length = mean_radius * angle_rad
        bend_area = math.pi * d * arc_length

        return straight_area + bend_area


@dataclass
class RectCap(StandardProduct):
    """Прямокутна заглушка."""
    def calculate_metal_area(self) -> float:
        w = self.width / 1000
        h = self.height / 1000
        border = self.profile / 1000
        return (w + 2 * border) * (h + 2 * border)


@dataclass
class RoundCap(StandardProduct):
    """Кругла заглушка."""
    depth: float = 30

    def calculate_metal_area(self) -> float:
        d = self.width / 1000
        depth = self.depth / 1000
        base_area = math.pi * (d / 2) ** 2
        side_area = math.pi * d * depth
        return base_area + side_area


@dataclass
class FlexibleConnector(StandardProduct):
    """Гнучка вставка."""
    fabric_type: str = "поліестер"

    def calculate_metal_area(self) -> float:
        w = self.width / 1000
        h = self.height / 1000
        l = self.length / 1000
        return 2 * (w + h) * l

    def calculate_price(self) -> float:
        fabric_prices = {"поліестер": 80.0, "склотканина": 150.0, "ПВХ": 120.0}
        price_per_m2 = fabric_prices.get(self.fabric_type, 80.0)
        return self.metal_area * price_per_m2 * self.quantity


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

    def get_total_metal_area(self) -> float:
        return sum(p.metal_area * p.quantity for p in self.products)

    def get_total_weight(self) -> float:
        return sum(p.weight * p.quantity for p in self.products)

    def get_total_price(self) -> float:
        return sum(p.total_price for p in self.products)

    def get_specification(self) -> list[dict]:
        """Отримати згруповану специфікацію."""
        from collections import defaultdict
        grouped = defaultdict(lambda: {"quantity": 0, "products": []})
        for p in self.products:
            key = (p.product_type, p.width, p.height, p.length, p.thickness, p.material)
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
                "thickness": p.thickness.value,
                "material": p.material.value,
                "quantity": data["quantity"],
                "metal_area_m2": round(p.metal_area, 4),
                "total_metal_area_m2": round(p.metal_area * data["quantity"], 4),
                "unit_price": round(p.unit_price, 2),
                "total_price": round(p.unit_price * data["quantity"], 2),
            })
        return result

    def to_dict(self) -> list[dict]:
        return [p.to_dict() for p in self.products]

    def from_dict(self, data: list[dict]):
        self.products = [StandardProduct.from_dict(p) for p in data]

    def __len__(self):
        return len(self.products)


def make_rect_duct(width: float, height: float, length: float,
                   thickness: float = 0.7, material: MaterialType = MaterialType.GALVANIZED,
                   quantity: int = 1) -> RectDuct:
    """Фабричний метод для прямокутного повітропроводу."""
    thick = Thickness.T0_7
    for t in Thickness:
        if abs(t.value - thickness) < 0.01:
            thick = t
            break
    return RectDuct(
        name=f"Повітропровід {width:.0f}×{height:.0f}×{length:.0f}",
        product_type="повітропровід прямокутний",
        width=width, height=height, length=length,
        thickness=thick, material=material, quantity=quantity,
    )


def make_round_duct(diameter: float, length: float,
                   thickness: float = 0.7, material: MaterialType = MaterialType.GALVANIZED,
                   quantity: int = 1) -> RoundDuct:
    """Фабричний метод для круглого повітропроводу."""
    thick = Thickness.T0_7
    for t in Thickness:
        if abs(t.value - thickness) < 0.01:
            thick = t
            break
    return RoundDuct(
        name=f"Повітропровід Ø{diameter:.0f}×{length:.0f}",
        product_type="повітропровід круглий",
        width=diameter, height=diameter, length=length,
        thickness=thick, material=material, quantity=quantity,
    )
