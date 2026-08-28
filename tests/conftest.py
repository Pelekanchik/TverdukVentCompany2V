"""Загальні фікстури та утиліти для тестів VentCompany."""

import os
import sys
import tempfile
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from ventilation_company.gui.settings_tab import PricingSettings


@pytest.fixture
def temp_db():
    """Тимчасова БД для тестів."""
    from ventilation_company.db_integration import ProjectDatabase
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = ProjectDatabase(path)
    yield db
    # Не видаляємо файл — Windows сам звільнить його після завершення pytest
    # tempfile очистить його при наступному запуску


@pytest.fixture
def default_settings():
    """Стандартні налаштування ціноутворення."""
    return PricingSettings.get_instance()


@pytest.fixture
def sample_project_data():
    """Тестові дані проєкту."""
    return {
        "project_name": "Тестовий проєкт",
        "products": [
            {
                "name": "Повітропровід 400×200×1000",
                "product_type": "повітропровід прямокутний",
                "width": 400,
                "height": 200,
                "length": 1000,
                "thickness": 0.7,
                "material": "оцинкована сталь",
                "quantity": 5,
                "metal_area_m2": 1.2,
            },
            {
                "name": "Перехід 400×400→300×150",
                "product_type": "перехід прямокутний",
                "width": 400,
                "height": 400,
                "length": 500,
                "thickness": 0.7,
                "material": "оцинкована сталь",
                "quantity": 2,
                "metal_area_m2": 1.05,
            },
        ],
    }
