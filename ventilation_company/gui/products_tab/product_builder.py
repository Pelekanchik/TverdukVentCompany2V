"""Будівник продуктів та валідація введених даних."""

from dataclasses import dataclass, field
from typing import Any

from ventilation_company.standard_products import StandardProduct
from ventilation_company.gui.products_tab.formula_utils import safe_float


@dataclass
class CustomProduct(StandardProduct):
    """Кастомний продукт з формулою розрахунку площі."""
    custom_formula: str = ""
    extra_vars: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name:
            self.name = "Кастомний виріб"

    def calculate_metal_area(self) -> float:
        if self.custom_formula:
            try:
                from ventilation_company.utils.safe_evaluator import safe_eval
                context = {
                    "w": self.width, "h": self.height,
                    "d": self.diameter, "l": self.length,
                    "pi": 3.14159265359,
                    **self.extra_vars,
                }
                return safe_eval(self.custom_formula, context)
            except Exception:
                pass
        return super().calculate_metal_area()


def validate_product_input(
    width_var, height_var, length_var, qty_var,
    price_var, flange_vars, extra_vars,
    ptype: str, selected_name: str,
) -> tuple[bool, dict[str, Any] | str]:
    """Валідувати введені дані для продукту.

    Повертає (True, data_dict) або (False, error_message).
    """
    def get_float(var, name):
        try:
            val = float(var.get().replace(",", "."))
            if val < 0:
                return False, f"{name} не може бути від\u0027ємним"
            return True, val
        except ValueError:
            return False, f"Невірне значення {name}"

    def get_int(var, name):
        try:
            val = int(var.get())
            if val < 1:
                return False, f"{name} має бути ≥ 1"
            return True, val
        except ValueError:
            return False, f"Невірне значення {name}"

    ok, w = get_float(width_var, "Ширина/Діаметр")
    if not ok:
        return False, w

    h = 0.0
    if ptype.startswith("прямокутн"):
        ok, h = get_float(height_var, "Висота")
        if not ok:
            return False, h

    ok, length = get_float(length_var, "Довжина")
    if not ok:
        return False, length

    ok, qty = get_int(qty_var, "Кількість")
    if not ok:
        return False, qty

    ok, price = get_float(price_var, "Ціна")
    if not ok:
        return False, price

    flange_type = flange_vars.get("type", "")
    flange_qty = 0
    if flange_type:
        ok, flange_qty = get_int(flange_vars.get("qty"), "Кількість фланців")
        if not ok:
            return False, flange_qty

    extra = {}
    for key, var in extra_vars.items():
        try:
            extra[key] = safe_float(var.get())
        except Exception:
            extra[key] = 0.0

    data = {
        "width": w, "height": h, "length": length,
        "quantity": qty, "price": price,
        "flange_type": flange_type, "flange_qty": flange_qty,
        "extra": extra,
    }
    return True, data
