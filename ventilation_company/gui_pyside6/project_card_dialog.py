"""Діалог "Картка проєкту" — v2.4 зі знижкою на виробах.

Логіка:
  Собівартість = сума cost_price × quantity
  Ціна замовнику = сума discounted_price (якщо > 0) інакше total_price
  Роботи = сума з project_works
  Витрати = сума з project_expenses
  Прибуток = ціна (зі знижкою) − собівартість − роботи − витрати
"""

import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QBrush, QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDateEdit,
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
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.database.repositories.payment_repo import PaymentRepository
from ventilation_company.database.repositories.product_repo import ProductRepository
from ventilation_company.database.repositories.project_document_repo import (
    ProjectDocumentRepository,
)
from ventilation_company.database.repositories.project_expense_repo import ProjectExpenseRepository
from ventilation_company.database.repositories.project_repo import ProjectRepository
from ventilation_company.database.repositories.project_work_repo import ProjectWorkRepository
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.gui_pyside6.workers import FunctionWorker
from ventilation_company.services.business_settings import BusinessSettings


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

        self.combo_work = QComboBox()
        self.combo_work.addItem("— Вручну —", None)
        self._work_rates = BusinessSettings.get_instance().work_rates
        for key in self._work_rates:
            self.combo_work.addItem(key.replace("_", " "), key)
        self.combo_work.currentIndexChanged.connect(self._on_work_selected)
        layout.addRow("Типова робота (з Бізнес)", self.combo_work)

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

        if work_data:
            self._preselect_work(work_data.get("work_name", ""))

    def _on_work_selected(self, index: int):
        key = self.combo_work.itemData(index)
        if not key:
            return
        rate = BusinessSettings.get_instance().get_work_rate(key)
        self.edit_name.setText(key.replace("_", " "))
        self.edit_unit.setText(str(rate.get("одиниця", "год")))
        self.spin_price.setValue(float(rate.get("ціна", 0) or 0))

    def _preselect_work(self, work_name: str):
        """Якщо назва роботи збігається з типовою — підсвітити її у списку."""
        self.combo_work.blockSignals(True)
        for i in range(self.combo_work.count()):
            key = self.combo_work.itemData(i)
            if key and key.replace("_", " ") == work_name:
                self.combo_work.setCurrentIndex(i)
                break
        self.combo_work.blockSignals(False)

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
        self.direction_combo = QComboBox()
        self.direction_combo.addItem("➖ Витрата", "minus")
        self.direction_combo.addItem("➕ Плюс", "plus")
        current_direction = expense_data.get("direction", "minus") if expense_data else "minus"
        self.direction_combo.setCurrentIndex(1 if current_direction == "plus" else 0)
        layout.addRow("Тип:", self.direction_combo)
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
            "direction": self.direction_combo.currentData(),
        }


class ComponentPickerDialog(QDialog):
    """Вибір комплектуючої з бізнес-налаштувань для додавання у витрати проєкту."""

    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle("Комплектуючі системи вентиляції")
        self.setMinimumSize(480, 380)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        lbl = QLabel("Оберіть комплектуючу зі списку (ціни — з «Налаштування → Бізнес»):")
        lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        layout.addWidget(lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Назва", "Ціна, грн", "Од."])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self._keys: list[str] = []
        components = BusinessSettings.get_instance().components
        for key, data in components.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(key.replace("_", " ")))
            self.table.setItem(row, 1, QTableWidgetItem(str(data.get("ціна", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(data.get("одиниця", ""))))
            self._keys.append(key)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        if self.table.rowCount():
            self.table.selectRow(0)

        form = QFormLayout()
        self.spin_qty = QDoubleSpinBox()
        self.spin_qty.setRange(0.01, 99999)
        self.spin_qty.setValue(1)
        form.addRow("Кількість", self.spin_qty)
        layout.addLayout(form)

        btn = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn.accepted.connect(self.accept)
        btn.rejected.connect(self.reject)
        layout.addWidget(btn)

    def get_data(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._keys):
            return None
        key = self._keys[row]
        data = BusinessSettings.get_instance().get_component(key)
        qty = self.spin_qty.value()
        price = float(data.get("ціна", 0) or 0)
        return {
            "project_id": self.project_id,
            "expense_name": key.replace("_", " "),
            "quantity": qty,
            "unit": str(data.get("одиниця", "шт")),
            "unit_price": price,
            "total_price": round(qty * price, 2),
            "direction": "minus",
        }


class PaymentEditDialog(QDialog):
    def __init__(self, project_id: int, payment_data=None, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.payment_data = payment_data or {}
        self.setWindowTitle("Редагувати оплату" if payment_data else "Нова оплата")
        self.setMinimumWidth(380)
        layout = QFormLayout(self)
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        value = self.payment_data.get("date")
        if value:
            try:
                self.date_edit.setDate(QDate(value.year, value.month, value.day))
            except Exception:
                self.date_edit.setDate(QDate.fromString(str(value)[:10], "yyyy-MM-dd"))
        layout.addRow("Дата:", self.date_edit)
        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0, 999999999)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(" ₴")
        self.spin_amount.setValue(float(self.payment_data.get("amount") or 0))
        layout.addRow("Сума:", self.spin_amount)
        self.combo_type = QComboBox()
        self.combo_type.addItems(["вхідний", "вихідний"])
        self.combo_type.setCurrentText(self.payment_data.get("type") or "вхідний")
        layout.addRow("Тип:", self.combo_type)
        self.edit_purpose = QLineEdit(self.payment_data.get("purpose") or "Оплата за проєкт")
        layout.addRow("Призначення:", self.edit_purpose)
        self.edit_notes = QLineEdit(self.payment_data.get("notes") or "")
        layout.addRow("Нотатки:", self.edit_notes)
        btn = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btn.accepted.connect(self.accept)
        btn.rejected.connect(self.reject)
        layout.addRow(btn)

    def get_data(self):
        return {
            "project_id": self.project_id,
            "date": self.date_edit.date().toPython(),
            "amount": self.spin_amount.value(),
            "currency": "UAH",
            "type": self.combo_type.currentText(),
            "purpose": self.edit_purpose.text().strip(),
            "notes": self.edit_notes.text().strip(),
        }


class ProjectCardDialog(QDialog):
    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle(f"📁 Картка проєкту #{project_id}")
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        self.resize(1000, 700)
        self._project_data: dict = {}
        self._products: list[dict] = []
        self._documents: list[dict] = []
        self._works: list[dict] = []
        self._expenses: list[dict] = []
        self._payments: list[dict] = []
        self._worker: FunctionWorker | None = None
        self._build_ui()
        self._start_load()

    # ── Асинхронне завантаження даних ──

    def _fetch_data(self) -> dict:
        """Зібрати всі дані картки проєкту (виконується у фоновому потоці).

        Не чіпає GUI-стану; у разі помилки виняток передається через worker.error.
        """
        p = ProjectRepository.get(self.project_id)
        if not p:
            return {"project": None}

        products = ProductRepository.get_all(project_id=self.project_id)
        works = ProjectWorkRepository.get_all(self.project_id)
        expenses = ProjectExpenseRepository.get_all(self.project_id)
        documents = ProjectDocumentRepository.get_by_project(self.project_id)
        payments = PaymentRepository.list_by_project(self.project_id)
        paid_total = sum(
            float(p.get("amount") or 0)
            for p in payments
            if (p.get("type") or "вхідний") == "вхідний"
        )

        cost = sum(
            float(item.get("cost_price") or 0) * float(item.get("quantity") or 1)
            for item in products
        )
        base_price = sum(
            (
                float(item.get("discounted_price") or 0)
                if float(item.get("discounted_price") or 0) > 0
                else float(item.get("total_price") or 0)
            )
            for item in products
        )
        works_total = sum(float(item.get("total_price") or 0) for item in works)
        plus_expenses_total = sum(
            float(item.get("total_price") or 0)
            for item in expenses
            if (item.get("direction") or "minus") == "plus"
        )
        minus_expenses_total = sum(
            float(item.get("total_price") or 0)
            for item in expenses
            if (item.get("direction") or "minus") != "plus"
        )

        project_data = dict(p)
        project_data["cost_price"] = cost
        project_data["customer_price"] = base_price
        project_data["works_total"] = works_total
        project_data["plus_expenses_total"] = plus_expenses_total
        project_data["minus_expenses_total"] = minus_expenses_total
        project_data["expenses_total"] = minus_expenses_total
        project_data["paid_total"] = paid_total
        return {
            "project": project_data,
            "products": products,
            "documents": documents,
            "works": works,
            "expenses": expenses,
            "payments": payments,
        }

    def _start_load(self):
        """Запустити фонове завантаження даних картки."""
        self._set_busy(True)
        worker = FunctionWorker(self._fetch_data)
        worker.result.connect(self._on_data_loaded)
        worker.error.connect(self._on_load_error)
        # Життєвий цикл worker'а прив'язано до finished потоку (а не до result):
        # посилання знімається лише після того, як run() справді завершився,
        # інакше можливий крах "QThread: Destroyed while thread is still running".
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(self._on_worker_finished)
        self._worker = worker  # захист від збирання сміття
        worker.start()

    def _on_worker_finished(self):
        """Потік завершився — знімаємо посилання (лише якщо це поточний worker)."""
        if self._worker is self.sender():
            self._worker = None

    def _on_data_loaded(self, result: dict):
        project = result.get("project")
        if project is None:
            self._set_busy(False)
            QMessageBox.warning(self, "Увага", f"Проєкт #{self.project_id} не знайдено")
            return
        self._project_data = project
        self._products = result["products"]
        self._documents = result["documents"]
        self._works = result["works"]
        self._expenses = result["expenses"]
        self._payments = result["payments"]

        name = self._project_data.get("name", "Проєкт")
        self.setWindowTitle(f"📁 {name} (#{self.project_id})")
        if hasattr(self, "lbl_title"):
            self.lbl_title.setText(f"📁 {name}")
        self._populate_all()
        self._set_busy(False)

    def _on_load_error(self, message: str):
        self._set_busy(False)
        QMessageBox.critical(self, "Помилка", f"Не вдалося завантажити проєкт:\n{message}")

    def _set_busy(self, busy: bool):
        if busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            if hasattr(self, "lbl_title"):
                self.lbl_title.setText("⏳ Завантаження…")
        else:
            QApplication.restoreOverrideCursor()

    def _populate_all(self):
        """Оновити всі вкладки після завантаження/перезавантаження даних."""
        self._populate_info_tab()
        self._populate_products()
        self._populate_documents()
        self._populate_works()
        self._populate_expenses()
        self._populate_payments()

    def _load_data(self):
        """Сумісність: синхронне завантаження (використовується лише у тестах)."""
        result = self._fetch_data()
        self._on_data_loaded(result)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        self.lbl_title = QLabel("⏳ Завантаження…")
        self.lbl_title.setObjectName("title")
        layout.addWidget(self.lbl_title)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_info_tab(), "ℹ️ Інформація")
        self.tabs.addTab(self._build_products_tab(), "🔧 Деталі")
        self.tabs.addTab(self._build_documents_tab(), "📄 Документи")
        self.tabs.addTab(self._build_works_tab(), "🔨 Роботи")
        self.tabs.addTab(self._build_expenses_tab(), "💸 Витрати")
        self.tabs.addTab(self._build_payments_tab(), "💳 Оплати")
        layout.addWidget(self.tabs)
        btn_close = QPushButton("✅ Закрити")
        btn_close.setMinimumHeight(36)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _build_info_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        layout.setSpacing(12)
        self._info_labels: dict[str, QLabel] = {}

        def add_row(key: str, caption: str) -> QLabel:
            lbl = QLabel("—")
            layout.addRow(caption, lbl)
            self._info_labels[key] = lbl
            return lbl

        add_row("project_number", "Номер:")
        add_row("name", "Назва:")
        add_row("client", "Клієнт:")
        add_row("status", "Статус:")
        add_row("created_at", "Дата створення:")
        layout.addRow(QLabel(""))
        add_row("cost_price", "🔧 Собівартість (вироби):")
        add_row("works_total", "🔨 Додаткові роботи:")
        add_row("expenses_total", "💸 Витрати:")
        add_row("plus_expenses_total", "➕ Надходження:")
        layout.addRow(QLabel(""))
        add_row("customer_price", "💰 Ціна замовнику (з виробів):")
        add_row("discounted_price", "🏷️ Ціна зі знижкою (проєкт):")
        layout.addRow(QLabel(""))
        add_row("products_total", "Сума виробів:")
        add_row("products_count", "Кількість виробів:")
        add_row("paid_total", "💳 Оплачено:")
        add_row("balance", "💳 Залишок:")
        add_row("profit", "📊 Прибуток (комплексний):")
        self._lbl_discount_note = QLabel("")
        self._lbl_discount_note.setStyleSheet(f"color: {Theme.WARNING}; font-size: 12px;")
        layout.addRow("", self._lbl_discount_note)
        self._info_tab = tab
        self._populate_info_tab()
        return tab

    def _populate_info_tab(self):
        d = self._project_data
        if not d:
            return
        cost = d.get("cost_price", 0)
        base_price = d.get("customer_price", 0)
        discounted = d.get("discounted_price", 0)
        works_total = d.get("works_total", 0)
        plus_expenses_total = d.get("plus_expenses_total", 0)
        minus_expenses_total = d.get("minus_expenses_total", 0)
        effective = discounted if discounted > 0 else base_price
        total_customer = effective + works_total + plus_expenses_total
        display_profit = total_customer - cost - minus_expenses_total
        paid_total = float(d.get("paid_total") or 0)
        balance = total_customer - paid_total

        def set_text(key: str, text: str, style: str | None = None):
            lbl = self._info_labels.get(key)
            if lbl is None:
                return
            lbl.setText(text)
            if style:
                lbl.setStyleSheet(style)

        set_text("project_number", str(d.get("project_number", "—")))
        set_text("name", str(d.get("name", "—")))
        set_text("client", str(d.get("client", "—")))
        set_text("status", str(d.get("status", "—")))
        set_text("created_at", str(d.get("created_at") or "—"))
        set_text("cost_price", f"₴ {cost:,.2f}", f"color: {Theme.SUCCESS}; font-weight: bold;")
        set_text(
            "works_total", f"₴ {works_total:,.2f}", f"color: {Theme.ACCENT}; font-weight: bold;"
        )
        set_text(
            "expenses_total",
            f"₴ {minus_expenses_total:,.2f}",
            f"color: {Theme.WARNING}; font-weight: bold;",
        )
        set_text(
            "plus_expenses_total",
            f"₴ {plus_expenses_total:,.2f}",
            f"color: {Theme.SUCCESS}; font-weight: bold;",
        )
        set_text(
            "customer_price", f"₴ {base_price:,.2f}", f"color: {Theme.ACCENT}; font-weight: bold;"
        )
        if discounted > 0:
            set_text(
                "discounted_price",
                f"₴ {discounted:,.2f}",
                f"color: {Theme.WARNING}; font-weight: bold; font-size: 15px;",
            )
        else:
            set_text("discounted_price", "— (не вказано)", f"color: {Theme.TEXT_MUTED};")
        set_text("products_total", f"₴ {base_price:,.2f}")
        set_text("products_count", str(len(self._products)))
        set_text("paid_total", f"₴ {paid_total:,.2f}")
        set_text("balance", f"₴ {balance:,.2f}")
        if display_profit >= 0:
            set_text(
                "profit",
                f"₴ {display_profit:,.2f}  ✅",
                f"color: {Theme.SUCCESS}; font-weight: bold; font-size: 16px; "
                f"padding: 8px 16px; background: #1a3a1a; border-radius: 8px;",
            )
        else:
            set_text(
                "profit",
                f"₴ {display_profit:,.2f}  ⚠️ ЗБИТОК",
                f"color: {Theme.DANGER}; font-weight: bold; font-size: 16px; "
                f"padding: 8px 16px; background: #3a1a1a; border-radius: 8px;",
            )

        if discounted > 0 and abs(discounted - base_price) > 0.01 and base_price > 0:
            diff = discounted - base_price
            diff_pct = diff / base_price * 100
            self._lbl_discount_note.setText(f"Знижка: ₴ {diff:,.2f} ({diff_pct:.1f}% від базової)")
        else:
            self._lbl_discount_note.setText("")

    def _build_products_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.products_table = QTableView()
        self.products_table.setAlternatingRowColors(True)
        self.products_table.horizontalHeader().setStretchLastSection(True)
        self.products_table.verticalHeader().setVisible(False)
        layout.addWidget(self.products_table)
        self.products_model = QStandardItemModel()
        # ← v2.4: додано колонку "Зі знижкою"
        self.products_model.setHorizontalHeaderLabels(
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
        self.products_table.setModel(self.products_model)
        self._populate_products()
        return tab

    def _populate_products(self):
        self.products_model.removeRows(0, self.products_model.rowCount())
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
            self.products_model.appendRow(row)

    def _build_documents_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        top = QHBoxLayout()
        self._lbl_docs_count = QLabel("📄 Документи проєкту (…)")
        self._lbl_docs_count.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-size: 14px;")
        top.addWidget(self._lbl_docs_count)
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
        self.docs_table.clicked.connect(self._on_docs_table_clicked)
        self.docs_table.doubleClicked.connect(lambda _idx: self._open_document())
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
        self._lbl_docs_count.setText(f"📄 Документи проєкту ({len(self._documents)})")
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

    def _on_docs_table_clicked(self, index):
        if not index.isValid():
            return
        if index.column() == self.docs_model.columnCount() - 1:
            self._open_document()

    def _open_document(self):
        doc_id = self._get_selected_doc_id()
        if not doc_id:
            QMessageBox.warning(self, "Увага", "Оберіть документ")
            return
        get_doc = getattr(ProjectDocumentRepository, "get_by_id", None) or getattr(
            ProjectDocumentRepository, "get", None
        )
        if get_doc is None:
            QMessageBox.warning(self, "Увага", "Документ недоступний")
            return
        doc = get_doc(doc_id)
        if not doc:
            QMessageBox.warning(self, "Увага", "Документ не знайдено")
            return
        content = doc.get("content") or b""
        if isinstance(content, str):
            content = content.encode("utf-8")
        filename = doc.get("filename") or f"document_{doc_id}.xlsx"
        filename = Path(filename).name
        suffix = Path(filename).suffix or ".xlsx"
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix, prefix="ventcompany_doc_"
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            os.startfile(tmp_path)
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося відкрити документ: {e}")

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
        self._lbl_works_count = QLabel("🔨 Додаткові роботи (…)")
        self._lbl_works_count.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-size: 14px;")
        top.addWidget(self._lbl_works_count)
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
        self._lbl_works_count.setText(f"🔨 Додаткові роботи ({len(self._works)})")
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
        self._lbl_expenses_count = QLabel("💸 Витрати / надходження (…)")
        self._lbl_expenses_count.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-size: 14px;")
        top.addWidget(self._lbl_expenses_count)
        top.addStretch()
        btn_add = QPushButton("➕ Додати витрату")
        btn_add.clicked.connect(self._on_add_expense)
        top.addWidget(btn_add)
        btn_components = QPushButton("🔩 Комплектуючі…")
        btn_components.setToolTip(
            "Додати комплектуючу з бізнес-налаштувань (вентилятор, фільтр, клапан…)"
        )
        btn_components.clicked.connect(self._on_add_component)
        top.addWidget(btn_components)
        layout.addLayout(top)
        self.expenses_table = QTableView()
        self.expenses_table.setAlternatingRowColors(True)
        self.expenses_table.horizontalHeader().setStretchLastSection(True)
        self.expenses_table.verticalHeader().setVisible(False)
        layout.addWidget(self.expenses_table)
        self.expenses_model = QStandardItemModel()
        self.expenses_model.setHorizontalHeaderLabels(
            ["ID", "Тип", "Назва", "К-ть", "Од.", "Ціна за од.", "Сума", ""]
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
        self._lbl_expenses_count.setText(f"💸 Витрати / надходження ({len(self._expenses)})")
        self.expenses_model.removeRows(0, self.expenses_model.rowCount())
        for e in self._expenses:
            direction = e.get("direction") or "minus"
            direction_label = "➕ Плюс" if direction == "plus" else "➖ Витрата"
            row = [
                QStandardItem(str(e["id"])),
                QStandardItem(direction_label),
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

    def _on_add_component(self):
        dlg = ComponentPickerDialog(self.project_id, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data:
            QMessageBox.warning(self, "Увага", "Оберіть комплектуючу зі списку")
            return
        try:
            ProjectExpenseRepository.create(data)
            self._reload_all()
            QMessageBox.information(
                self, "Успіх", f"Додано: {data['expense_name']} × {data['quantity']:g}"
            )
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

    def _build_payments_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        top = QHBoxLayout()
        btn_add = QPushButton("➕ Додати оплату")
        btn_add.clicked.connect(self._on_add_payment)
        top.addWidget(btn_add)
        top.addStretch()
        layout.addLayout(top)
        self.payments_table = QTableWidget()
        self.payments_table.setColumnCount(5)
        self.payments_table.setHorizontalHeaderLabels(
            ["Дата", "Тип", "Сума", "Призначення", "Нотатки"]
        )
        self.payments_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.payments_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.payments_table)
        self._populate_payments()
        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_edit = QPushButton("✏️ Редагувати")
        btn_edit.clicked.connect(self._on_edit_payment)
        bottom.addWidget(btn_edit)
        btn_delete = QPushButton("🗑 Видалити")
        btn_delete.setStyleSheet(f"color: {Theme.DANGER};")
        btn_delete.clicked.connect(self._on_delete_payment)
        bottom.addWidget(btn_delete)
        layout.addLayout(bottom)
        return tab

    def _populate_payments(self):
        self.payments_table.setRowCount(0)
        for p in getattr(self, "_payments", []):
            row = self.payments_table.rowCount()
            self.payments_table.insertRow(row)
            values = [
                str(p.get("date"))[:10] if p.get("date") else "",
                p.get("type") or "",
                f"₴ {float(p.get('amount') or 0):,.2f}",
                p.get("purpose") or "",
                p.get("notes") or "",
            ]
            for col, value in enumerate(values):
                self.payments_table.setItem(row, col, QTableWidgetItem(str(value)))

    def _get_selected_payment(self):
        row = self.payments_table.currentRow()
        if row < 0 or row >= len(getattr(self, "_payments", [])):
            QMessageBox.warning(self, "Увага", "Оберіть оплату")
            return None
        return self._payments[row]

    def _on_add_payment(self):
        dlg = PaymentEditDialog(self.project_id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                PaymentRepository.create(dlg.get_data())
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Оплату додано")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося додати оплату: {e}")

    def _on_edit_payment(self):
        payment = self._get_selected_payment()
        if not payment:
            return
        dlg = PaymentEditDialog(self.project_id, payment, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                PaymentRepository.update(payment["id"], dlg.get_data())
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Оплату оновлено")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося оновити оплату: {e}")

    def _on_delete_payment(self):
        payment = self._get_selected_payment()
        if not payment:
            return
        reply = QMessageBox.question(
            self,
            "Видалення",
            "Видалити обрану оплату?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                PaymentRepository.delete(payment["id"])
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Оплату видалено")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити оплату: {e}")

    def _reload_all(self):
        """Перезавантажити дані картки у фоновому потоці та оновити вкладки."""
        self._start_load()
