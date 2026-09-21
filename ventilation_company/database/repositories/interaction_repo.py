"""Interaction repository for CRM."""

from __future__ import annotations

from ventilation_company.database.db import get_db
from ventilation_company.database.models.unified import Interaction


def _to_dict(item: Interaction) -> dict:
    return {
        "id": item.id,
        "client_id": item.client_id,
        "date": item.date,
        "type": item.interaction_type,
        "subject": item.subject,
        "description": item.description,
        "result": item.result,
        "next_action": item.next_action,
        "next_action_date": item.next_action_date,
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
    def get(interaction_id: int) -> dict | None:
        with get_db() as session:
            item = session.get(Interaction, interaction_id)
            return _to_dict(item) if item else None

    @staticmethod
    def create(data: dict) -> dict:
        with get_db() as session:
            item = Interaction(
                client_id=data["client_id"],
                date=data.get("date"),
                interaction_type=data.get("type") or "дзвінок",
                subject=data.get("subject"),
                description=data.get("description"),
                result=data.get("result"),
                next_action=data.get("next_action"),
                next_action_date=data.get("next_action_date"),
                created_by=data.get("created_by"),
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return _to_dict(item)

    @staticmethod
    def update(interaction_id: int, data: dict) -> dict | None:
        with get_db() as session:
            item = session.get(Interaction, interaction_id)
            if not item:
                return None
            mapping = {
                "date": "date",
                "type": "interaction_type",
                "subject": "subject",
                "description": "description",
                "result": "result",
                "next_action": "next_action",
                "next_action_date": "next_action_date",
                "created_by": "created_by",
            }
            for key, attr in mapping.items():
                if key in data:
                    setattr(item, attr, data[key])
            session.commit()
            session.refresh(item)
            return _to_dict(item)

    @staticmethod
    def delete(interaction_id: int) -> bool:
        with get_db() as session:
            item = session.get(Interaction, interaction_id)
            if not item:
                return False
            session.delete(item)
            session.commit()
            return True
