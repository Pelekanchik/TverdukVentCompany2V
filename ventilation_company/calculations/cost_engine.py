"""CostEngine — розрахунок собівартості та ціни виробу.

Етап 3: Синхронізація ціноутворення з новими площами.

Використовує:
  • pricing_settings.json — ціни матеріалів, тарифи робіт, націнки
  • manufacturing_settings.json — KIM, припуски (вже враховані в material_area)

Розрахунок:
  1. material_cost  = material_area × price_per_m2
  2. labor_cost     = blank_area × rate_per_m2 × (1 + difficulty/100)
  3. overhead_cost  = (material_cost + labor_cost) × overhead_percent / 100
  4. depreciation   = (material_cost + labor_cost) × equipment_depreciation / 100
  5. base_cost      = material_cost + labor_cost + overhead_cost + depreciation
  6. profit         = base_cost × markup_percent / 100
  7. price_no_vat   = base_cost + profit
  8. vat            = price_no_vat × vat_rate / 100
  9. final_price    = price_no_vat + vat
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ventilation_company.manufacturing_params import get_material_price
from ventilation_company.utils.logging_config import get_logger

_logger = get_logger("cost_engine")

_PRICING_PATH = Path(__file__).parent.parent / "data" / "pricing_settings.json"


def _load_pricing() -> dict[str, Any]:
    try:
        with open(_PRICING_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _logger.error("Не вдалося завантажити %s", _PRICING_PATH)
        return {}


_pricing_cache: dict[str, Any] | None = None


def _pricing() -> dict[str, Any]:
    global _pricing_cache
    if _pricing_cache is None:
        _pricing_cache = _load_pricing()
    return _pricing_cache


def clear_cache() -> None:
    global _pricing_cache
    _pricing_cache = None


# ═══════════════════════════════════════════════════════════
# DTO для результату розрахунку
# ═══════════════════════════════════════════════════════════

@dataclass
class CostBreakdown:
    """Детальний розбив собівартості."""

    # Вхідні дані
    product_name: str = ""
    material_name: str = ""
    thickness_mm: float = 0.0
    surface_area_m2: float = 0.0
    blank_area_m2: float = 0.0
    material_area_m2: float = 0.0
    quantity: int = 1

    # Статті витрат
    material_cost: float = 0.0
    labor_cost: float = 0.0
    overhead_cost: float = 0.0
    depreciation_cost: float = 0.0
    flange_cost: float = 0.0
    other_cost: float = 0.0

    # Підсумки
    base_cost: float = 0.0
    profit: float = 0.0
    price_no_vat: float = 0.0
    vat_amount: float = 0.0
    final_price: float = 0.0

    # Налаштування, що застосовувалися
    material_price_per_m2: float = 0.0
    labor_rate_per_m2: float = 0.0
    labor_difficulty_percent: float = 0.0
    overhead_percent: float = 0.0
    depreciation_percent: float = 0.0
    markup_percent: float = 0.0
    category_waste_percent: float = 0.0
    category_waste_cost: float = 0.0
    vat_rate: float = 20.0

    def per_unit(self) -> "CostBreakdown":
        """Розбив на 1 штуку (якщо quantity > 1)."""
        if self.quantity <= 1:
            return self
        return CostBreakdown(
            product_name=self.product_name,
            material_name=self.material_name,
            thickness_mm=self.thickness_mm,
            surface_area_m2=self.surface_area_m2 / self.quantity,
            blank_area_m2=self.blank_area_m2 / self.quantity,
            material_area_m2=self.material_area_m2 / self.quantity,
            quantity=1,
            material_cost=self.material_cost / self.quantity,
            labor_cost=self.labor_cost / self.quantity,
            overhead_cost=self.overhead_cost / self.quantity,
            depreciation_cost=self.depreciation_cost / self.quantity,
            flange_cost=self.flange_cost / self.quantity,
            other_cost=self.other_cost / self.quantity,
            base_cost=self.base_cost / self.quantity,
            profit=self.profit / self.quantity,
            price_no_vat=self.price_no_vat / self.quantity,
            vat_amount=self.vat_amount / self.quantity,
            final_price=self.final_price / self.quantity,
            category_waste_percent=self.category_waste_percent,
            category_waste_cost=self.category_waste_cost / self.quantity,
            material_price_per_m2=self.material_price_per_m2,
            labor_rate_per_m2=self.labor_rate_per_m2,
            labor_difficulty_percent=self.labor_difficulty_percent,
            overhead_percent=self.overhead_percent,
            depreciation_percent=self.depreciation_percent,
            markup_percent=self.markup_percent,
            vat_rate=self.vat_rate,
        )

    def to_dict(self) -> dict:
        return {
            "product": self.product_name,
            "material": self.material_name,
            "thickness_mm": self.thickness_mm,
            "quantity": self.quantity,
            "areas": {
                "surface_m2": round(self.surface_area_m2, 4),
                "blank_m2": round(self.blank_area_m2, 4),
                "material_m2": round(self.material_area_m2, 4),
            },
            "costs": {
                "material": round(self.material_cost, 2),
                "labor": round(self.labor_cost, 2),
                "overhead": round(self.overhead_cost, 2),
                "depreciation": round(self.depreciation_cost, 2),
                "flanges": round(self.flange_cost, 2),
                "other": round(self.other_cost, 2),
                "base": round(self.base_cost, 2),
                "profit": round(self.profit, 2),
            },
            "pricing": {
                "price_no_vat": round(self.price_no_vat, 2),
                "vat": round(self.vat_amount, 2),
                "final_price": round(self.final_price, 2),
            },
            "rates_applied": {
                "material_price": self.material_price_per_m2,
                "labor_rate": self.labor_rate_per_m2,
                "labor_difficulty_%": self.labor_difficulty_percent,
                "overhead_%": self.overhead_percent,
                "depreciation_%": self.depreciation_percent,
                "markup_%": self.markup_percent,
                "vat_%": self.vat_rate,
            },
        }


# ═══════════════════════════════════════════════════════════
# CostEngine
# ═══════════════════════════════════════════════════════════

class CostEngine:
    """Двигун розрахунку собівартості та ціни."""

    def __init__(self):
        self.pricing = _pricing()

    def _get_labor_rate(self, product_type: str) -> tuple[float, float]:
        """Отримати тариф роботи і % складності за типом виробу.

        Returns:
            (rate_per_m2, difficulty_percent)
        """
        labor = self.pricing.get("labor_rates", {})
        pt = product_type.lower().strip()
        data = labor.get(pt, {"rate_per_m2": 100.0, "difficulty_percent": 0.0})
        return data.get("rate_per_m2", 100.0), data.get("difficulty_percent", 0.0)

    def _get_overhead_percent(self) -> float:
        """Загальний % накладних витрат (overhead)."""
        overhead = self.pricing.get("overhead", {})
        # Загальні накладні = waste + інші (електроенергія, оренда, транспорт)
        # Для спрощення беремо waste_percent як базу накладних
        return overhead.get("waste_percent", 8.0)

    def _get_depreciation_percent(self) -> float:
        """Сумарний % амортизації обладнання."""
        dep = self.pricing.get("depreciation", {})
        return sum(
            dep.get(k, 0.0)
            for k in ["guillotine_percent", "bending_percent", "welding_percent", "plasma_percent"]
        )

    def _get_markup_percent(self) -> float:
        """Базова націнка, %."""
        return self.pricing.get("markup_percent", 30.0)

    def _get_category_waste_percent(self, product_type: str) -> float:
        """Отримати %% запасу на брак/поворот для категорії виробу."""
        factors = self.pricing.get("category_waste_factors", {})
        pt = product_type.lower().strip()
        if "повітропровід прямокутний" in pt:
            return factors.get("rect_duct", 0.0)
        elif "повітропровід круглий" in pt:
            return factors.get("round_duct", 0.0)
        elif any(k in pt for k in ["фланець прямокутний", "трійник прямокутний", "перехід прямокутний", "відвід прямокутний", "заглушка прямокутна"]):
            return factors.get("rect_fitting", 0.0)
        elif any(k in pt for k in ["фланець круглий", "трійник круглий", "перехід круглий", "відвід круглий", "заглушка кругла"]):
            return factors.get("round_fitting", 0.0)
        return 0.0

    def _get_vat_rate(self) -> float:
        return 20.0

    def calculate(
        self,
        product_type: str,
        material_name: str,
        thickness_mm: float,
        surface_area_m2: float,
        blank_area_m2: float,
        material_area_m2: float,
        quantity: int = 1,
        flange_count: int = 0,
        flange_price: float = 0.0,
        category_waste_percent: float = 0.0,
        custom_markup_percent: float | None = None,
    ) -> CostBreakdown:
        """Розрахувати собівартість і ціну виробу.

        Args:
            product_type: Тип виробу (напр. "повітропровід прямокутний").
            material_name: Назва матеріалу ("оцинкована сталь" тощо).
            thickness_mm: Товщина металу, мм.
            surface_area_m2: Площа поверхні готового виробу, м².
            blank_area_m2: Площа заготовки, м².
            material_area_m2: Площа матеріалу з KIM, м².
            quantity: Кількість.
            flange_count: Кількість фланців.
            flange_price: Ціна одного фланця.
            custom_markup_percent: Кастомна націнка (якщо None — з JSON).

        Returns:
            CostBreakdown з детальним розбивом.
        """
        result = CostBreakdown(
            product_name=product_type,
            material_name=material_name,
            thickness_mm=thickness_mm,
            surface_area_m2=surface_area_m2 * quantity,
            blank_area_m2=blank_area_m2 * quantity,
            material_area_m2=material_area_m2 * quantity,
            quantity=quantity,
        )

        # ── 1. Ціна матеріалу ──
        material_price = get_material_price(material_name, thickness_mm)
        result.material_price_per_m2 = material_price
        result.material_cost = material_area_m2 * material_price * quantity

        # ── 1b. Запас на брак/поворот по категорії ──
        if category_waste_percent == 0.0:
            category_waste_percent = self._get_category_waste_percent(product_type)
        result.category_waste_percent = category_waste_percent
        result.category_waste_cost = result.material_cost * category_waste_percent / 100
        result.material_cost += result.category_waste_cost

        # ── 2. Вартість роботи ──
        labor_rate, labor_difficulty = self._get_labor_rate(product_type)
        result.labor_rate_per_m2 = labor_rate
        result.labor_difficulty_percent = labor_difficulty
        result.labor_cost = blank_area_m2 * labor_rate * (1 + labor_difficulty / 100) * quantity

        # ── 3. Фланці ──
        result.flange_cost = flange_count * flange_price * quantity

        # ── 4. Накладні витрати ──
        result.overhead_percent = self._get_overhead_percent()
        subtotal = result.material_cost + result.labor_cost + result.flange_cost
        result.overhead_cost = subtotal * result.overhead_percent / 100

        # ── 5. Амортизація ──
        result.depreciation_percent = self._get_depreciation_percent()
        result.depreciation_cost = subtotal * result.depreciation_percent / 100

        # ── 6. Базова собівартість ──
        result.base_cost = (
            result.material_cost
            + result.labor_cost
            + result.overhead_cost
            + result.depreciation_cost
            + result.flange_cost
            + result.other_cost
        )
        result.base_cost = (
            result.material_cost
            + result.labor_cost
            + result.overhead_cost
            + result.depreciation_cost
            + result.flange_cost
            + result.other_cost
            + result.category_waste_cost
        )

        # ── 7. Нцінка і прибуток ──
        result.markup_percent = custom_markup_percent if custom_markup_percent is not None else self._get_markup_percent()
        result.profit = result.base_cost * result.markup_percent / 100

        # ── 8. Ціна без ПДВ ──
        result.price_no_vat = result.base_cost + result.profit

        # ── 9. ПДВ ──
        result.vat_rate = self._get_vat_rate()
        result.vat_amount = result.price_no_vat * result.vat_rate / 100

        # ── 10. Кінцева ціна ──
        result.final_price = result.price_no_vat + result.vat_amount

        _logger.debug(
            "[CostEngine] %s | mat=%.2f | labor=%.2f | overhead=%.2f | "
            "deprec=%.2f | base=%.2f | profit=%.2f | final=%.2f",
            product_type,
            result.material_cost,
            result.labor_cost,
            result.overhead_cost,
            result.depreciation_cost,
            result.base_cost,
            result.profit,
            result.final_price,
        )

        return result

    def calculate_from_product(self, product: Any) -> CostBreakdown:
        """Розрахувати ціну з об'єкта StandardProduct.

        Args:
            product: Об'єкт з атрибутами: product_type, material, thickness,
                     surface_area, blank_area, material_area, quantity,
                     has_flanges, flange_count, flange_price.
        """
        return self.calculate(
            product_type=getattr(product, "product_type", ""),
            material_name=getattr(product, "_material_str", lambda: "оцинкована сталь")(),
            thickness_mm=getattr(product, "_thickness_float", lambda: 0.7)(),
            surface_area_m2=getattr(product, "surface_area", 0.0),
            blank_area_m2=getattr(product, "blank_area", 0.0),
            material_area_m2=getattr(product, "material_area", 0.0),
            quantity=getattr(product, "quantity", 1),
            flange_count=getattr(product, "flange_count", 0),
            flange_price=float(getattr(product, "flange_price", 0)),
            category_waste_percent=getattr(product, "category_waste_percent", 0.0),
        )
