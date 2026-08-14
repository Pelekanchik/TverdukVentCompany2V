"""Базова геометрія: точки, вектори, математика."""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Point2D:
    """Точка в 2D-просторі (мм)."""
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: Point2D) -> Point2D:
        return Point2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point2D) -> Point2D:
        return Point2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Point2D:
        return Point2D(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> Point2D:
        return Point2D(self.x / scalar, self.y / scalar)

    def distance_to(self, other: Point2D) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def distance_to_segment(self, a: Point2D, b: Point2D) -> float:
        """Відстань від точки до відрізка ab."""
        ab = b - a
        ab_len_sq = ab.x ** 2 + ab.y ** 2
        if ab_len_sq == 0:
            return self.distance_to(a)
        t = max(0, min(1, ((self.x - a.x) * ab.x + (self.y - a.y) * ab.y) / ab_len_sq))
        proj = a + ab * t
        return self.distance_to(proj)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def to_int_tuple(self) -> Tuple[int, int]:
        return (int(round(self.x)), int(round(self.y)))

    @staticmethod
    def from_tuple(t: Tuple[float, float]) -> Point2D:
        return Point2D(t[0], t[1])

    def __repr__(self) -> str:
        return f"Point2D({self.x:.1f}, {self.y:.1f})"


@dataclass(frozen=True)
class Point3D:
    """Точка в 3D-просторі (мм)."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: Point3D) -> Point3D:
        return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Point3D) -> Point3D:
        return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Point3D:
        return Point3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def distance_to(self, other: Point3D) -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2)

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def to_2d(self) -> Point2D:
        return Point2D(self.x, self.y)

    def __repr__(self) -> str:
        return f"Point3D({self.x:.1f}, {self.y:.1f}, {self.z:.1f})"


@dataclass(frozen=True)
class Vector2D:
    """2D-вектор."""
    x: float = 0.0
    y: float = 0.0

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> Vector2D:
        L = self.length()
        if L == 0:
            return Vector2D(0, 0)
        return Vector2D(self.x / L, self.y / L)

    def dot(self, other: Vector2D) -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: Vector2D) -> float:
        return self.x * other.y - self.y * other.x

    def perpendicular(self) -> Vector2D:
        return Vector2D(-self.y, self.x)

    def angle_to(self, other: Vector2D) -> float:
        """Кут між векторами в градусах."""
        dot = self.dot(other)
        det = self.cross(other)
        return math.degrees(math.atan2(det, dot))

    def to_point(self) -> Point2D:
        return Point2D(self.x, self.y)

    @staticmethod
    def from_points(a: Point2D, b: Point2D) -> Vector2D:
        return Vector2D(b.x - a.x, b.y - a.y)
