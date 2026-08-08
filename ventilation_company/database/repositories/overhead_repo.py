"""ORM-репозиторій для роботи з накладними витратами."""

from sqlalchemy.orm import Session

from ventilation_company.database.db import SessionLocal
from ventilation_company.database.models.calc import OverheadItem


class OverheadRepository:
    """CRUD для overhead_items через ORM."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_items(self) -> list[OverheadItem]:
        return self.db.query(OverheadItem).order_by(OverheadItem.name).all()

    def get_active_items(self) -> list[OverheadItem]:
        return self.db.query(OverheadItem).filter(OverheadItem.is_active == 1).all()

    def get_item_by_id(self, item_id: int) -> OverheadItem | None:
        return self.db.query(OverheadItem).filter(OverheadItem.id == item_id).first()

    def add_item(
        self, name: str, item_type: str = "fixed", value: float = 0.0, **kwargs
    ) -> OverheadItem:
        item = OverheadItem(name=name, type=item_type, value=value, **kwargs)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_item(self, item_id: int, **kwargs) -> OverheadItem | None:
        item = self.get_item_by_id(item_id)
        if not item:
            return None
        allowed = {"name", "type", "value", "is_active"}
        for k, v in kwargs.items():
            if k in allowed and hasattr(item, k):
                setattr(item, k, v)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_item(self, item_id: int) -> bool:
        item = self.get_item_by_id(item_id)
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        return True

    def get_all(self) -> list[OverheadItem]:
        """Alias for get_all_items."""
        return self.get_all_items()


# Зворотна сумісність
OverheadRepo = OverheadRepository
OverheadRepo = OverheadRepository(SessionLocal())
