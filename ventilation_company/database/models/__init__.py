"""ORM-моделі бази даних VentCompany.

Важливо: імпортувати всі моделі тут, щоб Base.metadata
міг створити всі таблиці через create_all().
"""

from ventilation_company.database.models.project import (
    Project,
    ProjectComponent,
    ProjectMaterial,
    ProjectWork,
)
from ventilation_company.database.models.product import (
    ProductType,
    ProductSubtype,
    SizeRange,
)
from ventilation_company.database.models.calculation import Calculation
from ventilation_company.database.models.employee import Employee
from ventilation_company.database.models.work_catalog import WorkCatalog
from ventilation_company.database.models.calc import (
    CalcMaterial,
    SubtypeMaterial,
    CalcCalculation,
    CalcItem,
    OverheadItem,
    CalcSetting,
)
from ventilation_company.database.models.unified import (
    ProjectProduct,
    Specification,
    CuttingPlan,
    StandardProductLibrary,
    MaterialPrice,
    Client,
    Interaction,
    Payment,
    ClientProject,
    WarrantyReminder,
)
from ventilation_company.database.models.user import UserORM

__all__ = [
    "Project",
    "ProjectComponent",
    "ProjectMaterial",
    "ProjectWork",
    "ProductType",
    "ProductSubtype",
    "SizeRange",
    "Calculation",
    "Employee",
    "WorkCatalog",
    "CalcMaterial",
    "SubtypeMaterial",
    "CalcCalculation",
    "CalcItem",
    "OverheadItem",
    "CalcSetting",
    "ProjectProduct",
    "Specification",
    "CuttingPlan",
    "StandardProductLibrary",
    "MaterialPrice",
    "Client",
    "Interaction",
    "Payment",
    "ClientProject",
    "WarrantyReminder",
    "UserORM",
]
