"""CRM client card dialog."""

from __future__ import annotations

from datetime import date, datetime

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from ventilation_company.database.repositories.client_repo import ClientRepository
from ventilation_company.database.repositories.interaction_repo import InteractionRepository
from ventilation_company.database.repositories.payment_repo import PaymentRepository
from ventilation_company.gui_pyside6.client_history_dialog import ClientHistoryDialog


def _to_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


class ClientCardDialog(QDialog):
    """Consolidated client info card with small editable fields."""

    def __init__(self, client: dict, parent=None):
        super().__init__(parent)
        self.client = client
        self.setWindowTitle(f"🪪 Картка клієнта — {client.get('name', '')}")
        self.resize(780, 600)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        info = QFormLayout()
        info.addRow("Назва:", QLabel(self.client.get("name") or "—"))
        info.addRow("Контакт:", QLabel(self.client.get("contact_person") or "—"))
        info.addRow("Телефон:", QLabel(self.client.get("phone") or "—"))
        info.addRow("Email:", QLabel(self.client.get("email") or "—"))
        info.addRow("Адреса:", QLabel(self.client.get("address") or "—"))
        layout.addLayout(info)

        self.combo_status = QComboBox()
        self.combo_status.addItems(["Активний", "Потенційний", "Неактивний", "Чорний список"])
        self.combo_status.setCurrentText(self.client.get("status") or "Потенційний")
        info.addRow("Статус:", self.combo_status)

        self.edit_notes = QTextEdit(self.client.get("notes") or "")
        self.edit_notes.setPlaceholderText("Нотатки про клієнта...")
        self.edit_notes.setMaximumHeight(80)
        info.addRow("Нотатки:", self.edit_notes)

        btn_save = QPushButton("💾 Зберегти")
        btn_save.clicked.connect(self._save)
        layout.addWidget(btn_save)

        self.grid = QGridLayout()
        self.lbl_interactions = QLabel()
        self.lbl_payments = QLabel()
        self.lbl_next_action = QLabel()
        self.grid.addWidget(QLabel("Взаємодій:"), 0, 0)
        self.grid.addWidget(self.lbl_interactions, 0, 1)
        self.grid.addWidget(QLabel("Оплат:"), 1, 0)
        self.grid.addWidget(self.lbl_payments, 1, 1)
        self.grid.addWidget(QLabel("Наступна дія:"), 2, 0)
        self.grid.addWidget(self.lbl_next_action, 2, 1)
        layout.addLayout(self.grid)

        btn_row = QHBoxLayout()
        btn_history = QPushButton("📜 Повна історія")
        btn_close = QPushButton("Закрити")
        btn_history.clicked.connect(self._open_history)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_history)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        layout.addWidget(QLabel("Останні взаємодії:"))
        self.table_interactions = QTableWidget()
        self.table_interactions.setColumnCount(5)
        self.table_interactions.setHorizontalHeaderLabels(
            ["Дата", "Тип", "Тема", "Результат", "Наступна дія"]
        )
        self.table_interactions.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table_interactions)

        layout.addWidget(QLabel("Останні оплати:"))
        self.table_payments = QTableWidget()
        self.table_payments.setColumnCount(4)
        self.table_payments.setHorizontalHeaderLabels(["Дата", "Сума", "Валюта", "Тип"])
        self.table_payments.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table_payments)

    def _save(self):
        data = {
            "status": self.combo_status.currentText(),
            "notes": self.edit_notes.toPlainText().strip(),
        }
        try:
            updated = ClientRepository.update(self.client["id"], data)
            if updated:
                self.client = updated
            if self.parent() is not None and hasattr(self.parent(), "_load_data"):
                self.parent()._load_data()
            QMessageBox.information(self, "Успіх", "Картку клієнта збережено")
        except Exception as exc:
            QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти картку: {exc}")

    def _open_history(self):
        dlg = ClientHistoryDialog(self.client["id"], self.client.get("name") or "Клієнт", self)
        dlg.exec()
        self._load_data()

    def _load_data(self):
        interactions = InteractionRepository.list_by_client(self.client["id"])
        payments = PaymentRepository.list_by_client(self.client["id"])

        payments_total = sum(
            float(p.get("amount") or 0) for p in payments if (p.get("currency") or "UAH") == "UAH"
        )
        next_dates = [
            d
            for d in (_to_date(i.get("next_action_date")) for i in interactions)
            if d is not None and d >= date.today()
        ]
        next_action = min(next_dates).isoformat() if next_dates else "—"

        self.lbl_interactions.setText(str(len(interactions)))
        self.lbl_payments.setText(f"{len(payments)} | {payments_total:,.2f} UAH")
        self.lbl_next_action.setText(next_action)
        self.combo_status.setCurrentText(self.client.get("status") or "Потенційний")
        if not self.edit_notes.toPlainText():
            self.edit_notes.setPlainText(self.client.get("notes") or "")

        self.table_interactions.setRowCount(0)
        for item in interactions[:5]:
            row = self.table_interactions.rowCount()
            self.table_interactions.insertRow(row)
            values = [
                item.get("date"),
                item.get("type"),
                item.get("subject"),
                item.get("result"),
                item.get("next_action"),
            ]
            for col, value in enumerate(values):
                self.table_interactions.setItem(
                    row, col, QTableWidgetItem("" if value is None else str(value))
                )

        self.table_payments.setRowCount(0)
        for item in payments[:5]:
            row = self.table_payments.rowCount()
            self.table_payments.insertRow(row)
            values = [item.get("date"), item.get("amount"), item.get("currency"), item.get("type")]
            for col, value in enumerate(values):
                self.table_payments.setItem(
                    row, col, QTableWidgetItem("" if value is None else str(value))
                )
