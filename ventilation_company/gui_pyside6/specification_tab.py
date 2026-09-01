"""Вкладка "Специфікація" (PySide6) — реальні дані з PostgreSQL.

Вибір проєкту з БД → таблиця виробів проєкту з БД → підсумки (вага, площа, сума).
Всі операції (додавання, редагування, видалення) працюють з БД через ProductRepository.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QComboBox, QMessageBox, QAbstractItemView,
    QDialog
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.database.db import get_db
from ventilation_company.database.models.project import Project
from ventilation_company.database.repositories.product_repo import ProductRepository
from ventilation_company.gui_pyside6.products_tab import ProductDialog


class SpecificationTab(QWidget):
    """Вкладка специфікації проєкту — реальні дані з PostgreSQL."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self._current_project_id: int | None = None
        self._items: list[dict] = []
        self._build_ui()
        self._load_projects()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ── Верхня панель: вибір проєкту ──
        top = QHBoxLayout()

        lbl_title = QLabel("📋 Специфікація")
        lbl_title.setObjectName("title")
        top.addWidget(lbl_title)

        top.addSpacing(24)

        lbl_proj = QLabel("Проєкт:")
        lbl_proj.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        top.addWidget(lbl_proj)

        self.combo_project = QComboBox()
        self.combo_project.setMinimumWidth(300)
        self.combo_project.setMinimumHeight(32)
        self.combo_project.currentIndexChanged.connect(self._on_project_changed)
        top.addWidget(self.combo_project)

        top.addStretch()

        btn_add = QPushButton("➕ Додати виріб")
        btn_add.setObjectName("primary")
        btn_add.setMinimumHeight(32)
        btn_add.clicked.connect(self._on_add_product)
        top.addWidget(btn_add)

        btn_refresh = QPushButton("🔄 Оновити")
        btn_refresh.setMinimumHeight(32)
        btn_refresh.clicked.connect(self._refresh_current)
        top.addWidget(btn_refresh)

        layout.addLayout(top)

        # ── Таблиця виробів ──
        self.table = QTableView()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(400)
        layout.addWidget(self.table)

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "№", "Назва", "Тип", "Розміри", "Матеріал", "Товщ.",
            "К-ть", "Площа м²", "Вага кг", "Ціна", "Сума"
        ])
        self.table.setModel(self.model)

        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 220)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 110)
        self.table.setColumnWidth(5, 50)
        self.table.setColumnWidth(6, 50)
        self.table.setColumnWidth(7, 70)
        self.table.setColumnWidth(8, 70)
        self.table.setColumnWidth(9, 80)
        self.table.setColumnWidth(10, 80)

        # ── Кнопки дій ──
        actions = QHBoxLayout()
        actions.addStretch()

        btn_edit = QPushButton("✏️ Редагувати")
        btn_edit.clicked.connect(self._on_edit)
        actions.addWidget(btn_edit)

        btn_del = QPushButton("🗑️ Видалити")
        btn_del.setStyleSheet(f"color: {Theme.DANGER};")
        btn_del.clicked.connect(self._on_delete)
        actions.addWidget(btn_del)

        layout.addLayout(actions)

        # ── Підсумки ──
        summary = QHBoxLayout()
        summary.setSpacing(24)

        self.lbl_count = QLabel("Позицій: 0")
        self.lbl_count.setStyleSheet(f"color: {Theme.TEXT}; font-size: 13px; padding: 8px 16px; background: {Theme.BG_CARD}; border-radius: 8px;")
        summary.addWidget(self.lbl_count)

        self.lbl_qty = QLabel("Кількість: 0 шт")
        self.lbl_qty.setStyleSheet(f"color: {Theme.TEXT}; font-size: 13px; padding: 8px 16px; background: {Theme.BG_CARD}; border-radius: 8px;")
        summary.addWidget(self.lbl_qty)

        self.lbl_area = QLabel("Площа: 0 м²")
        self.lbl_area.setStyleSheet(f"color: {Theme.ACCENT}; font-size: 13px; padding: 8px 16px; background: {Theme.BG_CARD}; border-radius: 8px;")
        summary.addWidget(self.lbl_area)

        self.lbl_weight = QLabel("Вага: 0 кг")
        self.lbl_weight.setStyleSheet(f"color: {Theme.WARNING}; font-size: 13px; padding: 8px 16px; background: {Theme.BG_CARD}; border-radius: 8px;")
        summary.addWidget(self.lbl_weight)

        self.lbl_total = QLabel("Сума: ₴ 0")
        self.lbl_total.setStyleSheet(f"color: {Theme.SUCCESS}; font-size: 14px; font-weight: bold; padding: 8px 16px; background: {Theme.BG_CARD}; border-radius: 8px;")
        summary.addWidget(self.lbl_total)

        summary.addStretch()
        layout.addLayout(summary)

    # ═══════════════════════════════════════════════════════════
    # Завантаження даних
    # ═══════════════════════════════════════════════════════════

    def _load_projects(self):
        """Завантажити список проєктів з БД та вибрати активний."""
        self.combo_project.blockSignals(True)
        self.combo_project.clear()
        try:
            with get_db() as session:
                projects = session.query(Project).order_by(Project.created_at.desc()).all()
                for p in projects:
                    display = f"{p.project_number or '—'} — {p.name or 'Без назви'}"
                    self.combo_project.addItem(display, p.id)
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося завантажити проєкти: {e}")
        self.combo_project.blockSignals(False)

        # ВИПРАВЛЕННЯ: явно встановлюємо _current_project_id після завантаження
        active_id = self.main_window.active_project_id if self.main_window else None
        if active_id:
            idx = self.combo_project.findData(active_id)
            if idx >= 0:
                self.combo_project.setCurrentIndex(idx)
                self._current_project_id = active_id
                self._load_specification()
                return

        if self.combo_project.count() > 0:
            self.combo_project.setCurrentIndex(0)
            self._current_project_id = self.combo_project.itemData(0)
            self._load_specification()
        else:
            self._current_project_id = None
            self.model.removeRows(0, self.model.rowCount())
            self._items = []
            self._update_summary([])

    def _on_project_changed(self, index: int):
        """При зміні проєкту в комбобоксі користувачем."""
        self._current_project_id = self.combo_project.itemData(index)
        if self.main_window and self._current_project_id:
            self.main_window.set_active_project(self._current_project_id)
        self._load_specification()

    def _load_specification(self, project_id: int | None = None):
        """Завантажити вироби вибраного проєкту з БД."""
        if project_id is None:
            project_id = self._current_project_id

        self.model.removeRows(0, self.model.rowCount())
        self._items = []

        if not project_id:
            self._update_summary([])
            return

        try:
            items = ProductRepository.get_all(project_id=project_id)
            self._items = items
            self._populate_table(items)
            self._update_summary(items)
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося завантажити специфікацію: {e}")

    def _populate_table(self, items: list[dict]):
        """Заповнити таблицю виробами."""
        for pos, item in enumerate(items, 1):
            w = item.get("width", 0) or 0
            h = item.get("height", 0) or 0
            l = item.get("length", 0) or 0

            if h > 0:
                dims = f"{w:.0f}×{h:.0f}"
                if l > 0:
                    dims += f" × {l:.0f}"
            else:
                dims = f"Ø{w:.0f}"
                if l > 0:
                    dims += f" × {l:.0f}"

            row = [
                QStandardItem(str(pos)),
                QStandardItem(item.get("name", "—")),
                QStandardItem(item.get("product_type", "—")),
                QStandardItem(dims),
                QStandardItem(item.get("material", "—")),
                QStandardItem(str(item.get("thickness", "—"))),
                QStandardItem(str(item.get("quantity", 1))),
                QStandardItem(f"{item.get('metal_area_m2', 0):.2f}"),
                QStandardItem(f"{item.get('weight_kg', 0):.2f}"),
                QStandardItem(f"₴ {item.get('unit_price', 0):,.2f}"),
                QStandardItem(f"₴ {item.get('total_price', 0):,.2f}"),
            ]
            for cell in row:
                cell.setEditable(False)
            self.model.appendRow(row)

    def _update_summary(self, items: list[dict]):
        """Оновити підсумкові мітки."""
        count = len(items)
        qty = sum(i.get("quantity", 1) for i in items)
        area = sum((i.get("metal_area_m2") or 0) * (i.get("quantity") or 1) for i in items)
        weight = sum((i.get("weight_kg") or 0) * (i.get("quantity") or 1) for i in items)
        total = sum(i.get("total_price", 0) for i in items)

        self.lbl_count.setText(f"Позицій: {count}")
        self.lbl_qty.setText(f"Кількість: {qty} шт")
        self.lbl_area.setText(f"Площа: {area:.2f} м²")
        self.lbl_weight.setText(f"Вага: {weight:.2f} кг")
        self.lbl_total.setText(f"Сума: ₴ {total:,.2f}")

    # ═══════════════════════════════════════════════════════════
    # CRUD операції
    # ═══════════════════════════════════════════════════════════

    def _get_selected_id(self) -> int | None:
        """Отримати ID вибраного виробу."""
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        row = idx.row()
        if 0 <= row < len(self._items):
            return self._items[row].get("id")
        return None

    def _on_add_product(self):
        """Додати виріб у специфікацію."""
        if not self._current_project_id:
            QMessageBox.warning(self, "Увага", "Спочатку виберіть проєкт")
            return

        # Встановлюємо активний проєкт для діалогу
        if self.main_window:
            self.main_window.set_active_project(self._current_project_id)

        dlg = ProductDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            # Перевірка: якщо діалог не підхопив project_id — підставляємо вручну
            if not data.get("project_id"):
                data["project_id"] = self._current_project_id
            try:
                ProductRepository.create(data)
                self._load_specification()
                QMessageBox.information(self, "Успіх", "Виріб додано до специфікації!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти: {e}")

    def _on_edit(self):
        """Редагувати вибраний виріб."""
        item_id = self._get_selected_id()
        if not item_id:
            QMessageBox.warning(self, "Увага", "Виберіть виріб для редагування")
            return
        try:
            item = ProductRepository.get_by_id(item_id)
            if not item:
                QMessageBox.warning(self, "Увага", "Виріб не знайдено в БД")
                return
            dlg = ProductDialog(item, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                new_data = dlg.get_data()
                if not new_data.get("project_id"):
                    new_data["project_id"] = self._current_project_id
                ProductRepository.update(item_id, new_data)
                self._load_specification()
                QMessageBox.information(self, "Успіх", "Виріб оновлено!")
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося оновити: {e}")

    def _on_delete(self):
        """Видалити вибраний виріб зі специфікації (і з БД)."""
        item_id = self._get_selected_id()
        if not item_id:
            QMessageBox.warning(self, "Увага", "Виберіть виріб для видалення")
            return
        name = self._items[self.table.currentIndex().row()].get("name", "")
        reply = QMessageBox.question(
            self, "Видалення",
            f'Видалити виріб "{name}" (ID: {item_id}) зі специфікації?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                ProductRepository.delete(item_id)
                self._load_specification()
                QMessageBox.information(self, "Успіх", "Виріб видалено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити: {e}")

    def _refresh_current(self):
        """Оновити поточну специфікацію."""
        self._load_specification()

    # ═══════════════════════════════════════════════════════════
    # Зовнішні події
    # ═══════════════════════════════════════════════════════════

    def refresh(self):
        """Повне оновлення (проєкти + специфікація)."""
        self._load_projects()

    def on_project_changed(self, project_id: int | None):
        """При зміні проєкту ззовні."""
        if project_id:
            idx = self.combo_project.findData(project_id)
            if idx >= 0:
                self.combo_project.blockSignals(True)
                self.combo_project.setCurrentIndex(idx)
                self.combo_project.blockSignals(False)
                self._current_project_id = project_id
                self._load_specification()
        else:
            self.combo_project.setCurrentIndex(-1)
            self._current_project_id = None
            self.model.removeRows(0, self.model.rowCount())
            self._items = []
            self._update_summary([])
