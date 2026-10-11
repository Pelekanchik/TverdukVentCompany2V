"""Репозиторій складу (v2.9): залишки та рухи матеріалів."""

from __future__ import annotations

from datetime import date

from ventilation_company.database.db import get_db
from ventilation_company.database.models.warehouse import WarehouseItem, WarehouseMove


def _to_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _item_to_dict(item: WarehouseItem) -> dict:
    quantity = float(item.quantity or 0)
    reserved = float(getattr(item, "reserved", 0) or 0)
    return {
        "id": item.id,
        "name": item.name,
        "unit": item.unit or "шт",
        "quantity": quantity,
        "min_quantity": float(item.min_quantity or 0),
        "reserved": reserved,
        "available": max(quantity - reserved, 0.0),
        "low": quantity <= float(item.min_quantity or 0) and float(item.min_quantity or 0) > 0,
    }


def _move_to_dict(move: WarehouseMove, item_name: str = "") -> dict:
    return {
        "id": move.id,
        "item_id": move.item_id,
        "item_name": item_name,
        "move_date": move.move_date.isoformat() if move.move_date else "",
        "quantity": float(move.quantity or 0),
        "kind": move.kind or "in",
        "project_id": move.project_id,
        "note": move.note or "",
    }


class WarehouseRepository:
    """CRUD для складу. Рухи коригують залишок позиції."""

    # ── Позиції ──

    @staticmethod
    def list_items() -> list[dict]:
        with get_db() as session:
            items = session.query(WarehouseItem).order_by(WarehouseItem.name).all()
            return [_item_to_dict(i) for i in items]

    @staticmethod
    def create_item(name: str, unit: str = "шт", min_quantity: float = 0) -> dict:
        with get_db() as session:
            item = WarehouseItem(name=name, unit=unit or "шт", min_quantity=min_quantity)
            session.add(item)
            session.flush()
            session.refresh(item)
            session.commit()
            return _item_to_dict(item)

    @staticmethod
    def update_item(item_id: int, data: dict) -> bool:
        with get_db() as session:
            item = session.query(WarehouseItem).filter(WarehouseItem.id == item_id).first()
            if not item:
                return False
            for key in ("name", "unit", "min_quantity"):
                if key in data:
                    setattr(item, key, data[key])
            session.commit()
            return True

    @staticmethod
    def delete_item(item_id: int) -> bool:
        with get_db() as session:
            item = session.query(WarehouseItem).filter(WarehouseItem.id == item_id).first()
            if not item:
                return False
            session.delete(item)
            session.commit()
            return True

    @staticmethod
    def low_stock() -> list[dict]:
        """Позиції на межі (залишок ≤ мінімального)."""
        return [i for i in WarehouseRepository.list_items() if i["low"]]

    @staticmethod
    def reserve(item_id: int, quantity: float) -> dict | None:
        """Зарезервувати кількість під виробництво (доступно = залишок − резерв).

        Не можна зарезервувати більше, ніж доступно. Повертає оновлену
        позицію або None, якщо позицію не знайдено.
        """
        if quantity <= 0:
            raise ValueError("Кількість має бути більшою за нуль")
        with get_db() as session:
            item = session.query(WarehouseItem).filter(WarehouseItem.id == item_id).first()
            if not item:
                return None
            available = float(item.quantity or 0) - float(getattr(item, "reserved", 0) or 0)
            if quantity > available:
                raise ValueError(
                    f"Доступно лише {available:g} {item.unit or 'шт'} позиції «{item.name}»"
                )
            item.reserved = float(getattr(item, "reserved", 0) or 0) + quantity
            session.commit()
            return _item_to_dict(item)

    @staticmethod
    def release(item_id: int, quantity: float) -> dict | None:
        """Зняти резерв (повернути в доступний залишок)."""
        if quantity <= 0:
            raise ValueError("Кількість має бути більшою за нуль")
        with get_db() as session:
            item = session.query(WarehouseItem).filter(WarehouseItem.id == item_id).first()
            if not item:
                return None
            item.reserved = max(float(getattr(item, "reserved", 0) or 0) - quantity, 0.0)
            session.commit()
            return _item_to_dict(item)

    # ── Рухи ──

    @staticmethod
    def add_move(
        item_id: int,
        quantity: float,
        kind: str,
        move_date=None,
        project_id: int | None = None,
        note: str = "",
    ) -> dict | None:
        """Додати рух і скоригувати залишок. Повертає None, якщо позицію не знайдено."""
        if quantity <= 0:
            raise ValueError("Кількість має бути більшою за нуль")
        with get_db() as session:
            item = session.query(WarehouseItem).filter(WarehouseItem.id == item_id).first()
            if not item:
                return None
            move = WarehouseMove(
                item_id=item_id,
                move_date=_to_date(move_date or date.today()),
                quantity=quantity,
                kind="out" if kind == "out" else "in",
                project_id=project_id,
                note=note or "",
            )
            delta = -quantity if move.kind == "out" else quantity
            item.quantity = float(item.quantity or 0) + delta
            # списання зі складу погашає резерв цієї позиції
            if move.kind == "out" and float(getattr(item, "reserved", 0) or 0) > 0:
                item.reserved = max(float(item.reserved or 0) - quantity, 0.0)
            session.add(move)
            session.flush()
            session.refresh(move)
            session.commit()
            return _move_to_dict(move, item.name)

    @staticmethod
    def list_moves(item_id: int | None = None, limit: int = 200) -> list[dict]:
        with get_db() as session:
            query = session.query(WarehouseMove, WarehouseItem.name).join(
                WarehouseItem, WarehouseItem.id == WarehouseMove.item_id
            )
            if item_id is not None:
                query = query.filter(WarehouseMove.item_id == item_id)
            rows = (
                query.order_by(WarehouseMove.move_date.desc(), WarehouseMove.id.desc())
                .limit(limit)
                .all()
            )
            return [_move_to_dict(m, name) for m, name in rows]
