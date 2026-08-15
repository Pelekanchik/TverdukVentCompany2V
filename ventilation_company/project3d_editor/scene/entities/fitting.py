"""Фасонний виріб (відвід, трійник, перехід тощо)."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple
import math

from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.core.bounds import Bounds
from ventilation_company.project3d_editor.scene.entity import Entity, EntityType

@dataclass
class DuctFittingEntity(Entity):
    """Фасонний виріб повітропроводу."""
    position: Point2D = field(default_factory=lambda: Point2D(0, 0))
    fitting_type: str = "відвід"
    width_in: float = 200.0
    height_in: float = 200.0
    width_out: float = 200.0
    height_out: float = 200.0
    angle: float = 90.0
    radius: float = 200.0
    rotation: float = 0.0
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
            self.position.x - size, self.position.y - size,
            self.position.x + size, self.position.y + size,
        )

    def get_points(self) -> List[Point2D]:
        return [self.position]

    def get_connection_points(self) -> List[Tuple[Point2D, Point2D]]:
        """Точки підключення з напрямковими векторами (від точки назовні).

        Повертає: [(point, outward_direction), ...]
        """
        rad = math.radians(self.rotation)
        cos_r, sin_r = math.cos(rad), math.sin(rad)

        def rot(v: Point2D) -> Point2D:
            return Point2D(v.x * cos_r - v.y * sin_r, v.x * sin_r + v.y * cos_r)

        ft = self.fitting_type.lower()
        result = []

        if ft == "відвід":
            # Вхід знизу, вихід збоку (праворуч за замовчуванням)
            a = math.radians(self.angle)
            r = self.radius
            w_in = self.width_in
            h_in = self.height_in
            w_out = self.width_out if self.width_out > 0 else w_in
            h_out = self.height_out if self.height_out > 0 else h_in

            # Центр дуги
            arc_center = self.position + rot(Point2D(0, r))
            # Вхідна точка (знизу)
            inlet = arc_center + rot(Point2D(0, -r))
            # Вихідна точка (під кутом)
            outlet = arc_center + rot(Point2D(r * math.sin(a), -r * math.cos(a)))

            result.append((inlet, rot(Point2D(0, -1))))
            result.append((outlet, rot(Point2D(math.sin(a), math.cos(a)))))

        elif ft == "трійник":
            # Вхід знизу, вихід прямо + вбік
            w_in = self.width_in
            h_in = self.height_in
            w_out = self.width_out if self.width_out > 0 else w_in * 0.5
            h_out = self.height_out if self.height_out > 0 else h_in * 0.5

            inlet = self.position + rot(Point2D(0, h_in / 2))
            outlet_main = self.position + rot(Point2D(0, -h_in / 2))
            outlet_branch = self.position + rot(Point2D(w_out / 2 + w_in / 2, 0))

            result.append((inlet, rot(Point2D(0, 1))))
            result.append((outlet_main, rot(Point2D(0, -1))))
            result.append((outlet_branch, rot(Point2D(1, 0))))

        elif ft == "перехід":
            # Вхід знизу, вихід зверху (зміна розміру)
            h_in = self.height_in
            h_out = self.height_out
            result.append((self.position + rot(Point2D(0, h_in / 2)), rot(Point2D(0, 1))))
            result.append((self.position + rot(Point2D(0, -h_out / 2)), rot(Point2D(0, -1))))

        elif ft == "фланець":
            # Знизу і зверху
            h = max(self.height_in, self.height_out)
            result.append((self.position + rot(Point2D(0, h / 2)), rot(Point2D(0, 1))))
            result.append((self.position + rot(Point2D(0, -h / 2)), rot(Point2D(0, -1))))

        elif ft == "заглушка":
            # Тільки знизу
            result.append((self.position + rot(Point2D(0, self.height_in / 2)), rot(Point2D(0, 1))))

        else:
            result.append((self.position, rot(Point2D(0, 1))))

        return result

    def get_inlet_point(self) -> Tuple[Point2D, Point2D]:
        """Головна вхідна точка (point, outward_direction)."""
        pts = self.get_connection_points()
        return pts[0] if pts else (self.position, Point2D(0, 1))

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

    def clone(self) -> "DuctFittingEntity":
        e = DuctFittingEntity(
            name=self.name, layer_id=self.layer_id, color=self.color,
            line_width=self.line_width, position=self.position,
            fitting_type=self.fitting_type, width_in=self.width_in,
            height_in=self.height_in, width_out=self.width_out,
            height_out=self.height_out, angle=self.angle,
            radius=self.radius, rotation=self.rotation,
            duct_type=self.duct_type, material=self.material,
            thickness=self.thickness, z_position=self.z_position,
        )
        e.tags = dict(self.tags)
        return e

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "position": self.position.to_tuple(),
            "fitting_type": self.fitting_type,
            "width_in": self.width_in, "height_in": self.height_in,
            "width_out": self.width_out, "height_out": self.height_out,
            "angle": self.angle, "radius": self.radius,
            "rotation": self.rotation, "duct_type": self.duct_type,
            "material": self.material, "thickness": self.thickness,
            "z_position": self.z_position,
        })
        return d
