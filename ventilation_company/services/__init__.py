"""Сервісний шар — бізнес-логіка відокремлена від GUI.

Ледачий пакет (PEP 562): імпорт підмодуля з services (наприклад,
business_settings) не тягне за собою pricing_service/salary_service,
тому жоден порядок імпортів не створює циклічного імпорту
services <-> calculations.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - лише для типізації/IDE
    from .pricing_service import PricingService
    from .project_service import ProjectService
    from .salary_service import SalaryService

__all__ = ["PricingService", "SalaryService", "ProjectService"]


def __getattr__(name: str):
    if name in ("PricingService", "SalaryService", "ProjectService"):
        from . import pricing_service, project_service, salary_service

        return {
            "PricingService": pricing_service.PricingService,
            "SalaryService": salary_service.SalaryService,
            "ProjectService": project_service.ProjectService,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
