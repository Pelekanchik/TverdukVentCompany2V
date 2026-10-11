"""Репозиторій історії закупівельних цін (v2.9)."""

from __future__ import annotations

from datetime import date

from ventilation_company.database.db import get_db
from ventilation_company.database.models.purchase import PurchasePrice


def _to_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _to_dict(row: PurchasePrice) -> dict:
    return {
        "id": row.id,
        "item_name": row.item_name,
        "supplier": row.supplier or "",
        "price": float(row.price or 0),
        "purchase_date": row.purchase_date.isoformat() if row.purchase_date else "",
        "project_id": row.project_id,
    }


class PurchasePriceRepository:
    """Запис та вибірка історії цін закупівель."""

    @staticmethod
    def record(
        item_name: str,
        price: float,
        supplier: str = "",
        purchase_date=None,
        project_id: int | None = None,
    ) -> dict:
        with get_db() as session:
            row = PurchasePrice(
                item_name=item_name.strip(),
                supplier=supplier.strip(),
                price=float(price),
                purchase_date=_to_date(purchase_date or date.today()),
                project_id=project_id,
            )
            session.add(row)
            session.flush()
            session.refresh(row)
            session.commit()
            return _to_dict(row)

    @staticmethod
    def latest_for(item_name: str, limit: int = 5) -> list[dict]:
        """Останні ціни за найменуванням (новіші першими)."""
        needle = (item_name or "").strip()
        if not needle:
            return []
        with get_db() as session:
            rows = (
                session.query(PurchasePrice)
                .filter(PurchasePrice.item_name == needle)
                .order_by(PurchasePrice.purchase_date.desc(), PurchasePrice.id.desc())
                .limit(limit)
                .all()
            )
            return [_to_dict(r) for r in rows]

    @staticmethod
    def best_price_for(item_name: str) -> float:
        """Мінімальна зафіксована ціна за найменуванням (0, якщо історії нема)."""
        history = PurchasePriceRepository.latest_for(item_name, limit=50)
        return min((h["price"] for h in history), default=0.0)
