"""Tests for CalculationRepository."""

from __future__ import annotations

from ventilation_company.database.repositories.calc_repo import CalculationRepository


class TestCalculationRepository:
    """CRUD tests for calculations and items."""

    def test_add_calculation(self, db_session):
        repo = CalculationRepository(db_session)
        calc = repo.add_calculation(
            client_name="ТОВ ВентПром",
            client_phone="+380501234567",
            markup_percent=25.0,
        )
        assert calc.id is not None
        assert calc.client_name == "ТОВ ВентПром"
        assert calc.status == "draft"
        assert calc.total_cost == 0

    def test_get_calculation_by_id(self, db_session):
        repo = CalculationRepository(db_session)
        created = repo.add_calculation(client_name="Клієнт А")
        fetched = repo.get_calculation_by_id(created.id)
        assert fetched is not None
        assert fetched.client_name == "Клієнт А"

    def test_get_calculations_by_client(self, db_session):
        repo = CalculationRepository(db_session)
        repo.add_calculation(client_name="Клієнт Альфа")
        repo.add_calculation(client_name="Клієнт Бета")
        repo.add_calculation(client_name="Альфа-груп")
        results = repo.get_calculations_by_client("Альфа")
        assert len(results) == 2

    def test_update_calculation(self, db_session):
        repo = CalculationRepository(db_session)
        calc = repo.add_calculation(client_name="Старе ім'я")
        updated = repo.update_calculation(calc.id, client_name="Нове ім'я", status="sent")
        assert updated is not None
        assert updated.client_name == "Нове ім'я"
        assert updated.status == "sent"

    def test_delete_calculation(self, db_session):
        repo = CalculationRepository(db_session)
        calc = repo.add_calculation(client_name="На видалення")
        assert repo.delete_calculation(calc.id) is True
        assert repo.get_calculation_by_id(calc.id) is None

    def test_add_item(self, db_session):
        repo = CalculationRepository(db_session)
        calc = repo.add_calculation(client_name="Тест")
        item = repo.add_item(
            calculation_id=calc.id,
            subtype_id=1,
            material_id=1,
            size_params='{"d": 250, "l": 500}',
            quantity=3,
            area_m2=1.5,
            total_price=4500.0,
        )
        assert item.id is not None
        assert item.calculation_id == calc.id
        assert item.quantity == 3

    def test_get_items_by_calculation(self, db_session):
        repo = CalculationRepository(db_session)
        calc = repo.add_calculation(client_name="Тест")
        repo.add_item(calc.id, subtype_id=1, material_id=1, size_params="{}", quantity=1)
        repo.add_item(calc.id, subtype_id=2, material_id=1, size_params="{}", quantity=2)
        items = repo.get_items_by_calculation(calc.id)
        assert len(items) == 2

    def test_delete_item(self, db_session):
        repo = CalculationRepository(db_session)
        calc = repo.add_calculation(client_name="Тест")
        item = repo.add_item(calc.id, subtype_id=1, material_id=1, size_params="{}", quantity=1)
        assert repo.delete_item(item.id) is True
        assert len(repo.get_items_by_calculation(calc.id)) == 0
