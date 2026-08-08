"""
Модель проєкту (Project)
"""

import random
import time
from datetime import datetime
from typing import Any


def generate_project_number() -> str:
    """Генерує унікальний номер проекту з мілісекундами та випадковим числом."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    ms = int(time.time() * 1000) % 1000
    rand = random.randint(10, 99)
    return f"PRJ-{timestamp}-{ms:03d}{rand}"


def validate_project_number(number: str) -> tuple[bool, str]:
    """Перевіряє формат номера проекту."""
    if not number or not isinstance(number, str):
        return False, "Номер проєкту не може бути пустим"
    if not number.startswith("PRJ-"):
        return False, "Номер проєкту має починатися з 'PRJ-'"
    return True, ""


class Project:
    """Модель проєкту вентиляційної системи."""

    VENTILATION_TYPES = [
        "припливна",
        "витяжна",
        "припливно-витяжна",
        "димовидалення",
        "кондиціонування",
    ]

    def __init__(
        self,
        name: str,
        client: str = "",
        address: str = "",
        ventilation_type: str = "припливна",
        air_flow: float = 0,
        pressure: float = 0,
        project_number: str | None = None,
    ):
        self.id: int | None = None
        self.project_number: str = project_number or generate_project_number()
        self.name: str = name
        self.client: str = client
        self.address: str = address
        self.ventilation_type: str = (
            ventilation_type if ventilation_type in self.VENTILATION_TYPES else "припливна"
        )
        self.air_flow: float = float(air_flow)
        self.pressure: float = float(pressure)
        self.created_at: str = datetime.now().isoformat()
        self.updated_at: str = self.created_at
        self.status: str = "draft"
        self.total_area: float = 0.0
        self.notes: str = ""
        self._components: list[dict[str, Any]] = []
        self._materials: list[dict[str, Any]] = []
        self._works: list[dict[str, Any]] = []

    def validate(self) -> tuple[bool, list[str]]:
        """Валідує проєкт."""
        errors: list[str] = []
        valid, msg = validate_project_number(self.project_number)
        if not valid:
            errors.append(msg)
        if not self.name or len(self.name) < 3:
            errors.append("Назва проєкту має бути не менше 3 символів")
        if self.air_flow > 0:
            try:
                float(self.air_flow)
            except ValueError:
                errors.append("Витрата повітря має бути числом")
        return len(errors) == 0, errors

    def add_component(
        self, component_name: str, quantity: float, unit: str, unit_price: float
    ) -> float:
        """Додає компонент до проєкту."""
        total = quantity * unit_price
        self._components.append(
            {
                "name": component_name,
                "quantity": quantity,
                "unit": unit,
                "unit_price": unit_price,
                "total_price": total,
            }
        )
        return total

    def add_material(
        self, material_name: str, quantity: float, unit: str, unit_price: float
    ) -> float:
        """Додає матеріал до проєкту."""
        total = quantity * unit_price
        self._materials.append(
            {
                "name": material_name,
                "quantity": quantity,
                "unit": unit,
                "unit_price": unit_price,
                "total_price": total,
            }
        )
        return total

    def add_work(self, work_name: str, quantity: float, unit: str, unit_price: float) -> float:
        """Додає роботу до проєкту."""
        total = quantity * unit_price
        self._works.append(
            {
                "name": work_name,
                "quantity": quantity,
                "unit": unit,
                "unit_price": unit_price,
                "total_price": total,
            }
        )
        return total

    def get_summary(self) -> dict[str, Any]:
        """Повертає підсумок проєкту."""
        components_total = sum(c["total_price"] for c in self._components)
        materials_total = sum(m["total_price"] for m in self._materials)
        works_total = sum(w["total_price"] for w in self._works)
        return {
            "project_number": self.project_number,
            "name": self.name,
            "client": self.client,
            "ventilation_type": self.ventilation_type,
            "components_cost": components_total,
            "materials_cost": materials_total,
            "works_cost": works_total,
            "total_base": components_total + materials_total + works_total,
        }

    def to_dict(self) -> dict[str, Any]:
        """Серіалізує проєкт у словник."""
        return {
            "project_number": self.project_number,
            "name": self.name,
            "client": self.client,
            "address": self.address,
            "ventilation_type": self.ventilation_type,
            "air_flow": self.air_flow,
            "pressure": self.pressure,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "total_area": self.total_area,
            "notes": self.notes,
            "components": self._components,
            "materials": self._materials,
            "works": self._works,
            "summary": self.get_summary(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        """Десеріалізує проєкт зі словника."""
        project = cls(
            name=data.get("name", ""),
            client=data.get("client", ""),
            address=data.get("address", ""),
            ventilation_type=data.get("ventilation_type", "припливна"),
            air_flow=data.get("air_flow", 0),
            pressure=data.get("pressure", 0),
            project_number=data.get("project_number"),
        )
        project.id = data.get("id")
        project.created_at = data.get("created_at", datetime.now().isoformat())
        project.updated_at = data.get("updated_at", project.created_at)
        project.status = data.get("status", "draft")
        project.total_area = data.get("total_area", 0.0)
        project.notes = data.get("notes", "")
        project._components = data.get("components", [])
        project._materials = data.get("materials", [])
        project._works = data.get("works", [])
        return project

    def __str__(self) -> str:
        return f"Проєкт {self.project_number}: {self.name} ({self.ventilation_type})"

    def __repr__(self) -> str:
        return f"Project(number={self.project_number!r}, name={self.name!r})"
