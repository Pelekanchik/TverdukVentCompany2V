"""Репозиторій для виробів (ProductItem) — v2.4.

Додано discounted_price в _item_to_dict.
"""

from typing import List

from ventilation_company.database.db import get_db
from ventilation_company.database.models.product_item import ProductItem


def _item_to_dict(item: ProductItem) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "product_type": item.product_type,
        "width": item.width,
        "height": item.height,
        "length": item.length,
        "thickness": item.thickness,
        "material": item.material,
        "quantity": item.quantity,
        "cost_price": float(item.cost_price) if item.cost_price else 0,
        "unit_price": float(item.unit_price) if item.unit_price else 0,
        "total_price": float(item.total_price) if item.total_price else 0,
        "discounted_price": float(item.discounted_price) if item.discounted_price else 0,  # ← v2.4
        "notes": item.notes,
        "project_id": item.project_id,
        "metal_area_m2": _extract_float(item.notes, "metal_area_m2"),
        "blank_area_m2": _extract_float(item.notes, "blank_area_m2"),
        "weight_kg": _extract_float(item.notes, "weight_kg"),
    }


def _extract_float(notes: str | None, key: str) -> float:
    if not notes:
        return 0.0
    try:
        import json

        data = json.loads(notes)
        val = data.get(key, 0)
        return float(val) if val else 0.0
    except (json.JSONDecodeError, ValueError, TypeError):
        return 0.0


class ProductRepository:
    @staticmethod
    def get_all(project_id: int = None) -> List[dict]:
        with get_db() as session:
            q = session.query(ProductItem)
            if project_id:
                q = q.filter(ProductItem.project_id == project_id)
            items = q.order_by(ProductItem.id.desc()).all()
            return [_item_to_dict(i) for i in items]

    @staticmethod
    def get_by_id(item_id: int) -> dict | None:
        with get_db() as session:
            item = session.query(ProductItem).filter(ProductItem.id == item_id).first()
            return _item_to_dict(item) if item else None

    @staticmethod
    def create(data: dict) -> dict:
        with get_db() as session:
            item = ProductItem(
                name=data["name"],
                product_type=data["product_type"],
                width=data.get("width"),
                height=data.get("height"),
                length=data.get("length"),
                thickness=data.get("thickness"),
                material=data.get("material"),
                quantity=data.get("quantity", 1),
                cost_price=data.get("cost_price", 0),
                unit_price=data.get("unit_price", 0),
                total_price=data.get("total_price", 0),
                discounted_price=data.get("discounted_price", 0),  # ← v2.4
                notes=data.get("notes"),
                project_id=data.get("project_id"),
            )
            session.add(item)
            session.flush()
            session.refresh(item)
            session.commit()
            return _item_to_dict(item)

    @staticmethod
    def update(item_id: int, data: dict) -> bool:
        with get_db() as session:
            item = session.query(ProductItem).filter(ProductItem.id == item_id).first()
            if not item:
                return False
            for key, value in data.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            session.commit()
            return True

    @staticmethod
    def delete(item_id: int) -> bool:
        with get_db() as session:
            item = session.query(ProductItem).filter(ProductItem.id == item_id).first()
            if not item:
                return False
            session.delete(item)
            session.commit()
            return True

    @staticmethod
    def search(
        query: str = "",
        product_type: str = "",
        material: str = "",
        thickness: str = "",
        project_id: int = None,
    ) -> List[dict]:
        with get_db() as session:
            q = session.query(ProductItem)
            if project_id:
                q = q.filter(ProductItem.project_id == project_id)
            if query:
                q = q.filter(ProductItem.name.ilike(f"%{query}%"))
            if product_type and product_type != "Всі":
                q = q.filter(ProductItem.product_type == product_type)
            if material and material != "Всі":
                q = q.filter(ProductItem.material == material)
            if thickness and thickness != "Всі":
                q = q.filter(ProductItem.thickness == float(thickness))
            items = q.order_by(ProductItem.id.desc()).all()
            return [_item_to_dict(i) for i in items]
