"""Tests for OverheadRepository."""

from __future__ import annotations

from ventilation_company.database.repositories.overhead_repo import OverheadRepository


class TestOverheadRepository:
    """CRUD tests for overhead items."""

    def test_add_item(self, db_session):
        repo = OverheadRepository(db_session)
        item = repo.add_item(name="Оренда приміщення", item_type="fixed", value=15000.0)
        assert item.id is not None
        assert item.name == "Оренда приміщення"
        assert item.type == "fixed"
        assert item.value == 15000.0
        assert item.is_active == 1

    def test_get_all_items(self, db_session):
        repo = OverheadRepository(db_session)
        repo.add_item("Електроенергія", "variable", 5000.0)
        repo.add_item("Вода", "fixed", 800.0)
        items = repo.get_all_items()
        assert len(items) == 2

    def test_get_active_items(self, db_session):
        repo = OverheadRepository(db_session)
        repo.add_item("Активна", "fixed", 100.0, is_active=1)
        repo.add_item("Неактивна", "fixed", 200.0, is_active=0)
        items = repo.get_active_items()
        assert len(items) == 1
        assert items[0].name == "Активна"

    def test_get_item_by_id(self, db_session):
        repo = OverheadRepository(db_session)
        created = repo.add_item("Тест", "fixed", 1000.0)
        fetched = repo.get_item_by_id(created.id)
        assert fetched is not None
        assert fetched.name == "Тест"

    def test_get_item_by_id_not_found(self, db_session):
        repo = OverheadRepository(db_session)
        assert repo.get_item_by_id(9999) is None

    def test_update_item(self, db_session):
        repo = OverheadRepository(db_session)
        item = repo.add_item("Старе", "fixed", 1000.0)
        updated = repo.update_item(item.id, name="Нове", value=2000.0, is_active=0)
        assert updated is not None
        assert updated.name == "Нове"
        assert updated.value == 2000.0
        assert updated.is_active == 0

    def test_update_item_not_found(self, db_session):
        repo = OverheadRepository(db_session)
        assert repo.update_item(9999, name="Тест") is None

    def test_delete_item(self, db_session):
        repo = OverheadRepository(db_session)
        item = repo.add_item("На видалення", "fixed", 100.0)
        assert repo.delete_item(item.id) is True
        assert repo.get_item_by_id(item.id) is None

    def test_delete_item_not_found(self, db_session):
        repo = OverheadRepository(db_session)
        assert repo.delete_item(9999) is False

    def test_get_all_alias(self, db_session):
        repo = OverheadRepository(db_session)
        repo.add_item("Тест", "fixed", 100.0)
        items = repo.get_all()
        assert len(items) == 1
