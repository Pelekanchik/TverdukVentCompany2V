"""Audit log viewer dialog (PySide6)."""

from __future__ import annotations

import csv
import json

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from ventilation_company.database.db import SessionLocal
from ventilation_company.database.models.audit import AuditLog


class AuditLogDialog(QDialog):
    """Read-only audit log viewer with simple filters."""

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._rows: list[AuditLog] = []
        self.setWindowTitle("📜 Audit Log")
        self.resize(1100, 650)
        self._build_ui()
        self.refresh_logs()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        filters = QHBoxLayout()
        self.edit_user = QLineEdit()
        self.edit_user.setPlaceholderText("Користувач")
        self.edit_action = QLineEdit()
        self.edit_action.setPlaceholderText("Action, напр. auth.login")
        self.edit_entity = QLineEdit()
        self.edit_entity.setPlaceholderText("Entity type")
        btn_apply = QPushButton("🔍 Показати")
        btn_apply.clicked.connect(self.refresh_logs)
        btn_export = QPushButton("💾 Експорт CSV")
        btn_export.clicked.connect(self.export_csv)

        filters.addWidget(QLabel("Користувач:"))
        filters.addWidget(self.edit_user)
        filters.addWidget(QLabel("Action:"))
        filters.addWidget(self.edit_action)
        filters.addWidget(QLabel("Entity:"))
        filters.addWidget(self.edit_entity)
        filters.addWidget(btn_apply)
        filters.addWidget(btn_export)
        layout.addLayout(filters)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Час", "Користувач", "Роль", "Action", "Entity", "Details"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._show_selected_details)
        layout.addWidget(self.table)

        layout.addWidget(QLabel("Деталі:"))
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(130)
        layout.addWidget(self.details)

    def refresh_logs(self) -> None:
        username = self.edit_user.text().strip().lower()
        action = self.edit_action.text().strip().lower()
        entity = self.edit_entity.text().strip().lower()

        session = SessionLocal()
        try:
            rows = session.query(AuditLog).order_by(AuditLog.id.desc()).limit(5000).all()
        finally:
            session.close()

        filtered = []
        for row in rows:
            if username and username not in (row.actor_username or "").lower():
                continue
            if action and action not in row.action.lower():
                continue
            if entity and entity not in (row.entity_type or "").lower():
                continue
            filtered.append(row)
            if len(filtered) >= 1000:
                break

        self._rows = filtered
        self.table.setRowCount(0)
        for row in filtered:
            idx = self.table.rowCount()
            self.table.insertRow(idx)
            compact_details = json.dumps(row.details or {}, ensure_ascii=False, sort_keys=True)
            values = [
                str(row.id),
                row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
                row.actor_username or "—",
                row.actor_role or "—",
                row.action,
                f"{row.entity_type or '—'}#{row.entity_id or '—'}",
                compact_details[:500],
            ]
            for col, value in enumerate(values):
                self.table.setItem(idx, col, QTableWidgetItem(value))
        self.details.clear()

    def _show_selected_details(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rows):
            return
        record = self._rows[row]
        self.details.setPlainText(
            json.dumps(
                {
                    "id": record.id,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    "actor_id": record.actor_id,
                    "actor_username": record.actor_username,
                    "actor_role": record.actor_role,
                    "action": record.action,
                    "entity_type": record.entity_type,
                    "entity_id": record.entity_id,
                    "details": record.details or {},
                    "message": record.message,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    def export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Експорт audit log", "audit_log.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "id",
                        "created_at",
                        "actor_id",
                        "actor_username",
                        "actor_role",
                        "action",
                        "entity_type",
                        "entity_id",
                        "details",
                        "message",
                    ]
                )
                for row in self._rows:
                    writer.writerow(
                        [
                            row.id,
                            row.created_at.isoformat() if row.created_at else "",
                            row.actor_id or "",
                            row.actor_username or "",
                            row.actor_role or "",
                            row.action,
                            row.entity_type or "",
                            row.entity_id or "",
                            json.dumps(row.details or {}, ensure_ascii=False),
                            row.message or "",
                        ]
                    )
            QMessageBox.information(self, "Успіх", f"Експортовано рядків: {len(self._rows)}")
        except Exception as exc:
            QMessageBox.critical(self, "Помилка", f"Не вдалося експортувати:\n{exc}")
