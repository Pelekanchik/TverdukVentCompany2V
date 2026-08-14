"""Архітектурна стіна."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List
import math

from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.core.bounds import Bounds
from ventilation_company.project3d_editor.scene.entity import Entity, EntityType


@dataclass
class WallEntity(Entity):
    """Архітектурна стіна з товщиною."""
    start: Point2D = field(default_factory=lambda: Point2D(0, 0))
    end: Point2D = field(default_factory=lambda: Point2D(1000, 0))
    height: float = 3000.0  # мм
    thickness: float = 200.0  # мм
    is_load_bearing: bool = False
    material: str = "Цегла"

    @property
    def entity_type(self) -> EntityType:
        return EntityType.WALL

    def get_bounds(self) -> Bounds:
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        length = math.hypot(dx, dy)
        if length == 0:
            return Bounds.from_points([self.start])
        nx, ny = dx / length, dy / length
        px, py = -ny * self.thickness / 2, nx * self.thickness / 2
        pts = [
            self.start + Point2D(px, py),
            self.start - Point2D(px, py),
            self.end - Point2D(px, py),
            self.end + Point2D(px, py),
        ]
        return Bounds.from_points(pts)

    def get_points(self) -> List[Point2D]:
        return [self.start, self.end]

    def get_polygon(self) -> List[Point2D]:
        """Повернути 4 точки полігону стіни."""
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        length = math.hypot(dx, dy)
        if length == 0:
            return [self.start] * 4
        nx, ny = dx / length, dy / length
        px, py = -ny * self.thickness / 2, nx * self.thickness / 2
        return [
            self.start + Point2D(px, py),
            self.start - Point2D(px, py),
            self.end - Point2D(px, py),
            self.end + Point2D(px, py),
        ]

    def is_hit(self, point: Point2D, tolerance: float = 5.0) -> bool:
        bounds = self.get_bounds()
        if bounds.is_empty():
            return self.start.distance_to(point) <= tolerance
        if not bounds.expand_by(tolerance).contains(point):
            return False
        return point.distance_to_segment(self.start, self.end) <= (self.thickness / 2 + tolerance)

    def move(self, delta: Point2D) -> None:
        self.start = self.start + delta
        self.end = self.end + delta

    def length(self) -> float:
        return self.start.distance_to(self.end)

    def clone(self) -> WallEntity:
        e = WallEntity(
            name=self.name,
            layer_id=self.layer_id,
            color=self.color,
            line_width=self.line_width,
            start=self.start,
            end=self.end,
            height=self.height,
            thickness=self.thickness,
            is_load_bearing=self.is_load_bearing,
            material=self.material,
        )
        e.tags = dict(self.tags)
        return e

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "start": self.start.to_tuple(),
            "end": self.end.to_tuple(),
            "height": self.height,
            "thickness": self.thickness,
            "is_load_bearing": self.is_load_bearing,
            "material": self.material,
        })
        return d
