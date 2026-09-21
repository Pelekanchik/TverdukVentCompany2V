"""Payment repository for CRM."""

from __future__ import annotations

from ventilation_company.database.db import get_db
from ventilation_company.database.models.unified import Payment


def _to_dict(item: Payment) -> dict:
    return {
        "id": item.id,
        "client_id": item.client_id,
        "date": item.date,
        "amount": item.amount,
        "currency": item.currency,
        "type": item.payment_type,
        "purpose": item.purpose,
        "project_name": item.project_name,
        "notes": item.notes,
    }


class PaymentRepository:
    @staticmethod
    def list_by_client(client_id: int) -> list[dict]:
        with get_db() as session:
            items = (
                session.query(Payment)
                .filter(Payment.client_id == client_id)
                .order_by(Payment.date.desc())
                .all()
            )
            return [_to_dict(p) for p in items]

    @staticmethod
    def get(payment_id: int) -> dict | None:
        with get_db() as session:
            item = session.get(Payment, payment_id)
            return _to_dict(item) if item else None

    @staticmethod
    def create(data: dict) -> dict:
        with get_db() as session:
            item = Payment(
                client_id=data["client_id"],
                date=data.get("date"),
                amount=data.get("amount") or 0,
                currency=data.get("currency") or "UAH",
                payment_type=data.get("type") or "вхідний",
                purpose=data.get("purpose"),
                project_name=data.get("project_name"),
                notes=data.get("notes"),
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return _to_dict(item)

    @staticmethod
    def update(payment_id: int, data: dict) -> dict | None:
        with get_db() as session:
            item = session.get(Payment, payment_id)
            if not item:
                return None
            mapping = {
                "date": "date",
                "amount": "amount",
                "currency": "currency",
                "type": "payment_type",
                "purpose": "purpose",
                "project_name": "project_name",
                "notes": "notes",
            }
            for key, attr in mapping.items():
                if key in data:
                    setattr(item, attr, data[key])
            session.commit()
            session.refresh(item)
            return _to_dict(item)

    @staticmethod
    def delete(payment_id: int) -> bool:
        with get_db() as session:
            item = session.get(Payment, payment_id)
            if not item:
                return False
            session.delete(item)
            session.commit()
            return True

    @staticmethod
    def list_all() -> list[dict]:
        with get_db() as session:
            items = session.query(Payment).order_by(Payment.date.desc()).all()
            return [_to_dict(p) for p in items]
