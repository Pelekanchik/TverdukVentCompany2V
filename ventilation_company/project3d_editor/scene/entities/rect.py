"""Прямокутник."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List

from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.core.bounds import Bounds
from ventilation_company.project3d_editor.scene.entity import Entity, EntityType


@dataclass
class RectEntity(Entity):
    """Прямокутник (кут + розміри або 2 кути)."""
    corner: Point2D = field(default_factory=lambda: Point2D(0, 0))
    width: float = 100.0
    height: float = 100.0
    rotation: float = 0.0  # градуси
    filled: bool = False
    fill_color: str = "#cccccc"
    fill_alpha: float = 0.3

    @property
    def entity_type(self) -> EntityType:
        return EntityType.RECTANGLE

    def get_bounds(self) -> Bounds:
        pts = self.get_corners()
        return Bounds.from_points(pts)

    def get_points(self) -> List[Point2D]:
        return self.get_corners()

    def get_corners(self) -> List[Point2D]:
        import math
        rad = math.radians(self.rotation)
        cos_r, sin_r = math.cos(rad), math.sin(rad)
        w, h = self.width, self.height
        local = [
            Point2D(0, 0),
            Point2D(w, 0),
            Point2D(w, h),
            Point2D(0, h),
        ]
        result = []
        for p in local:
            rx = p.x * cos_r - p.y * sin_r
            ry = p.x * sin_r + p.y * cos_r
            result.append(self.corner + Point2D(rx, ry))
        return result

    def center(self) -> Point2D:
        import math
        rad = math.radians(self.rotation)
        cx = self.width / 2
        cy = self.height / 2
        rx = cx * math.cos(rad) - cy * math.sin(rad)
        ry = cx * math.sin(rad) + cy * math.cos(rad)
        return self.corner + Point2D(rx, ry)

    def is_hit(self, point: Point2D, tolerance: float = 5.0) -> bool:
        # Перевірка попадання в прямокутник (з урахуванням повороту)
        # Трансформуємо точку в локальну систему координат прямокутника
        import math
        rad = math.radians(-self.rotation)
        cos_r, sin_r = math.cos(rad), math.sin(rad)
        dx = point.x - self.corner.x
        dy = point.y - self.corner.y
        lx = dx * cos_r - dy * sin_r
        ly = dx * sin_r + dy * cos_r
        return (-tolerance <= lx <= self.width + tolerance and
                -tolerance <= ly <= self.height + tolerance)

    def move(self, delta: Point2D) -> None:
        self.corner = self.corner + delta

    def clone(self) -> RectEntity:
        e = RectEntity(
            name=self.name,
            layer_id=self.layer_id,
            color=self.color,
            line_width=self.line_width,
            corner=self.corner,
            width=self.width,
            height=self.height,
            rotation=self.rotation,
            filled=self.filled,
            fill_color=self.fill_color,
            fill_alpha=self.fill_alpha,
        )
        e.tags = dict(self.tags)
        return e

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "corner": self.corner.to_tuple(),
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "filled": self.filled,
            "fill_color": self.fill_color,
            "fill_alpha": self.fill_alpha,
        })
        return d
