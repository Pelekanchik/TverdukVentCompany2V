"""Тести для моделі Project та допоміжних функцій."""

import pytest

from ventilation_company.models.project import (
    Project,
    generate_project_number,
    validate_project_number,
)


class TestGenerateProjectNumber:
    """Тести генерації номера проєкту."""

    def test_format(self):
        number = generate_project_number()
        assert number.startswith("PRJ-")
        parts = number.split("-")
        assert len(parts) == 3

    def test_uniqueness(self):
        n1 = generate_project_number()
        n2 = generate_project_number()
        assert n1 != n2


class TestValidateProjectNumber:
    """Тести валідації номера проєкту."""

    def test_valid_number(self):
        valid, msg = validate_project_number("PRJ-20260810120000-00123")
        assert valid is True
        assert msg == ""

    def test_empty_number(self):
        valid, msg = validate_project_number("")
        assert valid is False
        assert "пустим" in msg

    def test_none_number(self):
        valid, msg = validate_project_number(None)
        assert valid is False

    def test_wrong_prefix(self):
        valid, msg = validate_project_number("PROJ-123")
        assert valid is False
        assert "PRJ-" in msg


class TestProject:
    """Тести для моделі проєкту."""

    def test_basic_creation(self):
        p = Project(
            name="Офісний комплекс",
            client="ТОВ 'БудМакс'",
            address="м. Київ, вул. Хрещатик 1",
            ventilation_type="припливно-витяжна",
            air_flow=5000,
            pressure=300,
        )
        assert p.name == "Офісний комплекс"
        assert p.client == "ТОВ 'БудМакс'"
        assert p.ventilation_type == "припливно-витяжна"
        assert p.air_flow == 5000.0
        assert p.pressure == 300.0
        assert p.status == "draft"
        assert p.project_number.startswith("PRJ-")

    def test_invalid_ventilation_type_fallback(self):
        p = Project(name="Тест", ventilation_type="невідомий тип")
        assert p.ventilation_type == "припливна"

    def test_custom_project_number(self):
        p = Project(name="Тест", project_number="PRJ-CUSTOM-001")
        assert p.project_number == "PRJ-CUSTOM-001"

    def test_validate_success(self):
        p = Project(name="Тестовий проєкт", air_flow=1000)
        valid, errors = p.validate()
        assert valid is True
        assert len(errors) == 0

    def test_validate_short_name(self):
        p = Project(name="АБ")
        valid, errors = p.validate()
        assert valid is False
        assert any("3 символів" in e for e in errors)

    def test_add_component(self):
        p = Project(name="Тест")
        total = p.add_component("вентилятор_осьовий", 2, "шт", 3500.0)
        assert total == 7000.0
        assert len(p._components) == 1
        assert p._components[0]["name"] == "вентилятор_осьовий"

    def test_add_material(self):
        p = Project(name="Тест")
        total = p.add_material("оцинкована_сталь_0.7", 10, "м²", 580.0)
        assert total == 5800.0
        assert len(p._materials) == 1

    def test_add_work(self):
        p = Project(name="Тест")
        total = p.add_work("монтаж_повітропроводу", 50, "м²", 420.0)
        assert total == 21000.0
        assert len(p._works) == 1

    def test_get_summary(self):
        p = Project(name="Тест")
        p.add_component("фільтр", 2, "шт", 1200.0)
        p.add_material("сталь", 5, "м²", 500.0)
        p.add_work("монтаж", 10, "м²", 400.0)
        summary = p.get_summary()
        assert summary["components_cost"] == 2400.0
        assert summary["materials_cost"] == 2500.0
        assert summary["works_cost"] == 4000.0
        assert summary["total_base"] == 8900.0

    def test_get_summary_empty(self):
        p = Project(name="Тест")
        summary = p.get_summary()
        assert summary["total_base"] == 0.0

    def test_to_dict_roundtrip(self):
        p = Project(
            name="Офіс",
            client="Клієнт",
            address="Адреса",
            ventilation_type="витяжна",
            air_flow=2000,
            pressure=150,
        )
        p.add_component("вентилятор", 1, "шт", 5000.0)
        p.add_material("сталь", 2, "м²", 600.0)
        data = p.to_dict()
        p2 = Project.from_dict(data)
        assert p2.name == p.name
        assert p2.client == p.client
        assert p2.ventilation_type == p.ventilation_type
        assert len(p2._components) == 1
        assert len(p2._materials) == 1

    def test_from_dict_with_id(self):
        data = {
            "project_number": "PRJ-TEST-001",
            "name": "Відновлений",
            "client": "Клієнт",
            "address": "Адреса",
            "ventilation_type": "кондиціонування",
            "air_flow": 3000,
            "pressure": 200,
            "id": 42,
            "status": "active",
            "total_area": 150.5,
            "notes": "Примітка",
            "components": [],
            "materials": [],
            "works": [],
        }
        p = Project.from_dict(data)
        assert p.id == 42
        assert p.status == "active"
        assert p.total_area == 150.5
        assert p.notes == "Примітка"

    def test_str(self):
        p = Project(name="Тестовий")
        assert "Проєкт" in str(p)
        assert "Тестовий" in str(p)

    def test_repr(self):
        p = Project(name="Тест")
        assert "Project" in repr(p)

    def test_ventilation_types_list(self):
        assert "припливна" in Project.VENTILATION_TYPES
        assert "витяжна" in Project.VENTILATION_TYPES
        assert "кондиціонування" in Project.VENTILATION_TYPES
        assert len(Project.VENTILATION_TYPES) == 5
