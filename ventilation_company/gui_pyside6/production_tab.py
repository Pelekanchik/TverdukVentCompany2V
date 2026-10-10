"""Вкладка «Виробництво» (PySide6) — черга цеху та планові терміни.

Таблиця завдань (вироби проєктів) з пріоритетами та плановими датами;
кольором позначаються прострочені терміни. Додавання — з вибору
проєкту та його виробів (без дублікатів у черзі).
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.database.repositories.production_task_repo import (
    PRIORITY_ORDER,
    TASK_STATUSES,
    ProductionTaskRepository,
)
from ventilation_company.database.repositories.project_repo import ProjectRepository
from ventilation_company.gui_pyside6.table_utils import setup_table
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.services import production_materials_service, production_service

_STATUS_LABELS = {
    production_materials_service.STATUS_OK: "✅ вистачає",
    production_materials_service.STATUS_PARTIAL: "⚠ частково",
    production_materials_service.STATUS_MISSING: "❌ немає",
}


class MaterialsCheckDialog(QDialog):
    """Звірка потреб черги виробництва зі складом + резервування."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📦 Матеріали для виробництва")
        self.setMinimumSize(720, 420)
        self._rows: list[dict] = []
        self._build_ui()
        self._reload()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.lbl_hint = QLabel("")
        self.lbl_hint.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(self.lbl_hint)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Матеріал", "Потрібно", "На складі", "Зарезервовано", "Доступно", "Статус"]
        )
        setup_table(self.table, select_rows=False, single_selection=False, read_only=True)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        btn_reserve = QPushButton("🔒 Зарезервувати доступне")
        btn_reserve.setToolTip(
            "Зарезервувати під це виробництво мінімум із потрібного й доступного\n"
            "по кожній позиції (резерв не списує матеріал, лише відмічає)"
        )
        btn_reserve.clicked.connect(self._on_reserve)
        actions.addWidget(btn_reserve)
        btn_close = QPushButton("Закрити")
        btn_close.clicked.connect(self.accept)
        actions.addWidget(btn_close)
        layout.addLayout(actions)

    def _reload(self):
        self._rows = production_materials_service.check_materials()
        self.table.setRowCount(0)
        for row in self._rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            status = row["status"]
            label = _STATUS_LABELS.get(status, status)
            color = {
                production_materials_service.STATUS_OK: Theme.SUCCESS,
                production_materials_service.STATUS_PARTIAL: Theme.WARNING,
                production_materials_service.STATUS_MISSING: Theme.DANGER,
            }.get(status, Theme.TEXT)
            item_name = row["item_name"] or "— позицію не знайдено на складі —"
            values = [
                f"{row['material']}" + (f"  ({item_name})" if row["item_name"] else ""),
                f"{row['needed']:g}",
                f"{row['on_hand']:g} {row['unit']}",
                f"{row['reserved']:g} {row['unit']}",
                f"{row['available']:g} {row['unit']}",
                label,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 5:
                    item.setForeground(QColor(color))
                self.table.setItem(r, col, item)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

        total = len(self._rows)
        ok = sum(1 for r in self._rows if r["status"] == production_materials_service.STATUS_OK)
        missing = total - ok
        self.lbl_hint.setText(
            f"Потреби невиконаних завдань черги: {total} позицій, "
            f"забезпечено: {ok}, дефіцит: {missing}. "
            "Резерв відмічає матеріал під це виробництво, фактичне списання — зі вкладки «Склад»."
        )

    def _on_reserve(self):
        if not self._rows:
            QMessageBox.information(self, "Матеріали", "Немає потреб для резервування")
            return
        reserved, errors = production_materials_service.reserve_available(self._rows)
        message = f"Зарезервовано позицій: {reserved}"
        if errors:
            message += "\n\nПомилки:\n" + "\n".join(errors)
        QMessageBox.information(self, "Резервування", message)
        self._reload()


class AddToQueueDialog(QDialog):
    """Діалог додавання виробів проєкту в чергу виробництва."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("➕ Додати в чергу виробництва")
        self.setMinimumWidth(460)
        self._projects: list[dict] = []
        self._build_ui()
        self._load_projects()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.combo_project = QComboBox()
        self.combo_project.currentIndexChanged.connect(self._on_project_changed)
        form.addRow("Проєкт:", self.combo_project)

        self.list_products = QListWidget()
        self.list_products.setMinimumHeight(140)
        form.addRow("Вироби:", self.list_products)

        self.combo_priority = QComboBox()
        self.combo_priority.addItems(PRIORITY_ORDER)
        self.combo_priority.setCurrentText("звичайний")
        form.addRow("Пріоритет:", self.combo_priority)

        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate())
        form.addRow("План. початок:", self.date_start)

        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate().addDays(3))
        form.addRow("План. термін:", self.date_end)

        self.edit_notes = QLineEdit()
        self.edit_notes.setPlaceholderText("Примітка (необов'язково)")
        form.addRow("Примітка:", self.edit_notes)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Додати в чергу")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_projects(self):
        try:
            self._projects = ProjectRepository.list_all() or []
        except Exception:  # noqa: BLE001 — показуємо порожній список, не падаємо
            self._projects = []
        self.combo_project.clear()
        for p in self._projects:
            self.combo_project.addItem(
                f"{p.get('name') or '—'} (№{p.get('project_number') or '—'})", p.get("id")
            )

    def _on_project_changed(self, index: int):
        self.list_products.clear()
        project_id = self.combo_project.itemData(index)
        if not project_id:
            return
        try:
            from ventilation_company.database.repositories.product_repo import ProductRepository

            products = ProductRepository.get_all(project_id=project_id) or []
        except Exception:  # noqa: BLE001
            products = []
        for p in products:
            name = p.get("name") or "—"
            qty = p.get("quantity") or 1
            item = QListWidgetItem(f"{name}  ×{qty}")
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.list_products.addItem(item)

    def selected_product_names(self) -> list[str]:
        names = []
        for i in range(self.list_products.count()):
            item = self.list_products.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                names.append(item.data(Qt.ItemDataRole.UserRole))
        return names

    def selected_project_id(self) -> int | None:
        return self.combo_project.currentData()

    def values(self) -> dict:
        def _to_datetime(edit: QDateEdit) -> datetime:
            d = edit.date()
            return datetime(d.year(), d.month(), d.day())

        return {
            "project_id": self.selected_project_id(),
            "product_names": self.selected_product_names(),
            "priority": self.combo_priority.currentText(),
            "planned_start": _to_datetime(self.date_start),
            "planned_end": _to_datetime(self.date_end),
            "notes": self.edit_notes.text().strip(),
        }


class ProductionTab(QWidget):
    """Черга виробництва: проєкти в роботі, терміни, пріоритети."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks: list[dict] = []
        self._projects_by_id: dict[int, str] = {}
        self._build_ui()
        self.refresh()

    # ── UI ──

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        lbl_title = QLabel("🏭 Виробництво")
        lbl_title.setObjectName("title")
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Черга цеху: вироби з проєктів, пріоритети та планові терміни")
        lbl_sub.setObjectName("subtitle")
        layout.addWidget(lbl_sub)

        top = QHBoxLayout()
        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet(f"color: {Theme.TEXT}; font-size: 13px; font-weight: bold;")
        top.addWidget(self.lbl_summary)
        top.addStretch()

        top.addWidget(QLabel("Фільтр:"))
        self.combo_filter = QComboBox()
        self.combo_filter.addItem("Всі", None)
        for s in TASK_STATUSES:
            self.combo_filter.addItem(s.capitalize(), s)
        self.combo_filter.currentIndexChanged.connect(self.refresh)
        top.addWidget(self.combo_filter)

        btn_add = QPushButton("➕ З проєкту…")
        btn_add.clicked.connect(self._on_add_from_project)
        top.addWidget(btn_add)

        btn_materials = QPushButton("📦 Матеріали")
        btn_materials.setToolTip(
            "Звірка потреб невиконаних завдань зі складом + резервування матеріалів"
        )
        btn_materials.clicked.connect(self._on_check_materials)
        top.addWidget(btn_materials)
        layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["Проєкт", "Виріб", "К-сть", "Пріоритет", "Статус", "Початок", "Термін", "Залишилось"]
        )
        setup_table(self.table, select_rows=True, single_selection=True, read_only=True)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        btn_start = QPushButton("▶ В роботу")
        btn_start.clicked.connect(lambda: self._set_status("в роботі"))
        actions.addWidget(btn_start)
        btn_done = QPushButton("✅ Готово")
        btn_done.clicked.connect(lambda: self._set_status("готово"))
        actions.addWidget(btn_done)
        btn_back = QPushButton("↩️ В чергу")
        btn_back.clicked.connect(lambda: self._set_status("в черзі"))
        actions.addWidget(btn_back)
        btn_del = QPushButton("🗑️ Видалити")
        btn_del.setStyleSheet(f"color: {Theme.DANGER};")
        btn_del.clicked.connect(self._on_delete)
        actions.addWidget(btn_del)
        layout.addLayout(actions)

    # ── Дані ──

    def _load_project_names(self):
        try:
            projects = ProjectRepository.list_all() or []
            self._projects_by_id = {p["id"]: p.get("name") or f"#{p['id']}" for p in projects}
        except Exception:  # noqa: BLE001
            self._projects_by_id = {}

    def refresh(self):
        """Перечитати чергу з БД і перемалювати таблицю + підсумки."""
        self._load_project_names()
        status_filter = self.combo_filter.currentData()
        self._tasks = production_service.sorted_queue(status_filter)

        self.table.setRowCount(0)
        for t in self._tasks:
            row = self.table.rowCount()
            self.table.insertRow(row)
            left = production_service.days_left(t)
            project = self._projects_by_id.get(t["project_id"], f"#{t['project_id']}")
            overdue = left is not None and left < 0 and t["status"] != "готово"
            left_text = (
                "—" if left is None else (f"{left} дн" if left >= 0 else f"⚠ {-left} дн тому")
            )

            cells = [
                project,
                t["product_name"],
                str(t.get("quantity") or 1),
                t.get("priority") or "—",
                t.get("status") or "—",
                _fmt_date(t.get("planned_start")),
                _fmt_date(t.get("planned_end")),
                left_text,
            ]
            for col, value in enumerate(cells):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, t["id"])
                if overdue:
                    item.setForeground(QColor(Theme.DANGER))
                self.table.setItem(row, col, item)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

        all_tasks = production_service.sorted_queue()
        stats = production_service.summary(all_tasks)
        counts = stats["counts"]
        overdue_n = len(stats["overdue"])
        text = (
            f"📋 В черзі: {counts.get('в черзі', 0)}   🔩 В роботі: {counts.get('в роботі', 0)}"
            f"   ✔️ Готово: {counts.get('готово', 0)}"
        )
        if overdue_n:
            text += f"   <span style='color:{Theme.DANGER};'>⏰ Прострочено: {overdue_n}</span>"
        self.lbl_summary.setText(text)

    # ── Дії ──

    def _selected_task(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        for t in self._tasks:
            if t["id"] == task_id:
                return t
        return None

    def _on_add_from_project(self):
        dialog = AddToQueueDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        if not values["project_id"] or not values["product_names"]:
            QMessageBox.warning(self, "Увага", "Оберіть проєкт і хоча б один виріб")
            return
        added, skipped = production_service.add_project_to_queue(
            values["project_id"],
            product_names=values["product_names"],
            priority=values["priority"],
            planned_start=values["planned_start"],
            planned_end=values["planned_end"],
            notes=values["notes"],
        )
        message = f"Додано в чергу: {added}"
        if skipped:
            message += f"\nПропущено (вже в черзі): {skipped}"
        QMessageBox.information(self, "Черга виробництва", message)
        self.refresh()

    def _on_check_materials(self):
        dialog = MaterialsCheckDialog(self)
        dialog.exec()

    def _set_status(self, status: str):
        task = self._selected_task()
        if not task:
            QMessageBox.warning(self, "Увага", "Оберіть завдання в таблиці")
            return
        try:
            ProductionTaskRepository.update(task["id"], status=status)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Помилка", f"Не вдалося оновити статус: {e}")
            return
        self.refresh()

    def _on_delete(self):
        task = self._selected_task()
        if not task:
            QMessageBox.warning(self, "Увага", "Оберіть завдання для видалення")
            return
        reply = QMessageBox.question(
            self,
            "Видалення",
            f"Видалити з черги «{task['product_name']}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                ProductionTaskRepository.delete(task["id"])
            except Exception as e:  # noqa: BLE001
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити: {e}")
                return
            self.refresh()


def _fmt_date(value) -> str:
    return f"{value:%d.%m.%Y}" if isinstance(value, datetime) else "—"
