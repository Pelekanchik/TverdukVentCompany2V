"""ORM-репозиторії бази даних."""

from ventilation_company.database.repositories.calc_repo import CalculationRepository
from ventilation_company.database.repositories.material_repo import (
    MaterialRepository as MaterialRepository,
)
from ventilation_company.database.repositories.overhead_repo import (
    OverheadRepository as OverheadRepository,
)
from ventilation_company.database.repositories.product_repo import (
    ProductRepository as ProductRepository,
)
from ventilation_company.database.repositories.settings_repo import (
    SettingsRepository as SettingsRepository,
)

__all__ = [
    "CalculationRepository",
    "MaterialRepository",
    "OverheadRepository",
    "ProductRepository",
    "SettingsRepository",
]
