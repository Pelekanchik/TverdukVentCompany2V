"""Коло / дуга."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List
import math

from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.core.bounds import Bounds
from ventilation_company.project3d_editor.scene.entity import Entity, EntityType


@dataclass
class CircleEntity(Entity):
    """Коло або дуга."""
    center: Point2D = field(default_factory=lambda: Point2D(0, 0))
    radius: float = 100.0
    start_angle: float = 0.0   # для дуги
    end_angle: float = 360.0   # для дуги
    filled: bool = False
    fill_color: str = "#cccccc"
    fill_alpha: float = 0.3

    @property
    def entity_type(self) -> EntityType:
        return EntityType.CIRCLE

    def get_bounds(self) -> Bounds:
        return Bounds(
            self.center.x - self.radius,
            self.center.y - self.radius,
            self.center.x + self.radius,
            self.center.y + self.radius,
        )

    def get_points(self) -> List[Point2D]:
        pts = [self.center]
        if self.is_arc():
            steps = max(8, int(abs(self.end_angle - self.start_angle) / 10))
            for i in range(steps + 1):
                a = math.radians(self.start_angle + (self.end_angle - self.start_angle) * i / steps)
                pts.append(self.center + Point2D(math.cos(a) * self.radius, math.sin(a) * self.radius))
        return pts

    def is_arc(self) -> bool:
        return abs(self.end_angle - self.start_angle) < 360

    def is_hit(self, point: Point2D, tolerance: float = 5.0) -> bool:
        dist = point.distance_to(self.center)
        if self.is_arc():
            # Для дуги також перевіряємо кут
            angle = math.degrees(math.atan2(point.y - self.center.y, point.x - self.center.x))
            # Нормалізація кута
            while angle < self.start_angle:
                angle += 360
            while angle > self.start_angle + 360:
                angle -= 360
            if not (self.start_angle <= angle <= self.end_angle):
                return False
        return abs(dist - self.radius) <= tolerance

    def move(self, delta: Point2D) -> None:
        self.center = self.center + delta

    def clone(self) -> CircleEntity:
        e = CircleEntity(
            name=self.name,
            layer_id=self.layer_id,
            color=self.color,
            line_width=self.line_width,
            center=self.center,
            radius=self.radius,
            start_angle=self.start_angle,
            end_angle=self.end_angle,
            filled=self.filled,
            fill_color=self.fill_color,
            fill_alpha=self.fill_alpha,
        )
        e.tags = dict(self.tags)
        return e

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "center": self.center.to_tuple(),
            "radius": self.radius,
            "start_angle": self.start_angle,
            "end_angle": self.end_angle,
            "filled": self.filled,
            "fill_color": self.fill_color,
            "fill_alpha": self.fill_alpha,
        })
        return d
