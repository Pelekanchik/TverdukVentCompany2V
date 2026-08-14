"""Базовий клас усіх сутностей сцени."""

from __future__ import annotations
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum, auto

from ventilation_company.project3d_editor.core.point import Point2D, Point3D
from ventilation_company.project3d_editor.core.bounds import Bounds


class EntityType(Enum):
    LINE = auto()
    WALL = auto()
    RECTANGLE = auto()
    CIRCLE = auto()
    ARC = auto()
    POLYGON = auto()
    DUCT_SEGMENT = auto()
    DUCT_FITTING = auto()
    EQUIPMENT = auto()
    TEXT = auto()
    DIMENSION = auto()
    GRID_LINE = auto()
    OPENING = auto()


@dataclass
class Entity(ABC):
    """Базовий клас будь-якого об'єкта на сцені."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    layer_id: str = "default"
    visible: bool = True
    locked: bool = False
    color: str = "#000000"
    line_width: float = 1.0
    line_type: str = "solid"  # solid, dashed, dotted, dashdot
    selected: bool = False
    tags: Dict[str, Any] = field(default_factory=dict)

    @property
    @abstractmethod
    def entity_type(self) -> EntityType:
        ...

    @abstractmethod
    def get_bounds(self) -> Bounds:
        """Повернути bounding box сутності."""
        ...

    @abstractmethod
    def get_points(self) -> List[Point2D]:
        """Повернути ключові точки для рендерингу/редагування."""
        ...

    def is_hit(self, point: Point2D, tolerance: float = 5.0) -> bool:
        """Чи попадає точка в сутність (з допуском у мм)."""
        # За замовчуванням — перевірка відстані до ключових точок або bounds
        bounds = self.get_bounds()
        if not bounds.is_empty():
            bounds.expand_by(tolerance)
            if not bounds.contains(point):
                return False
        # Перевірка відстані до точок
        for p in self.get_points():
            if p.distance_to(point) <= tolerance:
                return True
        return False

    def move(self, delta: Point2D) -> None:
        """Перемістити сутність на вектор delta."""
        pass  # Перевизначається в підкласах

    def clone(self) -> Entity:
        """Створити копію сутності."""
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        """Серіалізація."""
        return {
            "id": self.id,
            "name": self.name,
            "layer_id": self.layer_id,
            "visible": self.visible,
            "locked": self.locked,
            "color": self.color,
            "line_width": self.line_width,
            "line_type": self.line_type,
            "entity_type": self.entity_type.name,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Entity:
        raise NotImplementedError
