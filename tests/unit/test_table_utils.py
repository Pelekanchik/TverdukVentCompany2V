"""Тести єдиного налаштування таблиць (table_utils.setup_table)."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QGuiApplication, QKeyEvent, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QLineEdit, QTableView

from ventilation_company.gui_pyside6.table_utils import (
    DEFAULT_ROW_HEIGHT,
    setup_table,
)


@pytest.fixture(scope="module")
def qapp():
    """Власна фікстура QApplication (pytest-qt у CI не встановлено)."""
    app = QApplication.instance() or QApplication([])
    yield app


def _model(rows: int = 3, cols: int = 3) -> QStandardItemModel:
    """Модель 3×3: колонка 0 — не редагована, решта — редаговані."""
    model = QStandardItemModel(rows, cols)
    for r in range(rows):
        for c in range(cols):
            item = QStandardItem(f"r{r}c{c}")
            item.setEditable(c > 0)
            model.setItem(r, c, item)
    return model


def _press(editor, key: Qt.Key, modifier: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier):
    event = QKeyEvent(QEvent.Type.KeyPress, key, modifier)
    QApplication.sendEvent(editor, event)


class TestSetupTableDefaults:
    def test_uniform_row_height_and_hidden_header(self, qapp):
        table = QTableView()
        table.setModel(_model())
        setup_table(table)
        assert table.verticalHeader().defaultSectionSize() == DEFAULT_ROW_HEIGHT
        assert not table.verticalHeader().isVisible()
        assert table.alternatingRowColors()

    def test_row_height_parameter(self, qapp):
        table = QTableView()
        table.setModel(_model())
        setup_table(table, row_height=40)
        assert table.verticalHeader().defaultSectionSize() == 40


class TestExcelKeys:
    def _editing_table(self, qapp):
        table = QTableView()
        table.setModel(_model())
        setup_table(table, excel_keys=True)
        table.show()
        return table

    def _open_editor(self, qapp, table, row: int, col: int):
        idx = table.model().index(row, col)
        table.setCurrentIndex(idx)
        table.edit(idx)
        qapp.processEvents()
        editors = table.findChildren(QLineEdit)
        assert editors, "редактор комірки не відкрився"
        return editors[0]

    def test_tab_moves_to_next_editable_column(self, qapp):
        table = self._editing_table(qapp)
        editor = self._open_editor(qapp, table, 0, 1)
        editor.setText("111")
        _press(editor, Qt.Key.Key_Tab)
        qapp.processEvents()
        assert table.currentIndex().row() == 0
        assert table.currentIndex().column() == 2
        # Дані зафіксовані
        assert table.model().item(0, 1).text() == "111"

    def test_tab_wraps_from_last_column_to_next_row(self, qapp):
        table = self._editing_table(qapp)
        editor = self._open_editor(qapp, table, 0, 2)  # остання редагована колонка
        _press(editor, Qt.Key.Key_Tab)
        qapp.processEvents()
        assert table.currentIndex().row() == 1
        assert table.currentIndex().column() == 1  # перша редагована колонка

    def test_enter_moves_to_next_row_same_column(self, qapp):
        table = self._editing_table(qapp)
        editor = self._open_editor(qapp, table, 0, 2)
        _press(editor, Qt.Key.Key_Return)
        qapp.processEvents()
        assert table.currentIndex().row() == 1
        assert table.currentIndex().column() == 2

    def test_enter_stays_on_last_row(self, qapp):
        table = self._editing_table(qapp)
        editor = self._open_editor(qapp, table, 2, 1)  # останній рядок
        _press(editor, Qt.Key.Key_Return)
        qapp.processEvents()
        assert table.currentIndex().row() == 2

    def test_backtab_moves_to_previous_column(self, qapp):
        table = self._editing_table(qapp)
        editor = self._open_editor(qapp, table, 1, 2)
        _press(editor, Qt.Key.Key_Backtab, Qt.KeyboardModifier.ShiftModifier)
        qapp.processEvents()
        assert table.currentIndex().row() == 1
        assert table.currentIndex().column() == 1

    def test_editor_reopened_at_target(self, qapp):
        table = self._editing_table(qapp)
        editor = self._open_editor(qapp, table, 0, 1)
        _press(editor, Qt.Key.Key_Tab)
        qapp.processEvents()
        editors = table.findChildren(QLineEdit)
        assert editors, "редактор не відкрився у цільовій комірці"

    def test_disabled_without_excel_keys(self, qapp):
        table = QTableView()
        table.setModel(_model())
        setup_table(table)  # без excel_keys
        table.show()
        editor = self._open_editor(qapp, table, 0, 1)
        editor.setText("залишається")
        _press(editor, Qt.Key.Key_Tab)
        qapp.processEvents()
        # Фільтр не встановлено — поточний індекс не змінюється нашою логікою
        assert table.model().item(0, 1).text() == "залишається"


class TestTypeToEdit:
    """Швидке редагування: друк на виділеній комірці відкриває редактор
    із заміною тексту (типова поведінка Qt AnyKeyPressed — зафіксовано тестом,
    щоб рефакторинг setup_table її не втратив)."""

    def test_typing_replaces_cell_content(self, qapp):
        table = QTableView()
        table.setModel(_model())
        setup_table(table, excel_keys=True)
        table.show()
        table.setFocus()
        idx = table.model().index(0, 1)  # було "r0c1"
        table.setCurrentIndex(idx)
        qapp.processEvents()
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_7, Qt.KeyboardModifier.NoModifier, "7")
        QApplication.sendEvent(table.viewport(), event)
        qapp.processEvents()
        editors = table.findChildren(QLineEdit)
        assert editors, "друк не відкрив редактор комірки"
        assert editors[0].text() == "7", "друк не замінив вміст комірки"

    def test_typing_on_readonly_column_opens_nothing(self, qapp):
        table = QTableView()
        table.setModel(_model())
        setup_table(table, excel_keys=True)
        table.show()
        table.setFocus()
        table.setCurrentIndex(table.model().index(0, 0))  # колонка 0 — не редагована
        qapp.processEvents()
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_7, Qt.KeyboardModifier.NoModifier, "7")
        QApplication.sendEvent(table.viewport(), event)
        qapp.processEvents()
        assert not table.findChildren(QLineEdit), "відкрився редактор у read-only колонці"


def _press_on_viewport(
    table, key: Qt.Key, modifier: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier
):
    """Надіслати клавішу viewport таблиці (без відкритого редактора)."""
    event = QKeyEvent(QEvent.Type.KeyPress, key, modifier)
    QApplication.sendEvent(table.viewport(), event)


class TestExcelCellActions:
    """Delete очищає комірки, Ctrl+C/V — копіювати/вставити (як у Excel)."""

    def _table(self, qapp):
        table = QTableView()
        table.setModel(_model())
        setup_table(table, excel_keys=True)
        table.show()
        table.setFocus()
        return table

    def test_delete_clears_editable_cell(self, qapp):
        table = self._table(qapp)
        table.setCurrentIndex(table.model().index(0, 1))
        table.selectionModel().select(
            table.model().index(0, 1),
            table.selectionModel().SelectionFlag.ClearAndSelect,
        )
        qapp.processEvents()
        _press_on_viewport(table, Qt.Key.Key_Delete)
        qapp.processEvents()
        assert table.model().item(0, 1).text() == ""

    def test_delete_keeps_readonly_column(self, qapp):
        table = self._table(qapp)
        idx = table.model().index(0, 0)  # колонка 0 — не редагована
        table.setCurrentIndex(idx)
        table.selectionModel().select(idx, table.selectionModel().SelectionFlag.ClearAndSelect)
        qapp.processEvents()
        _press_on_viewport(table, Qt.Key.Key_Delete)
        qapp.processEvents()
        assert table.model().item(0, 0).text() == "r0c0"

    def test_ctrl_c_copies_current_cell_to_clipboard(self, qapp):
        table = self._table(qapp)
        table.setCurrentIndex(table.model().index(1, 2))
        qapp.processEvents()
        _press_on_viewport(table, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
        qapp.processEvents()
        assert QGuiApplication.clipboard().text() == "r1c2"

    def test_ctrl_v_pastes_into_selected_editable_cells(self, qapp):
        table = self._table(qapp)
        QGuiApplication.clipboard().setText("450.50")
        idx = table.model().index(0, 1)
        table.setCurrentIndex(idx)
        table.selectionModel().select(idx, table.selectionModel().SelectionFlag.ClearAndSelect)
        qapp.processEvents()
        _press_on_viewport(table, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
        qapp.processEvents()
        assert table.model().item(0, 1).text() == "450.50"
