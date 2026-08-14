"""Обладнання вентиляції (вентилятор, рекуператор, калорифер тощо)."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List

from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.core.bounds import Bounds
from ventilation_company.project3d_editor.scene.entity import Entity, EntityType


@dataclass
class EquipmentEntity(Entity):
    """Обладнання вентиляційної системи."""
    position: Point2D = field(default_factory=lambda: Point2D(0, 0))
    width: float = 500.0   # мм
    height: float = 500.0  # мм
    depth: float = 500.0   # мм (3D)
    rotation: float = 0.0  # градуси
    equipment_type: str = "вентилятор"  # вентилятор, рекуператор, калорифер, фільтр, глушник
    air_flow: float = 0.0   # м³/год
    pressure: float = 0.0   # Па
    power: float = 0.0      # кВт
    noise_level: float = 0.0  # дБ
    z_position: float = 2500.0  # мм

    @property
    def entity_type(self) -> EntityType:
        return EntityType.EQUIPMENT

    def get_bounds(self) -> Bounds:
        import math
        rad = math.radians(self.rotation)
        cos_r, sin_r = math.cos(rad), math.sin(rad)
        # Обчислюємо bounds повернутого прямокутника
        corners = self.get_corners()
        return Bounds.from_points(corners)

    def get_points(self) -> List[Point2D]:
        return [self.position]

    def get_corners(self) -> List[Point2D]:
        import math
        rad = math.radians(self.rotation)
        cos_r, sin_r = math.cos(rad), math.sin(rad)
        w, h = self.width, self.height
        local = [
            Point2D(-w/2, -h/2),
            Point2D(w/2, -h/2),
            Point2D(w/2, h/2),
            Point2D(-w/2, h/2),
        ]
        return [self.position + Point2D(p.x * cos_r - p.y * sin_r, p.x * sin_r + p.y * cos_r) for p in local]

    def is_hit(self, point: Point2D, tolerance: float = 5.0) -> bool:
        # Перевірка попадання в повернутий прямокутник
        import math
        rad = math.radians(-self.rotation)
        cos_r, sin_r = math.cos(rad), math.sin(rad)
        dx = point.x - self.position.x
        dy = point.y - self.position.y
        lx = dx * cos_r - dy * sin_r
        ly = dx * sin_r + dy * cos_r
        return (-self.width/2 - tolerance <= lx <= self.width/2 + tolerance and
                -self.height/2 - tolerance <= ly <= self.height/2 + tolerance)

    def move(self, delta: Point2D) -> None:
        self.position = self.position + delta

    def clone(self) -> EquipmentEntity:
        e = EquipmentEntity(
            name=self.name,
            layer_id=self.layer_id,
            color=self.color,
            line_width=self.line_width,
            position=self.position,
            width=self.width,
            height=self.height,
            depth=self.depth,
            rotation=self.rotation,
            equipment_type=self.equipment_type,
            air_flow=self.air_flow,
            pressure=self.pressure,
            power=self.power,
            noise_level=self.noise_level,
            z_position=self.z_position,
        )
        e.tags = dict(self.tags)
        return e

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "position": self.position.to_tuple(),
            "width": self.width,
            "height": self.height,
            "depth": self.depth,
            "rotation": self.rotation,
            "equipment_type": self.equipment_type,
            "air_flow": self.air_flow,
            "pressure": self.pressure,
            "power": self.power,
            "noise_level": self.noise_level,
            "z_position": self.z_position,
        })
        return d
