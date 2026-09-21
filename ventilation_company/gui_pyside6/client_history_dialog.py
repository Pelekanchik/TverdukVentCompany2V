"""Client history dialog: interactions and payments."""

from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
)

from ventilation_company.database.repositories.interaction_repo import InteractionRepository
from ventilation_company.database.repositories.payment_repo import PaymentRepository


def _to_qdate(value) -> QDate:
    if value is None or value == "":
        return QDate.currentDate()
    if isinstance(value, datetime):
        return QDate(value.year, value.month, value.day)
    if isinstance(value, date):
        return QDate(value.year, value.month, value.day)
    return QDate.fromString(str(value)[:10], "yyyy-MM-dd")


class AddInteractionDialog(QDialog):
    def __init__(self, client_id: int, data: dict | None = None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self._data = data or {}
        self.setWindowTitle("Редагувати взаємодію" if data else "Додати взаємодію")
        self.setMinimumWidth(480)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        self.date_edit = QDateEdit(_to_qdate(self._data.get("date")))
        self.date_edit.setCalendarPopup(True)
        layout.addRow("Дата", self.date_edit)

        self.combo_type = QComboBox()
        self.combo_type.addItems(["дзвінок", "зустріч", "email", "примітка"])
        self.combo_type.setCurrentText(self._data.get("type") or "дзвінок")
        layout.addRow("Тип", self.combo_type)

        self.edit_subject = QLineEdit(self._data.get("subject") or "")
        self.edit_subject.setPlaceholderText("Тема розмови / зустрічі")
        layout.addRow("Тема", self.edit_subject)

        self.edit_result = QLineEdit(self._data.get("result") or "")
        self.edit_result.setPlaceholderText("Короткий результат")
        layout.addRow("Результат", self.edit_result)

        self.edit_next_action = QLineEdit(self._data.get("next_action") or "")
        self.edit_next_action.setPlaceholderText("Що робити далі")
        layout.addRow("Наступна дія", self.edit_next_action)

        self.next_action_date = QDateEdit(_to_qdate(self._data.get("next_action_date")))
        self.next_action_date.setCalendarPopup(True)
        layout.addRow("Дата наступної дії", self.next_action_date)

        self.edit_description = QTextEdit(self._data.get("description") or "")
        self.edit_description.setPlaceholderText("Деталі...")
        self.edit_description.setMaximumHeight(100)
        layout.addRow("Опис", self.edit_description)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        return {
            "client_id": self.client_id,
            "date": self.date_edit.date().toPython(),
            "type": self.combo_type.currentText(),
            "subject": self.edit_subject.text().strip(),
            "result": self.edit_result.text().strip(),
            "next_action": self.edit_next_action.text().strip(),
            "next_action_date": self.next_action_date.date().toPython(),
            "description": self.edit_description.toPlainText().strip(),
        }


class AddPaymentDialog(QDialog):
    def __init__(self, client_id: int, data: dict | None = None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self._data = data or {}
        self.setWindowTitle("Редагувати оплату" if data else "Додати оплату")
        self.setMinimumWidth(480)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        self.date_edit = QDateEdit(_to_qdate(self._data.get("date")))
        self.date_edit.setCalendarPopup(True)
        layout.addRow("Дата", self.date_edit)

        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0, 999999999)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setValue(float(self._data.get("amount") or 0))
        layout.addRow("Сума", self.spin_amount)

        self.edit_currency = QLineEdit(self._data.get("currency") or "UAH")
        layout.addRow("Валюта", self.edit_currency)

        self.combo_type = QComboBox()
        self.combo_type.addItems(["вхідний", "вихідний"])
        self.combo_type.setCurrentText(self._data.get("type") or "вхідний")
        layout.addRow("Тип", self.combo_type)

        self.edit_purpose = QLineEdit(self._data.get("purpose") or "")
        self.edit_purpose.setPlaceholderText("Призначення платежу")
        layout.addRow("Призначення", self.edit_purpose)

        self.edit_project = QLineEdit(self._data.get("project_name") or "")
        self.edit_project.setPlaceholderText("Проєкт")
        layout.addRow("Проєкт", self.edit_project)

        self.edit_notes = QTextEdit(self._data.get("notes") or "")
        self.edit_notes.setPlaceholderText("Нотатки")
        self.edit_notes.setMaximumHeight(80)
        layout.addRow("Нотатки", self.edit_notes)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        return {
            "client_id": self.client_id,
            "date": self.date_edit.date().toPython(),
            "amount": self.spin_amount.value(),
            "currency": self.edit_currency.text().strip() or "UAH",
            "type": self.combo_type.currentText(),
            "purpose": self.edit_purpose.text().strip(),
            "project_name": self.edit_project.text().strip(),
            "notes": self.edit_notes.toPlainText().strip(),
        }


class ClientHistoryDialog(QDialog):
    """Client history viewer/editor."""

    def __init__(self, client_id: int, client_name: str, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self._interactions: list[dict] = []
        self._payments: list[dict] = []
        self.setWindowTitle(f"Історія клієнта — {client_name}")
        self.resize(920, 560)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        btn_add_interaction = QPushButton("➕ Взаємодія")
        btn_edit_interaction = QPushButton("✏️ Взаємодію")
        btn_del_interaction = QPushButton("🗑 Взаємодію")
        btn_add_payment = QPushButton("➕ Оплата")
        btn_edit_payment = QPushButton("✏️ Оплату")
        btn_del_payment = QPushButton("🗑 Оплату")
        btn_refresh = QPushButton("🔄")
        btn_add_interaction.clicked.connect(self._add_interaction)
        btn_edit_interaction.clicked.connect(self._edit_interaction)
        btn_del_interaction.clicked.connect(self._delete_interaction)
        btn_add_payment.clicked.connect(self._add_payment)
        btn_edit_payment.clicked.connect(self._edit_payment)
        btn_del_payment.clicked.connect(self._delete_payment)
        btn_refresh.clicked.connect(self._load_data)
        for btn in [
            btn_add_interaction,
            btn_edit_interaction,
            btn_del_interaction,
            btn_add_payment,
            btn_edit_payment,
            btn_del_payment,
            btn_refresh,
        ]:
            btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.table_interactions = QTableWidget()
        self.table_interactions.setColumnCount(8)
        self.table_interactions.setHorizontalHeaderLabels(
            ["ID", "Дата", "Тип", "Тема", "Результат", "Наступна дія", "Дата дії", "Опис"]
        )
        self.table_interactions.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_interactions.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabs.addTab(self.table_interactions, "Взаємодії")

        self.table_payments = QTableWidget()
        self.table_payments.setColumnCount(8)
        self.table_payments.setHorizontalHeaderLabels(
            ["ID", "Дата", "Сума", "Валюта", "Тип", "Призначення", "Проєкт", "Нотатки"]
        )
        self.table_payments.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_payments.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabs.addTab(self.table_payments, "Оплати")

    def _add_interaction(self):
        dlg = AddInteractionDialog(self.client_id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                InteractionRepository.create(dlg.get_data())
                self._load_data()
            except Exception as exc:
                QMessageBox.critical(self, "Помилка", f"Не вдалося додати взаємодію: {exc}")

    def _edit_interaction(self):
        row = self.table_interactions.currentRow()
        if row < 0 or row >= len(self._interactions):
            QMessageBox.warning(self, "Увага", "Оберіть взаємодію")
            return
        item = self._interactions[row]
        dlg = AddInteractionDialog(self.client_id, data=item, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                InteractionRepository.update(item["id"], dlg.get_data())
                self._load_data()
            except Exception as exc:
                QMessageBox.critical(self, "Помилка", f"Не вдалося оновити взаємодію: {exc}")

    def _add_payment(self):
        dlg = AddPaymentDialog(self.client_id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                PaymentRepository.create(dlg.get_data())
                self._load_data()
            except Exception as exc:
                QMessageBox.critical(self, "Помилка", f"Не вдалося додати оплату: {exc}")

    def _edit_payment(self):
        row = self.table_payments.currentRow()
        if row < 0 or row >= len(self._payments):
            QMessageBox.warning(self, "Увага", "Оберіть оплату")
            return
        item = self._payments[row]
        dlg = AddPaymentDialog(self.client_id, data=item, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                PaymentRepository.update(item["id"], dlg.get_data())
                self._load_data()
            except Exception as exc:
                QMessageBox.critical(self, "Помилка", f"Не вдалося оновити оплату: {exc}")

    def _delete_interaction(self):
        row = self.table_interactions.currentRow()
        if row < 0 or row >= len(self._interactions):
            QMessageBox.warning(self, "Увага", "Оберіть взаємодію")
            return
        item = self._interactions[row]
        reply = QMessageBox.question(
            self,
            "Підтвердження",
            f'Видалити взаємодію #{item["id"]}?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                InteractionRepository.delete(item["id"])
                self._load_data()
            except Exception as exc:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити взаємодію: {exc}")

    def _delete_payment(self):
        row = self.table_payments.currentRow()
        if row < 0 or row >= len(self._payments):
            QMessageBox.warning(self, "Увага", "Оберіть оплату")
            return
        item = self._payments[row]
        reply = QMessageBox.question(
            self,
            "Підтвердження",
            f'Видалити оплату #{item["id"]}?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                PaymentRepository.delete(item["id"])
                self._load_data()
            except Exception as exc:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити оплату: {exc}")

    @staticmethod
    def _set_value(table, row, col, value):
        table.setItem(row, col, QTableWidgetItem("" if value is None else str(value)))

    def _load_data(self):
        self._interactions = InteractionRepository.list_by_client(self.client_id)
        self.table_interactions.setRowCount(0)
        for item in self._interactions:
            row = self.table_interactions.rowCount()
            self.table_interactions.insertRow(row)
            values = [
                item["id"],
                item.get("date"),
                item.get("type"),
                item.get("subject"),
                item.get("result"),
                item.get("next_action"),
                item.get("next_action_date"),
                item.get("description"),
            ]
            for col, value in enumerate(values):
                self._set_value(self.table_interactions, row, col, value)

        self._payments = PaymentRepository.list_by_client(self.client_id)
        self.table_payments.setRowCount(0)
        for item in self._payments:
            row = self.table_payments.rowCount()
            self.table_payments.insertRow(row)
            values = [
                item["id"],
                item.get("date"),
                item.get("amount"),
                item.get("currency"),
                item.get("type"),
                item.get("purpose"),
                item.get("project_name"),
                item.get("notes"),
            ]
            for col, value in enumerate(values):
                self._set_value(self.table_payments, row, col, value)
