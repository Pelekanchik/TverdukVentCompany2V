"""Тести для інтеграції з SQLite (db_integration)."""

import json
import os

import pytest

from ventilation_company.db_integration import ProjectDatabase, get_db, save_project_full


class TestProjectDatabase:
    """Тести для ProjectDatabase."""

    def test_creation(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        assert os.path.exists(temp_db_path)

    def test_create_project(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        project_id = db.create_project(name="Тестовий проєкт", client="ТОВ 'Тест'")
        assert isinstance(project_id, int)
        assert project_id > 0

    def test_get_project(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        project_id = db.create_project(name="Тест", client="Клієнт")
        project = db.get_project(project_id)
        assert project is not None
        assert project["name"] == "Тест"
        assert project["client"] == "Клієнт"

    def test_get_project_not_found(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        assert db.get_project(99999) is None

    def test_get_all_projects(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        db.create_project(name="П1")
        db.create_project(name="П2")
        projects = db.get_all_projects()
        assert len(projects) == 2

    def test_get_all_projects_by_status(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        db.create_project(name="П1")
        db.create_project(name="П2")
        projects = db.get_all_projects(status="draft")
        assert len(projects) == 2

    def test_update_project(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        project_id = db.create_project(name="Старе ім'я")
        result = db.update_project(project_id, name="Нове ім'я", client="Новий клієнт")
        assert result is True
        project = db.get_project(project_id)
        assert project["name"] == "Нове ім'я"
        assert project["client"] == "Новий клієнт"

    def test_update_project_no_changes(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        project_id = db.create_project(name="Тест")
        result = db.update_project(project_id, unknown_field="value")
        assert result is False

    def test_delete_project(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        project_id = db.create_project(name="На видалення")
        assert db.delete_project(project_id) is True
        assert db.get_project(project_id) is None

    def test_duplicate_project(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        project_id = db.create_project(name="Оригінал")
        db.add_product_to_project(project_id, {
            "name": "ПП", "product_type": "rect_duct",
            "width": 400, "height": 200, "length": 1000,
            "quantity": 2,
        })
        new_id = db.duplicate_project(project_id, "Копія")
        assert new_id != project_id
        new_project = db.get_project(new_id)
        assert new_project["name"] == "Копія"
        products = db.get_project_products(new_id)
        assert len(products) == 1
        assert products[0]["name"] == "ПП"

    def test_duplicate_project_not_found(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        with pytest.raises(ValueError, match="не знайдено"):
            db.duplicate_project(99999)

    # ── Вироби ──────────────────────────────────────────────

    def test_add_product_to_project(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        project_id = db.create_project(name="Тест")
        product_id = db.add_product_to_project(project_id, {
            "name": "Повітропровід 400×200",
            "product_type": "rect_duct",
            "width": 400, "height": 200, "length": 1000,
            "thickness": 0.7, "material": "оцинкована сталь",
            "quantity": 5,
            "metal_area_m2": 1.2, "weight_kg": 15.5,
        })
        assert isinstance(product_id, int)
        assert product_id > 0

    def test_get_project_products(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        project_id = db.create_project(name="Тест")
        db.add_product_to_project(project_id, {"name": "П1", "quantity": 1})
        db.add_product_to_project(project_id, {"name": "П2", "quantity": 2})
        products = db.get_project_products(project_id)
        assert len(products) == 2

    def test_update_product(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        project_id = db.create_project(name="Тест")
        product_id = db.add_product_to_project(project_id, {"name": "Старе", "quantity": 1})
        result = db.update_product(product_id, name="Нове", quantity=5)
        assert result is True
        products = db.get_project_products(project_id)
        assert products[0]["name"] == "Нове"
        assert products[0]["quantity"] == 5

    def test_delete_product(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        project_id = db.create_project(name="Тест")
        product_id = db.add_product_to_project(project_id, {"name": "На видалення", "quantity": 1})
        assert db.delete_product(product_id) is True
        assert len(db.get_project_products(project_id)) == 0

    def test_get_project_summary(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        project_id = db.create_project(name="Тест")
        db.add_product_to_project(project_id, {
            "name": "П1", "quantity": 2, "weight_kg": 10.0, "metal_area_m2": 1.0,
        })
        db.add_product_to_project(project_id, {
            "name": "П2", "quantity": 3, "weight_kg": 5.0, "metal_area_m2": 0.5,
        })
        summary = db.get_project_summary(project_id)
        assert summary["total_items"] == 2
        assert summary["total_quantity"] == 5
        assert summary["total_weight"] == 35.0  # 2*10 + 3*5
        assert summary["total_area"] == 3.5  # 2*1 + 3*0.5

    # ── Специфікації ────────────────────────────────────────

    def test_save_and_get_specification(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        project_id = db.create_project(name="Тест")
        spec_data = {
            "summary": {
                "total_items": 2, "total_quantity": 5,
                "total_weight_kg": 35.0, "total_area_m2": 3.5,
                "total_price": 5000.0,
            },
            "items": [{"name": "П1"}, {"name": "П2"}],
        }
        spec_id = db.save_specification(project_id, spec_data, name="Специфікація 1")
        assert isinstance(spec_id, int)

        specs = db.get_specifications(project_id)
        assert len(specs) == 1
        assert specs[0]["name"] == "Специфікація 1"

    def test_get_specification_by_id(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        project_id = db.create_project(name="Тест")
        spec_data = {"summary": {"total_items": 1}, "items": []}
        spec_id = db.save_specification(project_id, spec_data)
        spec = db.get_specification(spec_id)
        assert spec is not None
        assert "parsed_content" in spec

    def test_get_specification_not_found(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        assert db.get_specification(99999) is None

    # ── Плани розкрою ───────────────────────────────────────

    def test_save_and_get_cutting_plan(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        project_id = db.create_project(name="Тест")
        plan = {
            "sheet_width": 1250, "sheet_height": 2500,
            "thickness": 0.7, "material": "оцинкована сталь",
            "summary": {"sheets_required": 3, "utilization_percent": 85.5, "waste_percent": 14.5},
        }
        plan_id = db.save_cutting_plan(project_id, plan, name="План 1")
        assert isinstance(plan_id, int)

        plans = db.get_cutting_plans(project_id)
        assert len(plans) == 1
        assert plans[0]["sheets_required"] == 3
        assert "parsed_plan" in plans[0]

    # ── Бібліотека стандартних виробів ──────────────────────

    def test_add_and_get_standard_products(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        product_id = db.add_standard_product(
            name="ПП 400×200", product_type="rect_duct",
            width=400, height=200, length=1000,
            thickness=0.7, material="оцинкована сталь",
            parameters={"profile": 30},
        )
        assert isinstance(product_id, int)

        products = db.get_standard_products()
        assert len(products) == 1
        assert products[0]["name"] == "ПП 400×200"
        assert products[0]["parsed_parameters"]["profile"] == 30

    def test_get_standard_products_by_type(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        db.add_standard_product("ПП", "rect_duct", 400, 200, 1000, 0.7, "сталь")
        db.add_standard_product("КП", "round_duct", 250, 250, 1000, 0.7, "сталь")
        products = db.get_standard_products(product_type="rect_duct")
        assert len(products) == 1
        assert products[0]["product_type"] == "rect_duct"

    def test_update_standard_product(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        product_id = db.add_standard_product("ПП", "rect_duct", 400, 200, 1000, 0.7, "сталь")
        result = db.update_standard_product(product_id, name="ПП оновлений", is_active=0)
        assert result is True
        products = db.get_standard_products(active_only=False)
        assert products[0]["name"] == "ПП оновлений"
        assert products[0]["is_active"] == 0

    # ── Ціни на матеріали ───────────────────────────────────

    def test_set_and_get_material_price(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        db.set_material_price("оцинкована сталь", 0.7, price_per_kg=15.0, price_per_m2=580.0)
        price = db.get_material_price("оцинкована сталь", 0.7)
        assert price == 15.0

    def test_get_material_price_not_found(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        assert db.get_material_price("невідомий", 0.5) is None

    def test_get_material_prices(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        db.set_material_price("сталь", 0.7, price_per_m2=500.0)
        db.set_material_price("сталь", 1.0, price_per_m2=750.0)
        prices = db.get_material_prices()
        assert len(prices) == 2

    # ── Клієнти ─────────────────────────────────────────────

    def test_add_and_get_clients(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        client_id = db.add_client(
            name="ТОВ 'ВентПром'",
            contact="Іванов І.І.",
            phone="+380501234567",
            email="info@ventprom.ua",
            address="м. Київ",
        )
        assert isinstance(client_id, int)
        clients = db.get_clients()
        assert len(clients) == 1
        assert clients[0]["name"] == "ТОВ 'ВентПром'"
        assert clients[0]["phone"] == "+380501234567"

    # ── Звіти ───────────────────────────────────────────────

    def test_get_production_report(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        db.create_project(name="П1")
        db.create_project(name="П2")
        report = db.get_production_report()
        assert report["total_projects"] == 2

    def test_get_material_usage_report(self, temp_db_path):
        db = ProjectDatabase(temp_db_path)
        project_id = db.create_project(name="Тест")
        db.add_product_to_project(project_id, {
            "name": "П1", "material": "оцинкована сталь", "thickness": 0.7,
            "quantity": 10, "weight_kg": 5.0, "metal_area_m2": 0.5,
        })
        db.add_product_to_project(project_id, {
            "name": "П2", "material": "нержавіюча сталь", "thickness": 0.8,
            "quantity": 5, "weight_kg": 8.0, "metal_area_m2": 0.8,
        })
        report = db.get_material_usage_report()
        assert len(report) == 2
        materials = [r["material"] for r in report]
        assert "оцинкована сталь" in materials
        assert "нержавіюча сталь" in materials


class TestGetDb:
    """Тести фабрики БД."""

    def test_returns_instance(self, temp_db_path):
        db = get_db(temp_db_path)
        assert isinstance(db, ProjectDatabase)


class TestSaveProjectFull:
    """Тести збереження повного проєкту."""

    def test_full_save(self, temp_db_path):
        products = [
            {"name": "П1", "product_type": "rect_duct", "width": 400, "height": 200, "length": 1000, "quantity": 2},
        ]
        spec_data = {"summary": {"total_items": 1, "total_quantity": 2}, "items": []}
        cutting_plan = {"summary": {"sheets_required": 1}, "sheet_width": 1250}

        result = save_project_full("Повний проєкт", products, spec_data, cutting_plan, db_path=temp_db_path)
        assert "project_id" in result
        assert "specification_id" in result
        assert "cutting_plan_id" in result
        assert result["products_count"] == 1
