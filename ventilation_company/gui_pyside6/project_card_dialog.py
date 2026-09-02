"""Діалог "Картка проєкту" — повна інформація про проєкт.

ВИПРАВЛЕННЯ: додано "Розрахована собівартість" — автоматичний підрахунок з усіх виробів.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableView, QAbstractItemView, QMessageBox,
    QFileDialog, QFormLayout, QWidget
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.database.db import get_db
from ventilation_company.database.models.project import Project
from ventilation_company.database.repositories.product_repo import ProductRepository
from ventilation_company.database.repositories.project_document_repo import ProjectDocumentRepository


class ProjectCardDialog(QDialog):
    """Картка проєкту з повною інформацією."""

    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle(f"📁 Картка проєкту #{project_id}")
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        self.resize(1000, 700)

        self._project_data = {}
        self._products = []
        self._documents = []

        self._load_data()
        self._build_ui()

    def _load_data(self):
        try:
            with get_db() as session:
                p = session.query(Project).filter(Project.id == self.project_id).first()
                if p:
                    self._project_data = {
                        "id": p.id,
                        "name": p.name or "—",
                        "project_number": p.project_number or str(p.id),
                        "client": p.client or "—",
                        "status": p.status or "—",
                        "created_at": str(p.created_at)[:10] if p.created_at else "—",
                        "cost_price": float(p.cost_price or 0),
                        "customer_price": float(p.customer_price or 0),
                    }
            self._products = ProductRepository.get_all(project_id=self.project_id)
            self._documents = ProjectDocumentRepository.get_by_project(self.project_id)
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося завантажити дані проєкту: {e}")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        lbl_title = QLabel(f"📁 {self._project_data.get('name', 'Проєкт')}")
        lbl_title.setObjectName("title")
        layout.addWidget(lbl_title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_info_tab(), "ℹ️ Інформація")
        self.tabs.addTab(self._build_products_tab(), "🔧 Деталі")
        self.tabs.addTab(self._build_documents_tab(), "📄 Документи")
        self.tabs.addTab(self._build_works_tab(), "🔨 Роботи")
        self.tabs.addTab(self._build_expenses_tab(), "💸 Витрати")

        layout.addWidget(self.tabs)

        btn_close = QPushButton("✅ Закрити")
        btn_close.setMinimumHeight(36)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _build_info_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        layout.setSpacing(12)

        # Розраховані значення з виробів
        total_products = sum(item.get("total_price", 0) for item in self._products)
        calculated_cost = sum(item.get("unit_price", 0) * item.get("quantity", 1) for item in self._products)
        profit = total_products - calculated_cost

        layout.addRow("Номер:", QLabel(self._project_data.get("project_number", "—")))
        layout.addRow("Назва:", QLabel(self._project_data.get("name", "—")))
        layout.addRow("Клієнт:", QLabel(self._project_data.get("client", "—")))
        layout.addRow("Статус:", QLabel(self._project_data.get("status", "—")))
        layout.addRow("Дата створення:", QLabel(self._project_data.get("created_at", "—")))
        layout.addRow("", QLabel(""))  # відступ

        # Собівартість (ручний ввід з проєкту)
        lbl_manual_cost = QLabel(f"₴ {self._project_data.get('cost_price', 0):,.2f}")
        lbl_manual_cost.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        layout.addRow("Собівартість (введена):", lbl_manual_cost)

        # Розрахована собівартість (авто з виробів)
        lbl_calc_cost = QLabel(f"₴ {calculated_cost:,.2f}")
        lbl_calc_cost.setStyleSheet(f"color: {Theme.ACCENT}; font-weight: bold;")
        layout.addRow("Розрахована собівартість:", lbl_calc_cost)

        layout.addRow("Ціна замовнику:", QLabel(f"₴ {self._project_data.get('customer_price', 0):,.2f}"))
        layout.addRow("", QLabel(""))  # відступ

        layout.addRow("Сума виробів:", QLabel(f"₴ {total_products:,.2f}"))
        layout.addRow("Кількість виробів:", QLabel(str(len(self._products))))

        # Прибуток
        if profit >= 0:
            lbl_profit = QLabel(f"₴ {profit:,.2f}")
            lbl_profit.setStyleSheet(f"color: {Theme.SUCCESS}; font-weight: bold;")
        else:
            lbl_profit = QLabel(f"₴ {profit:,.2f}")
            lbl_profit.setStyleSheet(f"color: {Theme.DANGER}; font-weight: bold;")
        layout.addRow("Прибуток:", lbl_profit)

        return tab

    def _build_products_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.products_table = QTableView()
        self.products_table.setAlternatingRowColors(True)
        self.products_table.horizontalHeader().setStretchLastSection(True)
        self.products_table.verticalHeader().setVisible(False)
        layout.addWidget(self.products_table)

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["№", "Назва", "Тип", "Розміри", "Матеріал", "К-ть", "Ціна", "Сума"])
        self.products_table.setModel(model)

        for i, item in enumerate(self._products, 1):
            w = item.get("width", 0) or 0
            h = item.get("height", 0) or 0
            l = item.get("length", 0) or 0
            dims = f"Ø{w:.0f} x {l:.0f}" if h == 0 else f"{w:.0f}x{h:.0f}x{l:.0f}"
            row = [
                QStandardItem(str(i)),
                QStandardItem(item.get("name", "—")),
                QStandardItem(item.get("product_type", "—")),
                QStandardItem(dims),
                QStandardItem(item.get("material", "—")),
                QStandardItem(str(item.get("quantity", 1))),
                QStandardItem(f"₴ {item.get('unit_price', 0):,.2f}"),
                QStandardItem(f"₴ {item.get('total_price', 0):,.2f}"),
            ]
            for cell in row:
                cell.setEditable(False)
            model.appendRow(row)

        return tab

    def _build_documents_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        top = QHBoxLayout()
        lbl = QLabel(f"📄 Документи проєкту ({len(self._documents)})")
        lbl.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-size: 14px;")
        top.addWidget(lbl)
        top.addStretch()

        btn_refresh = QPushButton("🔄 Оновити")
        btn_refresh.clicked.connect(self._refresh_documents)
        top.addWidget(btn_refresh)
        layout.addLayout(top)

        self.docs_table = QTableView()
        self.docs_table.setAlternatingRowColors(True)
        self.docs_table.horizontalHeader().setStretchLastSection(True)
        self.docs_table.verticalHeader().setVisible(False)
        layout.addWidget(self.docs_table)

        self.docs_model = QStandardItemModel()
        self.docs_model.setHorizontalHeaderLabels(["ID", "Тип", "Файл", "Розмір", "Дата", "Дії"])
        self.docs_table.setModel(self.docs_model)

        self.docs_table.setColumnWidth(0, 40)
        self.docs_table.setColumnWidth(1, 120)
        self.docs_table.setColumnWidth(2, 250)
        self.docs_table.setColumnWidth(3, 80)
        self.docs_table.setColumnWidth(4, 120)
        self.docs_table.setColumnWidth(5, 100)

        self._populate_documents()

        actions = QHBoxLayout()
        actions.addStretch()

        btn_export = QPushButton("💾 Експортувати вибраний")
        btn_export.clicked.connect(self._export_document)
        actions.addWidget(btn_export)

        btn_delete = QPushButton("🗑️ Видалити вибраний")
        btn_delete.setStyleSheet(f"color: {Theme.DANGER};")
        btn_delete.clicked.connect(self._delete_document)
        actions.addWidget(btn_delete)

        layout.addLayout(actions)
        return tab

    def _populate_documents(self):
        self.docs_model.removeRows(0, self.docs_model.rowCount())
        type_names = {"spec": "Специфікація", "calc": "Калькуляція", "metal": "Метал", "order": "Наряд"}
        for doc in self._documents:
            row = [
                QStandardItem(str(doc["id"])),
                QStandardItem(type_names.get(doc["doc_type"], doc["doc_type"])),
                QStandardItem(doc["filename"]),
                QStandardItem(f"{doc['file_size'] / 1024:.1f} КБ"),
                QStandardItem(str(doc["created_at"])[:16] if doc["created_at"] else "—"),
                QStandardItem("📥 Завантажити"),
            ]
            for cell in row:
                cell.setEditable(False)
            self.docs_model.appendRow(row)

    def _refresh_documents(self):
        self._documents = ProjectDocumentRepository.get_by_project(self.project_id)
        self._populate_documents()

    def _get_selected_doc_id(self):
        idx = self.docs_table.currentIndex()
        if not idx.isValid():
            return None
        row = idx.row()
        if 0 <= row < len(self._documents):
            return self._documents[row]["id"]
        return None

    def _export_document(self):
        doc_id = self._get_selected_doc_id()
        if not doc_id:
            QMessageBox.warning(self, "Увага", "Виберіть документ для експорту")
            return

        doc = ProjectDocumentRepository.get_by_id(doc_id)
        if not doc:
            QMessageBox.warning(self, "Увага", "Документ не знайдено")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Зберегти документ", doc["filename"],
            "Excel files (*.xlsx);;All files (*.*)"
        )
        if path:
            try:
                with open(path, "wb") as f:
                    f.write(doc["content"])
                QMessageBox.information(self, "Успіх", f"Документ збережено:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти: {e}")

    def _delete_document(self):
        doc_id = self._get_selected_doc_id()
        if not doc_id:
            QMessageBox.warning(self, "Увага", "Виберіть документ для видалення")
            return

        reply = QMessageBox.question(self, "Видалення", "Видалити документ з бази даних?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                ProjectDocumentRepository.delete(doc_id)
                self._refresh_documents()
                QMessageBox.information(self, "Успіх", "Документ видалено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити: {e}")

    def _build_works_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        lbl = QLabel("🔨 Список виконаних робіт\n\n(Функціонал у розробці — буде додано пізніше)")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED}; padding: 40px;")
        layout.addWidget(lbl)
        return tab

    def _build_expenses_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        lbl = QLabel("💸 Додаткові витрати\n\n(Функціонал у розробці — буде додано пізніше)")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED}; padding: 40px;")
        layout.addWidget(lbl)
        return tab
