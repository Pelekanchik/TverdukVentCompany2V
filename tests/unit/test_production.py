"""Тести планування виробництва (розділ 5.2): репозиторій, сервіс, черга."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ventilation_company.database.base import Base
from ventilation_company.database.repositories import production_task_repo as repo_module


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
    yield repo_module.ProductionTaskRepository
    session.close()


class TestProductionTaskRepository:
    def test_create_and_get_all(self, repo):
        t = repo.create(project_id=1, product_name="Відвод 400×200", quantity=3)
        assert t["id"] > 0
        assert t["status"] == "в черзі"
        assert t["priority"] == "звичайний"

        rows = repo.get_all()
        assert len(rows) == 1
        assert rows[0]["product_name"] == "Відвод 400×200"
        assert rows[0]["quantity"] == 3

    def test_get_all_status_filter(self, repo):
        repo.create(project_id=1, product_name="A", status="в черзі")
        repo.create(project_id=1, product_name="B", status="готово")
        assert len(repo.get_all(status="готово")) == 1
        assert len(repo.get_all()) == 2

    def test_get_by_project(self, repo):
        repo.create(project_id=1, product_name="A")
        repo.create(project_id=2, product_name="B")
        assert len(repo.get_by_project(1)) == 1
        assert repo.get_by_project(1)[0]["product_name"] == "A"

    def test_update_status_and_fields(self, repo):
        t = repo.create(project_id=1, product_name="A", planned_end=datetime.now())
        updated = repo.update(t["id"], status="в роботі", priority="терміново", quantity=5)
        assert updated["status"] == "в роботі"
        assert updated["priority"] == "терміново"
        assert updated["quantity"] == 5
        assert repo.get_all()[0]["status"] == "в роботі"

    def test_update_unknown_id_returns_none(self, repo):
        assert repo.update(999, status="готово") is None

    def test_delete(self, repo):
        t = repo.create(project_id=1, product_name="A")
        repo.delete(t["id"])
        assert repo.get_all() == []

    def test_delete_unknown_id_noop(self, repo):
        repo.delete(999)  # не має підняти виняток


class TestProductionService:
    def _patch_products(self, monkeypatch, products):
        from ventilation_company.database.repositories import product_repo

        monkeypatch.setattr(
            product_repo.ProductRepository,
            "get_all",
            staticmethod(lambda project_id=None: products),
        )

    def test_add_project_to_queue_all_products(self, repo, monkeypatch):
        from ventilation_company.services import production_service

        self._patch_products(
            monkeypatch,
            [
                {"name": "Відвод", "quantity": 2},
                {"name": "Фланець", "quantity": 8},
            ],
        )
        added, skipped = production_service.add_project_to_queue(1, priority="високий")
        assert (added, skipped) == (2, 0)
        tasks = repo.get_by_project(1)
        assert {t["product_name"] for t in tasks} == {"Відвод", "Фланець"}
        assert all(t["priority"] == "високий" for t in tasks)

    def test_add_project_to_queue_skips_duplicates(self, repo, monkeypatch):
        from ventilation_company.services import production_service

        self._patch_products(monkeypatch, [{"name": "Відвод", "quantity": 1}])
        production_service.add_project_to_queue(1)
        added, skipped = production_service.add_project_to_queue(1)
        assert (added, skipped) == (0, 1)  # вже в черзі — пропущено

    def test_add_project_to_queue_allows_readd_after_done(self, repo, monkeypatch):
        from ventilation_company.services import production_service

        self._patch_products(monkeypatch, [{"name": "Відвод", "quantity": 1}])
        production_service.add_project_to_queue(1)
        task = repo.get_by_project(1)[0]
        repo.update(task["id"], status="готово")
        added, skipped = production_service.add_project_to_queue(1)
        assert (added, skipped) == (1, 0)  # готове не блокує повторну партію

    def test_add_project_to_queue_selected_names(self, repo, monkeypatch):
        from ventilation_company.services import production_service

        self._patch_products(
            monkeypatch,
            [{"name": "Відвод"}, {"name": "Фланець"}, {"name": "Трійник"}],
        )
        added, _ = production_service.add_project_to_queue(1, product_names=["Відвод"])
        assert added == 1
        assert [t["product_name"] for t in repo.get_by_project(1)] == ["Відвод"]

    def test_add_project_to_queue_products_error_returns_zero(self, monkeypatch):
        from ventilation_company.database.repositories import product_repo
        from ventilation_company.services import production_service

        def _boom(project_id=None):
            raise RuntimeError("db down")

        monkeypatch.setattr(product_repo.ProductRepository, "get_all", staticmethod(_boom))
        assert production_service.add_project_to_queue(1) == (0, 0)

    def test_sorted_queue_priority_then_deadline(self, repo, monkeypatch):
        from ventilation_company.services import production_service

        now = datetime.now()
        repo.create(
            project_id=1, product_name="звичайний-пізно", planned_end=now + timedelta(days=5)
        )
        repo.create(
            project_id=1,
            product_name="терміново-пізно",
            priority="терміново",
            planned_end=now + timedelta(days=5),
        )
        repo.create(
            project_id=1,
            product_name="терміново-рано",
            priority="терміново",
            planned_end=now + timedelta(days=1),
        )

        queue = production_service.sorted_queue()
        names = [t["product_name"] for t in queue]
        assert names == ["терміново-рано", "терміново-пізно", "звичайний-пізно"]

    def test_sorted_queue_done_goes_last(self, repo):
        from ventilation_company.services import production_service

        repo.create(project_id=1, product_name="готово", status="готово", priority="терміново")
        repo.create(project_id=1, product_name="в-черзі", priority="низький")
        queue = production_service.sorted_queue()
        assert queue[-1]["product_name"] == "готово"
        assert queue[0]["product_name"] == "в-черзі"

    def test_days_left_and_summary_overdue(self, repo):
        from ventilation_company.services import production_service

        repo.create(
            project_id=1, product_name="в-термін", planned_end=datetime.now() + timedelta(days=2)
        )
        repo.create(
            project_id=1, product_name="прострочено", planned_end=datetime.now() - timedelta(days=3)
        )
        repo.create(
            project_id=1,
            product_name="готове-прострочено",
            status="готово",
            planned_end=datetime.now() - timedelta(days=3),
        )
        repo.create(project_id=1, product_name="без-терміну")

        tasks = repo.get_all()
        stats = production_service.summary(tasks)
        assert stats["counts"]["в черзі"] == 3
        assert stats["counts"]["готово"] == 1
        # простроченим рахується лише не-готове
        assert len(stats["overdue"]) == 1
        assert stats["overdue"][0]["product_name"] == "прострочено"
        assert production_service.days_left(stats["overdue"][0]) < 0
        # без терміну — None
        no_end = next(t for t in tasks if t["product_name"] == "без-терміну")
        assert production_service.days_left(no_end) is None


class TestProductionTabUI:
    def test_tab_builds_and_shows_queue(self, qapp, monkeypatch):
        """Вкладка будується та показує чергу (репозиторії ізольовані)."""
        from datetime import datetime as dt

        from ventilation_company.gui_pyside6 import production_tab as tab_module
        from ventilation_company.services import production_service

        now = dt.now()
        tasks = [
            {
                "id": 1,
                "project_id": 7,
                "product_name": "Відвод",
                "quantity": 2,
                "priority": "терміново",
                "status": "в черзі",
                "planned_start": now,
                "planned_end": now + timedelta(days=1),
                "created_at": now,
            },
            {
                "id": 2,
                "project_id": 7,
                "product_name": "Старий фланець",
                "quantity": 4,
                "priority": "звичайний",
                "status": "в роботі",
                "planned_start": now,
                "planned_end": now - timedelta(days=2),
                "created_at": now,
            },
        ]
        monkeypatch.setattr(production_service, "sorted_queue", lambda status=None: tasks)
        monkeypatch.setattr(
            production_service,
            "summary",
            lambda t, now=None: {
                "counts": {"в черзі": 1, "в роботі": 1, "готово": 0},
                "overdue": [tasks[1]],
            },
        )
        monkeypatch.setattr(
            tab_module.ProjectRepository,
            "list_all",
            staticmethod(lambda: [{"id": 7, "name": "Вентиляція ТЦ"}]),
        )

        tab = tab_module.ProductionTab()
        assert tab.table.rowCount() == 2
        assert "Відвод" in tab.table.item(0, 1).text()
        assert "Вентиляція ТЦ" in tab.table.item(0, 0).text()
        # прострочений рядок виділено червоним
        overdue_item = tab.table.item(1, 7)
        assert overdue_item is not None and overdue_item.foreground().color().isValid()
        # підсумок у шапці містить кількості
        assert "В черзі: 1" in tab.lbl_summary.text()
        assert "Прострочено: 1" in tab.lbl_summary.text()
