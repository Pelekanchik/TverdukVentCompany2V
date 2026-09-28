"""CRM client card dialog."""

from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
from ventilation_company.database.repositories.project_repo import ProjectRepository
from ventilation_company.gui_pyside6.client_history_dialog import ClientHistoryDialog
from ventilation_company.gui_pyside6.workers import FunctionWorker


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
    """Editable client info card."""

    def __init__(self, client: dict, parent=None):
        super().__init__(parent)
        self.client = client
        self._worker: FunctionWorker | None = None
        self.setWindowTitle(f"🪪 Картка клієнта — {client.get('name', '')}")
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.resize(820, 640)
        self._build_ui()
        self._start_load()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        info = QFormLayout()
        self.edit_name = QLineEdit(self.client.get("name") or "")
        self.edit_contact = QLineEdit(self.client.get("contact_person") or "")
        self.edit_phone = QLineEdit(self.client.get("phone") or "")
        self.edit_email = QLineEdit(self.client.get("email") or "")
        self.edit_address = QLineEdit(self.client.get("address") or "")

        info.addRow("Назва:", self.edit_name)
        info.addRow("Контакт:", self.edit_contact)
        info.addRow("Телефон:", self.edit_phone)
        info.addRow("Email:", self.edit_email)
        info.addRow("Адреса:", self.edit_address)

        self.combo_status = QComboBox()
        self.combo_status.addItems(["Активний", "Потенційний", "Неактивний", "Чорний список"])
        self.combo_status.setCurrentText(self.client.get("status") or "Потенційний")
        info.addRow("Статус:", self.combo_status)

        self.edit_notes = QTextEdit(self.client.get("notes") or "")
        self.edit_notes.setPlaceholderText("Нотатки про клієнта...")
        self.edit_notes.setMaximumHeight(80)
        info.addRow("Нотатки:", self.edit_notes)

        layout.addLayout(info)

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
        self.lbl_projects_total = QLabel("—")
        self.lbl_payments_total = QLabel("—")
        self.lbl_balance = QLabel("—")
        self.grid.addWidget(QLabel("Проєкти:"), 3, 0)
        self.grid.addWidget(self.lbl_projects_total, 3, 1)
        self.grid.addWidget(QLabel("Оплачено:"), 4, 0)
        self.grid.addWidget(self.lbl_payments_total, 4, 1)
        self.grid.addWidget(QLabel("Борг / залишок:"), 5, 0)
        self.grid.addWidget(self.lbl_balance, 5, 1)
        layout.addLayout(self.grid)
        layout.addWidget(QLabel("Проєкти клієнта:"))
        self.table_projects = QTableWidget()
        self.table_projects.setColumnCount(5)
        self.table_projects.setHorizontalHeaderLabels(["ID", "Номер", "Назва", "Статус", "Сума"])
        self.table_projects.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_projects.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table_projects)

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
        self.table_interactions.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table_interactions)

        layout.addWidget(QLabel("Останні оплати:"))
        self.table_payments = QTableWidget()
        self.table_payments.setColumnCount(4)
        self.table_payments.setHorizontalHeaderLabels(["Дата", "Сума", "Валюта", "Тип"])
        self.table_payments.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table_payments)

    def _save(self):
        data = {
            "name": self.edit_name.text().strip(),
            "contact_person": self.edit_contact.text().strip(),
            "phone": self.edit_phone.text().strip(),
            "email": self.edit_email.text().strip(),
            "address": self.edit_address.text().strip(),
            "status": self.combo_status.currentText(),
            "notes": self.edit_notes.toPlainText().strip(),
        }
        if not data["name"]:
            QMessageBox.warning(self, "Увага", "Назва клієнта не може бути порожньою")
            return
        try:
            updated = ClientRepository.update(self.client["id"], data)
            if updated:
                self.client = updated
            parent = self.parent()
            loader = getattr(parent, "_load_data", None) if parent is not None else None
            if callable(loader):
                loader()
            QMessageBox.information(self, "Успіх", "Картку клієнта збережено")
        except Exception as exc:
            QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти картку: {exc}")

    def _open_history(self):
        dlg = ClientHistoryDialog(self.client["id"], self.client.get("name") or "Клієнт", self)
        dlg.exec()
        self._start_load()

    # ── Асинхронне завантаження (worker-патерн, як у картки проєкту) ──

    def _fetch_data(self) -> dict:
        """Зібрати дані картки клієнта з БД (чиста функція, без UI)."""
        client_id = self.client["id"]
        try:
            projects = ProjectRepository.list_by_client(client_id)
        except Exception:
            projects = []
        try:
            payments = PaymentRepository.list_by_client(client_id)
        except Exception:
            payments = []
        interactions = InteractionRepository.list_by_client(client_id)
        return {
            "projects": projects,
            "payments": payments,
            "interactions": interactions,
        }

    def _start_load(self):
        """Запустити фонове завантаження даних картки."""
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

    def _on_load_error(self, message: str):
        QMessageBox.critical(self, "Помилка БД", f"Не вдалося завантажити картку: {message}")

    def _on_data_loaded(self, data: dict):
        self._populate_finance_summary(data["projects"], data["payments"])
        self._populate_projects(data["projects"])
        self._populate_summary(data["interactions"], data["payments"])

    def _populate_finance_summary(self, projects, payments):
        projects_total = sum(
            float(p.get("discounted_price") or 0) or float(p.get("customer_price") or 0)
            for p in projects
        )
        payments_total = sum(
            float(p.get("amount") or 0)
            for p in payments
            if (p.get("type") or "вхідний") == "вхідний"
        )
        balance = projects_total - payments_total
        self.lbl_projects_total.setText(f"{projects_total:,.2f} UAH")
        self.lbl_payments_total.setText(f"{payments_total:,.2f} UAH")
        self.lbl_balance.setText(f"{balance:,.2f} UAH")

    def _populate_projects(self, projects):
        self.table_projects.setRowCount(0)
        for project in projects:
            row = self.table_projects.rowCount()
            self.table_projects.insertRow(row)
            amount = float(project.get("discounted_price") or 0)
            if amount <= 0:
                amount = float(project.get("customer_price") or 0)
            values = [
                project.get("id"),
                project.get("project_number"),
                project.get("name"),
                project.get("status"),
                amount,
            ]
            for col, value in enumerate(values):
                self.table_projects.setItem(
                    row, col, QTableWidgetItem("" if value is None else str(value))
                )

    def _populate_summary(self, interactions, payments):
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
