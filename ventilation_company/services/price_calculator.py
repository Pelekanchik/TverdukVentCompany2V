"""Розрахунок цін виробів.

Винесено з products_tab.py та settings_tab.py для розділення
GUI і бізнес-логіки.
"""

from ventilation_company.gui.settings_tab import PricingSettings
from ventilation_company.gui.markup_matrix_tab import classify_product, is_standard_size


class PriceCalculator:
    """Калькулятор цін для виробів.

    Інкапсулює всю логіку ціноутворення, яка раніше була
    розмазана по GUI-класах.
    """

    def __init__(self):
        self._pricing = PricingSettings.get_instance()

    def calculate(self, product_data: dict) -> float:
        """Розрахувати ціну виробу (коротка форма).

        Args:
            product_data: Словник з параметрами виробу

        Returns:
            Ціна за одиницю (грн)
        """
        return self._pricing.calculate_product_price(product_data)

    def calculate_detailed(self, product_data: dict) -> dict:
        """Розрахувати ціну з покроковим розбиттям.

        Returns:
            {
                "formula": str,
                "steps": [{"name": str, "calc": str, "value": float}, ...],
                "total": float,
            }
        """
        return self._pricing.calculate_product_price_detailed(product_data)

    def get_markup_info(self, product_data: dict) -> dict:
        """Отримати інформацію про категорію націнки.

        Returns:
            {
                "material_key": str,
                "category_key": str,
                "size_label": str,
                "markup_percent": float,
                "is_standard": bool,
            }
        """
        name = product_data.get("name", "")
        ptype = product_data.get("type", product_data.get("product_type", ""))
        material = product_data.get("material", "оцинкована сталь")
        width = product_data.get("width", 0)
        height = product_data.get("height", 0)
        length = product_data.get("length", 0)
        diameter = product_data.get("diameter", 0)

        mat_key, cat_key = classify_product(name, ptype, material)
        is_round = "кругл" in name.lower() or "round" in name.lower() or "спірал" in name.lower()
        is_std = is_standard_size(width, height, length, diameter if is_round else 0)
        size_label = "стандарт" if is_std else "нестандарт"
        markup_pct = self._pricing.get_markup_percent(product_data)

        return {
            "material_key": mat_key,
            "category_key": cat_key,
            "size_label": size_label,
            "markup_percent": markup_pct,
            "is_standard": is_std,
        }

    def build_preview_data(
        self,
        ptype: str,
        selected_name: str,
        width: float,
        height: float,
        length: float,
        material_str: str,
        thickness_str: str,
        quantity: int,
        profile: float,
        extra_params: dict,
        dynamic_params: dict,
        metal_area: float,
    ) -> dict:
        """Побудувати словник product_data для розрахунку ціни.

        Args:
            ptype: Технічний тип виробу
            selected_name: Назва для користувача
            width, height, length: Розміри (мм)
            material_str: Назва матеріалу
            thickness_str: Товщина ("0.7" тощо)
            quantity: Кількість
            profile: Розмір профілю (мм)
            extra_params: Додаткові параметри (angle, radius тощо)
            dynamic_params: Кастомні параметри
            metal_area: Розрахована площа металу (м²)

        Returns:
            Словник, готовий для calculate() / calculate_detailed()
        """
        density = 7850
        thickness_val = float(thickness_str) if isinstance(thickness_str, str) else thickness_str
        weight = metal_area * (thickness_val / 1000) * density

        data = {
            "name": selected_name,
            "type": ptype if not ptype.startswith("custom_") else selected_name,
            "material": material_str,
            "thickness": thickness_val,
            "metal_area_m2": metal_area,
            "metal_area": metal_area,
            "weight_kg": weight,
            "weight": weight,
            "quantity": quantity,
            "width": width,
            "height": height,
            "length": length,
            "profile": profile,
        }
        data.update(extra_params)
        data.update(dynamic_params)
        return data
