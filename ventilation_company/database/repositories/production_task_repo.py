"""Репозиторій черги виробництва (ProductionTask).

CRUD + фільтрація за статусом. Завдання живуть у таблиці production_tasks,
створюються з виробів проєкту та ведуть цех від черги до готовності.
"""

from __future__ import annotations

from ventilation_company.database.db import get_db
from ventilation_company.database.models.production_task import ProductionTask
from ventilation_company.services.audit_service import log_action

# Порядок сортування пріоритетів (перший — найважливіший).
PRIORITY_ORDER = ["терміново", "високий", "звичайний", "низький"]

# Статуси життєвого циклу завдання.
TASK_STATUSES = ["в черзі", "в роботі", "готово"]


class ProductionTaskRepository:
    """CRUD для завдань виробництва."""

    @staticmethod
    def create(
        project_id: int,
        product_name: str,
        quantity: int = 1,
        priority: str = "звичайний",
        status: str = "в черзі",
        planned_start=None,
        planned_end=None,
        notes: str = "",
    ) -> dict:
        with get_db() as session:
            task = ProductionTask(
                project_id=project_id,
                product_name=product_name,
                quantity=quantity,
                priority=priority,
                status=status,
                planned_start=planned_start,
                planned_end=planned_end,
                notes=notes,
            )
            session.add(task)
            session.flush()
            session.refresh(task)
            session.commit()
            log_action(
                "production.create",
                entity_type="production_task",
                entity_id=task.id,
                details={
                    "project_id": task.project_id,
                    "product_name": task.product_name,
                    "quantity": task.quantity,
                    "priority": task.priority,
                },
            )
            return ProductionTaskRepository._to_dict(task)

    @staticmethod
    def get_all(status: str | None = None) -> list[dict]:
        """Усі завдання; опційно — лише з вказаним статусом."""
        with get_db() as session:
            q = session.query(ProductionTask)
            if status:
                q = q.filter(ProductionTask.status == status)
            tasks = q.all()
            return [ProductionTaskRepository._to_dict(t) for t in tasks]

    @staticmethod
    def get_by_project(project_id: int) -> list[dict]:
        with get_db() as session:
            tasks = (
                session.query(ProductionTask)
                .filter(ProductionTask.project_id == project_id)
                .order_by(ProductionTask.created_at.desc())
                .all()
            )
            return [ProductionTaskRepository._to_dict(t) for t in tasks]

    @staticmethod
    def update(
        task_id: int,
        status: str | None = None,
        priority: str | None = None,
        quantity: int | None = None,
        planned_start=None,
        planned_end=None,
        notes: str | None = None,
    ) -> dict | None:
        """Оновити поля завдання; повертає оновлений запис або None."""
        with get_db() as session:
            task = session.get(ProductionTask, task_id)
            if task is None:
                return None
            if status is not None:
                task.status = status
            if priority is not None:
                task.priority = priority
            if quantity is not None:
                task.quantity = quantity
            if planned_start is not None:
                task.planned_start = planned_start
            if planned_end is not None:
                task.planned_end = planned_end
            if notes is not None:
                task.notes = notes
            session.commit()
            log_action(
                "production.update",
                entity_type="production_task",
                entity_id=task.id,
                details={"status": task.status, "priority": task.priority},
            )
            return ProductionTaskRepository._to_dict(task)

    @staticmethod
    def delete(task_id: int) -> None:
        with get_db() as session:
            task = session.get(ProductionTask, task_id)
            if task:
                session.delete(task)
                session.commit()
                log_action(
                    "production.delete",
                    entity_type="production_task",
                    entity_id=task_id,
                    details={"product_name": task.product_name},
                )

    @staticmethod
    def _to_dict(task: ProductionTask) -> dict:
        return {
            "id": task.id,
            "project_id": task.project_id,
            "product_name": task.product_name,
            "quantity": task.quantity,
            "priority": task.priority,
            "status": task.status,
            "planned_start": task.planned_start,
            "planned_end": task.planned_end,
            "notes": task.notes,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }
