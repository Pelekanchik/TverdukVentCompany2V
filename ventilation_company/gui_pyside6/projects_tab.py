"""Вкладка проєктів (PySide6 + PostgreSQL).

Функціонал:
  • Таблиця проєктів з сумою виробів
  • Подвійний клік — вибір активного проєкту
  • Редагування (статус, назва, клієнт, ціна)
  • Видалення з підтвердженням
  • Створення нового проєкту
  • Пошук/фільтрація
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QLineEdit, QMessageBox, QAbstractItemView,
    QDialog, QFormLayout, QDialogButtonBox, QComboBox,
    QDoubleSpinBox, QDateEdit
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.database.db import get_db
from ventilation_company.database.models.project import Project
from ventilation_company.database.repositories.product_repo import ProductRepository
from datetime import datetime


class ProjectEditDialog(QDialog):
    """Діалог редагування проєкту."""

    STATUSES = ["Новий", "В роботі", "На виробництві", "Готовий", "Відвантажено", "Закрито"]

    def __init__(self, project_data=None, parent=None):
        super().__init__(parent)
        self.project_data = project_data or {}
        self.setWindowTitle("Редагування проєкту" if project_data else "Новий проєкт")
        self.setMinimumWidth(400)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)

        self.edit_name = QLineEdit()
        self.edit_name.setText(self.project_data.get("name", ""))
        self.edit_name.setPlaceholderText("Назва проєкту")
        layout.addRow("Назва *", self.edit_name)

        self.edit_number = QLineEdit()
        self.edit_number.setText(self.project_data.get("project_number", ""))
        self.edit_number.setPlaceholderText("Авто-генерація якщо порожньо")
        layout.addRow("Номер", self.edit_number)

        self.edit_client = QLineEdit()
        self.edit_client.setText(self.project_data.get("client", ""))
        self.edit_client.setPlaceholderText("ПІБ або назва компанії")
        layout.addRow("Клієнт", self.edit_client)

        self.combo_status = QComboBox()
        self.combo_status.addItems(self.STATUSES)
        current_status = self.project_data.get("status", "Новий")
        idx = self.combo_status.findText(current_status)
        if idx >= 0:
            self.combo_status.setCurrentIndex(idx)
        layout.addRow("Статус", self.combo_status)

        self.spin_cost = QDoubleSpinBox()
        self.spin_cost.setRange(0, 99999999)
        self.spin_cost.setSuffix(" ₴")
        self.spin_cost.setValue(float(self.project_data.get("cost_price", 0) or 0))
        layout.addRow("Собівартість", self.spin_cost)

        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0, 99999999)
        self.spin_price.setSuffix(" ₴")
        self.spin_price.setValue(float(self.project_data.get("customer_price", 0) or 0))
        layout.addRow("Ціна для замовника", self.spin_price)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {
            "name": self.edit_name.text().strip(),
            "project_number": self.edit_number.text().strip(),
            "client": self.edit_client.text().strip(),
            "status": self.combo_status.currentText(),
            "cost_price": self.spin_cost.value(),
            "customer_price": self.spin_price.value(),
        }


class ProjectsTab(QWidget):
    """Вкладка управління проєктами."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self._projects = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ── Верхня панель ──
        header = QHBoxLayout()

        lbl_title = QLabel("📁 Проєкти")
        lbl_title.setObjectName("title")
        header.addWidget(lbl_title)
        header.addStretch()

        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("🔍 Пошук проєкту...")
        self.edit_search.setFixedWidth(250)
        self.edit_search.setMinimumHeight(32)
        self.edit_search.textChanged.connect(self._on_search)
        header.addWidget(self.edit_search)

        btn_refresh = QPushButton("🔄 Оновити")
        btn_refresh.setMinimumHeight(32)
        btn_refresh.clicked.connect(self._load_data)
        header.addWidget(btn_refresh)

        btn_new = QPushButton("➕ Новий проєкт")
        btn_new.setObjectName("primary")
        btn_new.setMinimumHeight(32)
        btn_new.clicked.connect(self._on_new_project)
        header.addWidget(btn_new)

        layout.addLayout(header)

        # ── Таблиця ──
        self.table = QTableView()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(400)
        self.table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "ID", "Номер", "Назва", "Клієнт", "Статус", "Дата створення", "Сума виробів", "Ціна замовнику"
        ])
        self.table.setModel(self.model)

        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 150)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 100)
        self.table.setColumnWidth(6, 100)
        self.table.setColumnWidth(7, 120)

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

        lbl_hint = QLabel("💡 Двічі клікніть на рядок для вибору проєкту | Редагуйте статус для дашборду")
        lbl_hint.setObjectName("subtitle")
        layout.addWidget(lbl_hint)

    def _get_selected_id(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        row = idx.row()
        if 0 <= row < len(self._projects):
            return self._projects[row].get("id")
        return None

    def _load_data(self):
        """Завантажити проєкти з БД + підрахувати суму виробів."""
        self.model.removeRows(0, self.model.rowCount())
        self._projects = []

        try:
            with get_db() as session:
                projects = session.query(Project).order_by(Project.created_at.desc()).all()

                for p in projects:
                    # Підрахунок суми виробів проєкту
                    try:
                        products = ProductRepository.get_all(project_id=p.id)
                        total = sum(item.get("total_price", 0) for item in products)
                    except Exception:
                        total = 0

                    data = {
                        "id": p.id,
                        "name": p.name or "—",
                        "project_number": p.project_number or "—",
                        "client": p.client or "—",
                        "status": p.status or "Новий",
                        "created_at": str(p.created_at)[:10] if p.created_at else "—",
                        "cost_price": float(p.cost_price or 0),
                        "customer_price": float(p.customer_price or 0),
                        "products_total": total,
                    }
                    self._projects.append(data)

                    row = [
                        QStandardItem(str(p.id)),
                        QStandardItem(data["project_number"]),
                        QStandardItem(data["name"]),
                        QStandardItem(data["client"]),
                        QStandardItem(data["status"]),
                        QStandardItem(data["created_at"]),
                        QStandardItem(f"₴ {total:,.0f}"),
                        QStandardItem(f"₴ {data['customer_price']:,.0f}"),
                    ]
                    for cell in row:
                        cell.setEditable(False)
                    self.model.appendRow(row)

        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося завантажити проєкти: {e}")

    def _on_search(self, text):
        text = text.lower()
        for row in range(self.model.rowCount()):
            visible = False
            for col in range(self.model.columnCount()):
                item = self.model.item(row, col)
                if item and text in item.text().lower():
                    visible = True
                    break
            self.table.setRowHidden(row, not visible)

    def _on_double_click(self, index):
        """Подвійний клік — вибір проєкту як активного."""
        row = index.row()
        if 0 <= row < len(self._projects):
            project_id = self._projects[row]["id"]
            if self.main_window:
                self.main_window.set_active_project(project_id)
            QMessageBox.information(self, "Проєкт вибрано",
                f"Активний проєкт: {self._projects[row]['name']}")

    def _on_new_project(self):
        dlg = ProjectEditDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "Помилка", "Введіть назву проєкту")
                return
            try:
                with get_db() as session:
                    project = Project(
                        name=data["name"],
                        project_number=data["project_number"] or f"PRJ-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                        client=data["client"],
                        status=data["status"],
                        cost_price=data["cost_price"],
                        customer_price=data["customer_price"],
                        created_at=datetime.now(),
                    )
                    session.add(project)
                    session.flush()
                    project_id = project.id

                self._load_data()
                if self.main_window:
                    self.main_window.set_active_project(project_id)
                QMessageBox.information(self, "Успіх", f"Проєкт створено (ID: {project_id})")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося створити: {e}")

    def _on_edit(self):
        project_id = self._get_selected_id()
        if not project_id:
            QMessageBox.warning(self, "Увага", "Виберіть проєкт для редагування")
            return

        # Знаходимо дані проєкту
        project_data = None
        for p in self._projects:
            if p["id"] == project_id:
                project_data = p
                break
        if not project_data:
            return

        dlg = ProjectEditDialog(project_data, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "Помилка", "Введіть назву проєкту")
                return
            try:
                with get_db() as session:
                    project = session.query(Project).filter(Project.id == project_id).first()
                    if project:
                        project.name = data["name"]
                        project.project_number = data["project_number"] or project.project_number
                        project.client = data["client"]
                        project.status = data["status"]
                        project.cost_price = data["cost_price"]
                        project.customer_price = data["customer_price"]
                        session.commit()

                self._load_data()
                QMessageBox.information(self, "Успіх", "Проєкт оновлено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося оновити: {e}")

    def _on_delete(self):
        project_id = self._get_selected_id()
        if not project_id:
            QMessageBox.warning(self, "Увага", "Виберіть проєкт для видалення")
            return

        project_name = ""
        for p in self._projects:
            if p["id"] == project_id:
                project_name = p["name"]
                break

        reply = QMessageBox.question(
            self, "Видалення",
            f'Видалити проєкт "{project_name}" (ID: {project_id})?\n\nВСІ вироби цього проєкту також будуть видалені!',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with get_db() as session:
                    # Видаляємо вироби проєкту
                    from ventilation_company.database.models.product_item import ProductItem
                    session.query(ProductItem).filter(ProductItem.project_id == project_id).delete()
                    # Видаляємо проєкт
                    session.query(Project).filter(Project.id == project_id).delete()
                    session.commit()

                self._load_data()
                QMessageBox.information(self, "Успіх", "Проєкт та його вироби видалено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити: {e}")
