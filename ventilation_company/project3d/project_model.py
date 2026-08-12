"""Головна модель проєкту 3D/креслення.

Об'єднує вентиляційну систему та архітектурний контекст.
"""

import json
import os
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

from ventilation_company.project3d.vent_system import (
    VentilationSystem, VentilationTrunk, DuctSegment, Fitting, Equipment,
    Point3D, DuctType,
)
from ventilation_company.project3d.arch_context import ArchitecturalContext, Floor, Wall, Opening
from ventilation_company.project3d.arch_context import ArchitecturalContext, Floor


@dataclass
class VentProject:
    """Повний проєкт вентиляції з архітектурним контекстом."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Новий проєкт"
    client: str = ""
    address: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Основні компоненти
    arch_context: ArchitecturalContext = field(default_factory=ArchitecturalContext)
    ventilation_systems: List[VentilationSystem] = field(default_factory=list)

    # 2D-креслення
    drawing_files: List[Dict[str, Any]] = field(default_factory=list)
    # [{"path": "...", "floor": "Поверх 1", "type": "план", "format": "dxf"}]

    # Налаштування
    units: str = "мм"
    notes: str = ""

    @property
    def total_air_flow(self) -> float:
        return sum(vs.total_air_flow for vs in self.ventilation_systems)

    @property
    def total_duct_length(self) -> float:
        return sum(vs.total_duct_length for vs in self.ventilation_systems)

    @property
    def total_metal_area(self) -> float:
        return sum(vs.total_metal_area for vs in self.ventilation_systems)

    def get_all_floors(self) -> List[Floor]:
        return self.arch_context.floors

    def get_floor_systems(self, floor_name: str) -> List[VentilationSystem]:
        """Отримати системи, що проходять через певний поверх."""
        result = []
        for vs in self.ventilation_systems:
            for trunk in vs.trunks:
                if trunk.floor == floor_name or str(trunk.floor) in floor_name:
                    result.append(vs)
                    break
        return result

    def add_drawing(self, filepath: str, floor: str = "", drawing_type: str = "план") -> None:
        """Додати 2D-креслення до проєкту."""
        ext = os.path.splitext(filepath)[1].lower().replace(".", "")
        self.drawing_files.append({
            "id": str(uuid.uuid4())[:8],
            "path": filepath,
            "floor": floor,
            "type": drawing_type,
            "format": ext,
            "added_at": datetime.now().isoformat(),
        })
        self.updated_at = datetime.now().isoformat()

    def remove_drawing(self, drawing_id: str) -> bool:
        for i, d in enumerate(self.drawing_files):
            if d.get("id") == drawing_id:
                self.drawing_files.pop(i)
                self.updated_at = datetime.now().isoformat()
                return True
        return False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "client": self.client,
            "address": self.address,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "arch_context": self.arch_context.to_dict(),
            "ventilation_systems": [vs.to_dict() for vs in self.ventilation_systems],
            "drawing_files": self.drawing_files,
            "units": self.units,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VentProject":
        return cls(
            id=d.get("id", str(uuid.uuid4())[:8]),
            name=d.get("name", "Новий проєкт"),
            client=d.get("client", ""),
            address=d.get("address", ""),
            created_at=d.get("created_at", datetime.now().isoformat()),
            updated_at=d.get("updated_at", datetime.now().isoformat()),
            arch_context=ArchitecturalContext.from_dict(d.get("arch_context", {})),
            ventilation_systems=[VentilationSystem.from_dict(vs) for vs in d.get("ventilation_systems", [])],
            drawing_files=d.get("drawing_files", []),
            units=d.get("units", "мм"),
            notes=d.get("notes", ""),
        )

    def save(self, filepath: str) -> None:
        """Зберегти проєкт у файл .ventproj (JSON)."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "VentProject":
        """Завантажити проєкт з файлу .ventproj."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def create_sample_project(self) -> None:
        """Створити демо-проєкт для тестування."""
        self.name = "Демо: Офісна будівля"
        self.client = "ТОВ \"БудІнвест\""
        self.address = "м. Київ, вул. Хрещатик, 1"

        # Створюємо архітектурний контекст
        floor1 = Floor(
            id="f1",
            name="Поверх 1",
            level=3000,
            height=3000,
            walls=[
                Wall(id="w1", name="Північна", start=Point3D(0, 0, 0), end=Point3D(10000, 0, 0), height=3000, thickness=250),
                Wall(id="w2", name="Південна", start=Point3D(0, 8000, 0), end=Point3D(10000, 8000, 0), height=3000, thickness=250),
                Wall(id="w3", name="Східна", start=Point3D(10000, 0, 0), end=Point3D(10000, 8000, 0), height=3000, thickness=250),
                Wall(id="w4", name="Західна", start=Point3D(0, 0, 0), end=Point3D(0, 8000, 0), height=3000, thickness=250),
                Wall(id="w5", name="Перегородка", start=Point3D(5000, 0, 0), end=Point3D(5000, 8000, 0), height=3000, thickness=150),
            ],
            openings=[
                Opening(id="o1", name="Отвір ПВ1", wall_id="w1", position=Point3D(5000, 0, 2500), width=400, height=300),
            ],
        )
        self.arch_context = ArchitecturalContext(
            project_name="Офісна будівля",
            floors=[floor1],
        )

        # Створюємо вентиляційну систему
        trunk = VentilationTrunk(
            id="t1",
            name="Магістраль припливу",
            floor=1,
            duct_type=DuctType.SUPPLY,
            segments=[
                DuctSegment(id="s1", start=Point3D(2000, 1000, 2500), end=Point3D(8000, 1000, 2500), width=400, height=250, length=6000),
                DuctSegment(id="s2", start=Point3D(8000, 1000, 2500), end=Point3D(8000, 6000, 2500), width=400, height=250, length=5000),
                DuctSegment(id="s3", start=Point3D(8000, 6000, 2500), end=Point3D(2000, 6000, 2500), width=315, height=200, length=6000),
            ],
            fittings=[
                Fitting(id="f1", position=Point3D(8000, 1000, 2500), fitting_type="відвід", width_in=400, height_in=250, width_out=400, height_out=250, angle=90),
                Fitting(id="f2", position=Point3D(8000, 6000, 2500), fitting_type="відвід", width_in=400, height_in=250, width_out=315, height_out=200, angle=90),
            ],
            equipment=[
                Equipment(id="e1", name="Вентилятор ВКП", position=Point3D(1500, 1000, 2500), width=600, height=500, length=800, air_flow=5000, pressure=450, power=2.2),
            ],
            air_flow=5000,
        )
        system = VentilationSystem(
            id="vs1",
            name="Система припливу П1",
            system_type="припливна",
            total_air_flow=5000,
            total_pressure=450,
            trunks=[trunk],
        )
        self.ventilation_systems = [system]


# Імпорти для зручності
from ventilation_company.project3d.vent_system import (
    DuctType, DuctShape, DuctSegment, Fitting, Equipment, VentilationTrunk, VentilationSystem
)
