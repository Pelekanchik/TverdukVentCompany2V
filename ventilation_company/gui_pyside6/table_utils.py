"""Єдине налаштування таблиць VentCompany.

Усі таблиці програми (QTableView/QTableWidget) проходять через setup_table():
однакова висота рядків (щоб редактори комірок поміщалися й текст не обрізався),
смугастий фон, прихований вертикальний заголовок, єдина поведінка вибору.

Опційно — Excel-подібна навігація клавіатурою (excel_keys=True):
  • друк символу на виділеній комірці — відкрити редактор із заміною
    (типова поведінка Qt AnyKeyPressed, зафіксована тестами);
  • Enter — зберегти комірку й перейти на рядок нижче (та ж колонка);
  • Tab — зберегти й перейти до наступної редагованої колонки,
    з останньої — до першої колонки наступного рядка;
  • Shift+Tab — назад (у т. ч. на попередній рядок);
  • Delete/Backspace — очистити виділені редаговані комірки;
  • Ctrl+C / Ctrl+V — скопіювати поточну комірку / вставити у виділені.
"""

from typing import cast

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QLineEdit,
    QSpinBox,
    QTableView,
)

# Стандартна висота рядка: з запасом під компактний редактор комірки (див. theme.py)
DEFAULT_ROW_HEIGHT = 32

_EDITOR_TYPES = (QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox)


class _ExcelKeysFilter(QObject):
    """Перехоплює Enter/Tab у редакторі комірки й рухає курсор як у Excel.

    Фільтр ставиться на QApplication, але реагує лише на редактори,
    що належать «своїй» таблиці. Живе, поки жива таблиця (батько).
    """

    def __init__(self, table: QTableView):
        super().__init__(table)
        self._table = table
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() != QEvent.Type.KeyPress:
            return False
        key_event = cast(QKeyEvent, event)
        # ── Клавіші у відкритому редакторі комірки: переходи Enter/Tab ──
        if isinstance(obj, _EDITOR_TYPES) and self._table.isAncestorOf(obj):
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
        # ── Клавіші на самій таблиці (без редактора): Excel-дії ──
        if obj is not self._table.viewport():
            return False
        if self._table.state() == QAbstractItemView.State.EditingState:
            return False  # редактор відкритий — його клавіші його й обробляють
        key = key_event.key()
        modifiers = key_event.modifiers()
        ctrl = modifiers & Qt.KeyboardModifier.ControlModifier
        if ctrl and key == Qt.Key.Key_C:
            self._copy()
            return True
        if ctrl and key == Qt.Key.Key_V:
            self._paste()
            return True
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and not ctrl:
            self._clear_selection()
            return True
        return False

    # ── Excel-дії над виділеними комірками ──

    def _selected_editable(self) -> list:
        model = self._table.model()
        if model is None:
            return []
        seen: set = set()
        result = []
        for idx in self._table.selectedIndexes():
            if idx in seen:
                continue
            seen.add(idx)
            if model.flags(idx) & Qt.ItemFlag.ItemIsEditable:
                result.append(idx)
        return result

    def _clear_selection(self) -> None:
        """Delete/Backspace: очистити виділені редаговані комірки."""
        model = self._table.model()
        if model is None:
            return
        for idx in self._selected_editable():
            model.setData(idx, "", Qt.ItemDataRole.EditRole)

    def _copy(self) -> None:
        """Ctrl+C: скопіювати текст поточної комірки у системний буфер."""
        clipboard = QGuiApplication.clipboard()
        idx = self._table.currentIndex()
        if idx.isValid() and self._table.model() is not None:
            text = str(self._table.model().data(idx, Qt.ItemDataRole.DisplayRole) or "")
            clipboard.setText(text)

    def _paste(self) -> None:
        """Ctrl+V: вставити буфер у всі виділені редаговані комірки."""
        clipboard = QGuiApplication.clipboard()
        text = clipboard.text()
        if not text:
            return
        model = self._table.model()
        if model is None:
            return
        for idx in self._selected_editable():
            model.setData(idx, text, Qt.ItemDataRole.EditRole)

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
        excel_keys: Enter/Tab у редакторі комірки переходять до наступної
            комірки/рядка, як у Excel (для таблиць з вводом даних).
            Швидке редагування друком (AnyKeyPressed) — типова поведінка Qt
            і працює за замовчуванням: символ на виділеній комірці відкриває
            редактор із заміною тексту; тести в test_table_utils.py
            фіксують, що setup_table цю поведінку не ламає.
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
    if excel_keys:
        _ExcelKeysFilter(table)
