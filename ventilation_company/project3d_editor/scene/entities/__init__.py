"""Конкретні сутності сцени."""

from ventilation_company.project3d_editor.scene.entities.line import LineEntity
from ventilation_company.project3d_editor.scene.entities.wall import WallEntity
from ventilation_company.project3d_editor.scene.entities.rect import RectEntity
from ventilation_company.project3d_editor.scene.entities.circle import CircleEntity
from ventilation_company.project3d_editor.scene.entities.duct import DuctSegmentEntity
from ventilation_company.project3d_editor.scene.entities.fitting import DuctFittingEntity
from ventilation_company.project3d_editor.scene.entities.equipment import EquipmentEntity

__all__ = [
    "LineEntity",
    "WallEntity",
    "RectEntity",
    "CircleEntity",
    "DuctSegmentEntity",
    "DuctFittingEntity",
    "EquipmentEntity",
]
