"""Тести «Склад у виробництві»: резервування, звірка потреб, алерти."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ventilation_company.database.base import Base
from ventilation_company.database.repositories import warehouse_repo as wh_module


@pytest.fixture()
def warehouse(monkeypatch):
    """Репозиторій складу над in-memory SQLite."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    class _Ctx:
        def __enter__(self):
            return session

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(wh_module, "get_db", lambda: _Ctx())
    yield wh_module.WarehouseRepository
    session.close()


class TestWarehouseReserve:
    def test_reserve_and_available(self, warehouse):
        item = warehouse.create_item("Оцинкована сталь 0.7", unit="м²", min_quantity=10)
        warehouse.add_move(item["id"], 100, "in")
        updated = warehouse.reserve(item["id"], 30)
        assert updated["reserved"] == 30
        assert updated["available"] == 70
        assert updated["quantity"] == 100  # резерв не списує

    def test_reserve_more_than_available_raises(self, warehouse):
        item = warehouse.create_item("Метал")
        warehouse.add_move(item["id"], 5, "in")
        with pytest.raises(ValueError):
            warehouse.reserve(item["id"], 10)

    def test_release(self, warehouse):
        item = warehouse.create_item("Метал")
        warehouse.add_move(item["id"], 50, "in")
        warehouse.reserve(item["id"], 20)
        updated = warehouse.release(item["id"], 8)
        assert updated["reserved"] == 12
        assert updated["available"] == 38

    def test_out_move_consumes_reserved(self, warehouse):
        item = warehouse.create_item("Метал")
        warehouse.add_move(item["id"], 50, "in")
        warehouse.reserve(item["id"], 20)
        warehouse.add_move(item["id"], 10, "out")
        rows = warehouse.list_items()
        assert rows[0]["quantity"] == 40
        assert rows[0]["reserved"] == 10  # списання погасило частину резерву
        assert rows[0]["available"] == 30

    def test_reserve_unknown_item_returns_none(self, warehouse):
        assert warehouse.reserve(999, 1) is None
        assert warehouse.release(999, 1) is None


class TestMatchItem:
    def test_exact_and_substring_match(self):
        from ventilation_company.services.production_materials_service import (
            match_warehouse_item,
        )

        items = [
            {"id": 1, "name": "Оцинкована сталь 0.7 мм"},
            {"id": 2, "name": "Нержавійка"},
        ]
        assert match_warehouse_item("Оцинкована сталь 0.7 мм", items)["id"] == 1
        assert match_warehouse_item("Оцинкована сталь 0.7", items)["id"] == 1
        assert match_warehouse_item("НЕРЖАВІЙКА 1.0", items)["id"] == 2
        assert match_warehouse_item("Мідь", items) is None
        assert match_warehouse_item("", items) is None


class TestMaterialsCheck:
    def _tasks(self):
        return [
            {"project_id": 1, "product_name": "Відвод", "quantity": 3, "status": "в черзі"},
            {"project_id": 1, "product_name": "Фланець", "quantity": 2, "status": "в роботі"},
            {"project_id": 1, "product_name": "Старий", "quantity": 9, "status": "готово"},
        ]

    def test_required_materials_groups_active_only(self, monkeypatch):
        from ventilation_company.database.repositories import product_repo
        from ventilation_company.services import production_materials_service as svc

        monkeypatch.setattr(
            product_repo.ProductRepository,
            "get_all",
            staticmethod(
                lambda project_id=None: [
                    {"name": "Відвод", "material": "Оцинкована сталь 0.7"},
                    {"name": "Фланець", "material": "Оцинкована сталь 0.7"},
                    {"name": "Старий", "material": "Нержавійка"},
                ]
            ),
        )
        needed = svc.required_materials(self._tasks())
        assert needed == {"Оцинкована сталь 0.7": 5.0}  # готове не рахується

    def test_check_materials_statuses(self, monkeypatch, warehouse):
        from ventilation_company.services import production_materials_service as svc

        full = warehouse.create_item("Оцинкована сталь 0.7")
        warehouse.add_move(full["id"], 100, "in")
        part = warehouse.create_item("Нержавійка")
        warehouse.add_move(part["id"], 2, "in")
        # «Алюміній» на складі відсутній

        # get_db вже підмінено фікстурою warehouse — list_items працює напряму
        monkeypatch.setattr(
            svc.ProductRepository,
            "get_all",
            staticmethod(
                lambda project_id=None: [
                    {"name": "Відвод", "material": "Оцинкована сталь 0.7"},
                    {"name": "Фланець", "material": "Нержавійка"},
                    {"name": "Решітка", "material": "Алюміній"},
                ]
            ),
        )
        tasks = [
            {"project_id": 1, "product_name": "Відвод", "quantity": 10, "status": "в черзі"},
            {"project_id": 1, "product_name": "Фланець", "quantity": 5, "status": "в черзі"},
            {"project_id": 1, "product_name": "Решітка", "quantity": 4, "status": "в черзі"},
        ]
        rows = {r["material"]: r for r in svc.check_materials(tasks)}
        assert rows["Оцинкована сталь 0.7"]["status"] == svc.STATUS_OK
        assert rows["Нержавійка"]["status"] == svc.STATUS_PARTIAL
        assert rows["Алюміній"]["status"] == svc.STATUS_MISSING
        assert rows["Алюміній"]["item_id"] is None

    def test_reserve_available(self, monkeypatch, warehouse):
        from ventilation_company.services import production_materials_service as svc

        item = warehouse.create_item("Метал")
        warehouse.add_move(item["id"], 50, "in")
        rows = [
            {"material": "Метал", "needed": 30.0, "item_id": item["id"], "available": 50.0},
            {"material": "Немає на складі", "needed": 5.0, "item_id": None, "available": 0.0},
        ]
        reserved, errors = svc.reserve_available(rows)
        assert reserved == 1
        assert errors == []
        assert warehouse.list_items()[0]["reserved"] == 30

    def test_required_materials_products_error_groups_under_unknown(self, monkeypatch):
        from ventilation_company.database.repositories import product_repo
        from ventilation_company.services import production_materials_service as svc

        def _boom(project_id=None):
            raise RuntimeError("db down")

        monkeypatch.setattr(product_repo.ProductRepository, "get_all", staticmethod(_boom))
        # матеріал визначити не вдалося — завдання групуються під «—» (у звірці пропускаються)
        assert svc.required_materials(self._tasks()) == {"—": 5.0}


class TestLowStockAlert:
    def test_build_low_stock_text(self):
        from ventilation_company.services.project_notifications import build_low_stock_text

        text = build_low_stock_text(
            [
                {
                    "name": "Оцинкована сталь 0.7",
                    "quantity": 5.0,
                    "min_quantity": 10.0,
                    "unit": "м²",
                    "reserved": 2.0,
                    "available": 3.0,
                },
            ]
        )
        assert "Оцинкована сталь 0.7" in text
        assert "залишок 5" in text
        assert "мін. 10" in text
        assert "доступно 3" in text

    def test_check_low_stock_sends(self, monkeypatch):
        from ventilation_company.database.repositories import warehouse_repo
        from ventilation_company.services import project_notifications

        monkeypatch.setattr(
            project_notifications, "cloud_backup_preferences", lambda: (True, "tok", "42")
        )
        sent: list[str] = []
        monkeypatch.setattr(
            project_notifications,
            "send_telegram_message",
            lambda token, chat, text: sent.append(text) or True,
        )
        monkeypatch.setattr(
            warehouse_repo.WarehouseRepository,
            "low_stock",
            staticmethod(
                lambda: [{"name": "Метал", "quantity": 1.0, "min_quantity": 5.0, "unit": "шт"}]
            ),
        )
        assert project_notifications.check_low_stock() is True
        assert sent and "Метал" in sent[0]

    def test_check_low_stock_nothing_to_send(self, monkeypatch):
        from ventilation_company.database.repositories import warehouse_repo
        from ventilation_company.services import project_notifications

        monkeypatch.setattr(
            project_notifications, "cloud_backup_preferences", lambda: (True, "tok", "42")
        )
        monkeypatch.setattr(
            warehouse_repo.WarehouseRepository, "low_stock", staticmethod(lambda: [])
        )
        assert project_notifications.check_low_stock() is False

    def test_check_low_stock_without_bot(self, monkeypatch):
        from ventilation_company.services import project_notifications

        monkeypatch.setattr(
            project_notifications, "cloud_backup_preferences", lambda: (False, "", "")
        )
        assert project_notifications.check_low_stock() is False
