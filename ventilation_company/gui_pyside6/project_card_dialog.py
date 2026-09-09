"""Діалог "Картка проєкту" — v2.4 зі знижкою на виробах.

Логіка:
  Собівартість = сума cost_price × quantity
  Ціна замовнику = сума discounted_price (якщо > 0) інакше total_price
  Роботи = сума з project_works
  Витрати = сума з project_expenses
  Прибуток = ціна (зі знижкою) − собівартість − роботи − витрати
"""

from PySide6.QtGui import QBrush, QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.database.db import get_db
from ventilation_company.database.models.project import Project
from ventilation_company.database.repositories.product_repo import ProductRepository
from ventilation_company.database.repositories.project_document_repo import (
    ProjectDocumentRepository,
)
from ventilation_company.database.repositories.project_expense_repo import ProjectExpenseRepository
from ventilation_company.database.repositories.project_work_repo import ProjectWorkRepository
from ventilation_company.gui_pyside6.theme import Theme


class WorkEditDialog(QDialog):
    def __init__(self, project_id: int, work_data=None, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.work_id = work_data.get("id") if work_data else None
        self.setWindowTitle("Редагувати роботу" if work_data else "Нова робота")
        self.setMinimumWidth(350)
        self._build_ui(work_data)

    def _build_ui(self, work_data):
        layout = QFormLayout(self)
        self.edit_name = QLineEdit()
        self.edit_name.setText(work_data.get("work_name", "") if work_data else "")
        layout.addRow("Назва роботи *", self.edit_name)
        self.spin_qty = QDoubleSpinBox()
        self.spin_qty.setRange(0.01, 99999)
        self.spin_qty.setValue(work_data.get("quantity", 1) if work_data else 1)
        layout.addRow("Кількість", self.spin_qty)
        self.edit_unit = QLineEdit()
        self.edit_unit.setText(work_data.get("unit", "год") if work_data else "год")
        layout.addRow("Од. виміру", self.edit_unit)
        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0, 999999)
        self.spin_price.setSuffix(" ₴")
        self.spin_price.setDecimals(2)
        self.spin_price.setValue(work_data.get("unit_price", 0) if work_data else 0)
        layout.addRow("Ціна за од.", self.spin_price)
        btn = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btn.accepted.connect(self.accept)
        btn.rejected.connect(self.reject)
        layout.addRow(btn)

    def get_data(self):
        qty = self.spin_qty.value()
        price = self.spin_price.value()
        return {
            "project_id": self.project_id,
            "work_name": self.edit_name.text().strip(),
            "quantity": qty,
            "unit": self.edit_unit.text().strip(),
            "unit_price": price,
            "total_price": round(qty * price, 2),
        }


class ExpenseEditDialog(QDialog):
    def __init__(self, project_id: int, expense_data=None, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.expense_id = expense_data.get("id") if expense_data else None
        self.setWindowTitle("Редагувати витрату" if expense_data else "Нова витрата")
        self.setMinimumWidth(350)
        self._build_ui(expense_data)

    def _build_ui(self, expense_data):
        layout = QFormLayout(self)
        self.edit_name = QLineEdit()
        self.edit_name.setText(expense_data.get("expense_name", "") if expense_data else "")
        layout.addRow("Назва витрати *", self.edit_name)
        self.spin_qty = QDoubleSpinBox()
        self.spin_qty.setRange(0.01, 99999)
        self.spin_qty.setValue(expense_data.get("quantity", 1) if expense_data else 1)
        layout.addRow("Кількість", self.spin_qty)
        self.edit_unit = QLineEdit()
        self.edit_unit.setText(expense_data.get("unit", "шт") if expense_data else "шт")
        layout.addRow("Од. виміру", self.edit_unit)
        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0, 999999)
        self.spin_price.setSuffix(" ₴")
        self.spin_price.setDecimals(2)
        self.spin_price.setValue(expense_data.get("unit_price", 0) if expense_data else 0)
        layout.addRow("Ціна за од.", self.spin_price)
        btn = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btn.accepted.connect(self.accept)
        btn.rejected.connect(self.reject)
        layout.addRow(btn)

    def get_data(self):
        qty = self.spin_qty.value()
        price = self.spin_price.value()
        return {
            "project_id": self.project_id,
            "expense_name": self.edit_name.text().strip(),
            "quantity": qty,
            "unit": self.edit_unit.text().strip(),
            "unit_price": price,
            "total_price": round(qty * price, 2),
        }


class ProjectCardDialog(QDialog):
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
        self._works = []
        self._expenses = []
        self._load_data()
        self._build_ui()

    def _load_data(self):
        try:
            self._products = ProductRepository.get_all(project_id=self.project_id)
            self._documents = ProjectDocumentRepository.get_by_project(self.project_id)
            self._works = ProjectWorkRepository.get_all(project_id=self.project_id)
            self._expenses = ProjectExpenseRepository.get_all(project_id=self.project_id)

            # Рахуємо з виробів (з урахуванням знижки на виріб)
            cost_from_products = sum(
                p.get("cost_price", 0) * p.get("quantity", 1) for p in self._products
            )
            # ← v2.4: використовуємо discounted_price, якщо вона вказана
            price_from_products = sum(
                (
                    p.get("discounted_price", 0)
                    if p.get("discounted_price", 0) > 0
                    else p.get("total_price", 0)
                )
                for p in self._products
            )

            works_total = sum(w.get("total_price", 0) for w in self._works)
            expenses_total = sum(e.get("total_price", 0) for e in self._expenses)

            if cost_from_products == 0 and price_from_products > 0:
                cost_from_products = round(price_from_products / 1.56, 2)

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
                        "cost_price": cost_from_products,
                        "customer_price": price_from_products,
                        "discounted_price": float(p.discounted_price or 0),
                        "works_total": works_total,
                        "expenses_total": expenses_total,
                        "profit": float(p.profit or 0),
                    }
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
        cost = self._project_data.get("cost_price", 0)
        base_price = self._project_data.get("customer_price", 0)
        discounted = self._project_data.get("discounted_price", 0)
        works_total = self._project_data.get("works_total", 0)
        expenses_total = self._project_data.get("expenses_total", 0)
        effective = discounted if discounted > 0 else base_price
        display_profit = effective - cost - works_total - expenses_total
        layout.addRow("Номер:", QLabel(self._project_data.get("project_number", "—")))
        layout.addRow("Назва:", QLabel(self._project_data.get("name", "—")))
        layout.addRow("Клієнт:", QLabel(self._project_data.get("client", "—")))
        layout.addRow("Статус:", QLabel(self._project_data.get("status", "—")))
        layout.addRow("Дата створення:", QLabel(self._project_data.get("created_at", "—")))
        layout.addRow(QLabel(""))
        lbl_cost = QLabel(f"₴ {cost:,.2f}")
        lbl_cost.setStyleSheet(f"color: {Theme.SUCCESS}; font-weight: bold;")
        layout.addRow("🔧 Собівартість (вироби):", lbl_cost)
        lbl_works = QLabel(f"₴ {works_total:,.2f}")
        lbl_works.setStyleSheet(f"color: {Theme.ACCENT}; font-weight: bold;")
        layout.addRow("🔨 Додаткові роботи:", lbl_works)
        lbl_exp = QLabel(f"₴ {expenses_total:,.2f}")
        lbl_exp.setStyleSheet(f"color: {Theme.WARNING}; font-weight: bold;")
        layout.addRow("💸 Додаткові витрати:", lbl_exp)
        layout.addRow(QLabel(""))
        lbl_base = QLabel(f"₴ {base_price:,.2f}")
        lbl_base.setStyleSheet(f"color: {Theme.ACCENT}; font-weight: bold;")
        layout.addRow("💰 Ціна замовнику (з виробів):", lbl_base)
        lbl_disc = QLabel(f"₴ {discounted:,.2f}")
        if discounted > 0:
            lbl_disc.setStyleSheet(f"color: {Theme.WARNING}; font-weight: bold; font-size: 15px;")
            layout.addRow("🏷️ Ціна зі знижкою (проєкт):", lbl_disc)
        else:
            lbl_disc.setText("— (не вказано)")
            lbl_disc.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
            layout.addRow("🏷️ Ціна зі знижкою (проєкт):", lbl_disc)
        layout.addRow(QLabel(""))
        layout.addRow("Сума виробів:", QLabel(f"₴ {base_price:,.2f}"))
        layout.addRow("Кількість виробів:", QLabel(str(len(self._products))))
        if display_profit >= 0:
            lbl_profit = QLabel(f"₴ {display_profit:,.2f}  ✅")
            lbl_profit.setStyleSheet(
                f"color: {Theme.SUCCESS}; font-weight: bold; font-size: 16px; "
                f"padding: 8px 16px; background: #1a3a1a; border-radius: 8px;"
            )
        else:
            lbl_profit = QLabel(f"₴ {display_profit:,.2f}  ⚠️ ЗБИТОК")
            lbl_profit.setStyleSheet(
                f"color: {Theme.DANGER}; font-weight: bold; font-size: 16px; "
                f"padding: 8px 16px; background: #3a1a1a; border-radius: 8px;"
            )
        layout.addRow("📊 Прибуток (комплексний):", lbl_profit)
        if discounted > 0 and abs(discounted - base_price) > 0.01:
            diff = discounted - base_price
            diff_pct = (diff / base_price * 100) if base_price > 0 else 0
            lbl_note = QLabel(f"Знижка: ₴ {diff:,.2f} ({diff_pct:.1f}% від базової)")
            lbl_note.setStyleSheet(f"color: {Theme.WARNING}; font-size: 12px;")
            layout.addRow("", lbl_note)
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
        # ← v2.4: додано колонку "Зі знижкою"
        model.setHorizontalHeaderLabels(
            [
                "№",
                "Назва",
                "Тип",
                "Розміри",
                "Матеріал",
                "К-ть",
                "Собіварт.",
                "Ціна",
                "Зі знижкою",
                "Сума",
            ]
        )
        self.products_table.setModel(model)
        for i, item in enumerate(self._products, 1):
            w = item.get("width", 0) or 0
            h = item.get("height", 0) or 0
            l = item.get("length", 0) or 0
            dims = f"Ø{w:.0f} x {l:.0f}" if h == 0 else f"{w:.0f}x{h:.0f}x{l:.0f}"
            cost = item.get("cost_price", 0)
            unit = item.get("unit_price", 0)
            disc = item.get("discounted_price", 0)
            total = item.get("total_price", 0)
            qty = item.get("quantity", 1)
            # Якщо є знижка — показуємо її, інакше базову ціну
            effective_price = disc if disc > 0 else total
            row = [
                QStandardItem(str(i)),
                QStandardItem(item.get("name", "—")),
                QStandardItem(item.get("product_type", "—")),
                QStandardItem(dims),
                QStandardItem(item.get("material", "—")),
                QStandardItem(str(qty)),
                QStandardItem(f"₴ {cost:,.2f}"),
                QStandardItem(f"₴ {unit:,.2f}"),
                QStandardItem(f"₴ {disc:,.2f}" if disc > 0 else "—"),
                QStandardItem(f"₴ {effective_price:,.2f}"),
            ]
            for cell in row:
                cell.setEditable(False)
            # Зафарбовуємо знижку жовтим, якщо вона є
            if disc > 0:
                row[8].setForeground(QBrush(QColor(Theme.WARNING)))
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
        type_names = {
            "spec": "Специфікація",
            "calc": "Калькуляція",
            "metal": "Метал",
            "order": "Наряд",
        }
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
            self, "Зберегти документ", doc["filename"], "Excel files (*.xlsx);;All files (*.*)"
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
        reply = QMessageBox.question(
            self,
            "Видалення",
            "Видалити документ з бази даних?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
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
        top = QHBoxLayout()
        lbl = QLabel(f"🔨 Додаткові роботи ({len(self._works)})")
        lbl.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-size: 14px;")
        top.addWidget(lbl)
        top.addStretch()
        btn_add = QPushButton("➕ Додати роботу")
        btn_add.clicked.connect(self._on_add_work)
        top.addWidget(btn_add)
        layout.addLayout(top)
        self.works_table = QTableView()
        self.works_table.setAlternatingRowColors(True)
        self.works_table.horizontalHeader().setStretchLastSection(True)
        self.works_table.verticalHeader().setVisible(False)
        layout.addWidget(self.works_table)
        self.works_model = QStandardItemModel()
        self.works_model.setHorizontalHeaderLabels(
            ["ID", "Назва", "К-ть", "Од.", "Ціна за од.", "Сума", ""]
        )
        self.works_table.setModel(self.works_model)
        self.works_table.setColumnWidth(0, 40)
        self.works_table.setColumnWidth(1, 200)
        self.works_table.setColumnWidth(2, 60)
        self.works_table.setColumnWidth(3, 60)
        self.works_table.setColumnWidth(4, 100)
        self.works_table.setColumnWidth(5, 100)
        self.works_table.setColumnWidth(6, 80)
        self._populate_works()
        actions = QHBoxLayout()
        actions.addStretch()
        btn_edit = QPushButton("✏️ Редагувати")
        btn_edit.clicked.connect(self._on_edit_work)
        actions.addWidget(btn_edit)
        btn_del = QPushButton("🗑️ Видалити")
        btn_del.setStyleSheet(f"color: {Theme.DANGER};")
        btn_del.clicked.connect(self._on_delete_work)
        actions.addWidget(btn_del)
        layout.addLayout(actions)
        return tab

    def _populate_works(self):
        self.works_model.removeRows(0, self.works_model.rowCount())
        for w in self._works:
            row = [
                QStandardItem(str(w["id"])),
                QStandardItem(w["work_name"]),
                QStandardItem(f"{w['quantity']:,.2f}"),
                QStandardItem(w["unit"]),
                QStandardItem(f"₴ {w['unit_price']:,.2f}"),
                QStandardItem(f"₴ {w['total_price']:,.2f}"),
                QStandardItem(""),
            ]
            for cell in row:
                cell.setEditable(False)
            self.works_model.appendRow(row)

    def _on_add_work(self):
        dlg = WorkEditDialog(self.project_id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data["work_name"]:
                QMessageBox.warning(self, "Помилка", "Введіть назву роботи")
                return
            try:
                ProjectWorkRepository.create(data)
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Роботу додано!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося додати: {e}")

    def _on_edit_work(self):
        idx = self.works_table.currentIndex()
        if not idx.isValid():
            QMessageBox.warning(self, "Увага", "Виберіть роботу для редагування")
            return
        row = idx.row()
        if row < 0 or row >= len(self._works):
            return
        dlg = WorkEditDialog(self.project_id, self._works[row], parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                ProjectWorkRepository.update(self._works[row]["id"], data)
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Роботу оновлено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося оновити: {e}")

    def _on_delete_work(self):
        idx = self.works_table.currentIndex()
        if not idx.isValid():
            QMessageBox.warning(self, "Увага", "Виберіть роботу для видалення")
            return
        row = idx.row()
        if row < 0 or row >= len(self._works):
            return
        reply = QMessageBox.question(
            self,
            "Видалення",
            "Видалити роботу?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                ProjectWorkRepository.delete(self._works[row]["id"])
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Роботу видалено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити: {e}")

    def _build_expenses_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        top = QHBoxLayout()
        lbl = QLabel(f"💸 Додаткові витрати ({len(self._expenses)})")
        lbl.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-size: 14px;")
        top.addWidget(lbl)
        top.addStretch()
        btn_add = QPushButton("➕ Додати витрату")
        btn_add.clicked.connect(self._on_add_expense)
        top.addWidget(btn_add)
        layout.addLayout(top)
        self.expenses_table = QTableView()
        self.expenses_table.setAlternatingRowColors(True)
        self.expenses_table.horizontalHeader().setStretchLastSection(True)
        self.expenses_table.verticalHeader().setVisible(False)
        layout.addWidget(self.expenses_table)
        self.expenses_model = QStandardItemModel()
        self.expenses_model.setHorizontalHeaderLabels(
            ["ID", "Назва", "К-ть", "Од.", "Ціна за од.", "Сума", ""]
        )
        self.expenses_table.setModel(self.expenses_model)
        self.expenses_table.setColumnWidth(0, 40)
        self.expenses_table.setColumnWidth(1, 200)
        self.expenses_table.setColumnWidth(2, 60)
        self.expenses_table.setColumnWidth(3, 60)
        self.expenses_table.setColumnWidth(4, 100)
        self.expenses_table.setColumnWidth(5, 100)
        self.expenses_table.setColumnWidth(6, 80)
        self._populate_expenses()
        actions = QHBoxLayout()
        actions.addStretch()
        btn_edit = QPushButton("✏️ Редагувати")
        btn_edit.clicked.connect(self._on_edit_expense)
        actions.addWidget(btn_edit)
        btn_del = QPushButton("🗑️ Видалити")
        btn_del.setStyleSheet(f"color: {Theme.DANGER};")
        btn_del.clicked.connect(self._on_delete_expense)
        actions.addWidget(btn_del)
        layout.addLayout(actions)
        return tab

    def _populate_expenses(self):
        self.expenses_model.removeRows(0, self.expenses_model.rowCount())
        for e in self._expenses:
            row = [
                QStandardItem(str(e["id"])),
                QStandardItem(e["expense_name"]),
                QStandardItem(f"{e['quantity']:,.2f}"),
                QStandardItem(e["unit"]),
                QStandardItem(f"₴ {e['unit_price']:,.2f}"),
                QStandardItem(f"₴ {e['total_price']:,.2f}"),
                QStandardItem(""),
            ]
            for cell in row:
                cell.setEditable(False)
            self.expenses_model.appendRow(row)

    def _on_add_expense(self):
        dlg = ExpenseEditDialog(self.project_id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data["expense_name"]:
                QMessageBox.warning(self, "Помилка", "Введіть назву витрати")
                return
            try:
                ProjectExpenseRepository.create(data)
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Витрату додано!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося додати: {e}")

    def _on_edit_expense(self):
        idx = self.expenses_table.currentIndex()
        if not idx.isValid():
            QMessageBox.warning(self, "Увага", "Виберіть витрату для редагування")
            return
        row = idx.row()
        if row < 0 or row >= len(self._expenses):
            return
        dlg = ExpenseEditDialog(self.project_id, self._expenses[row], parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                ProjectExpenseRepository.update(self._expenses[row]["id"], data)
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Витрату оновлено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося оновити: {e}")

    def _on_delete_expense(self):
        idx = self.expenses_table.currentIndex()
        if not idx.isValid():
            QMessageBox.warning(self, "Увага", "Виберіть витрату для видалення")
            return
        row = idx.row()
        if row < 0 or row >= len(self._expenses):
            return
        reply = QMessageBox.question(
            self,
            "Видалення",
            "Видалити витрату?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                ProjectExpenseRepository.delete(self._expenses[row]["id"])
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Витрату видалено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити: {e}")

    def _reload_all(self):
        self._load_data()
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)
        self.tabs.addTab(self._build_info_tab(), "ℹ️ Інформація")
        self.tabs.addTab(self._build_products_tab(), "🔧 Деталі")
        self.tabs.addTab(self._build_documents_tab(), "📄 Документи")
        self.tabs.addTab(self._build_works_tab(), "🔨 Роботи")
        self.tabs.addTab(self._build_expenses_tab(), "💸 Витрати")
