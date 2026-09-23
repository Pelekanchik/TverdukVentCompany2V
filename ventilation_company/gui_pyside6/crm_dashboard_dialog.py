"""Simple CRM dashboard dialog."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGridLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ventilation_company.database.repositories.client_repo import ClientRepository
from ventilation_company.database.repositories.interaction_repo import InteractionRepository
from ventilation_company.database.repositories.payment_repo import PaymentRepository
from ventilation_company.paths import APP_ROOT


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
    """Small read-only CRM dashboard with CSV export and upcoming actions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 CRM Dashboard")
        self.resize(720, 560)
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

        layout.addWidget(QLabel("Майбутні дії:"))
        self.table_actions = QTableWidget()
        self.table_actions.setColumnCount(5)
        self.table_actions.setHorizontalHeaderLabels(
            ["Дата", "Клієнт", "Тип", "Тема", "Наступна дія"]
        )
        self.table_actions.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table_actions)

        btn_refresh = QPushButton("🔄 Оновити")
        btn_export = QPushButton("💾 Експорт CSV")
        btn_refresh.clicked.connect(self.refresh)
        btn_export.clicked.connect(self.export_csv)
        layout.addWidget(btn_refresh)
        layout.addWidget(btn_export)

    def refresh(self):
        clients = ClientRepository.list_all()
        interactions = InteractionRepository.list_all()
        payments = PaymentRepository.list_all()
        client_names = {c["id"]: c.get("name") or f"#{c['id']}" for c in clients}

        total = len(clients)
        active = sum(1 for c in clients if (c.get("status") or "") == "Активний")
        potential = sum(1 for c in clients if (c.get("status") or "") == "Потенційний")
        payments_total = sum(
            float(p.get("amount") or 0) for p in payments if (p.get("currency") or "UAH") == "UAH"
        )
        today = date.today()

        upcoming = []
        for item in interactions:
            action_date = _to_date(item.get("next_action_date"))
            if action_date and action_date >= today:
                upcoming.append((action_date, item))
        upcoming.sort(key=lambda pair: pair[0])
        next_actions = len(upcoming)

        self.lbl_total_clients.setText(str(total))
        self.lbl_active_clients.setText(str(active))
        self.lbl_potential_clients.setText(str(potential))
        self.lbl_interactions.setText(str(len(interactions)))
        self.lbl_payments_total.setText(f"{payments_total:,.2f}")
        self.lbl_next_actions.setText(str(next_actions))

        self.table_actions.setRowCount(0)
        for action_date, item in upcoming[:50]:
            row = self.table_actions.rowCount()
            self.table_actions.insertRow(row)
            values = [
                action_date.isoformat(),
                client_names.get(item.get("client_id"), "—"),
                item.get("type"),
                item.get("subject"),
                item.get("next_action"),
            ]
            for col, value in enumerate(values):
                self.table_actions.setItem(
                    row, col, QTableWidgetItem("" if value is None else str(value))
                )

    @staticmethod
    def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in fieldnames})

    def export_csv(self):
        default_dir = APP_ROOT / "exports"
        default_dir.mkdir(parents=True, exist_ok=True)
        directory = QFileDialog.getExistingDirectory(
            self, "Оберіть папку для CSV", str(default_dir)
        )
        if not directory:
            return
        out_dir = Path(directory)

        clients = ClientRepository.list_all()
        interactions = InteractionRepository.list_all()
        payments = PaymentRepository.list_all()

        try:
            self._write_csv(
                out_dir / "clients.csv",
                [
                    "id",
                    "name",
                    "contact_person",
                    "phone",
                    "email",
                    "address",
                    "company_type",
                    "edrpou",
                    "status",
                    "notes",
                ],
                clients,
            )
            self._write_csv(
                out_dir / "interactions.csv",
                [
                    "id",
                    "client_id",
                    "date",
                    "type",
                    "subject",
                    "result",
                    "next_action",
                    "next_action_date",
                    "description",
                ],
                interactions,
            )
            self._write_csv(
                out_dir / "payments.csv",
                [
                    "id",
                    "client_id",
                    "date",
                    "amount",
                    "currency",
                    "type",
                    "purpose",
                    "project_name",
                    "notes",
                ],
                payments,
            )
            today = date.today()
            client_names = {c["id"]: c.get("name") or f"#{c['id']}" for c in clients}
            upcoming_rows = []
            for item in interactions:
                action_date = _to_date(item.get("next_action_date"))
                if action_date and action_date >= today:
                    upcoming_rows.append(
                        {
                            "date": action_date.isoformat(),
                            "client": client_names.get(item.get("client_id"), ""),
                            "type": item.get("type") or "",
                            "subject": item.get("subject") or "",
                            "next_action": item.get("next_action") or "",
                        }
                    )
            self._write_csv(
                out_dir / "upcoming_actions.csv",
                ["date", "client", "type", "subject", "next_action"],
                upcoming_rows,
            )
            QMessageBox.information(self, "Успіх", f"CSV експортовано у: {out_dir}")
        except Exception as exc:
            QMessageBox.critical(self, "Помилка", f"Не вдалося експортувати CSV: {exc}")
