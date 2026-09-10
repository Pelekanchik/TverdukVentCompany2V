"""Audit logging service.

Writes audit events to PostgreSQL. Audit failures must never break the main
business operation, so all exceptions are swallowed and logged as warnings.
"""

from __future__ import annotations

import logging
from typing import Any

from ventilation_company.database.db import SessionLocal
from ventilation_company.database.models.audit import AuditLog

logger = logging.getLogger(__name__)


def _actor_value(actor: Any, attr: str) -> Any:
    if actor is None:
        return None
    return getattr(actor, attr, None)


def log_action(
    action: str,
    *,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    details: dict | None = None,
    message: str | None = None,
    actor: Any = None,
) -> None:
    """Write one audit event. Never raises."""
    try:
        session = SessionLocal()
        try:
            session.add(
                AuditLog(
                    actor_id=_actor_value(actor, "id"),
                    actor_username=_actor_value(actor, "username"),
                    actor_role=_actor_value(actor, "role"),
                    action=action,
                    entity_type=entity_type,
                    entity_id=None if entity_id is None else str(entity_id),
                    details=details or {},
                    message=message,
                )
            )
            session.commit()
        finally:
            session.close()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to write audit action %s: %s", action, exc)
