"""Вкладка «Гроші»: дебіторка по проєктах.

Показує по кожному проєкту: вартість для замовника, сплачено, залишок
і % оплати, з фільтрами та загальними підсумками. Подвійний клік —
картка проєкту.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.gui_pyside6.table_utils import setup_table
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.services import accounting_export_service
from ventilation_company.services.receivables import (
    build_receivables,
    is_overdue,
    receivables_totals,
)

FILTERS = [
    "Усі",
    "Борг",
    "Прострочено",
    "Оплачено повністю",
    "Частково оплачено",
    "Переплата",
    "Без оплат",
]

COLUMNS = [
    "№ проєкту",
    "Назва",
    "Клієнт",
    "Статус",
    "Вартість",
    "Сплачено",
    "Залишок",
    "%",
    "Остання оплата",
]


class AccountingExportDialog(QDialog):
    """Експорт виписки оплат для бухгалтерії + звіт по ПДВ."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("💼 Для бухгалтерії")
        self.setMinimumWidth(440)
        layout = QFormLayout(self)

        first = QDate.currentDate().addDays(1 - QDate.currentDate().day())
        self.date_from = QDateEdit(first)
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        layout.addRow("Період з:", self.date_from)

        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        layout.addRow("по:", self.date_to)

        self.combo_format = QComboBox()
        self.combo_format.addItem("CSV для Excel (з BOM, роздільник ;) ", "csv")
        self.combo_format.addItem("1С:Клієнт банку (TXT)", "1c")
        layout.addRow("Формат виписки:", self.combo_format)

        self.lbl_vat = QLabel("—")
        self.lbl_vat.setWordWrap(True)
        self.lbl_vat.setStyleSheet(f"color: {Theme.TEXT};")
        layout.addRow(self.lbl_vat)

        buttons = QHBoxLayout()
        btn_export = QPushButton("📤 Експорт виписки")
        btn_export.clicked.connect(self._on_export)
        buttons.addWidget(btn_export)
        btn_vat = QPushButton("📊 Розрахувати ПДВ")
        btn_vat.clicked.connect(self._on_vat)
        buttons.addWidget(btn_vat)
        btn_vat_csv = QPushButton("💾 ПДВ у CSV")
        btn_vat_csv.clicked.connect(self._on_vat_csv)
        buttons.addWidget(btn_vat_csv)
        btn_close = QPushButton("Закрити")
        btn_close.clicked.connect(self.reject)
        buttons.addWidget(btn_close)
        layout.addRow(buttons)

        self._last_report: tuple | None = None

    def _period(self):
        d = self.date_from.date()
        date_from = date(d.year(), d.month(), d.day())
        d = self.date_to.date()
        date_to = date(d.year(), d.month(), d.day())
        return date_from, date_to

    def _on_export(self):
        date_from, date_to = self._period()
        payments = accounting_export_service.payments_between(date_from, date_to)
        if not payments:
            QMessageBox.information(self, "Виписка", "За вказаний період оплат не знайдено")
            return
        fmt = self.combo_format.currentData()
        default = f"виписка_{date_from:%Y%m%d}_{date_to:%Y%m%d}." + (
            "csv" if fmt == "csv" else "txt"
        )
        path, _ = QFileDialog.getSaveFileName(self, "Зберегти виписку", default)
        if not path:
            return
        try:
            if fmt == "csv":
                accounting_export_service.export_payments_csv(payments, path)
            else:
                accounting_export_service.export_payments_1c(payments, path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Помилка експорту", str(e))
            return
        QMessageBox.information(self, "Виписка", f"Збережено {len(payments)} операцій:\n{path}")

    def _calc_vat(self):
        date_from, date_to = self._period()
        report = accounting_export_service.vat_report(date_from, date_to)
        self._last_report = (report, date_from, date_to)
        self.lbl_vat.setText(
            f"Операцій: {report['payments_count']}\n"
            f"Надходження: {report['income']:,.2f} ₴ → ПДВ зобов'язання: {report['income_vat']:,.2f} ₴\n"
            f"Витрати: {report['expense']:,.2f} ₴ → податковий кредит: {report['expense_vat']:,.2f} ₴\n"
            f"ПДВ до сплати: {report['net_vat']:,.2f} ₴"
        )

    def _on_vat(self):
        self._calc_vat()

    def _on_vat_csv(self):
        if self._last_report is None:
            self._calc_vat()
        assert self._last_report is not None
        report, date_from, date_to = self._last_report
        default = f"pdv_{date_from:%Y%m%d}_{date_to:%Y%m%d}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Зберегти звіт ПДВ", default)
        if not path:
            return
        try:
            accounting_export_service.export_vat_csv(report, date_from, date_to, path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Помилка", str(e))
            return
        QMessageBox.information(self, "ПДВ", f"Звіт збережено:\n{path}")


class MoneyTab(QWidget):
    """Дебіторка: хто і скільки винен по проєктах."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[dict] = []
        self._build_ui()
        self.refresh()

    # ── UI ──

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QLabel("💵 Гроші: дебіторка по проєктах")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        root.addWidget(header)

        # ── Загальні підсумки ──
        summary = QGroupBox("Загальний підсумок")
        grid = QGridLayout(summary)
        self.lbl_projects = self._summary_cell(grid, 0, 0, "Проєктів:")
        self.lbl_total = self._summary_cell(grid, 0, 2, "Всього виставлено:")
        self.lbl_paid = self._summary_cell(grid, 1, 0, "Сплачено:")
        self.lbl_debt = self._summary_cell(grid, 1, 2, "Борг (до отримання):")
        self.lbl_overpaid = self._summary_cell(grid, 2, 0, "Переплати:")
        root.addWidget(summary)

        # ── Фільтри ──
        filters = QHBoxLayout()
        filters.addWidget(QLabel("Показати:"))
        self.combo_filter = QComboBox()
        self.combo_filter.addItems(FILTERS)
        self.combo_filter.currentTextChanged.connect(self._refill_table)
        filters.addWidget(self.combo_filter)
        filters.addWidget(QLabel("Пошук:"))
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("назва проєкту, клієнт або номер…")
        self.edit_search.setMinimumWidth(260)
        self.edit_search.textChanged.connect(self._refill_table)
        filters.addWidget(self.edit_search)
        filters.addStretch()
        btn_accounting = QPushButton("💼 Для бухгалтерії")
        btn_accounting.setToolTip("Виписка оплат за період (CSV / 1С:Клієнт банку) та звіт по ПДВ")
        btn_accounting.clicked.connect(self._on_accounting_export)
        filters.addWidget(btn_accounting)
        root.addLayout(filters)

        # ── Таблиця ──
        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        setup_table(self.table, select_rows=True, read_only=True, stretch_last=False)
        self.table.doubleClicked.connect(self._on_double_click)
        root.addWidget(self.table, 1)

        # ── Підсумок відфільтрованих ──
        bottom = QHBoxLayout()
        bottom.addStretch()
        self.lbl_filtered = QLabel("")
        self.lbl_filtered.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        bottom.addWidget(self.lbl_filtered)
        root.addLayout(bottom)

    def _summary_cell(self, grid: QGridLayout, row: int, col: int, title: str) -> QLabel:
        grid.addWidget(QLabel(title), row, col)
        value = QLabel("—")
        value.setStyleSheet("font-weight: bold;")
        grid.addWidget(value, row, col + 1)
        return value

    # ── Дані ──

    def refresh(self):
        """Перезавантажити дані з бази."""
        try:
            self._rows = build_receivables()
        except Exception:  # noqa: BLE001 — вкладка не має падати через БД
            self._rows = []
        self._update_summary()
        self._refill_table()

    def _update_summary(self):
        t = receivables_totals(self._rows)
        self.lbl_projects.setText(str(t["projects"]))
        self.lbl_total.setText(f"₴ {t['total']:,.2f}")
        self.lbl_paid.setText(f"₴ {t['paid']:,.2f}")
        self.lbl_debt.setText(f"₴ {t['debt']:,.2f}")
        self.lbl_debt.setStyleSheet(
            f"color: {Theme.DANGER if t['debt'] > 0 else Theme.SUCCESS}; font-weight: bold;"
        )
        self.lbl_overpaid.setText(f"₴ {t['overpaid']:,.2f}")
        self.lbl_overpaid.setStyleSheet(
            f"color: {Theme.ACCENT if t['overpaid'] > 0 else Theme.TEXT_MUTED}; font-weight: bold;"
        )

    def _filtered_rows(self) -> list[dict]:
        mode = self.combo_filter.currentText()
        needle = self.edit_search.text().strip().lower()
        rows = self._rows
        if mode == "Борг":
            rows = [r for r in rows if not r["overpaid"] and r["balance"] > 0]
        elif mode == "Прострочено":
            rows = [r for r in rows if is_overdue(r.get("status"), r["balance"])]
        elif mode == "Оплачено повністю":
            rows = [r for r in rows if not r["overpaid"] and r["balance"] <= 0 and r["paid"] > 0]
        elif mode == "Частково оплачено":
            rows = [r for r in rows if r["paid"] > 0 and r["balance"] > 0]
        elif mode == "Переплата":
            rows = [r for r in rows if r["overpaid"]]
        elif mode == "Без оплат":
            rows = [r for r in rows if r["payments_count"] == 0]
        if needle:
            rows = [
                r
                for r in rows
                if needle in (r["name"] or "").lower()
                or needle in (r["client"] or "").lower()
                or needle in (r["project_number"] or "").lower()
            ]
        return rows

    def _refill_table(self):
        rows = self._filtered_rows()
        self.table.setRowCount(0)
        for r in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            overdue = is_overdue(r.get("status"), r["balance"])
            balance_text = (
                f"Переплата {abs(r['balance']):,.2f}" if r["overpaid"] else f"{r['balance']:,.2f}"
            )
            if overdue:
                balance_text = f"{r['balance']:,.2f} ⏰"
            values = [
                r["project_number"],
                r["name"],
                r["client"],
                r["status"],
                f"{r['total']:,.2f}",
                f"{r['paid']:,.2f}",
                balance_text,
                f"{r['percent']:.0f} %",
                r["last_payment"],
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col in (4, 5, 6):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                if col == 6 and not r["overpaid"] and r["balance"] > 0:
                    item.setForeground(QColor(Theme.DANGER))
                if col == 6 and r["overpaid"]:
                    item.setForeground(QColor(Theme.ACCENT))
                if overdue and col in (3, 6):
                    item.setForeground(QColor(Theme.DANGER))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.table.setItem(row, col, item)
        # Підсумок відфільтрованих
        total = round(sum(r["total"] for r in rows), 2)
        paid = round(sum(r["paid"] for r in rows), 2)
        debt = round(sum(max(r["balance"], 0.0) for r in rows), 2)
        self.lbl_filtered.setText(
            f"Відображено {len(rows)} з {len(self._rows)}: виставлено ₴ {total:,.2f}, "
            f"сплачено ₴ {paid:,.2f}, борг ₴ {debt:,.2f}"
        )

    # ── Дії ──

    def _on_accounting_export(self):
        AccountingExportDialog(self).exec()

    def _on_double_click(self):
        row = self.table.currentRow()
        rows = self._filtered_rows()
        if 0 <= row < len(rows):
            self._open_project(rows[row]["project_id"])

    def _open_project(self, project_id):
        from ventilation_company.gui_pyside6.project_card_dialog import ProjectCardDialog

        dlg = ProjectCardDialog(project_id, parent=self)
        dlg.exec()
        self.refresh()
