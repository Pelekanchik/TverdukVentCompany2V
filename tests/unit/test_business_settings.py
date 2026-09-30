"""Тести бізнес-налаштувань (BusinessSettings)."""

import json

import pytest

from ventilation_company.services import business_settings as bs_module
from ventilation_company.services.business_settings import (
    DEFAULT_COMPONENTS,
    DEFAULT_POSITIONS,
    DEFAULT_VAT_RATE,
    BusinessSettings,
)


@pytest.fixture
def business_settings(tmp_path, monkeypatch):
    """Ізольований екземпляр BusinessSettings у тимчасовому файлі."""
    filepath = str(tmp_path / "business_settings.json")
    monkeypatch.setattr(bs_module.BusinessSettings, "_instance", None)
    settings = BusinessSettings.get_instance(filepath)
    yield settings
    monkeypatch.setattr(bs_module.BusinessSettings, "_instance", None)


class TestDefaults:
    def test_vat_rate_default(self, business_settings):
        assert business_settings.get_vat_rate() == DEFAULT_VAT_RATE

    def test_component_default(self, business_settings):
        comp = business_settings.get_component("вентилятор_осьовий")
        assert comp["ціна"] == DEFAULT_COMPONENTS["вентилятор_осьовий"]["ціна"]
        assert comp["одиниця"] == "шт"

    def test_unknown_component_empty(self, business_settings):
        assert business_settings.get_component("неіснує") == {}

    def test_insulation_price_default(self, business_settings):
        assert business_settings.get_extra_material_price("ізоляція_мінвата", 180) == 180

    def test_position_default(self, business_settings):
        pos = business_settings.get_position("директор")
        assert pos["ставка"] == DEFAULT_POSITIONS["директор"]["ставка"]

    def test_unknown_position_zero(self, business_settings):
        pos = business_settings.get_position("космонавт")
        assert pos == {"ставка": 0, "премія_%": 0}


class TestPersistence:
    def test_save_and_load(self, business_settings, tmp_path):
        business_settings.vat_rate = 7.0
        business_settings.components["тест_вентилятор"] = {"ціна": 100, "одиниця": "шт"}
        business_settings.save()

        filepath = tmp_path / "business_settings.json"
        assert filepath.exists()
        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert data["vat_rate"] == 7.0
        assert data["components"]["тест_вентилятор"]["ціна"] == 100

        # Новий екземпляр (симуляція перезапуску) має прочитати збережене
        bs_module.BusinessSettings._instance = None
        reloaded = BusinessSettings.get_instance(str(filepath))
        assert reloaded.get_vat_rate() == 7.0
        assert reloaded.get_component("тест_вентилятор")["ціна"] == 100

    def test_reload_picks_external_change(self, business_settings, tmp_path):
        filepath = tmp_path / "business_settings.json"
        data = {
            "vat_rate": 14.0,
            "components": {},
            "extra_materials": {},
            "positions": {},
        }
        filepath.write_text(json.dumps(data), encoding="utf-8")
        business_settings._last_modified = 0  # примусово застаріти
        assert business_settings.get_vat_rate() == 14.0


class TestCompany:
    """Реквізити фірми для КП/договорів/актів."""

    def test_company_defaults(self, business_settings):
        company = business_settings.get_company()
        assert company["name"] == "ТОВ «ВентКомпані»"
        assert company["edrpou"] == "12345678"
        assert company["city"] == "м. Київ"
        assert set(company) == {
            "name",
            "address",
            "phone",
            "email",
            "website",
            "edrpou",
            "signatory",
            "city",
        }

    def test_company_save_and_reload(self, business_settings, tmp_path):
        business_settings.company = {
            "name": "ПП «ВентБуд»",
            "edrpou": "98765432",
            "city": "м. Львів",
        }
        business_settings.save()

        filepath = tmp_path / "business_settings.json"
        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert data["company"]["name"] == "ПП «ВентБуд»"

        # Перезапуск: злиття з дефолтами, незадані поля — дефолтні.
        bs_module.BusinessSettings._instance = None
        reloaded = BusinessSettings.get_instance(str(filepath))
        company = reloaded.get_company()
        assert company["name"] == "ПП «ВентБуд»"
        assert company["edrpou"] == "98765432"
        assert company["city"] == "м. Львів"
        assert company["phone"] == "+38 (044) 123-45-67"

    def test_company_merged_from_partial_json(self, business_settings, tmp_path):
        """Старий файл без «company» (або з частковими полями) не ламає get_company."""
        filepath = tmp_path / "business_settings.json"
        filepath.write_text(
            json.dumps({"company": {"name": "ФОП Твердух"}}),
            encoding="utf-8",
        )
        business_settings._last_modified = 0
        company = business_settings.get_company()
        assert company["name"] == "ФОП Твердух"
        assert company["address"]  # дефолт підтягнувся
