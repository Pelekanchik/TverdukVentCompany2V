"""Тести гарячих клавій головного вікна: Ctrl+1..9 для перемикання вкладок."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QStackedWidget

from ventilation_company.gui_pyside6.main_window import add_tab_shortcuts


@pytest.fixture(scope="module")
def qapp():
    """Власна фікстура QApplication (pytest-qt у CI не встановлено)."""
    app = QApplication.instance() or QApplication([])
    yield app


def test_shortcuts_switch_active_widget(qapp):
    window = QMainWindow()
    stack = QStackedWidget()
    for i in range(4):
        stack.addWidget(QLabel(f"tab{i}"))
    window.setCentralWidget(stack)
    activated = []

    def on_activate(tab_id):
        activated.append(tab_id)
        stack.setCurrentIndex(tab_ids.index(tab_id))

    tab_ids = ["dashboard", "projects", "products", "crm"]
    shortcuts = add_tab_shortcuts(window, tab_ids, on_activate)
    assert len(shortcuts) == 4

    shortcuts[2].activated.emit()  # ніби натиснули Ctrl+3
    qapp.processEvents()
    assert activated == ["products"]
    assert stack.currentIndex() == 2


def test_shortcuts_limited_to_nine(qapp):
    window = QMainWindow()
    tab_ids = [f"tab{i}" for i in range(12)]
    shortcuts = add_tab_shortcuts(window, tab_ids, lambda tid: None)
    assert len(shortcuts) == 9
    window.close()
