"""2D-трансформації: масштаб, зсув, поворот."""

from __future__ import annotations
import math
from dataclasses import dataclass
from ventilation_company.project3d_editor.core.point import Point2D


@dataclass
class Transform2D:
    """Афінна трансформація: scale, offset, rotation (в градусах)."""
    scale: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    rotation: float = 0.0  # градуси

    def world_to_screen(self, p: Point2D) -> Point2D:
        """Перетворення світових координат (мм) → екранні (px)."""
        if self.rotation != 0:
            rad = math.radians(-self.rotation)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            rx = p.x * cos_r - p.y * sin_r
            ry = p.x * sin_r + p.y * cos_r
            p = Point2D(rx, ry)
        return Point2D(
            p.x * self.scale + self.offset_x,
            -p.y * self.scale + self.offset_y,  # Y вгору в світі, вниз на екрані
        )

    def screen_to_world(self, p: Point2D) -> Point2D:
        """Перетворення екранних (px) → світові (мм)."""
        x = (p.x - self.offset_x) / self.scale
        y = -(p.y - self.offset_y) / self.scale
        if self.rotation != 0:
            rad = math.radians(self.rotation)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            rx = x * cos_r - y * sin_r
            ry = x * sin_r + y * cos_r
            return Point2D(rx, ry)
        return Point2D(x, y)

    def zoom_at(self, screen_point: Point2D, factor: float) -> None:
        """Масштабування відносно точки на екрані."""
        world_before = self.screen_to_world(screen_point)
        self.scale *= factor
        world_after = self.screen_to_world(screen_point)
        delta = world_after - world_before
        # Коригуємо offset щоб точка залишилась на місці
        self.offset_x += delta.x * self.scale
        self.offset_y -= delta.y * self.scale

    def pan(self, dx_screen: float, dy_screen: float) -> None:
        """Панорама (зсув)."""
        self.offset_x += dx_screen
        self.offset_y += dy_screen
