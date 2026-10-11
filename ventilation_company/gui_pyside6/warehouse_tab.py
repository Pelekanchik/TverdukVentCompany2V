"""Вкладка «Склад»: залишки матеріалів, надходження/списання, історія рухів.

Позиції зі зниженим залишком (≤ мінімального) підсвічуються.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.auth.permissions import Permission, has_permission
from ventilation_company.database.repositories.purchase_price_repo import (
    PurchasePriceRepository,
)
from ventilation_company.database.repositories.warehouse_repo import WarehouseRepository
from ventilation_company.gui_pyside6.table_utils import setup_table
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.services import supplier_prices_service

COLUMNS = ["Найменування", "Од. вим.", "Залишок", "Зарезерв.", "Доступно", "Мін. залишок", "Статус"]

_LOW_BG = "#fde8e8"


class ItemEditDialog(QDialog):
    """Додавання/редагування позиції складу."""

    def __init__(self, item: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Позиція складу" if item is None else "Змінити позицію")
        self.setMinimumWidth(380)
        layout = QFormLayout(self)
        self.edit_name = QLineEdit(item.get("name", "") if item else "")
        self.edit_unit = QLineEdit(item.get("unit", "шт") if item else "шт")
        self.spin_min = QDoubleSpinBox()
        self.spin_min.setRange(0, 1_000_000)
        self.spin_min.setDecimals(2)
        self.spin_min.setValue(float(item.get("min_quantity", 0)) if item else 0.0)
        layout.addRow("Найменування:", self.edit_name)
        layout.addRow("Од. вим.:", self.edit_unit)
        layout.addRow("Мін. залишок:", self.spin_min)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        return {
            "name": self.edit_name.text().strip(),
            "unit": self.edit_unit.text().strip() or "шт",
            "min_quantity": self.spin_min.value(),
        }


class MoveDialog(QDialog):
    """Надходження або списання позиції."""

    def __init__(self, item: dict, kind: str, parent=None):
        super().__init__(parent)
        title = "Надходження на склад" if kind == "in" else "Списання зі складу"
        self.setWindowTitle(f"{title} — {item['name']}")
        self.setMinimumWidth(380)
        layout = QFormLayout(self)
        self.spin_qty = QDoubleSpinBox()
        self.spin_qty.setRange(0.01, 1_000_000)
        self.spin_qty.setDecimals(2)
        layout.addRow("Кількість:", self.spin_qty)
        self.edit_date = QLineEdit(date.today().isoformat())
        layout.addRow("Дата (РРРР-ММ-ДД):", self.edit_date)
        self.edit_note = QLineEdit()
        layout.addRow("Примітка:", self.edit_note)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        return {
            "quantity": self.spin_qty.value(),
            "move_date": self.edit_date.text().strip() or date.today().isoformat(),
            "note": self.edit_note.text().strip(),
        }


class WarehouseTab(QWidget):
    """Склад: залишки, рухи, мінімальні залишки."""

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._rows: list[dict] = []
        self._build_ui()
        self.refresh()

    def _can_edit(self) -> bool:
        if self.current_user is None:
            return True  # тести / сумісність
        return has_permission(self.current_user.role, Permission.WAREHOUSE_EDIT)

    # ── UI ──

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QLabel("📦 Склад: залишки матеріалів")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        root.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        setup_table(self.table, select_rows=True, read_only=True, stretch_last=False)
        root.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.btn_add = QPushButton("➕ Додати позицію")
        self.btn_add.clicked.connect(self._on_add)
        actions.addWidget(self.btn_add)
        self.btn_edit = QPushButton("✏️ Змінити")
        self.btn_edit.clicked.connect(self._on_edit)
        actions.addWidget(self.btn_edit)
        self.btn_in = QPushButton("📥 Надходження")
        self.btn_in.clicked.connect(lambda: self._on_move("in"))
        actions.addWidget(self.btn_in)
        self.btn_out = QPushButton("📤 Списання")
        self.btn_out.clicked.connect(lambda: self._on_move("out"))
        actions.addWidget(self.btn_out)
        self.btn_history = QPushButton("🧾 Історія рухів")
        self.btn_history.clicked.connect(self._on_history)
        actions.addWidget(self.btn_history)
        self.btn_price_import = QPushButton("📥 Прайс постачальника")
        self.btn_price_import.setToolTip(
            "Імпорт прайсу постачальника (CSV/XLSX): історія цін + сповіщення\n"
            "у Telegram, якщо ціни зросли"
        )
        self.btn_price_import.clicked.connect(self._on_price_import)
        actions.addWidget(self.btn_price_import)
        self.btn_price_history = QPushButton("📈 Історія цін")
        self.btn_price_history.clicked.connect(self._on_price_history)
        actions.addWidget(self.btn_price_history)
        self.btn_del = QPushButton("🗑 Видалити")
        self.btn_del.setStyleSheet(f"color: {Theme.DANGER};")
        self.btn_del.clicked.connect(self._on_delete)
        actions.addWidget(self.btn_del)
        actions.addStretch()
        self.lbl_total = QLabel("")
        self.lbl_total.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        actions.addWidget(self.lbl_total)
        root.addLayout(actions)

        if not self._can_edit():
            for btn in (self.btn_add, self.btn_edit, self.btn_in, self.btn_out, self.btn_del):
                btn.setEnabled(False)

    # ── Дані ──

    def refresh(self):
        try:
            self._rows = WarehouseRepository.list_items()
        except Exception:  # noqa: BLE001 — вкладка не має падати через БД
            self._rows = []
        self._refill_table()

    def _refill_table(self):
        self.table.setRowCount(0)
        low_count = 0
        for r in self._rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            status = "⚠️ замовити" if r["low"] else "✓"
            values = [
                r["name"],
                r["unit"],
                f"{r['quantity']:,.2f}",
                f"{r.get('reserved', 0):,.2f}",
                f"{r.get('available', r['quantity']):,.2f}",
                f"{r['min_quantity']:,.2f}",
                status,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col in (2, 3, 4, 5):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                if r["low"]:
                    item.setBackground(QColor(_LOW_BG))
                    if col == 6:
                        item.setForeground(QColor(Theme.DANGER))
                self.table.setItem(row, col, item)
            if r["low"]:
                low_count += 1
        self.lbl_total.setText(
            f"Позицій: {len(self._rows)}" + (f" · на межі: {low_count}" if low_count else "")
        )

    def _selected_row(self) -> dict | None:
        row = self.table.currentRow()
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    # ── Дії ──

    def _on_add(self):
        dlg = ItemEditDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data["name"]:
            QMessageBox.warning(self, "Увага", "Вкажіть найменування.")
            return
        WarehouseRepository.create_item(
            name=data["name"], unit=data["unit"], min_quantity=data["min_quantity"]
        )
        self.refresh()

    def _on_edit(self):
        item = self._selected_row()
        if not item:
            QMessageBox.information(self, "Увага", "Спочатку оберіть позицію у таблиці.")
            return
        dlg = ItemEditDialog(item=item, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data["name"]:
            QMessageBox.warning(self, "Увага", "Вкажіть найменування.")
            return
        WarehouseRepository.update_item(item["id"], data)
        self.refresh()

    def _on_move(self, kind: str):
        item = self._selected_row()
        if not item:
            QMessageBox.information(self, "Увага", "Спочатку оберіть позицію у таблиці.")
            return
        dlg = MoveDialog(item=item, kind=kind, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        try:
            result = WarehouseRepository.add_move(
                item_id=item["id"], quantity=data["quantity"], kind=kind, **data
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Увага", str(exc))
            return
        if result is None:
            QMessageBox.warning(self, "Увага", "Позицію не знайдено.")
        self.refresh()

    def _on_history(self):
        item = self._selected_row()
        if not item:
            QMessageBox.information(self, "Увага", "Спочатку оберіть позицію у таблиці.")
            return
        try:
            moves = WarehouseRepository.list_moves(item_id=item["id"])
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Помилка", f"Не вдалося завантажити історію:\n{exc}")
            return
        lines = [
            f"{m['move_date']}  {'📥' if m['kind'] == 'in' else '📤'} "
            f"{m['quantity']:,.2f}  {m['note']}"
            for m in moves
        ]
        text = "\n".join(lines) if lines else "Рухів ще не було."
        QMessageBox.information(self, f"Історія рухів — {item['name']}", text)

    def _on_price_import(self):
        if not self._can_edit():
            QMessageBox.warning(self, "Увага", "Недостатньо прав для імпорту прайсів")
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Оберіть прайс постачальника",
            "",
            "Прайси (*.csv *.xlsx);;CSV (*.csv);;Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            entries = supplier_prices_service.parse_price_file(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Помилка читання", str(exc))
            return
        if not entries:
            QMessageBox.information(
                self, "Прайс", "У файлі не знайдено жодного рядка з назвою та ціною"
            )
            return
        report = supplier_prices_service.import_prices(entries)
        increased = report["increased"]
        message = f"Імпортовано цін: {report['recorded']}" + (
            f"\nПропущено рядків: {report['skipped']}" if report["skipped"] else ""
        )
        if increased:
            message += f"\n\n⚠️ Здорожчало позицій: {len(increased)}\n" + "\n".join(
                f"• {r['item']}: {r['old']:g} → {r['new']:g} ₴" for r in increased[:10]
            )
        QMessageBox.information(self, "Імпорт прайсу", message)
        if (
            increased
            and QMessageBox.question(
                self,
                "Telegram",
                "Надіслати дайджест здорожчань у Telegram?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            sent = supplier_prices_service.notify_price_increases(increased)
            if not sent:
                QMessageBox.information(
                    self,
                    "Telegram",
                    "Не надіслано — бота не налаштовано (Налаштування → Резервні копії → Telegram)",
                )

    def _on_price_history(self):
        item = self._selected_row()
        default_name = item["name"] if item else ""
        name, ok = QInputDialog.getText(
            self, "Історія цін", "Найменування матеріалу:", text=default_name
        )
        if not ok or not name.strip():
            return
        try:
            history = PurchasePriceRepository.latest_for(name.strip(), limit=10)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Помилка", f"Не вдалося завантажити історію:\n{exc}")
            return
        if not history:
            QMessageBox.information(
                self, "Історія цін", f"За «{name.strip()}» історії цін ще немає"
            )
            return
        best = PurchasePriceRepository.best_price_for(name.strip())
        lines = [
            f"{h['purchase_date'] or '—'}  {h['price']:g} ₴"
            + (f"  ({h['supplier']})" if h["supplier"] else "")
            for h in history
        ]
        QMessageBox.information(
            self,
            f"Історія цін — {name.strip()}",
            f"Найкраща ціна: {best:g} ₴\n\n" + "\n".join(lines),
        )

    def _on_delete(self):
        item = self._selected_row()
        if not item:
            QMessageBox.information(self, "Увага", "Спочатку оберіть позицію у таблиці.")
            return
        answer = QMessageBox.question(
            self,
            "Видалення позиції",
            f"Видалити «{item['name']}» зі складу?\nІсторія рухів теж буде видалена.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        WarehouseRepository.delete_item(item["id"])
        self.refresh()
