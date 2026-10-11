"""Єдине налаштування таблиць VentCompany.

Усі таблиці програми (QTableView/QTableWidget) проходять через setup_table():
однакова висота рядків (щоб редактори комірок поміщалися й текст не обрізався),
смугастий фон, прихований вертикальний заголовок, єдина поведінка вибору.

Клавіатурні дії (Excel-подібні):
  • друк символу на виділеній комірці — відкрити редактор із заміною
    (типова поведінка Qt AnyKeyPressed, зафіксована тестами);
  • Ctrl+F — швидкий пошук по таблиці (для всіх таблиць);
  • у таблицях з excel_keys=True:
      – Enter — зберегти комірку й перейти на рядок нижче (та ж колонка);
      – Tab — наступна редагована колонка, з останньої — наступний рядок;
      – Shift+Tab — назад (у т. ч. на попередній рядок);
      – Delete/Backspace — очистити виділені редаговані комірки;
      – Ctrl+C / Ctrl+V — копіювати поточну / вставити у виділені;
      – правий клік — контекстне меню цих дій.
"""

from typing import cast

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QInputDialog,
    QLineEdit,
    QMenu,
    QSpinBox,
    QTableView,
)

# Стандартна висота рядка: з запасом під компактний редактор комірки (див. theme.py)
DEFAULT_ROW_HEIGHT = 32

_EDITOR_TYPES = (QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox)


# ── Дії над комірками (використовуються і фільтром, і контекстним меню) ──


def selected_editable_indexes(table: QTableView) -> list:
    """Виділені комірки, які дозволяють редагування (без дублікатів)."""
    model = table.model()
    if model is None:
        return []
    seen: set = set()
    result = []
    for idx in table.selectedIndexes():
        if idx in seen:
            continue
        seen.add(idx)
        if model.flags(idx) & Qt.ItemFlag.ItemIsEditable:
            result.append(idx)
    return result


def clear_selection(table: QTableView) -> None:
    """Очистити виділені редаговані комірки (клавіша Delete)."""
    model = table.model()
    if model is None:
        return
    for idx in selected_editable_indexes(table):
        model.setData(idx, "", Qt.ItemDataRole.EditRole)


def copy_cell(table: QTableView) -> None:
    """Скопіювати текст поточної комірки у системний буфер (Ctrl+C)."""
    model = table.model()
    idx = table.currentIndex()
    if model is None or not idx.isValid():
        return
    text = str(model.data(idx, Qt.ItemDataRole.DisplayRole) or "")
    QGuiApplication.clipboard().setText(text)


def paste_to_selection(table: QTableView) -> None:
    """Вставити буфер обміну у всі виділені редаговані комірки (Ctrl+V)."""
    text = QGuiApplication.clipboard().text()
    if not text:
        return
    model = table.model()
    if model is None:
        return
    for idx in selected_editable_indexes(table):
        model.setData(idx, text, Qt.ItemDataRole.EditRole)


def quick_search(table: QTableView, text: str) -> bool:
    """Знайти наступну комірку з текстом (без урахування регістру).

    Пошук від поточного рядка вниз з переходом на початок (циклічно).
    Повертає True, якщо знайшов і виділив комірку.
    """
    model = table.model()
    if model is None or not text:
        return False
    rows, cols = model.rowCount(), model.columnCount()
    if rows == 0 or cols == 0:
        return False
    needle = text.casefold()
    current = table.currentIndex()
    start_row = current.row() + 1 if current.isValid() else 0
    order = [(r, c) for r in range(start_row, rows) for c in range(cols)]
    order += [(r, c) for r in range(0, start_row) for c in range(cols)]
    for r, c in order:
        idx = model.index(r, c)
        value = str(model.data(idx, Qt.ItemDataRole.DisplayRole) or "")
        if needle in value.casefold():
            table.setCurrentIndex(idx)
            selection = table.selectionModel()
            if selection is not None:
                selection.select(idx, selection.SelectionFlag.ClearAndSelect)
            table.scrollTo(idx)
            return True
    return False


# ── Контекстне меню ──


def build_cell_menu(table: QTableView) -> QMenu:
    """Контекстне меню дій над комірками (показати через menu.exec(...))."""
    menu = QMenu(table)
    menu.addAction("Копіювати\tCtrl+C", lambda: copy_cell(table))
    menu.addAction("Вставити\tCtrl+V", lambda: paste_to_selection(table))
    menu.addAction("Очистити\tDelete", lambda: clear_selection(table))
    return menu


def show_cell_menu(table: QTableView, global_pos) -> None:
    build_cell_menu(table).exec(global_pos)


# ── Фільтр клавіатури ──


class _ExcelKeysFilter(QObject):
    """Перехоплює клавіші таблиці: Enter/Tab у редакторі, дії над комірками.

    Фільтр ставиться на QApplication, але реагує лише на події «своєї»
    таблиці (редактори та viewport як її нащадки). Живе, поки жива таблиця.
    """

    def __init__(self, table: QTableView, excel_keys: bool = False):
        super().__init__(table)
        self._table = table
        self._excel = excel_keys
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() != QEvent.Type.KeyPress:
            return False
        key_event = cast(QKeyEvent, event)
        # ── Клавіші у відкритому редакторі комірки: переходи Enter/Tab ──
        if isinstance(obj, _EDITOR_TYPES) and self._table.isAncestorOf(obj):
            if not self._excel:
                return False
            key = key_event.key()
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._move(Qt.Key.Key_Down)
                return True
            if key == Qt.Key.Key_Tab:
                self._move(Qt.Key.Key_Tab)
                return True
            if key == Qt.Key.Key_Backtab:
                self._move(Qt.Key.Key_Backtab)
                return True
            return False
        # ── Клавіші на самій таблиці (viewport) ──
        if obj is not self._table.viewport():
            return False
        if self._table.state() == QAbstractItemView.State.EditingState:
            return False  # редактор відкритий — його клавіші його й обробляють
        key = key_event.key()
        modifiers = key_event.modifiers()
        ctrl = modifiers & Qt.KeyboardModifier.ControlModifier
        if ctrl and key == Qt.Key.Key_F:
            self._search_dialog()
            return True
        if not self._excel:
            return False
        if ctrl and key == Qt.Key.Key_C:
            copy_cell(self._table)
            return True
        if ctrl and key == Qt.Key.Key_V:
            paste_to_selection(self._table)
            return True
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and not ctrl:
            clear_selection(self._table)
            return True
        return False

    def _search_dialog(self) -> None:
        text, ok = QInputDialog.getText(self._table, "Пошук у таблиці", "Текст для пошуку:")
        if ok and text:
            quick_search(self._table, text)

    # ── Логіка переходу ──

    def _editable_columns(self, row: int) -> list[int]:
        model = self._table.model()
        if model is None:
            return []
        return [
            c
            for c in range(model.columnCount())
            if model.flags(model.index(row, c)) & Qt.ItemFlag.ItemIsEditable
        ]

    def _move(self, mode: Qt.Key) -> None:
        table = self._table
        model = table.model()
        idx = table.currentIndex()
        if model is None or not idx.isValid():
            return
        cols = self._editable_columns(idx.row())
        if not cols:
            table.setFocus()  # закрити редактор без переходу
            return
        row, col = idx.row(), idx.column()
        target_row, target_col = row, col
        last_row = model.rowCount() - 1
        if mode == Qt.Key.Key_Down:
            # Enter: униз тією ж колонкою; з останнього рядка — лишитися
            if row < last_row and col in cols:
                target_row = row + 1
        elif mode == Qt.Key.Key_Tab:
            later = [c for c in cols if c > col]
            if later:
                target_col = later[0]
            elif row < last_row:
                target_row, target_col = row + 1, cols[0]
        elif mode == Qt.Key.Key_Backtab:
            earlier = [c for c in cols if c < col]
            if earlier:
                target_col = earlier[-1]
            elif row > 0:
                target_row, target_col = row - 1, cols[-1]
        # Передаємо фокус таблиці — редактор коміть дані автоматично
        table.setFocus()
        target = model.index(target_row, target_col)
        table.setCurrentIndex(target)
        table.edit(target)


def setup_table(
    table: QTableView,
    *,
    select_rows: bool = False,
    single_selection: bool = False,
    extended_selection: bool = False,
    sorting: bool = False,
    read_only: bool = False,
    stretch_last: bool = True,
    alternating: bool = True,
    row_height: int = DEFAULT_ROW_HEIGHT,
    excel_keys: bool = False,
    cell_context_menu: bool = True,
) -> None:
    """Застосувати єдиний стиль і поведінку до таблиці.

    Параметри:
        select_rows: вибирати цілі рядки замість окремих комірок.
        single_selection: лише один рядок/комірка за раз.
        extended_selection: дозволити вибір кількох рядків (Ctrl/Shift).
        sorting: ввімкнути сортування кліком по заголовку.
        read_only: заборонити редагування комірок (лише перегляд).
        stretch_last: остання колонка розтягується на вільне місце.
        alternating: смугастий фон рядків.
        row_height: стандартна висота рядка в пікселях.
        excel_keys: Enter/Tab/Delete/Ctrl+C/V у редакторі й над комірками,
            як у Excel (для таблиць з вводом даних).
        cell_context_menu: правий клік у таблиці з excel_keys відкриває
            меню дій над комірками (вимкніть, якщо треба власне меню).
    """
    if alternating:
        table.setAlternatingRowColors(True)
    vh = table.verticalHeader()
    vh.setVisible(False)
    vh.setDefaultSectionSize(row_height)
    vh.setMinimumSectionSize(row_height)
    if stretch_last:
        table.horizontalHeader().setStretchLastSection(True)
    if select_rows:
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    if single_selection:
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    if extended_selection:
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    if sorting:
        table.setSortingEnabled(True)
    if read_only:
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    # Фільтр клавіатури — завжди (Ctrl+F для всіх, решта — з excel_keys)
    _ExcelKeysFilter(table, excel_keys=excel_keys)
    if excel_keys and cell_context_menu:
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(
            lambda pos, t=table: show_cell_menu(t, t.viewport().mapToGlobal(pos))
        )
