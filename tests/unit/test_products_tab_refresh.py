"""Регресійний тест: новий проєкт має з'являтися у списку проєктів вкладки «Вироби».

Баг: combo_project наповнювався лише раз у __init__, а on_project_changed() і
refresh() лише перезавантажували таблицю виробів. Тому після створення проєкту
у вкладці «Проєкти» він не з'являвся у списку «Вироби» до перезапуску програми.

Запуск: pytest tests/unit/test_products_tab_refresh.py -v
"""

import os
import types

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

import ventilation_company.gui_pyside6.products_tab as products_tab_module
from ventilation_company.database.repositories.product_repo import ProductRepository
from ventilation_company.database.repositories.project_repo import ProjectRepository
from ventilation_company.gui_pyside6.products_tab import ProductsTab


class _FakeMainWindow:
    """Мінімальна заміна MainWindow для вкладки (active_project_id + setter)."""

    def __init__(self):
        self.active_project_id = None

    def set_active_project(self, project_id):
        self.active_project_id = project_id


@pytest.fixture()
def products_tab_ctx(monkeypatch):
    app = QApplication.instance() or QApplication([])

    projects = [
        {"id": 1, "project_number": "PRJ-1", "name": "Старий проєкт"},
    ]
    monkeypatch.setattr(ProjectRepository, "list_all", staticmethod(lambda: list(projects)))
    monkeypatch.setattr(ProductRepository, "get_all", staticmethod(lambda project_id=None: []))
    monkeypatch.setattr(ProductRepository, "search", staticmethod(lambda **kwargs: []))
    # load_settings читає data/pricing_settings.json — у тестах не потрібен
    monkeypatch.setattr(
        products_tab_module, "load_settings", lambda: {"material_prices": {}}
    )

    main_window = _FakeMainWindow()
    tab = ProductsTab(main_window=main_window)

    # types.SimpleNamespace — тому що клас у тілі фікстури не бачить
    # локальних змінних функції (NameError), а namespace — бачить
    return types.SimpleNamespace(tab=tab, main_window=main_window, projects=projects)


def _project_ids(tab) -> list:
    return [tab.combo_project.itemData(i) for i in range(tab.combo_project.count())]


def test_new_project_appears_after_on_project_changed(products_tab_ctx):
    """Симуляція створення проєкту у вкладці «Проєкти» (ProjectsTab._on_new_project)."""
    ctx = products_tab_ctx
    ctx.projects.append({"id": 2, "project_number": "PRJ-2", "name": "Новий проєкт"})

    # Так само, як MainWindow.set_active_project → tab.on_project_changed(...)
    ctx.main_window.active_project_id = 2
    ctx.tab.on_project_changed(2)

    assert 2 in _project_ids(ctx.tab), "Новий проєкт не з'явився у списку вкладки «Вироби»"
    assert ctx.tab.combo_project.currentData() == 2


def test_new_project_appears_after_tab_refresh(products_tab_ctx):
    """refresh() викликається при кожному перемиканні на вкладку."""
    ctx = products_tab_ctx
    ctx.projects.append({"id": 3, "project_number": "PRJ-3", "name": "Ще один проєкт"})

    ctx.tab.refresh()

    assert 3 in _project_ids(ctx.tab)


def test_deleted_project_removed_after_tab_refresh(products_tab_ctx):
    ctx = products_tab_ctx
    del ctx.projects[0]

    ctx.tab.refresh()

    assert _project_ids(ctx.tab) == [None]
