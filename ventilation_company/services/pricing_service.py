"""PricingService — єдиний сервіс розрахунку ціни виробу."""

from decimal import Decimal
from ventilation_company.standard_products import StandardProduct


class PricingService:
    """GUI тільки викликає цей сервіс. Тут зосереджена ВСЯ логіка ціноутворення."""

    @staticmethod
    def calculate(product_dict: dict) -> dict:
        """
        Приймає dict виробу (як у БД).
        Повертає dict з розрахованими полями.
        """
        try:
            product = StandardProduct.from_dict(product_dict)
            product.recalculate_price()
            breakdown = product.get_cost_breakdown()
            qty = product_dict.get("quantity", 1) or 1

            return {
                "unit_price": float(product.unit_price),
                "total_price": float(product.total_price),
                "cost_price": float(breakdown.base_cost / qty),
                "salary_per_unit": round(breakdown.labor_cost / qty, 2),
                "salary_total": round(breakdown.labor_cost, 2),
                "material_cost": round(breakdown.material_cost / qty, 2),
                "overhead_cost": round(
                    (breakdown.overhead_cost + breakdown.depreciation_cost) / qty, 2
                ),
            }
        except Exception:
            # Якщо не вдалося — залишаємо оригінал
            return {
                "unit_price": product_dict.get("unit_price", 0),
                "total_price": product_dict.get("total_price", 0),
                "cost_price": product_dict.get("cost_price", 0),
                "salary_per_unit": product_dict.get("salary_per_unit", 0),
                "salary_total": product_dict.get("salary_total", 0),
                "material_cost": product_dict.get("material_cost", 0),
                "overhead_cost": product_dict.get("overhead_cost", 0),
            }
