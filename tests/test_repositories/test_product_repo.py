"""Tests for ProductRepository."""

from __future__ import annotations

from ventilation_company.database.repositories.product_repo import ProductRepository


class TestProductRepository:
    """CRUD tests for product types, subtypes and size ranges."""

    def test_add_type(self, db_session):
        repo = ProductRepository(db_session)
        pt = repo.add_type(name="Відводи", slug="elbows", icon="🔧")
        assert pt.id is not None
        assert pt.name == "Відводи"
        assert pt.slug == "elbows"

    def test_get_type_by_id(self, db_session):
        repo = ProductRepository(db_session)
        created = repo.add_type(name="Переходи", slug="transitions")
        fetched = repo.get_type_by_id(created.id)
        assert fetched is not None
        assert fetched.name == "Переходи"

    def test_get_type_by_slug(self, db_session):
        repo = ProductRepository(db_session)
        repo.add_type(name="Фланці", slug="flanges")
        fetched = repo.get_type_by_slug("flanges")
        assert fetched is not None
        assert fetched.name == "Фланці"

    def test_get_type_by_id_not_found(self, db_session):
        repo = ProductRepository(db_session)
        assert repo.get_type_by_id(9999) is None

    def test_update_type(self, db_session):
        repo = ProductRepository(db_session)
        pt = repo.add_type(name="Заглушки", slug="caps")
        updated = repo.update_type(pt.id, name="Заглушки оновлені")
        assert updated is not None
        assert updated.name == "Заглушки оновлені"
        assert updated.slug == "caps"

    def test_delete_type(self, db_session):
        repo = ProductRepository(db_session)
        pt = repo.add_type(name="Трійники", slug="tees")
        assert repo.delete_type(pt.id) is True
        assert repo.get_type_by_id(pt.id) is None

    def test_add_subtype(self, db_session):
        repo = ProductRepository(db_session)
        pt = repo.add_type(name="Відводи", slug="elbows")
        st = repo.add_subtype(
            type_id=pt.id,
            name="Відвід 90°",
            slug="elbow-90",
            formula="pi*d*l/1e6",
            shape_type="round",
        )
        assert st.id is not None
        assert st.product_type_id == pt.id
        assert st.formula == "pi*d*l/1e6"

    def test_get_subtypes_by_type(self, db_session):
        repo = ProductRepository(db_session)
        pt = repo.add_type(name="Фланці", slug="flanges")
        repo.add_subtype(pt.id, "Фланець круглий", "flange-round", "pi*d*thickness")
        repo.add_subtype(pt.id, "Фланець прямокутний", "flange-rect", "2*(w+h)*thickness")
        subtypes = repo.get_subtypes_by_type(pt.id)
        assert len(subtypes) == 2

    def test_delete_subtype_cascade(self, db_session):
        repo = ProductRepository(db_session)
        pt = repo.add_type(name="Тест", slug="test")
        st = repo.add_subtype(pt.id, "Підтип", "subtype", "formula")
        assert repo.delete_subtype(st.id) is True
        assert repo.get_subtype_by_id(st.id) is None

    def test_add_size_range(self, db_session):
        repo = ProductRepository(db_session)
        pt = repo.add_type(name="Відводи", slug="elbows")
        st = repo.add_subtype(pt.id, "Відвід 90°", "elbow-90", "formula")
        sr = repo.add_size_range(
            subtype_id=st.id,
            param_name="diameter",
            param_label="Діаметр",
            min_value=100,
            max_value=1000,
            step=50,
        )
        assert sr.id is not None
        assert sr.param_name == "diameter"
        assert sr.min_value == 100
