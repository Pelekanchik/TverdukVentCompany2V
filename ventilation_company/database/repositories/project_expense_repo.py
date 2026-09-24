"""Репозиторій для витрат проєкту (ProjectExpense) — v2.3."""

from ventilation_company.database.db import get_db
from ventilation_company.database.models.project import ProjectExpense


def _expense_to_dict(expense: ProjectExpense) -> dict:
    return {
        "id": expense.id,
        "project_id": expense.project_id,
        "expense_name": expense.expense_name or "—",
        "quantity": float(expense.quantity or 1),
        "unit": expense.unit or "шт",
        "unit_price": float(expense.unit_price or 0),
        "total_price": float(expense.total_price or 0),
        "direction": getattr(expense, "direction", None) or "minus",
        "created_at": str(expense.created_at)[:16] if expense.created_at else "—",
    }


class ProjectExpenseRepository:
    @staticmethod
    def get_all(project_id: int) -> list[dict]:
        with get_db() as session:
            items = (
                session.query(ProjectExpense)
                .filter(ProjectExpense.project_id == project_id)
                .order_by(ProjectExpense.id)
                .all()
            )
            return [_expense_to_dict(i) for i in items]

    @staticmethod
    def create(data: dict) -> dict:
        with get_db() as session:
            qty = data.get("quantity", 1)
            unit_price = data.get("unit_price", 0)
            expense = ProjectExpense(
                project_id=data["project_id"],
                expense_name=data.get("expense_name", ""),
                quantity=qty,
                unit=data.get("unit", "шт"),
                unit_price=unit_price,
                total_price=qty * unit_price,
                direction=data.get("direction") or "minus",
            )
            session.add(expense)
            session.flush()
            session.refresh(expense)
            session.commit()
            return _expense_to_dict(expense)

    @staticmethod
    def update(expense_id: int, data: dict) -> bool:
        with get_db() as session:
            expense = session.query(ProjectExpense).filter(ProjectExpense.id == expense_id).first()
            if not expense:
                return False
            for key, value in data.items():
                if hasattr(expense, key):
                    setattr(expense, key, value)
            expense.total_price = (expense.quantity or 1) * (expense.unit_price or 0)
            session.commit()
            return True

    @staticmethod
    def delete(expense_id: int) -> bool:
        with get_db() as session:
            expense = session.query(ProjectExpense).filter(ProjectExpense.id == expense_id).first()
            if not expense:
                return False
            session.delete(expense)
            session.commit()
            return True
