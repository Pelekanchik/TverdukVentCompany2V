"""Моделі та норми часу для планування виробництва."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class OperationType(Enum):
    """Типи виробничих операцій."""
    CUTTING = "розкрій"
    BENDING = "гнуття"
    WELDING = "зварка"
    PAINTING = "фарбування"
    ASSEMBLY = "складання"
    PACKING = "упаковка"


class OperationStatus(Enum):
    """Статус операції."""
    PLANNED = "заплановано"
    IN_PROGRESS = "в роботі"
    COMPLETED = "виконано"
    DELAYED = "затримка"
    BLOCKED = "очікує"


@dataclass
class Equipment:
    """Одиниця обладнання."""
    id: str
    name: str
    operation_types: list[OperationType]
    capacity_per_hour: float  # м²/год або шт/год
    shift_start: int = 8       # година початку зміни
    shift_end: int = 17        # година кінця зміни
    is_active: bool = True


@dataclass
class OperationNorm:
    """Норма часу на операцію (хвилин на м² або на штуку)."""
    operation_type: OperationType
    time_per_m2: float = 0.0   # хв/м²
    time_per_piece: float = 0.0  # хв/шт
    setup_time: float = 10.0   # хв — наладка


# ── СТАНДАРТНІ НОРМИ ЧАСУ ──
DEFAULT_NORMS = {
    OperationType.CUTTING: OperationNorm(
        OperationType.CUTTING, time_per_m2=2.0, setup_time=15.0
    ),
    OperationType.BENDING: OperationNorm(
        OperationType.BENDING, time_per_m2=5.0, setup_time=10.0
    ),
    OperationType.WELDING: OperationNorm(
        OperationType.WELDING, time_per_m2=8.0, setup_time=20.0
    ),
    OperationType.PAINTING: OperationNorm(
        OperationType.PAINTING, time_per_m2=3.0, setup_time=30.0
    ),
    OperationType.ASSEMBLY: OperationNorm(
        OperationType.ASSEMBLY, time_per_piece=10.0, setup_time=5.0
    ),
    OperationType.PACKING: OperationNorm(
        OperationType.PACKING, time_per_piece=2.0, setup_time=5.0
    ),
}


# ── СТАНДАРТНЕ ОБЛАДНАННЯ ──
DEFAULT_EQUIPMENT = [
    Equipment("CUT_01", "Гільйотина", [OperationType.CUTTING], 30.0, 8, 17),
    Equipment("PLZ_01", "Плазмовий верстат", [OperationType.CUTTING], 20.0, 8, 17),
    Equipment("BND_01", "Верстат гнуття", [OperationType.BENDING], 12.0, 8, 17),
    Equipment("WLD_01", "Зварювальний пост", [OperationType.WELDING], 8.0, 8, 17),
    Equipment("WLD_02", "Зварювальний пост 2", [OperationType.WELDING], 8.0, 8, 17),
    Equipment("PNT_01", "Фарбувальна камера", [OperationType.PAINTING], 20.0, 8, 17),
    Equipment("ASM_01", "Складальний стіл", [OperationType.ASSEMBLY, OperationType.PACKING], 6.0, 8, 17),
]


@dataclass
class ScheduledOperation:
    """Одна запланована операція для конкретного виробу."""
    id: str
    product_name: str
    product_type: str
    operation_type: OperationType
    equipment: Equipment
    start_time: datetime
    end_time: datetime
    duration_minutes: float
    status: OperationStatus = OperationStatus.PLANNED
    depends_on: Optional[str] = None  # ID попередньої операції
    notes: str = ""

    @property
    def duration_hours(self) -> float:
        return self.duration_minutes / 60.0


@dataclass
class ProductionPlan:
    """Повний план виробництва проєкту."""
    project_name: str
    project_id: Optional[int] = None
    start_date: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    operations: list[ScheduledOperation] = field(default_factory=list)

    @property
    def total_operations(self) -> int:
        return len(self.operations)

    @property
    def completion_percent(self) -> float:
        if not self.operations:
            return 0.0
        completed = sum(1 for o in self.operations if o.status == OperationStatus.COMPLETED)
        return (completed / len(self.operations)) * 100

    @property
    def estimated_end(self) -> Optional[datetime]:
        if not self.operations:
            return None
        return max(o.end_time for o in self.operations)

    @property
    def is_on_time(self) -> bool:
        if self.deadline is None or self.estimated_end is None:
            return True
        return self.estimated_end <= self.deadline

    def get_equipment_load(self) -> dict[str, list[tuple[datetime, datetime]]]:
        """Розклад завантаження обладнання."""
        load = {}
        for op in self.operations:
            eq_id = op.equipment.id
            if eq_id not in load:
                load[eq_id] = []
            load[eq_id].append((op.start_time, op.end_time))
        return load
