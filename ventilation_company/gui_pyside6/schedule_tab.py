"""Вкладка «Монтажі»: календар робіт з датами по всіх проєктах.

Фільтри: бригада та період (сьогодні / тиждень / місяць / усі).
Подвійний клік — картка проєкту. Дати й бригади задаються у картці
проєкту на вкладці «Роботи».
"""

from __future__ import annotations

import contextlib

from PySide6.QtCore import QDate, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
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

from ventilation_company.database.repositories.project_repo import ProjectRepository
from ventilation_company.database.repositories.project_work_repo import ProjectWorkRepository
from ventilation_company.gui_pyside6.calendar_picker import DatePicker
from ventilation_company.gui_pyside6.table_utils import setup_table
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.services.schedule_service import (
    list_crews,
    list_scheduled_works,
    period_bounds,
)

PERIODS = [
    ("all", "Усі дати"),
    ("today", "Сьогодні"),
    ("week", "Цей тиждень"),
    ("month", "Цей місяць"),
]

COLUMNS = ["Дата", "Проєкт", "Робота", "Бригада", "Сума, ₴"]


class QuickWorkDialog(QDialog):
    """Швидке додавання монтажної роботи до проєкту без відкриття картки.

    Дата — обов'язкова (це і є суть плану монтажів); назва й бригада —
    довільні тексти; ціза за одиницю опційна.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Швидке додавання монтажної роботи")
        self.setMinimumWidth(420)
        layout = QFormLayout(self)

        self.combo_project = QComboBox()
        self._projects: list[dict] = []
        try:
            self._projects = [p for p in ProjectRepository.list_all() if int(p.get("id") or 0)]
        except Exception:  # noqa: BLE001 — покажемо порожній список і помилку при збереженні
            self._projects = []
        for p in self._projects:
            label = f"{p.get('project_number') or ''} {p.get('name') or ''}".strip()
            self.combo_project.addItem(label, int(p["id"]))
        layout.addRow("Проєкт:", self.combo_project)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("напр. Монтаж повітропроводів")
        layout.addRow("Робота *:", self.edit_name)

        self.date_edit = DatePicker(QDate.currentDate())
        layout.addRow("Дата:", self.date_edit)

        self.edit_crew = QLineEdit()
        self.edit_crew.setPlaceholderText("напр. Бригада №2")
        layout.addRow("Бригада:", self.edit_crew)

        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0, 999999)
        self.spin_price.setSuffix(" ₴")
        self.spin_price.setDecimals(2)
        layout.addRow("Ціна за од.:", self.spin_price)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def create_work(self) -> bool:
        """Створити роботу в БД. Повертає True при успіху."""
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Увага", "Введіть назву роботи.")
            return False
        project_id = self.combo_project.currentData()
        if not project_id:
            QMessageBox.warning(self, "Увага", "Оберіть проєкт.")
            return False
        try:
            ProjectWorkRepository.create(
                {
                    "project_id": int(project_id),
                    "work_name": name,
                    "quantity": 1,
                    "unit": "шт",
                    "unit_price": self.spin_price.value(),
                    "work_date": self.date_edit.date().toString("yyyy-MM-dd"),
                    "crew": self.edit_crew.text().strip(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти роботу:\n{exc}")
            return False
        return True


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
            "Додавайте монтажі кнопкою «➕ Швидко додати» — або у картці проєкту "
            "→ вкладка «Роботи» → «➕ Додати» (там є календар)."
        )
        hint.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 12px;")
        root.addWidget(hint)

        filters = QHBoxLayout()
        btn_quick = QPushButton("➕ Швидко додати роботу")
        btn_quick.setToolTip("Додати монтажну роботу до будь-якого проєкту без відкриття картки")
        btn_quick.clicked.connect(self._on_quick_add)
        filters.addWidget(btn_quick)
        btn_plan = QPushButton("🖨 План для бригад (PDF)")
        btn_plan.setToolTip(
            "Друкований план робіт за обраними фільтрами (бригада + період) для роздачі бригадам"
        )
        btn_plan.clicked.connect(self._on_export_plan)
        filters.addWidget(btn_plan)
        filters.addSpacing(12)
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

    def _on_quick_add(self):
        """Швидке додавання монтажної роботи без відкриття картки проєкту."""
        dlg = QuickWorkDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if dlg.create_work():
            self.refresh()

    def _on_export_plan(self):
        """PDF-план монтажів за поточними фільтрами (бригада + період)."""
        from datetime import date as _date

        from ventilation_company.crew_plan_generator import generate_crew_plan
        from ventilation_company.services.business_settings import BusinessSettings

        crew = self.combo_crew.currentText()
        if crew == "Усі бригади":
            crew = ""
        period = self.combo_period.currentData() or "all"
        note = ""
        if period == "all":
            period = "week"
            note = "\n\nПеріод «Усі дати» — згенеровано план на поточний тиждень."
        date_from, date_to = period_bounds(period)
        # Для всіх режимів, крім "all" (який вище замінено на "week"), межі завжди є.
        assert date_from is not None and date_to is not None

        try:
            works = list_scheduled_works(crew=crew, period=period)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Помилка", f"Не вдалося прочитати дані:\n{exc}")
            return
        if not works:
            QMessageBox.information(
                self,
                "План для бригад",
                "Немає робіт із датами за обраний період.",
            )
            return

        week = _date.today().isocalendar()[1]
        suggested = f"plan-bryhad-tyzhden-{week}.pdf"
        path, _selected = QFileDialog.getSaveFileName(
            self, "Зберегти план для бригад", suggested, "PDF (*.pdf)"
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"

        company = {}
        with contextlib.suppress(Exception):  # реквізити не критичні
            company = BusinessSettings.get_instance().get_company()
        try:
            generate_crew_plan(works, crew, date_from, date_to, path, company)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Помилка", f"Не вдалося створити PDF:\n{exc}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        QMessageBox.information(
            self,
            "План для бригад",
            f"План збережено:\n{path}{note}",
        )

    def _on_double_click(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._rows):
            self._open_project(self._rows[row]["project_id"])

    def _open_project(self, project_id):
        from ventilation_company.gui_pyside6.project_card_dialog import ProjectCardDialog

        dlg = ProjectCardDialog(project_id, parent=self)
        dlg.exec()
        self.refresh()
