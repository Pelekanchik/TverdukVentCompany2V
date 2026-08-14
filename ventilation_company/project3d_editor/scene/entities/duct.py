"""Сегмент повітропроводу."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List
import math

from ventilation_company.project3d_editor.core.point import Point2D, Point3D
from ventilation_company.project3d_editor.core.bounds import Bounds
from ventilation_company.project3d_editor.scene.entity import Entity, EntityType


@dataclass
class DuctSegmentEntity(Entity):
    """Сегмент повітропроводу (2D/3D)."""
    start: Point2D = field(default_factory=lambda: Point2D(0, 0))
    end: Point2D = field(default_factory=lambda: Point2D(1000, 0))
    width: float = 200.0   # мм (діаметр для круглого)
    height: float = 200.0  # мм
    is_round: bool = False
    duct_type: str = "приплив"  # приплив, витяжка, димовидалення
    material: str = "оцинкована сталь"
    thickness: float = 0.7  # мм
    insulation: bool = False
    z_start: float = 2500.0  # мм
    z_end: float = 2500.0    # мм
    air_flow: float = 0.0    # м³/год
    velocity: float = 0.0    # м/с

    @property
    def entity_type(self) -> EntityType:
        return EntityType.DUCT_SEGMENT

    def get_bounds(self) -> Bounds:
        half = max(self.width, self.height) / 2
        return Bounds.from_points([
            Point2D(min(self.start.x, self.end.x) - half, min(self.start.y, self.end.y) - half),
            Point2D(max(self.start.x, self.end.x) + half, max(self.start.y, self.end.y) + half),
        ])

    def get_points(self) -> List[Point2D]:
        return [self.start, self.end]

    def length(self) -> float:
        return self.start.distance_to(self.end)

    def is_hit(self, point: Point2D, tolerance: float = 5.0) -> bool:
        # Перевірка попадання в сегмент з урахуванням профілю
        dist = point.distance_to_segment(self.start, self.end)
        half_profile = max(self.width, self.height) / 2
        return dist <= (half_profile + tolerance)

    def get_profile_at(self, t: float) -> List[Point2D]:
        """Отримати профіль перерізу в точці t (0..1) уздовж сегмента."""
        pos = self.start + (self.end - self.start) * t
        if self.is_round:
            # Повертаємо наближений полігон кола
            pts = []
            steps = 16
            r = self.width / 2
            for i in range(steps):
                a = 2 * math.pi * i / steps
                pts.append(pos + Point2D(math.cos(a) * r, math.sin(a) * r))
            return pts
        else:
            # Прямокутний профіль
            dx = self.end.x - self.start.x
            dy = self.end.y - self.start.y
            seg_len = math.hypot(dx, dy)
            if seg_len == 0:
                return [pos] * 4
            nx, ny = dx / seg_len, dy / seg_len
            px, py = -ny * self.width / 2, nx * self.height / 2
            return [
                pos + Point2D(px, py),
                pos - Point2D(px, py),
                pos - Point2D(px, py) + Point2D(nx * self.height, ny * self.height),
                pos + Point2D(px, py) + Point2D(nx * self.height, ny * self.height),
            ]

    def move(self, delta: Point2D) -> None:
        self.start = self.start + delta
        self.end = self.end + delta

    def get_system_color(self) -> str:
        t = self.duct_type.lower()
        if "витяж" in t or "exhaust" in t:
            return "#009900"
        if "дим" in t or "smoke" in t:
            return "#cc6600"
        return "#0066cc"  # приплив

    def clone(self) -> DuctSegmentEntity:
        e = DuctSegmentEntity(
            name=self.name,
            layer_id=self.layer_id,
            color=self.color,
            line_width=self.line_width,
            start=self.start,
            end=self.end,
            width=self.width,
            height=self.height,
            is_round=self.is_round,
            duct_type=self.duct_type,
            material=self.material,
            thickness=self.thickness,
            insulation=self.insulation,
            z_start=self.z_start,
            z_end=self.z_end,
            air_flow=self.air_flow,
            velocity=self.velocity,
        )
        e.tags = dict(self.tags)
        return e

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "start": self.start.to_tuple(),
            "end": self.end.to_tuple(),
            "width": self.width,
            "height": self.height,
            "is_round": self.is_round,
            "duct_type": self.duct_type,
            "material": self.material,
            "thickness": self.thickness,
            "insulation": self.insulation,
            "z_start": self.z_start,
            "z_end": self.z_end,
            "air_flow": self.air_flow,
            "velocity": self.velocity,
        })
        return d
