"""ORM-репозиторій для роботи з розрахунками (КП)."""

from sqlalchemy.orm import Session

from ventilation_company.database.db import SessionLocal
from ventilation_company.database.models.calc import CalcCalculation, CalcItem


class CalculationRepository:
    """CRUD для calc_calculations, calc_items через ORM."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_calculations(self) -> list[CalcCalculation]:
        return self.db.query(CalcCalculation).order_by(CalcCalculation.created_at.desc()).all()

    def get_calculation_by_id(self, calc_id: int) -> CalcCalculation | None:
        return self.db.query(CalcCalculation).filter(CalcCalculation.id == calc_id).first()

    def get_calculations_by_client(self, client_name: str) -> list[CalcCalculation]:
        return (
            self.db.query(CalcCalculation)
            .filter(CalcCalculation.client_name.ilike(f"%{client_name}%"))
            .order_by(CalcCalculation.created_at.desc())
            .all()
        )

    def add_calculation(
        self,
        client_name: str,
        client_phone: str = "",
        markup_percent: float = 30.0,
        overhead_percent: float = 15.0,
        **kwargs,
    ) -> CalcCalculation:
        from datetime import datetime

        calc = CalcCalculation(
            client_name=client_name,
            client_phone=client_phone,
            markup_percent=markup_percent,
            overhead_percent=overhead_percent,
            created_at=datetime.now().isoformat(),
            **kwargs,
        )
        self.db.add(calc)
        self.db.commit()
        self.db.refresh(calc)
        return calc

    def update_calculation(self, calc_id: int, **kwargs) -> CalcCalculation | None:
        calc = self.get_calculation_by_id(calc_id)
        if not calc:
            return None
        allowed = {
            "client_name",
            "client_phone",
            "markup_percent",
            "overhead_percent",
            "labor_mode",
            "total_cost",
            "sale_price",
            "status",
        }
        for k, v in kwargs.items():
            if k in allowed and hasattr(calc, k):
                setattr(calc, k, v)
        from datetime import datetime

        calc.created_at = datetime.now().isoformat()  # або updated_at, якщо є
        self.db.commit()
        self.db.refresh(calc)
        return calc

    def delete_calculation(self, calc_id: int) -> bool:
        calc = self.get_calculation_by_id(calc_id)
        if not calc:
            return False
        self.db.delete(calc)
        self.db.commit()
        return True

    # ── calc_items ──
    def get_items_by_calculation(self, calc_id: int) -> list[CalcItem]:
        return self.db.query(CalcItem).filter(CalcItem.calculation_id == calc_id).all()

    def add_item(self, calculation_id: int, **kwargs) -> CalcItem:
        item = CalcItem(calculation_id=calculation_id, **kwargs)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_item(self, item_id: int) -> bool:
        item = self.db.query(CalcItem).filter(CalcItem.id == item_id).first()
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        return True


# Зворотна сумісність
CalcRepo = CalculationRepository

CalcRepo = CalculationRepository(SessionLocal())
