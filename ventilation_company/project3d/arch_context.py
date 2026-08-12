"""Архітектурний контекст проєкту.

Стіни, перекриття, отвори, поверхи — для прив'язки вентиляції.
"""

import math
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum

from ventilation_company.project3d.vent_system import Point3D


class WallMaterial(Enum):
    BRICK = "цегла"
    CONCRETE = "бетон"
    GYPSUM = "гіпсокартон"
    METAL = "метал"
    UNKNOWN = "невідомо"


@dataclass
class Wall:
    """Архітектурна стіна."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Стіна"
    start: Point3D = field(default_factory=Point3D)
    end: Point3D = field(default_factory=Point3D)
    height: float = 3000.0  # мм
    thickness: float = 200.0  # мм
    material: WallMaterial = WallMaterial.BRICK
    is_load_bearing: bool = True
    has_opening: bool = False
    notes: str = ""

    @property
    def length(self) -> float:
        return self.start.distance(self.end)

    @property
    def center(self) -> Point3D:
        return Point3D(
            (self.start.x + self.end.x) / 2,
            (self.start.y + self.end.y) / 2,
            self.height / 2,
        )

    @property
    def direction(self) -> Point3D:
        """Одиничний вектор напрямку стіни."""
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        dz = self.end.z - self.start.z
        length = math.sqrt(dx**2 + dy**2 + dz**2)
        if length == 0:
            return Point3D(1, 0, 0)
        return Point3D(dx / length, dy / length, dz / length)

    @property
    def normal(self) -> Point3D:
        """Нормаль до стіни (площина XY)."""
        d = self.direction
        return Point3D(-d.y, d.x, 0)

    def get_bounding_box(self) -> Tuple[Point3D, Point3D]:
        """Повертає (min, max) точки bounding box."""
        n = self.normal
        hw = self.thickness / 2
        pts = [
            self.start + Point3D(n.x * hw, n.y * hw, 0),
            self.start - Point3D(n.x * hw, n.y * hw, 0),
            self.end + Point3D(n.x * hw, n.y * hw, 0),
            self.end - Point3D(n.x * hw, n.y * hw, 0),
        ]
        xs = [p.x for p in pts]
        ys = [p.y for p in pts]
        return (
            Point3D(min(xs), min(ys), 0),
            Point3D(max(xs), max(ys), self.height),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "start": {"x": self.start.x, "y": self.start.y, "z": self.start.z},
            "end": {"x": self.end.x, "y": self.end.y, "z": self.end.z},
            "height": self.height,
            "thickness": self.thickness,
            "material": self.material.value,
            "is_load_bearing": self.is_load_bearing,
            "has_opening": self.has_opening,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Wall":
        return cls(
            id=d.get("id", str(uuid.uuid4())[:8]),
            name=d.get("name", "Стіна"),
            start=Point3D(**d.get("start", {"x": 0, "y": 0, "z": 0})),
            end=Point3D(**d.get("end", {"x": 0, "y": 0, "z": 0})),
            height=d.get("height", 3000),
            thickness=d.get("thickness", 200),
            material=WallMaterial(d.get("material", "цегла")),
            is_load_bearing=d.get("is_load_bearing", True),
            has_opening=d.get("has_opening", False),
            notes=d.get("notes", ""),
        )


@dataclass
class Opening:
    """Отвір у стіні або перекритті (для повітропроводу)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Отвір"
    wall_id: Optional[str] = None
    position: Point3D = field(default_factory=Point3D)
    width: float = 200.0
    height: float = 200.0
    shape: str = "прямокутний"  # прямокутний, круглий
    diameter: float = 0.0
    is_sealed: bool = False  # чи загерметизовано
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "wall_id": self.wall_id,
            "position": {"x": self.position.x, "y": self.position.y, "z": self.position.z},
            "width": self.width,
            "height": self.height,
            "shape": self.shape,
            "diameter": self.diameter,
            "is_sealed": self.is_sealed,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Opening":
        return cls(
            id=d.get("id", str(uuid.uuid4())[:8]),
            name=d.get("name", "Отвір"),
            wall_id=d.get("wall_id"),
            position=Point3D(**d.get("position", {"x": 0, "y": 0, "z": 0})),
            width=d.get("width", 200),
            height=d.get("height", 200),
            shape=d.get("shape", "прямокутний"),
            diameter=d.get("diameter", 0),
            is_sealed=d.get("is_sealed", False),
            notes=d.get("notes", ""),
        )


@dataclass
class Floor:
    """Поверх будівлі."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Поверх 1"
    level: float = 0.0  # відмітка верху перекриття, мм
    height: float = 3000.0  # висота поверху, мм
    walls: List[Wall] = field(default_factory=list)
    openings: List[Opening] = field(default_factory=list)
    notes: str = ""

    @property
    def floor_z(self) -> float:
        """Рівень підлоги (низ перекриття)."""
        return self.level - self.height

    def get_bounding_box(self) -> Tuple[Point3D, Point3D]:
        """Повертає (min, max) точки всіх стін поверху."""
        if not self.walls:
            return (Point3D(0, 0, self.floor_z), Point3D(10000, 10000, self.level))
        all_pts = []
        for w in self.walls:
            bb = w.get_bounding_box()
            all_pts.extend([bb[0], bb[1]])
        xs = [p.x for p in all_pts]
        ys = [p.y for p in all_pts]
        return (
            Point3D(min(xs), min(ys), self.floor_z),
            Point3D(max(xs), max(ys), self.level),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "height": self.height,
            "walls": [w.to_dict() for w in self.walls],
            "openings": [o.to_dict() for o in self.openings],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Floor":
        return cls(
            id=d.get("id", str(uuid.uuid4())[:8]),
            name=d.get("name", "Поверх 1"),
            level=d.get("level", 0),
            height=d.get("height", 3000),
            walls=[Wall.from_dict(w) for w in d.get("walls", [])],
            openings=[Opening.from_dict(o) for o in d.get("openings", [])],
            notes=d.get("notes", ""),
        )


@dataclass
class ArchitecturalContext:
    """Повний архітектурний контекст проєкту."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    project_name: str = "Архітектурний проєкт"
    floors: List[Floor] = field(default_factory=list)
    reference_point: Point3D = field(default_factory=Point3D)  # точка прив'язки
    units: str = "мм"
    notes: str = ""

    def get_floor(self, floor_name: str) -> Optional[Floor]:
        for f in self.floors:
            if f.name == floor_name:
                return f
        return None

    def get_all_walls(self) -> List[Wall]:
        walls = []
        for f in self.floors:
            walls.extend(f.walls)
        return walls

    def get_all_openings(self) -> List[Opening]:
        openings = []
        for f in self.floors:
            openings.extend(f.openings)
        return openings

    def get_bounding_box(self) -> Tuple[Point3D, Point3D]:
        if not self.floors:
            return (Point3D(0, 0, 0), Point3D(10000, 10000, 10000))
        all_min = []
        all_max = []
        for f in self.floors:
            bb = f.get_bounding_box()
            all_min.append(bb[0])
            all_max.append(bb[1])
        return (
            Point3D(
                min(p.x for p in all_min),
                min(p.y for p in all_min),
                min(p.z for p in all_min),
            ),
            Point3D(
                max(p.x for p in all_max),
                max(p.y for p in all_max),
                max(p.z for p in all_max),
            ),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_name": self.project_name,
            "floors": [f.to_dict() for f in self.floors],
            "reference_point": {"x": self.reference_point.x, "y": self.reference_point.y, "z": self.reference_point.z},
            "units": self.units,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ArchitecturalContext":
        return cls(
            id=d.get("id", str(uuid.uuid4())[:8]),
            project_name=d.get("project_name", "Архітектурний проєкт"),
            floors=[Floor.from_dict(f) for f in d.get("floors", [])],
            reference_point=Point3D(**d.get("reference_point", {"x": 0, "y": 0, "z": 0})),
            units=d.get("units", "мм"),
            notes=d.get("notes", ""),
        )
