"""Тести для імпорту/експорту Project3D (IFC, DXF, STEP, FCStd)."""

import os
import tempfile
import pytest

from ventilation_company.project3d import (
    VentProject, ProjectConverter,
    Point3D, DuctSegment, VentilationTrunk, VentilationSystem,
    Wall, Floor, DuctShape,
)


class TestProjectConverter:
    """Тести для конвертера проєктів."""

    def test_creation(self):
        conv = ProjectConverter()
        assert conv is not None

    def test_supported_export_formats(self):
        formats = ProjectConverter.get_supported_export_formats()
        assert isinstance(formats, list)
        names = [f[0] for f in formats]
        assert "VentProject" in names

    def test_supported_import_formats(self):
        formats = ProjectConverter.get_supported_import_formats()
        assert isinstance(formats, list)
        names = [f[0] for f in formats]
        assert "VentProject" in names

    def test_export_formats_include_ifc(self):
        formats = ProjectConverter.get_supported_export_formats()
        names = [f[0] for f in formats]
        assert any("IFC" in n or "Revit" in n for n in names)

    def test_import_formats_include_dxf(self):
        formats = ProjectConverter.get_supported_import_formats()
        names = [f[0] for f in formats]
        assert any("DXF" in n or "AutoCAD" in n for n in names)


class TestVentProjectSerialization:
    """Тести серіалізації/десеріалізації VentProject."""

    def test_to_dict_basic(self):
        proj = VentProject(name="Проєкт А")
        proj.client = "Клієнт А"
        data = proj.to_dict()
        assert data["name"] == "Проєкт А"
        assert data["client"] == "Клієнт А"
        assert "ventilation_systems" in data
        assert "arch_context" in data

    def test_to_dict_with_systems(self):
        proj = VentProject(name="Тест")
        sys = VentilationSystem(name="С-1", total_air_flow=1500)
        trunk = VentilationTrunk(name="Т-1")
        trunk.segments.append(DuctSegment(
            start=Point3D(0, 0, 0),
            end=Point3D(500, 0, 0),
            width=300, height=150, shape=DuctShape.RECT,
        ))
        sys.trunks.append(trunk)
        proj.ventilation_systems.append(sys)

        data = proj.to_dict()
        assert len(data["ventilation_systems"]) == 1
        assert data["ventilation_systems"][0]["name"] == "С-1"
        assert data["ventilation_systems"][0]["total_air_flow"] == 1500

    def test_create_sample_project(self):
        proj = VentProject(name="Демо")
        proj.create_sample_project()
        assert "Офісна" in proj.name or "БудІнвест" in proj.client
        assert len(proj.ventilation_systems) > 0
        assert proj.total_air_flow > 0
