"""Діалог перевірки заявки на матеріали перед формуванням Excel.

Розрахований список матеріалів показується у вигляді таблиці: користувач
може змінити кількість, ціну, назву, специфікацію, видалити зайві позиції
або додати власні — і лише потім сформувати Excel-файл заявки.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.gui_pyside6.table_utils import build_cell_menu, setup_table
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.material_order import MaterialItem, MaterialOrder

COLUMNS = [
    "Категорія",
    "Найменування",
    "Специфікація",
    "Од. вим.",
    "Кількість",
    "Ціна",
    "Сума",
    "Примітки",
]
# Колонки, доступні для редагування (сума — обчислювана)
EDITABLE_COLUMNS = {0, 1, 2, 3, 4, 5, 7}
QTY_COL = 4
PRICE_COL = 5
SUM_COL = 6

# Фон рядка без ціни (попереджувальна підсвітка)
_NO_PRICE_BG = "#fde8e8"


def _parse_float(text: str) -> float:
    try:
        return float(text.replace(",", ".").replace(" ", ""))
    except (TypeError, ValueError):
        return 0.0


class MaterialOrderPreviewDialog(QDialog):
    """Попередній перегляд і редагування заявки на матеріали."""

    def __init__(
        self, order: MaterialOrder, parent: QWidget | None = None, project_id: int | None = None
    ):
        super().__init__(parent)
        self._order = order
        self._project_id = project_id
        self.setWindowTitle(f"Замовлення матеріалів — {order.project_name}")
        self.setMinimumWidth(980)
        self.setMinimumHeight(560)
        self.resize(1050, 620)
        self._updating_sum = False
        self._filling_price = False
        self._build_ui()
        self._populate()

    # ── UI ──

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.lbl_info = QLabel()
        self.lbl_info.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-size: 14px;")
        layout.addWidget(self.lbl_info)

        hint = QLabel(
            "✏️ Відкорегуйте позиції: друк — замінити комірку, Enter — рядок нижче, "
            "Tab — наступна колонка, Delete — очистити, Ctrl+C/V — копіювати/вставити. "
            "Сума перераховується автоматично."
        )
        hint.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(hint)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        setup_table(self.table, select_rows=True, excel_keys=True, cell_context_menu=False)
        self.table.itemChanged.connect(self._on_item_changed)
        # Власне контекстне меню: дії над комірками + над рядками
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self.table.setColumnWidth(0, 130)
        self.table.setColumnWidth(1, 190)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 60)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(5, 90)
        self.table.setColumnWidth(6, 100)
        self.table.setColumnWidth(7, 180)
        layout.addWidget(self.table)

        row_actions = QHBoxLayout()
        btn_add = QPushButton("➕ Додати рядок")
        btn_add.clicked.connect(self._add_row)
        row_actions.addWidget(btn_add)
        btn_dup = QPushButton("⧉ Дублювати рядок")
        btn_dup.setToolTip("Скопіювати виділений рядок нижче нього")
        btn_dup.clicked.connect(self._duplicate_selected_row)
        row_actions.addWidget(btn_dup)
        btn_sort = QPushButton("🔡 Впорядкувати")
        btn_sort.setToolTip("Відсортувати позиції за категорією й назвою")
        btn_sort.clicked.connect(self._sort_rows)
        row_actions.addWidget(btn_sort)
        btn_del = QPushButton("🗑 Видалити рядок")
        btn_del.setStyleSheet(f"color: {Theme.DANGER};")
        btn_del.clicked.connect(self._delete_selected_row)
        row_actions.addWidget(btn_del)
        row_actions.addStretch()
        self.lbl_total = QLabel()
        self.lbl_total.setStyleSheet(
            f"color: {Theme.TEXT_BRIGHT}; font-weight: bold; font-size: 14px;"
        )
        row_actions.addWidget(self.lbl_total)
        layout.addLayout(row_actions)

        buttons = QHBoxLayout()
        buttons.addStretch()
        btn_cancel = QPushButton("Скасувати")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_cancel)
        btn_ok = QPushButton("💾 Сформувати заявку")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._on_accept)
        buttons.addWidget(btn_ok)
        layout.addLayout(buttons)

    def _populate(self):
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(0)
            for item in self._order.items:
                self._append_row(item)
        finally:
            self.table.blockSignals(False)
        self._update_totals()

    def _append_row(self, item: MaterialItem, at_row: int | None = None):
        """Додати рядок у кінець (at_row=None) або вставити після вказаного рядка."""
        row = self.table.rowCount() if at_row is None else at_row + 1
        self.table.insertRow(row)
        values = [
            item.category,
            item.name,
            item.specification,
            item.unit,
            f"{item.quantity:g}",
            f"{item.price_per_unit:g}" if item.price_per_unit else "",
            "",
            item.notes,
        ]
        for col, text in enumerate(values):
            cell = QTableWidgetItem(text)
            if col not in EDITABLE_COLUMNS:
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if col in (QTY_COL, PRICE_COL, SUM_COL):
                cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, col, cell)
        self._update_row_sum(row)
        self._highlight_row(row)

    def _highlight_row(self, row: int):
        """Підсвітити рядок, якщо ціна не заповнена (щоб не забути вписати)."""
        no_price = _parse_float(self._cell_text(row, PRICE_COL)) <= 0
        brush = QBrush(QColor(_NO_PRICE_BG)) if no_price else QBrush()
        for col in range(self.table.columnCount()):
            cell = self.table.item(row, col)
            if cell is not None:
                cell.setBackground(brush)

    def _update_row_sum(self, row: int):
        qty = _parse_float(self._cell_text(row, QTY_COL))
        price = _parse_float(self._cell_text(row, PRICE_COL))
        self._updating_sum = True
        try:
            cell = self.table.item(row, SUM_COL)
            if cell is not None:
                cell.setText(f"{qty * price:,.2f}")
        finally:
            self._updating_sum = False

    def _update_totals(self):
        total = 0.0
        for row in range(self.table.rowCount()):
            qty_item = self.table.item(row, QTY_COL)
            price_item = self.table.item(row, PRICE_COL)
            if qty_item and price_item:
                total += _parse_float(qty_item.text()) * _parse_float(price_item.text())
        self.lbl_info.setText(f"📦 {self._order.project_name} — позицій: {self.table.rowCount()}")
        self.lbl_total.setText(f"Разом: ₴ {total:,.2f}")

    def _on_item_changed(self, item: QTableWidgetItem):
        if self._updating_sum or self._filling_price:
            return
        if item.column() in (QTY_COL, PRICE_COL):
            self._update_row_sum(item.row())
            self._highlight_row(item.row())
        elif item.column() == 1:
            # Зміна найменування → підставити останню відом ціну, якщо ціна порожня
            self._apply_history_price(item.row())
        self._update_totals()

    def _apply_history_price(self, row: int):
        """Якщо для введеної назви є історія цін — підставити останню у порожню ціну."""
        name = self._cell_text(row, 1)
        if not name or _parse_float(self._cell_text(row, PRICE_COL)) > 0:
            return
        try:
            from ventilation_company.database.repositories.purchase_price_repo import (
                PurchasePriceRepository,
            )

            history = PurchasePriceRepository.latest_for(name, limit=1)
        except Exception:  # noqa: BLE001 — історія не має блокувати редагування
            return
        if not history:
            return
        price = history[0]["price"]
        price_item = self.table.item(row, PRICE_COL)
        if price_item is None:
            return
        self._filling_price = True
        try:
            price_item.setText(f"{price:g}")
            self._update_row_sum(row)
            self._highlight_row(row)
        finally:
            self._filling_price = False

    # ── Дії ──

    def _add_row(self):
        self.table.blockSignals(True)
        try:
            self._append_row(
                MaterialItem(
                    category="Розхідні матеріали",
                    name="Новий матеріал",
                    specification="",
                    unit="шт",
                    quantity=1,
                    price_per_unit=0,
                )
            )
        finally:
            self.table.blockSignals(False)
        self._update_totals()
        last = self.table.rowCount() - 1
        self.table.setCurrentCell(last, 1)
        name_item = self.table.item(last, 1)
        if name_item is not None:
            self.table.editItem(name_item)

    def _delete_selected_row(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            QMessageBox.information(self, "Видалення", "Спочатку виберіть рядок у таблиці.")
            return
        reply = QMessageBox.question(
            self,
            "Видалення",
            (
                f"Видалити {len(rows)} ряд. з заявки?"
                if len(rows) > 1
                else "Видалити виділений рядок із заявки?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for row in rows:
            self.table.removeRow(row)
        self._update_totals()

    def _sort_rows(self):
        """Впорядкувати позиції за категорією, далі за назвою."""
        items = self.get_order().items
        items.sort(key=lambda i: (i.category.casefold(), i.name.casefold()))
        self._populate_from_items(items)

    def _populate_from_items(self, items: list[MaterialItem]):
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(0)
            for item in items:
                self._append_row(item)
        finally:
            self.table.blockSignals(False)
        self._update_totals()

    def _on_context_menu(self, pos):
        menu = build_cell_menu(self.table)
        menu.addSeparator()
        menu.addAction("⧉ Дублювати рядок", self._duplicate_selected_row)
        menu.addAction("🗑 Видалити рядок(и)", self._delete_selected_row)
        menu.addAction("🔡 Впорядкувати", self._sort_rows)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _duplicate_selected_row(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Дублювання", "Спочатку виберіть рядок у таблиці.")
            return
        item = MaterialItem(
            category=self._cell_text(row, 0) or "Матеріали",
            name=self._cell_text(row, 1) or "—",
            specification=self._cell_text(row, 2),
            unit=self._cell_text(row, 3) or "шт",
            quantity=_parse_float(self._cell_text(row, QTY_COL)),
            price_per_unit=_parse_float(self._cell_text(row, PRICE_COL)),
            notes=self._cell_text(row, 7),
        )
        self.table.blockSignals(True)
        try:
            self._append_row(item, at_row=row)
        finally:
            self.table.blockSignals(False)
        self._update_totals()
        self.table.setCurrentCell(row + 1, 1)

    def _on_accept(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(
                self, "Заявка порожня", "У заявці немає жодної позиції — додайте матеріали."
            )
            return
        without_price = sum(
            1
            for row in range(self.table.rowCount())
            if _parse_float(self._cell_text(row, PRICE_COL)) <= 0
        )
        if without_price:
            reply = QMessageBox.question(
                self,
                "Позиції без ціни",
                f"У {without_price} поз. не вказано ціну (0). " "Сформувати заявку так?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self._record_purchase_prices()
        self.accept()

    def _record_purchase_prices(self):
        """Зафіксувати ціни затвердженої заявки в історії закупівель."""
        try:
            from ventilation_company.database.repositories.purchase_price_repo import (
                PurchasePriceRepository,
            )

            for item in self.get_order().items:
                if item.price_per_unit > 0 and item.name and item.name != "—":
                    PurchasePriceRepository.record(
                        item_name=item.name,
                        price=item.price_per_unit,
                        supplier=item.supplier,
                        project_id=self._project_id,
                    )
        except Exception:  # noqa: BLE001 — історія не має блокувати заявку
            pass

    # ── Результат ──

    def _cell_text(self, row: int, col: int) -> str:
        cell = self.table.item(row, col)
        return cell.text().strip() if cell else ""

    def get_order(self) -> MaterialOrder:
        """Заявка з урахуванням правок користувача."""
        items: list[MaterialItem] = []
        for row in range(self.table.rowCount()):
            items.append(
                MaterialItem(
                    category=self._cell_text(row, 0) or "Матеріали",
                    name=self._cell_text(row, 1) or "—",
                    specification=self._cell_text(row, 2),
                    unit=self._cell_text(row, 3) or "шт",
                    quantity=_parse_float(self._cell_text(row, QTY_COL)),
                    price_per_unit=_parse_float(self._cell_text(row, PRICE_COL)),
                    notes=self._cell_text(row, 7),
                )
            )
        return MaterialOrder(
            project_name=self._order.project_name,
            order_date=self._order.order_date,
            items=items,
            notes=self._order.notes,
        )
