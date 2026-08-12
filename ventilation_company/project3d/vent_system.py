"""Моделі вентиляційної системи як цілого.

Описує повітропроводи, траси, гілки, точки приєднання.
"""

import math
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum


class DuctType(Enum):
    SUPPLY = "приплив"
    EXHAUST = "витяжка"
    RECIRCULATION = "рециркуляція"
    SMOKE = "димовидалення"


class DuctShape(Enum):
    ROUND = "круглий"
    RECT = "прямокутний"


@dataclass
class Point3D:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: "Point3D") -> "Point3D":
        return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Point3D") -> "Point3D":
        return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def distance(self, other: "Point3D") -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @classmethod
    def from_tuple(cls, t: Tuple[float, float, float]) -> "Point3D":
        return cls(t[0], t[1], t[2])


@dataclass
class DuctSegment:
    """Один відрізок повітропроводу."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    start: Point3D = field(default_factory=Point3D)
    end: Point3D = field(default_factory=Point3D)
    width: float = 100.0
    height: float = 100.0
    length: float = 0.0
    shape: DuctShape = DuctShape.RECT
    duct_type: DuctType = DuctType.SUPPLY
    material: str = "оцинкована сталь"
    thickness: float = 0.7
    insulation: bool = False
    notes: str = ""

    def __post_init__(self):
        if self.length == 0:
            self.length = self.start.distance(self.end)

    @property
    def diameter(self) -> float:
        return self.width if self.shape == DuctShape.ROUND else 0

    @property
    def center(self) -> Point3D:
        return Point3D(
            (self.start.x + self.end.x) / 2,
            (self.start.y + self.end.y) / 2,
            (self.start.z + self.end.z) / 2,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "start": {"x": self.start.x, "y": self.start.y, "z": self.start.z},
            "end": {"x": self.end.x, "y": self.end.y, "z": self.end.z},
            "width": self.width,
            "height": self.height,
            "length": self.length,
            "shape": self.shape.value,
            "duct_type": self.duct_type.value,
            "material": self.material,
            "thickness": self.thickness,
            "insulation": self.insulation,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DuctSegment":
        return cls(
            id=d.get("id", str(uuid.uuid4())[:8]),
            start=Point3D(**d["start"]),
            end=Point3D(**d["end"]),
            width=d.get("width", 100),
            height=d.get("height", 100),
            length=d.get("length", 0),
            shape=DuctShape(d.get("shape", "прямокутний")),
            duct_type=DuctType(d.get("duct_type", "приплив")),
            material=d.get("material", "оцинкована сталь"),
            thickness=d.get("thickness", 0.7),
            insulation=d.get("insulation", False),
            notes=d.get("notes", ""),
        )


@dataclass
class Fitting:
    """Фасонний виріб (відвід, трійник, перехід, фланець)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    position: Point3D = field(default_factory=Point3D)
    fitting_type: str = "відвід"  # відвід, трійник, перехід, фланець, заглушка, гнучка вставка
    width_in: float = 100.0
    height_in: float = 100.0
    width_out: float = 100.0
    height_out: float = 100.0
    angle: float = 90.0
    radius: float = 150.0
    shape: DuctShape = DuctShape.RECT
    material: str = "оцинкована сталь"
    thickness: float = 0.7
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "position": {"x": self.position.x, "y": self.position.y, "z": self.position.z},
            "fitting_type": self.fitting_type,
            "width_in": self.width_in,
            "height_in": self.height_in,
            "width_out": self.width_out,
            "height_out": self.height_out,
            "angle": self.angle,
            "radius": self.radius,
            "shape": self.shape.value,
            "material": self.material,
            "thickness": self.thickness,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Fitting":
        return cls(
            id=d.get("id", str(uuid.uuid4())[:8]),
            position=Point3D(**d.get("position", {"x": 0, "y": 0, "z": 0})),
            fitting_type=d.get("fitting_type", "відвід"),
            width_in=d.get("width_in", 100),
            height_in=d.get("height_in", 100),
            width_out=d.get("width_out", 100),
            height_out=d.get("height_out", 100),
            angle=d.get("angle", 90),
            radius=d.get("radius", 150),
            shape=DuctShape(d.get("shape", "прямокутний")),
            material=d.get("material", "оцинкована сталь"),
            thickness=d.get("thickness", 0.7),
            notes=d.get("notes", ""),
        )


@dataclass
class Equipment:
    """Обладнання (вентилятор, фільтр, калорифер, глушник)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    position: Point3D = field(default_factory=Point3D)
    rotation: Tuple[float, float, float] = (0, 0, 0)  # градуси
    width: float = 400.0
    height: float = 400.0
    length: float = 600.0
    air_flow: float = 0.0  # м³/год
    pressure: float = 0.0  # Па
    power: float = 0.0  # кВт
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "position": {"x": self.position.x, "y": self.position.y, "z": self.position.z},
            "rotation": self.rotation,
            "width": self.width,
            "height": self.height,
            "length": self.length,
            "air_flow": self.air_flow,
            "pressure": self.pressure,
            "power": self.power,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Equipment":
        return cls(
            id=d.get("id", str(uuid.uuid4())[:8]),
            name=d.get("name", ""),
            position=Point3D(**d.get("position", {"x": 0, "y": 0, "z": 0})),
            rotation=tuple(d.get("rotation", [0, 0, 0])),
            width=d.get("width", 400),
            height=d.get("height", 400),
            length=d.get("length", 600),
            air_flow=d.get("air_flow", 0),
            pressure=d.get("pressure", 0),
            power=d.get("power", 0),
            notes=d.get("notes", ""),
        )


@dataclass
class VentilationTrunk:
    """Магістральна трасса — послідовність сегментів і фасонних виробів."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Магістраль"
    floor: int = 1
    duct_type: DuctType = DuctType.SUPPLY
    segments: List[DuctSegment] = field(default_factory=list)
    fittings: List[Fitting] = field(default_factory=list)
    equipment: List[Equipment] = field(default_factory=list)
    air_flow: float = 0.0
    notes: str = ""

    @property
    def total_length(self) -> float:
        return sum(s.length for s in self.segments)

    @property
    def total_area(self) -> float:
        area = 0.0
        for s in self.segments:
            if s.shape == DuctShape.RECT:
                area += 2 * (s.width + s.height) * s.length / 1e6  # м²
            else:
                area += math.pi * s.width * s.length / 1e6
        return area

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "floor": self.floor,
            "duct_type": self.duct_type.value,
            "segments": [s.to_dict() for s in self.segments],
            "fittings": [f.to_dict() for f in self.fittings],
            "equipment": [e.to_dict() for e in self.equipment],
            "air_flow": self.air_flow,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VentilationTrunk":
        return cls(
            id=d.get("id", str(uuid.uuid4())[:8]),
            name=d.get("name", "Магістраль"),
            floor=d.get("floor", 1),
            duct_type=DuctType(d.get("duct_type", "приплив")),
            segments=[DuctSegment.from_dict(s) for s in d.get("segments", [])],
            fittings=[Fitting.from_dict(f) for f in d.get("fittings", [])],
            equipment=[Equipment.from_dict(e) for e in d.get("equipment", [])],
            air_flow=d.get("air_flow", 0),
            notes=d.get("notes", ""),
        )


@dataclass
class VentilationSystem:
    """Повна вентиляційна система проєкту."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Система вентиляції"
    system_type: str = "припливно-витяжна"
    total_air_flow: float = 0.0
    total_pressure: float = 0.0
    trunks: List[VentilationTrunk] = field(default_factory=list)
    notes: str = ""

    @property
    def total_duct_length(self) -> float:
        return sum(t.total_length for t in self.trunks)

    @property
    def total_metal_area(self) -> float:
        return sum(t.total_area for t in self.trunks)

    def get_all_segments(self) -> List[DuctSegment]:
        segments = []
        for t in self.trunks:
            segments.extend(t.segments)
        return segments

    def get_all_fittings(self) -> List[Fitting]:
        fittings = []
        for t in self.trunks:
            fittings.extend(t.fittings)
        return fittings

    def get_all_equipment(self) -> List[Equipment]:
        equipment = []
        for t in self.trunks:
            equipment.extend(t.equipment)
        return equipment

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "system_type": self.system_type,
            "total_air_flow": self.total_air_flow,
            "total_pressure": self.total_pressure,
            "trunks": [t.to_dict() for t in self.trunks],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VentilationSystem":
        return cls(
            id=d.get("id", str(uuid.uuid4())[:8]),
            name=d.get("name", "Система вентиляції"),
            system_type=d.get("system_type", "припливно-витяжна"),
            total_air_flow=d.get("total_air_flow", 0),
            total_pressure=d.get("total_pressure", 0),
            trunks=[VentilationTrunk.from_dict(t) for t in d.get("trunks", [])],
            notes=d.get("notes", ""),
        )
