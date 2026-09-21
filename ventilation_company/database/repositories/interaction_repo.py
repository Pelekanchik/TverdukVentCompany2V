"""Interaction repository for CRM."""

from __future__ import annotations

from ventilation_company.database.db import get_db
from ventilation_company.database.models.unified import Interaction


def _to_dict(item: Interaction) -> dict:
    return {
        "id": item.id,
        "client_id": item.client_id,
        "date": item.date,
        "type": item.type,
        "subject": item.subject,
        "notes": item.notes,
        "next_action_date": item.next_action_date,
        "status": item.status,
        "created_by": item.created_by,
    }


class InteractionRepository:
    @staticmethod
    def list_by_client(client_id: int) -> list[dict]:
        with get_db() as session:
            items = (
                session.query(Interaction)
                .filter(Interaction.client_id == client_id)
                .order_by(Interaction.date.desc())
                .all()
            )
            return [_to_dict(i) for i in items]

    @staticmethod
    def create(data: dict) -> dict:
        with get_db() as session:
            item = Interaction(
                client_id=data["client_id"],
                date=data.get("date"),
                type=data.get("type"),
                subject=data.get("subject"),
                notes=data.get("notes"),
                next_action_date=data.get("next_action_date"),
                status=data.get("status") or "Заплановано",
                created_by=data.get("created_by"),
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return _to_dict(item)
