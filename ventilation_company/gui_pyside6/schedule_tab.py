"""Вкладка «Монтажі»: календар робіт з датами по всіх проєктах.

Фільтри: бригада та період (сьогодні / тиждень / місяць / усі).
Подвійний клік — картка проєкту. Дати й бригади задаються у картці
проєкту на вкладці «Роботи».
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.gui_pyside6.table_utils import setup_table
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.services.schedule_service import list_crews, list_scheduled_works

PERIODS = [
    ("all", "Усі дати"),
    ("today", "Сьогодні"),
    ("week", "Цей тиждень"),
    ("month", "Цей місяць"),
]

COLUMNS = ["Дата", "Проєкт", "Робота", "Бригада", "Сума, ₴"]


class ScheduleTab(QWidget):
    """План монтажів: роботи з датами по проєктах."""

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

        header = QLabel("📅 Монтажі: план робіт з датами")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        root.addWidget(header)

        hint = QLabel(
            "Дати й бригади задаються у картці проєкту → вкладка «Роботи» → "
            "«➕ Додати» / «✏️ Змінити»."
        )
        hint.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 12px;")
        root.addWidget(hint)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("Бригада:"))
        self.combo_crew = QComboBox()
        self.combo_crew.currentTextChanged.connect(self._refill_table)
        filters.addWidget(self.combo_crew)
        filters.addWidget(QLabel("Період:"))
        self.combo_period = QComboBox()
        for key, label in PERIODS:
            self.combo_period.addItem(label, key)
        self.combo_period.currentIndexChanged.connect(self._refill_table)
        filters.addWidget(self.combo_period)
        filters.addStretch()
        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        filters.addWidget(self.lbl_count)
        root.addLayout(filters)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        setup_table(self.table, select_rows=True, read_only=True, stretch_last=False)
        self.table.doubleClicked.connect(self._on_double_click)
        root.addWidget(self.table, 1)

    # ── Дані ──

    def refresh(self):
        """Перезавантажити дані (викликається при переході на вкладку)."""
        try:
            crews = list_crews()
        except Exception:  # noqa: BLE001 — вкладка не має падати через БД
            crews = []
        current = self.combo_crew.currentText()
        self.combo_crew.blockSignals(True)
        self.combo_crew.clear()
        self.combo_crew.addItem("Усі бригади")
        self.combo_crew.addItems(crews)
        if current in ("", "Усі бригади") or current not in crews:
            self.combo_crew.setCurrentIndex(0)
        else:
            self.combo_crew.setCurrentText(current)
        self.combo_crew.blockSignals(False)
        self._reload_rows()

    def _reload_rows(self):
        crew = self.combo_crew.currentText()
        if crew == "Усі бригади":
            crew = ""
        period = self.combo_period.currentData() or "all"
        try:
            self._rows = list_scheduled_works(crew=crew, period=period)
        except Exception:  # noqa: BLE001
            self._rows = []
        self._refill_table()

    def _refill_table(self):
        self.table.setRowCount(0)
        for r in self._rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            project = f"{r['project_number']} {r['project_name']}".strip()
            values = [
                r["work_date"],
                project,
                r["work_name"],
                r["crew"],
                f"{r['total_price']:,.2f}",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col == 4:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                if not r["crew"] and col == 3:
                    item.setForeground(QColor(Theme.TEXT_MUTED))
                self.table.setItem(row, col, item)
        self.lbl_count.setText(f"Робіт із датою: {len(self._rows)}")

    # ── Дії ──

    def _on_double_click(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._rows):
            self._open_project(self._rows[row]["project_id"])

    def _open_project(self, project_id):
        from ventilation_company.gui_pyside6.project_card_dialog import ProjectCardDialog

        dlg = ProjectCardDialog(project_id, parent=self)
        dlg.exec()
        self.refresh()
