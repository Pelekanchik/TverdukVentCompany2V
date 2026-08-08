"""Tests for MaterialRepository."""

from __future__ import annotations

from ventilation_company.database.repositories.material_repo import MaterialRepository


class TestMaterialRepository:
    """CRUD tests for materials."""

    def test_add_material(self, db_session):
        repo = MaterialRepository(db_session)
        mat = repo.add_material(
            name="Оцинкована сталь",
            grade="08пс",
            thickness=0.5,
            price_per_m2=450.0,
        )
        assert mat.id is not None
        assert mat.name == "Оцинкована сталь"
        assert mat.unit == "мм"

    def test_get_material_by_id(self, db_session):
        repo = MaterialRepository(db_session)
        created = repo.add_material("Нержавійка", "AISI 304", 0.8, 1200.0)
        fetched = repo.get_material_by_id(created.id)
        assert fetched is not None
        assert fetched.grade == "AISI 304"

    def test_update_material(self, db_session):
        repo = MaterialRepository(db_session)
        mat = repo.add_material("Алюміній", "АД0", 1.0, 800.0)
        updated = repo.update_material(mat.id, price_per_m2=850.0, is_active=0)
        assert updated is not None
        assert updated.price_per_m2 == 850.0
        assert updated.is_active == 0

    def test_delete_material(self, db_session):
        repo = MaterialRepository(db_session)
        mat = repo.add_material("На видалення", "Тест", 0.5, 100.0)
        assert repo.delete_material(mat.id) is True
        assert repo.get_material_by_id(mat.id) is None
