"""Bounding box для сутностей та сцени."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List
from ventilation_company.project3d_editor.core.point import Point2D


@dataclass
class Bounds:
    """Осіbounds (min_x, min_y, max_x, max_y)."""
    min_x: float = float("inf")
    min_y: float = float("inf")
    max_x: float = float("-inf")
    max_y: float = float("-inf")

    def is_empty(self) -> bool:
        return self.min_x > self.max_x or self.min_y > self.max_y

    def center(self) -> Point2D:
        return Point2D((self.min_x + self.max_x) / 2, (self.min_y + self.max_y) / 2)

    def width(self) -> float:
        return self.max_x - self.min_x

    def height(self) -> float:
        return self.max_y - self.min_y

    def expand(self, point: Point2D) -> None:
        self.min_x = min(self.min_x, point.x)
        self.min_y = min(self.min_y, point.y)
        self.max_x = max(self.max_x, point.x)
        self.max_y = max(self.max_y, point.y)

    def expand_by(self, margin: float) -> Bounds:
        """Розширити bounds на margin. Повертає self для ланцюжка викликів."""
        self.min_x -= margin
        self.min_y -= margin
        self.max_x += margin
        self.max_y += margin
        return self

    def contains(self, point: Point2D) -> bool:
        return (self.min_x <= point.x <= self.max_x and
                self.min_y <= point.y <= self.max_y)

    def intersects(self, other: Bounds) -> bool:
        return not (self.max_x < other.min_x or self.min_x > other.max_x or
                    self.max_y < other.min_y or self.min_y > other.max_y)

    @staticmethod
    def from_points(points: List[Point2D]) -> Bounds:
        b = Bounds()
        for p in points:
            b.expand(p)
        return b

    @staticmethod
    def union(a: Bounds, b: Bounds) -> Bounds:
        if a.is_empty():
            return b
        if b.is_empty():
            return a
        return Bounds(
            min_x=min(a.min_x, b.min_x),
            min_y=min(a.min_y, b.min_y),
            max_x=max(a.max_x, b.max_x),
            max_y=max(a.max_y, b.max_y),
        )
