"""Модуль розрахунків: ціноутворення, зарплата, собівартість.

Ледачий пакет (PEP 562): імпорт підпакета чи модуля з calculations не
тягне за собою cost_engine, тому жоден порядок імпортів не створює
циклічного імпорту calculations <-> services.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - лише для типізації/IDE
    from ventilation_company.calculations.cost_engine import CostBreakdown, CostEngine

__all__ = ["CostBreakdown", "CostEngine"]


def __getattr__(name: str):
    if name in ("CostBreakdown", "CostEngine"):
        from ventilation_company.calculations.cost_engine import CostBreakdown, CostEngine

        return {"CostBreakdown": CostBreakdown, "CostEngine": CostEngine}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
