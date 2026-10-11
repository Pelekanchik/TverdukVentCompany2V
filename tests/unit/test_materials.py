"""Тести реєстру матеріалів (ventilation_company.materials) та густин у PricingSettings."""

import json

import pytest

from ventilation_company.materials import (
    DEFAULT_MATERIAL_DENSITIES,
    FALLBACK_DENSITY_KG_M3,
    list_materials,
    resolve_density,
)
from ventilation_company.services import pricing_settings as ps_module
from ventilation_company.services.pricing_settings import PricingSettings

# ── Чисті функції materials.py ──


def test_resolve_density_known_material_case_insensitive():
    assert resolve_density({}, "Оцинкована сталь") == 7850.0
    assert resolve_density({}, "АЛЮМІНІЙ") == 2700.0


def test_resolve_density_user_override_wins():
    densities = {"Мідь": 8960.0}
    assert resolve_density(densities, "мідь") == 8960.0


def test_resolve_density_unknown_material_falls_back():
    assert resolve_density({}, "титан") == FALLBACK_DENSITY_KG_M3
    assert resolve_density({}, "титан", default=4500.0) == 4500.0


def test_resolve_density_ignores_garbage_values():
    densities = {"мідь": "не число"}
    assert resolve_density(densities, "мідь") == FALLBACK_DENSITY_KG_M3


def test_list_materials_sorted_case_insensitive():
    prices = {"оцинкована сталь": {}, "Алюміній": {}, "нержавіюча сталь": {}}
    assert list_materials(prices) == ["Алюміній", "нержавіюча сталь", "оцинкована сталь"]


def test_default_densities_match_legacy_values():
    # Регресія: значення, на які спираються розрахунки ваги
    assert DEFAULT_MATERIAL_DENSITIES["оцинкована сталь"] == 7850.0
    assert DEFAULT_MATERIAL_DENSITIES["нержавіюча сталь"] == 7900.0
    assert DEFAULT_MATERIAL_DENSITIES["алюміній"] == 2700.0


# ── PricingSettings: material_densities ──


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    path = tmp_path / "pricing_settings.json"

    def apply(data=None):
        if data is not None:
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(ps_module.PricingSettings, "_instance", None)
        PricingSettings.get_instance(str(path))

    yield path, apply
    monkeypatch.setattr(ps_module.PricingSettings, "_instance", None)


def test_densities_persisted(isolated_settings):
    path, apply = isolated_settings
    apply()
    s = PricingSettings.get_instance()
    s.material_prices["мідь"] = {"0.5": 2100.0}
    s.sync_material_densities()
    s.material_densities["мідь"] = 8960.0
    s.save()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["material_densities"]["мідь"] == 8960.0


def test_new_material_gets_default_density(isolated_settings):
    _, apply = isolated_settings
    apply()
    s = PricingSettings.get_instance()
    s.material_prices["титан"] = {"0.5": 1500.0}
    s.sync_material_densities()
    assert s.get_material_density("титан") == FALLBACK_DENSITY_KG_M3
    # Відомі матеріали — зі своїми густинами
    assert s.get_material_density("алюміній") == 2700.0


def test_density_loaded_from_file(isolated_settings):
    _, apply = isolated_settings
    apply(
        {
            "material_prices": {"мідь": {"0.5": 2100.0}},
            "material_densities": {"мідь": 8960.0},
        }
    )
    s = PricingSettings.get_instance()
    assert s.get_material_density("Мідь") == 8960.0


def test_list_materials_from_settings(isolated_settings):
    _, apply = isolated_settings
    apply({"material_prices": {"мідь": {}, "оцинкована сталь": {}}})
    s = PricingSettings.get_instance()
    assert set(s.list_materials()) == {"мідь", "оцинкована сталь"}


def test_cost_engine_density_alias_unchanged():
    # Зворотна сумісність: константа, яку імпортують інші модулі/тести
    from ventilation_company.calculations.cost_engine import METAL_DENSITY_KG_M3

    assert METAL_DENSITY_KG_M3["оцинкована сталь"] == 7850
    assert METAL_DENSITY_KG_M3["алюміній"] == 2700
