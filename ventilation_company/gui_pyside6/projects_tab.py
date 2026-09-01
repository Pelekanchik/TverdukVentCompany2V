"""Вкладка проєктів з таблицею (PySide6 + SQLAlchemy)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QLineEdit, QMessageBox, QAbstractItemView
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.database.db import get_db
from ventilation_company.database.models.project import Project


class ProjectsTab(QWidget):
    """Вкладка управління проєктами з нормальною таблицею."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Заголовок + кнопки
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

        # Таблиця
        self.table = QTableView()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(400)
        layout.addWidget(self.table)

        # Модель таблиці
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "ID", "Номер", "Назва", "Клієнт", "Статус", "Дата створення", "Сума"
        ])
        self.table.setModel(self.model)

        # Ширина колонок
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 250)
        self.table.setColumnWidth(3, 150)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 120)
        self.table.setColumnWidth(6, 100)

        # Підказка
        lbl_hint = QLabel("💡 Двічі клікніть на рядок для відкриття проєкту")
        lbl_hint.setObjectName("subtitle")
        layout.addWidget(lbl_hint)

    def _load_data(self):
        """Завантажити проєкти з БД."""
        self.model.removeRows(0, self.model.rowCount())

        try:
            with get_db() as session:
                projects = session.query(Project).order_by(Project.created_at.desc()).all()

                for p in projects:
                    row = [
                        QStandardItem(str(p.id)),
                        QStandardItem(p.project_number or "—"),
                        QStandardItem(p.name or "—"),
                        QStandardItem(p.client or "—"),
                        QStandardItem(p.status or "draft"),
                        QStandardItem(str(p.created_at)[:10] if p.created_at else "—"),
                        QStandardItem(f"₴ {float(p.customer_price or 0):,.0f}"),
                    ]
                    for item in row:
                        item.setEditable(False)
                    self.model.appendRow(row)

        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося завантажити проєкти: {e}")

    def _on_search(self, text: str):
        """Фільтрація таблиці."""
        text = text.lower()
        for row in range(self.model.rowCount()):
            visible = False
            for col in range(self.model.columnCount()):
                item = self.model.item(row, col)
                if item and text in item.text().lower():
                    visible = True
                    break
            self.table.setRowHidden(row, not visible)

    def _on_new_project(self):
        QMessageBox.information(self, "Новий проєкт", "Тут буде діалог створення проєкту")
