"""ProjectService — робота з проєктом."""

from ventilation_company.services.pricing_service import PricingService


class ProjectService:
    """Завантаження, збереження, перерахунок проєкту."""

    @staticmethod
    def recalculate_products(products: list) -> int:
        """Перерахувати ціни для списку виробів. Повертає кількість оновлених."""
        updated = 0
        for p in products:
            try:
                result = PricingService.calculate(p)
                p.update(result)
                updated += 1
            except Exception:
                pass
        return updated
