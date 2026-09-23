"""Audit log repository."""

from __future__ import annotations

from ventilation_company.database.db import get_db
from ventilation_company.database.models.audit import AuditLog


class AuditLogRepository:
    @staticmethod
    def list_recent(limit: int = 5000) -> list[AuditLog]:
        with get_db() as session:
            rows = session.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
            session.expunge_all()
            return rows
