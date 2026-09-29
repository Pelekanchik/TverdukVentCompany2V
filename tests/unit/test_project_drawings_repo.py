"""Тести репозиторію креслень проєкту (ProjectDrawingRepository)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ventilation_company.database.base import Base
from ventilation_company.database.repositories import project_drawing_repo as repo_module


@pytest.fixture()
def repo(monkeypatch):
    """Репозиторій над in-memory SQLite; audit вимкнено."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    class _Ctx:
        def __enter__(self):
            return session

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(repo_module, "get_db", lambda: _Ctx())
    monkeypatch.setattr(repo_module, "log_action", lambda *a, **k: None)
    yield repo_module.ProjectDrawingRepository
    session.close()


class TestProjectDrawingRepository:
    def test_create_and_get_by_project(self, repo):
        d = repo.create(
            project_id=1,
            filename="план_3й_поверх.dwg",
            file_path="C:/Креслення/план_3й_поверх.dwg",
            drawing_type="креслення",
        )
        assert d["id"] > 0
        assert d["filename"] == "план_3й_поверх.dwg"

        rows = repo.get_by_project(1)
        assert len(rows) == 1
        assert rows[0]["file_path"].endswith("план_3й_поверх.dwg")
        assert rows[0]["drawing_type"] == "креслення"

    def test_get_by_project_isolated(self, repo):
        repo.create(project_id=1, filename="a.dwg", file_path="/a.dwg")
        assert len(repo.get_by_project(2)) == 0
        assert len(repo.get_by_project(1)) == 1

    def test_delete(self, repo):
        d = repo.create(project_id=1, filename="b.dxf", file_path="/b.dxf")
        repo.delete(d["id"])
        assert repo.get_by_project(1) == []

    def test_delete_unknown_id_noop(self, repo):
        repo.delete(999)  # не має підняти виняток
