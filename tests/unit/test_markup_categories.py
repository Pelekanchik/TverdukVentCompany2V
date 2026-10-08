"""Тести get_markup_categories() — націнки зі збережених налаштувань.

Канонічна реалізація — у services/pricing_settings.py; модуль GUI
(gui_pyside6/pricing_tab.py) лише делегує до неї. Тести покривають обидва
рівні: сервіс напряму та GUI-обгортку (через той самий ізольований файл).
"""

import json

import pytest

from ventilation_company.services import pricing_settings as ps_module
from ventilation_company.services.pricing_settings import (
    DEFAULT_MARKUP_CATEGORIES,
    MARKUP_CATEGORY_NAMES,
    PricingSettings,
)


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    """Ізольований singleton PricingSettings у тимчасовому файлі.

    Повертає (path, apply) — apply(data) записує дані у файл до завантаження.
    """
    path = tmp_path / "pricing_settings.json"
    state = {"ready": False}

    def apply(data=None):
        if data is not None:
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(ps_module.PricingSettings, "_instance", None)
        PricingSettings.get_instance(str(path))
        state["ready"] = True

    yield path, apply
    monkeypatch.setattr(ps_module.PricingSettings, "_instance", None)


EXPECTED_DEFAULTS = [(name, DEFAULT_MARKUP_CATEGORIES[name]) for name in MARKUP_CATEGORY_NAMES]


def test_defaults_when_no_settings(isolated_settings):
    _, apply = isolated_settings
    apply()

    assert ps_module.get_markup_categories() == EXPECTED_DEFAULTS


def test_saved_categories_are_used(isolated_settings):
    _, apply = isolated_settings
    apply({"markup_categories": {"Стандартна": 50.0, "Преміум": 70.0, "Економ": 35.0}})

    cats = ps_module.get_markup_categories()
    assert ("Стандартна", 50.0) in cats
    assert ("Преміум", 70.0) in cats
    assert ("Економ", 35.0) in cats


def test_partial_categories_fall_back_to_defaults(isolated_settings):
    _, apply = isolated_settings
    apply({"markup_categories": {"Преміум": 65.0}})

    cats = ps_module.get_markup_categories()
    assert ("Преміум", 65.0) in cats
    assert ("Стандартна", DEFAULT_MARKUP_CATEGORIES["Стандартна"]) in cats


def test_legacy_flat_matrix_is_migrated(isolated_settings):
    """Стара GUI писала плоскі категорії у ключ «markup_matrix»."""
    _, apply = isolated_settings
    apply(
        {
            "markup_matrix": {
                "Стандартна": 50.0,
                "Преміум": 70.0,
                "Економ": 35.0,
                "Спецзамовлення": 150.0,
            }
        }
    )

    cats = ps_module.get_markup_categories()
    assert ("Стандартна", 50.0) in cats
    assert ("Спецзамовлення", 150.0) in cats
    # Категорії зберігаються у канонічному ключі після save()
    data = json.loads((isolated_settings[0]).read_text(encoding="utf-8"))
    assert data["markup_categories"]["Стандартна"] == 50.0
    # Вкладена матриця для розрахунку — дефолтна, не плоска
    assert "цинк" in data["markup_matrix"]


def test_gui_wrapper_delegates_to_service(isolated_settings):
    _, apply = isolated_settings
    apply({"markup_categories": {"Стандартна": 44.0}})

    from ventilation_company.gui_pyside6.pricing_tab import get_markup_categories

    cats = get_markup_categories()
    assert ("Стандартна", 44.0) in cats
