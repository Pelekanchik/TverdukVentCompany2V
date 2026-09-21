"""Client repository for CRM."""

from __future__ import annotations

from ventilation_company.database.db import get_db
from ventilation_company.database.models.unified import Client


def _to_dict(client: Client) -> dict:
    return {
        "id": client.id,
        "name": client.name,
        "contact_person": client.contact_person,
        "phone": client.phone,
        "email": client.email,
        "address": client.address,
        "company_type": client.company_type,
        "edrpou": client.edrpou,
        "status": getattr(client, "status", None) or "Потенційний",
        "notes": client.notes,
    }


class ClientRepository:
    @staticmethod
    def list_all() -> list[dict]:
        with get_db() as session:
            clients = session.query(Client).order_by(Client.updated_at.desc()).all()
            return [_to_dict(c) for c in clients]

    @staticmethod
    def get(client_id: int) -> dict | None:
        with get_db() as session:
            client = session.get(Client, client_id)
            return _to_dict(client) if client else None

    @staticmethod
    def create(data: dict) -> dict:
        with get_db() as session:
            client = Client(
                name=data.get("name", "").strip(),
                contact_person=data.get("contact_person"),
                phone=data.get("phone"),
                email=data.get("email"),
                address=data.get("address"),
                company_type=data.get("company_type"),
                edrpou=data.get("edrpou"),
                status=data.get("status") or "Потенційний",
                notes=data.get("notes"),
            )
            session.add(client)
            session.commit()
            session.refresh(client)
            return _to_dict(client)

    @staticmethod
    def update(client_id: int, data: dict) -> dict | None:
        with get_db() as session:
            client = session.get(Client, client_id)
            if not client:
                return None
            for key in (
                "name",
                "contact_person",
                "phone",
                "email",
                "address",
                "company_type",
                "edrpou",
                "status",
                "notes",
            ):
                if key in data:
                    setattr(client, key, data[key])
            session.commit()
            session.refresh(client)
            return _to_dict(client)

    @staticmethod
    def delete(client_id: int) -> bool:
        with get_db() as session:
            client = session.get(Client, client_id)
            if not client:
                return False
            session.delete(client)
            session.commit()
            return True
