"""Simple CRM dashboard dialog."""

from __future__ import annotations

from datetime import date, datetime

from PySide6.QtWidgets import QDialog, QGridLayout, QLabel, QPushButton, QVBoxLayout

from ventilation_company.database.repositories.client_repo import ClientRepository
from ventilation_company.database.repositories.interaction_repo import InteractionRepository
from ventilation_company.database.repositories.payment_repo import PaymentRepository


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


class CRMDashboardDialog(QDialog):
    """Small read-only CRM dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 CRM Dashboard")
        self.resize(420, 320)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.grid = QGridLayout()
        layout.addLayout(self.grid)

        self.lbl_total_clients = QLabel()
        self.lbl_active_clients = QLabel()
        self.lbl_potential_clients = QLabel()
        self.lbl_interactions = QLabel()
        self.lbl_payments_total = QLabel()
        self.lbl_next_actions = QLabel()

        rows = [
            ("Клієнтів:", self.lbl_total_clients),
            ("Активних:", self.lbl_active_clients),
            ("Потенційних:", self.lbl_potential_clients),
            ("Взаємодій:", self.lbl_interactions),
            ("Сума оплат UAH:", self.lbl_payments_total),
            ("Наступних дій:", self.lbl_next_actions),
        ]
        for row, (title, label) in enumerate(rows):
            self.grid.addWidget(QLabel(title), row, 0)
            self.grid.addWidget(label, row, 1)

        btn_refresh = QPushButton("🔄 Оновити")
        btn_refresh.clicked.connect(self.refresh)
        layout.addWidget(btn_refresh)

    def refresh(self):
        clients = ClientRepository.list_all()
        interactions = InteractionRepository.list_all()
        payments = PaymentRepository.list_all()

        total = len(clients)
        active = sum(1 for c in clients if (c.get("status") or "") == "Активний")
        potential = sum(1 for c in clients if (c.get("status") or "") == "Потенційний")
        payments_total = sum(
            float(p.get("amount") or 0) for p in payments if (p.get("currency") or "UAH") == "UAH"
        )
        today = date.today()
        next_actions = 0
        for item in interactions:
            action_date = _to_date(item.get("next_action_date"))
            if action_date and action_date >= today:
                next_actions += 1

        self.lbl_total_clients.setText(str(total))
        self.lbl_active_clients.setText(str(active))
        self.lbl_potential_clients.setText(str(potential))
        self.lbl_interactions.setText(str(len(interactions)))
        self.lbl_payments_total.setText(f"{payments_total:,.2f}")
        self.lbl_next_actions.setText(str(next_actions))
