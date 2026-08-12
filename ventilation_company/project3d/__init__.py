"""Модуль project3d — 3D/2D проєкти, імпорт/експорт, перегляд.

Основні класи:
  • VentProject — головна модель проєкту
  • ProjectConverter — хаб конвертації (IFC, DXF, STEP, FCStd)
  • Project3DPreview — 3D-перегляд matplotlib
  • Project2DPreview — 2D-перегляд планів
"""

from ventilation_company.project3d.vent_system import (
    Point3D, DuctType, DuctShape, DuctSegment, Fitting, Equipment,
    VentilationTrunk, VentilationSystem,
)
from ventilation_company.project3d.arch_context import (
    ArchitecturalContext, Floor, Wall, WallMaterial, Opening,
)
from ventilation_company.project3d.project_model import VentProject
from ventilation_company.project3d.converters import ProjectConverter
from ventilation_company.project3d.preview_3d import Project3DPreview
from ventilation_company.project3d.preview_2d import Project2DPreview

__all__ = [
    "Point3D", "DuctType", "DuctShape", "DuctSegment", "Fitting", "Equipment",
    "VentilationTrunk", "VentilationSystem",
    "ArchitecturalContext", "Floor", "Wall", "WallMaterial", "Opening",
    "VentProject", "ProjectConverter",
    "Project3DPreview", "Project2DPreview",
]
