"""Фасонний виріб (відвід, трійник, перехід тощо)."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List
import math

from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.core.bounds import Bounds
from ventilation_company.project3d_editor.scene.entity import Entity, EntityType


@dataclass
class DuctFittingEntity(Entity):
    """Фасонний виріб повітропроводу."""
    position: Point2D = field(default_factory=lambda: Point2D(0, 0))
    fitting_type: str = "відвід"  # відвід, трійник, перехід, заглушка, фланець
    width_in: float = 200.0
    height_in: float = 200.0
    width_out: float = 200.0
    height_out: float = 200.0
    angle: float = 90.0  # градуси
    radius: float = 200.0  # радіус відводу
    rotation: float = 0.0  # орієнтація
    duct_type: str = "приплив"
    material: str = "оцинкована сталь"
    thickness: float = 0.7
    z_position: float = 2500.0

    @property
    def entity_type(self) -> EntityType:
        return EntityType.DUCT_FITTING

    def get_bounds(self) -> Bounds:
        size = max(self.width_in, self.height_in, self.width_out, self.height_out, self.radius) / 2 + 50
        return Bounds(
            self.position.x - size,
            self.position.y - size,
            self.position.x + size,
            self.position.y + size,
        )

    def get_points(self) -> List[Point2D]:
        return [self.position]

    def is_hit(self, point: Point2D, tolerance: float = 10.0) -> bool:
        return self.position.distance_to(point) <= (max(self.width_in, self.height_in) / 2 + tolerance)

    def move(self, delta: Point2D) -> None:
        self.position = self.position + delta

    def get_display_size(self) -> float:
        return max(self.width_in, self.height_in, 100) / 2

    def get_system_color(self) -> str:
        t = self.duct_type.lower()
        if "витяж" in t or "exhaust" in t:
            return "#009900"
        if "дим" in t or "smoke" in t:
            return "#cc6600"
        return "#0066cc"

    def clone(self) -> DuctFittingEntity:
        e = DuctFittingEntity(
            name=self.name,
            layer_id=self.layer_id,
            color=self.color,
            line_width=self.line_width,
            position=self.position,
            fitting_type=self.fitting_type,
            width_in=self.width_in,
            height_in=self.height_in,
            width_out=self.width_out,
            height_out=self.height_out,
            angle=self.angle,
            radius=self.radius,
            rotation=self.rotation,
            duct_type=self.duct_type,
            material=self.material,
            thickness=self.thickness,
            z_position=self.z_position,
        )
        e.tags = dict(self.tags)
        return e

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "position": self.position.to_tuple(),
            "fitting_type": self.fitting_type,
            "width_in": self.width_in,
            "height_in": self.height_in,
            "width_out": self.width_out,
            "height_out": self.height_out,
            "angle": self.angle,
            "radius": self.radius,
            "rotation": self.rotation,
            "duct_type": self.duct_type,
            "material": self.material,
            "thickness": self.thickness,
            "z_position": self.z_position,
        })
        return d
