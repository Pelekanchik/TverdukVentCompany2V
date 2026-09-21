"""Payment repository for CRM."""

from __future__ import annotations

from ventilation_company.database.db import get_db
from ventilation_company.database.models.unified import Payment


def _to_dict(item: Payment) -> dict:
    return {
        "id": item.id,
        "client_id": item.client_id,
        "amount": item.amount,
        "payment_date": item.payment_date,
        "method": item.method,
        "status": item.status,
        "notes": item.notes,
        "created_by": item.created_by,
    }


class PaymentRepository:
    @staticmethod
    def list_by_client(client_id: int) -> list[dict]:
        with get_db() as session:
            items = (
                session.query(Payment)
                .filter(Payment.client_id == client_id)
                .order_by(Payment.payment_date.desc())
                .all()
            )
            return [_to_dict(p) for p in items]

    @staticmethod
    def create(data: dict) -> dict:
        with get_db() as session:
            item = Payment(
                client_id=data["client_id"],
                amount=data.get("amount"),
                payment_date=data.get("payment_date"),
                method=data.get("method"),
                status=data.get("status") or "Очікується",
                notes=data.get("notes"),
                created_by=data.get("created_by"),
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return _to_dict(item)
