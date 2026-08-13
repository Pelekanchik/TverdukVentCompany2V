"""Планувальник виробництва — розбивка на операції та розподіл по обладнанню."""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from ventilation_company.production_models import (
    DEFAULT_EQUIPMENT,
    DEFAULT_NORMS,
    Equipment,
    OperationNorm,
    OperationStatus,
    OperationType,
    ProductionPlan,
    ScheduledOperation,
)


class ProductionScheduler:
    """Алгоритм планування виробництва з урахуванням обладнання та залежностей."""

    # Послідовність операцій для кожного типу виробу
    OPERATION_SEQUENCE = {
        "default": [
            OperationType.CUTTING,
            OperationType.BENDING,
            OperationType.WELDING,
            OperationType.PAINTING,
            OperationType.ASSEMBLY,
            OperationType.PACKING,
        ],
        "round_duct": [
            OperationType.CUTTING,
            OperationType.BENDING,
            OperationType.WELDING,
            OperationType.PAINTING,
            OperationType.PACKING,
        ],
        "rect_duct": [
            OperationType.CUTTING,
            OperationType.BENDING,
            OperationType.WELDING,
            OperationType.PAINTING,
            OperationType.ASSEMBLY,
            OperationType.PACKING,
        ],
        "flange": [
            OperationType.CUTTING,
            OperationType.BENDING,
            OperationType.PAINTING,
            OperationType.PACKING,
        ],
        "elbow": [
            OperationType.CUTTING,
            OperationType.BENDING,
            OperationType.WELDING,
            OperationType.PAINTING,
            OperationType.PACKING,
        ],
        "tee": [
            OperationType.CUTTING,
            OperationType.BENDING,
            OperationType.WELDING,
            OperationType.PAINTING,
            OperationType.PACKING,
        ],
        "transition": [
            OperationType.CUTTING,
            OperationType.BENDING,
            OperationType.WELDING,
            OperationType.PAINTING,
            OperationType.PACKING,
        ],
        "cap": [
            OperationType.CUTTING,
            OperationType.BENDING,
            OperationType.WELDING,
            OperationType.PAINTING,
            OperationType.PACKING,
        ],
        "flexible": [
            OperationType.ASSEMBLY,
            OperationType.PACKING,
        ],
    }

    def __init__(
        self,
        equipment: Optional[list[Equipment]] = None,
        norms: Optional[dict[OperationType, OperationNorm]] = None,
    ):
        self.equipment = equipment or DEFAULT_EQUIPMENT.copy()
        self.norms = norms or DEFAULT_NORMS.copy()
        self._equipment_busy_until: dict[str, datetime] = {}

    def _get_sequence(self, product_type: str) -> list[OperationType]:
        """Отримати послідовність операцій для типу виробу."""
        pt = product_type.lower().strip()
        for key in self.OPERATION_SEQUENCE:
            if key in pt:
                return self.OPERATION_SEQUENCE[key]
        return self.OPERATION_SEQUENCE["default"]

    def _find_equipment(self, op_type: OperationType, after: datetime) -> Optional[Equipment]:
        """Знайти вільне обладнання для операції після заданого часу."""
        candidates = [e for e in self.equipment if op_type in e.operation_types and e.is_active]
        if not candidates:
            return None

        # Сортуємо: спочатку те, що звільниться раніше
        candidates.sort(key=lambda e: self._equipment_busy_until.get(e.id, after))
        return candidates[0]

    def _calc_duration(
        self, op_type: OperationType, area_m2: float, quantity: int
    ) -> float:
        """Розрахувати тривалість операції в хвилинах."""
        norm = self.norms.get(op_type)
        if norm is None:
            return 30.0  # default

        duration = norm.setup_time
        if norm.time_per_m2 > 0 and area_m2 > 0:
            duration += norm.time_per_m2 * area_m2 * quantity
        if norm.time_per_piece > 0:
            duration += norm.time_per_piece * quantity
        return max(duration, 5.0)  # мінімум 5 хв

    def _next_work_time(self, dt: datetime, equipment: Equipment) -> datetime:
        """Знайти наступний робочий момент (враховує зміну)."""
        # Якщо зараз поза зміною — переносимо на початок наступної зміни
        if dt.hour < equipment.shift_start:
            return dt.replace(hour=equipment.shift_start, minute=0, second=0, microsecond=0)
        if dt.hour >= equipment.shift_end:
            next_day = dt + timedelta(days=1)
            return next_day.replace(hour=equipment.shift_start, minute=0, second=0, microsecond=0)
        return dt

    def _advance_time(self, start: datetime, duration_min: float) -> datetime:
        """Додати робочий час (пропускаємо неробочі години)."""
        hours = duration_min / 60.0
        end = start + timedelta(hours=hours)
        # Проста реалізація: якщо вийшли за зміну — переносимо
        if end.hour >= 17:
            remaining = (end.hour - 17) + end.minute / 60.0
            next_day = end + timedelta(days=1)
            end = next_day.replace(hour=8, minute=0) + timedelta(hours=remaining)
        return end

    def schedule_project(
        self,
        project_name: str,
        products: list[dict],
        start_date: Optional[datetime] = None,
        deadline: Optional[datetime] = None,
    ) -> ProductionPlan:
        """Запланувати виробництво проєкту."""
        start_date = start_date or datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        plan = ProductionPlan(
            project_name=project_name,
            start_date=start_date,
            deadline=deadline,
        )

        self._equipment_busy_until = {}

        for product in products:
            name = product.get("name", "Виріб")
            ptype = product.get("product_type", "default")
            qty = int(product.get("quantity", 1))
            area = float(product.get("area_m2", 0.5))

            sequence = self._get_sequence(ptype)
            prev_op_id = None
            prev_end = start_date

            for op_type in sequence:
                eq = self._find_equipment(op_type, prev_end)
                if eq is None:
                    continue

                # Час початку = max(коли звільниться обладнання, коли закінчиться попередня операція)
                eq_free = self._equipment_busy_until.get(eq.id, start_date)
                op_start = max(prev_end, eq_free)
                op_start = self._next_work_time(op_start, eq)

                duration = self._calc_duration(op_type, area, qty)
                op_end = self._advance_time(op_start, duration)

                op_id = f"{uuid.uuid4().hex[:8]}"
                op = ScheduledOperation(
                    id=op_id,
                    product_name=name,
                    product_type=ptype,
                    operation_type=op_type,
                    equipment=eq,
                    start_time=op_start,
                    end_time=op_end,
                    duration_minutes=duration,
                    status=OperationStatus.PLANNED,
                    depends_on=prev_op_id,
                )
                plan.operations.append(op)

                self._equipment_busy_until[eq.id] = op_end
                prev_op_id = op_id
                prev_end = op_end

        return plan

    def reschedule_with_priority(
        self,
        plan: ProductionPlan,
        priority_product: str,
    ) -> ProductionPlan:
        """Перепланувати з пріоритетом для конкретного виробу."""
        # Проста реалізація: переносимо операції priority_product на початок
        priority_ops = [o for o in plan.operations if o.product_name == priority_product]
        other_ops = [o for o in plan.operations if o.product_name != priority_product]

        # Переплановуємо priority_ops з початкової дати
        new_plan = ProductionPlan(
            project_name=plan.project_name,
            start_date=plan.start_date,
            deadline=plan.deadline,
        )

        self._equipment_busy_until = {}
        for op in priority_ops + other_ops:
            eq = op.equipment
            eq_free = self._equipment_busy_until.get(eq.id, plan.start_date)
            op_start = max(op.start_time, eq_free)
            op_start = self._next_work_time(op_start, eq)
            op_end = self._advance_time(op_start, op.duration_minutes)

            op.start_time = op_start
            op.end_time = op_end
            self._equipment_busy_until[eq.id] = op_end
            new_plan.operations.append(op)

        return new_plan
