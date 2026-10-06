"""Тести get_markup_categories() — націнки зі збережених налаштувань."""

import json


def test_defaults_when_no_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "ventilation_company.gui_pyside6.pricing_tab.SETTINGS_PATH",
        tmp_path / "missing.json",
    )
    from ventilation_company.gui_pyside6.pricing_tab import get_markup_categories

    cats = get_markup_categories()
    assert cats == [
        ("Стандартна", 30.0),
        ("Преміум", 40.0),
        ("Економ", 20.0),
        ("Спецзамовлення", 50.0),
    ]


def test_saved_matrix_is_used(tmp_path, monkeypatch):
    path = tmp_path / "pricing_settings.json"
    path.write_text(
        json.dumps(
            {
                "markup_matrix": {
                    "Стандартна": 50.0,
                    "Преміум": 70.0,
                    "Економ": 35.0,
                    "Спецзамовлення": 150.0,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "ventilation_company.gui_pyside6.pricing_tab.SETTINGS_PATH",
        path,
    )
    from ventilation_company.gui_pyside6.pricing_tab import get_markup_categories

    cats = get_markup_categories()
    assert cats == [
        ("Стандартна", 50.0),
        ("Преміум", 70.0),
        ("Економ", 35.0),
        ("Спецзамовлення", 150.0),
    ]


def test_partial_matrix_falls_back_to_defaults(tmp_path, monkeypatch):
    path = tmp_path / "pricing_settings.json"
    path.write_text(json.dumps({"markup_matrix": {"Преміум": 65.0}}), encoding="utf-8")
    monkeypatch.setattr(
        "ventilation_company.gui_pyside6.pricing_tab.SETTINGS_PATH",
        path,
    )
    from ventilation_company.gui_pyside6.pricing_tab import get_markup_categories

    cats = get_markup_categories()
    assert ("Преміум", 65.0) in cats
    assert ("Стандартна", 30.0) in cats
