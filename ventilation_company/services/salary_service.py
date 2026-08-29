"""SalaryService — уніфікований розрахунок зарплати."""

from ventilation_company.gui.settings_tab import PricingSettings


class SalaryService:
    """Розрахунок зарплати для Виробництва, Специфікації, Архіву."""

    @staticmethod
    def calculate(
        product_type: str,
        dimensions: str,
        quantity: int = 1,
        area: float = None,
    ) -> float:
        """
        Якщо area передано (наприклад, metal_area_m2) — використовує його.
        Інакше — рахує площу з розмірів.
        """
        settings = PricingSettings.get_instance()
        labor = settings.get_labor_rate(product_type or "")
        # Якщо конкретний тип не знайдено — беремо default
        if not labor or labor.get("rate_per_m2") is None:
            labor = settings.get_labor_rate("default") or {}
        rate = labor.get("rate_per_m2", 120.0)
        difficulty = labor.get("difficulty_percent", 0.0)

        if area is None:
            try:
                parts = dimensions.replace("×", "x").replace("X", "x").split("x")
                if len(parts) >= 3:
                    w, h, l = float(parts[0]), float(parts[1]), float(parts[2])
                    area = 2 * (w / 1000 + h / 1000) * (l / 1000)
                elif len(parts) == 2:
                    d, l = float(parts[0]), float(parts[1])
                    area = 3.14159 * (d / 1000) * (l / 1000)
                else:
                    area = 0
            except (ValueError, IndexError):
                area = 0

        return round(area * rate * (1 + difficulty / 100) * quantity, 2)
