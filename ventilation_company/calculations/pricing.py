"""Двигун ціноутворення — Cost-plus, Competitive, Value-based."""

from decimal import Decimal

from ventilation_company.utils.logging_config import get_logger

_logger = get_logger("pricing")

from ventilation_company.config import VAT_RATE, OVERHEAD_PERCENTAGE


class PricingEngine:
    """Розрахунок ціни виробу/проєкту різними методами."""

    def __init__(self, base_cost: float = 10000, markup_percent: float = None):
        self.base_cost = float(base_cost)
        self.markup_percent = markup_percent if markup_percent is not None else 30.0

    def cost_plus_pricing(self) -> dict:
        markup_amount = self.base_cost * self.markup_percent / 100
        price_without_vat = self.base_cost + markup_amount
        vat_amount = price_without_vat * VAT_RATE / 100
        final_price = price_without_vat + vat_amount
        return {
            "method": "cost_plus",
            "base_cost": self.base_cost,
            "markup_percent": self.markup_percent,
            "markup_amount": round(markup_amount, 2),
            "price_without_vat": round(price_without_vat, 2),
            "vat_percent": VAT_RATE,
            "vat_amount": round(vat_amount, 2),
            "final_price": round(final_price, 2),
        }

    def competitive_pricing(self, competitor_price: float = 15000) -> dict:
        min_price = self.base_cost * 1.10
        recommended = max(min_price, competitor_price * 0.95)
        vat_amount = recommended * VAT_RATE / 100
        return {
            "method": "competitive",
            "base_cost": self.base_cost,
            "competitor_price": competitor_price,
            "recommended_price_without_vat": round(recommended, 2),
            "vat_amount": round(vat_amount, 2),
            "final_price": round(recommended + vat_amount, 2),
        }

    def value_based_pricing(self, client_value: float = 50000) -> dict:
        min_price = self.base_cost * 1.15
        max_price = client_value * 0.60
        price_without_vat = max(min_price, min(max_price, self.base_cost * 2.5))
        vat_amount = price_without_vat * VAT_RATE / 100
        return {
            "method": "value_based",
            "base_cost": self.base_cost,
            "client_value": client_value,
            "price_without_vat": round(price_without_vat, 2),
            "vat_amount": round(vat_amount, 2),
            "final_price": round(price_without_vat + vat_amount, 2),
        }

    def compare_methods(self, competitor_price: float = 15000, client_value: float = 50000) -> dict:
        return {
            "cost_plus": self.cost_plus_pricing(),
            "competitive": self.competitive_pricing(competitor_price),
            "value_based": self.value_based_pricing(client_value),
        }
