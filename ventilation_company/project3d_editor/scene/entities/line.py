"""Лінія — базова сутність."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List

from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.core.bounds import Bounds
from ventilation_company.project3d_editor.scene.entity import Entity, EntityType


@dataclass
class LineEntity(Entity):
    """Відрізок прямої."""
    start: Point2D = field(default_factory=lambda: Point2D(0, 0))
    end: Point2D = field(default_factory=lambda: Point2D(100, 100))

    @property
    def entity_type(self) -> EntityType:
        return EntityType.LINE

    def get_bounds(self) -> Bounds:
        return Bounds.from_points([self.start, self.end])

    def get_points(self) -> List[Point2D]:
        return [self.start, self.end]

    def is_hit(self, point: Point2D, tolerance: float = 5.0) -> bool:
        return point.distance_to_segment(self.start, self.end) <= tolerance

    def move(self, delta: Point2D) -> None:
        self.start = self.start + delta
        self.end = self.end + delta

    def length(self) -> float:
        return self.start.distance_to(self.end)

    def angle(self) -> float:
        import math
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        return math.degrees(math.atan2(dy, dx))

    def midpoint(self) -> Point2D:
        return (self.start + self.end) / 2

    def clone(self) -> LineEntity:
        e = LineEntity(
            name=self.name,
            layer_id=self.layer_id,
            color=self.color,
            line_width=self.line_width,
            line_type=self.line_type,
            start=self.start,
            end=self.end,
        )
        e.tags = dict(self.tags)
        return e

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "start": self.start.to_tuple(),
            "end": self.end.to_tuple(),
        })
        return d
