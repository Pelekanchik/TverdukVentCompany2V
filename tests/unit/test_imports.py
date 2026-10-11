"""Тести на відсутність циклічних імпортів (будь-який порядок імпорту)."""

import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _run_import(code: str):
    """Виконати імпорт у чистому інтерпретаторі (підпроцес)."""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"Імпорт впав:\n{result.stderr}"


def test_calculations_submodule_first():
    _run_import(
        "from ventilation_company.calculations.safe_evaluator import SafeFormulaEvaluator;"
        "from ventilation_company.services.business_settings import BusinessSettings;"
        "print(SafeFormulaEvaluator, BusinessSettings)"
    )


def test_services_submodule_first():
    _run_import(
        "from ventilation_company.services.pricing_settings import PricingSettings;"
        "from ventilation_company.calculations.cost_engine import CostEngine;"
        "print(PricingSettings, CostEngine)"
    )


def test_package_level_reexports():
    _run_import(
        "from ventilation_company.calculations import CostEngine, CostBreakdown;"
        "from ventilation_company.services import PricingService, SalaryService, ProjectService;"
        "print(CostEngine, CostBreakdown, PricingService, SalaryService, ProjectService)"
    )


def test_gui_import_last():
    _run_import(
        "from ventilation_company.services.audit_service import log_action;"
        "from ventilation_company.gui_pyside6.workers import FunctionWorker;"
        "from ventilation_company.calculations.cost_engine import CostEngine;"
        "print(log_action, FunctionWorker, CostEngine)"
    )
