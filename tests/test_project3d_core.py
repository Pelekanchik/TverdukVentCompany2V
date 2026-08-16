"""Тести для ядра project3d — моделі, геометрія, зіткнення."""

import pytest
import math

from ventilation_company.project3d import (
    Point3D, DuctSegment, Fitting, Equipment,
    VentilationTrunk, VentilationSystem, VentProject,
    Wall, Floor, ArchitecturalContext,
    CollisionDetector, Collision,
    DuctShape, DuctType,
)


class TestPoint3D:
    """Тести для 3D-точки."""

    def test_creation(self):
        p = Point3D(100, 200, 300)
        assert p.x == 100
        assert p.y == 200
        assert p.z == 300

    def test_addition(self):
        p1 = Point3D(1, 2, 3)
        p2 = Point3D(4, 5, 6)
        result = p1 + p2
        assert result.x == 5
        assert result.y == 7
        assert result.z == 9

    def test_subtraction(self):
        p1 = Point3D(5, 5, 5)
        p2 = Point3D(2, 3, 4)
        result = p1 - p2
        assert result.x == 3
        assert result.y == 2
        assert result.z == 1

    def test_distance(self):
        p1 = Point3D(0, 0, 0)
        p2 = Point3D(3, 4, 0)
        assert p1.distance(p2) == pytest.approx(5.0)

    def test_to_tuple(self):
        p = Point3D(10, 20, 30)
        assert p.to_tuple() == (10, 20, 30)


class TestDuctSegment:
    """Тести для сегмента повітропроводу."""

    def test_creation_rect(self):
        seg = DuctSegment(
            start=Point3D(0, 0, 0),
            end=Point3D(1000, 0, 0),
            width=400,
            height=200,
            shape=DuctShape.RECT,
        )
        assert seg.length == pytest.approx(1000.0)
        assert seg.width == 400
        assert seg.height == 200
        assert seg.shape == DuctShape.RECT

    def test_creation_round(self):
        seg = DuctSegment(
            start=Point3D(0, 0, 0),
            end=Point3D(500, 0, 0),
            width=250,
            height=250,
            shape=DuctShape.ROUND,
        )
        assert seg.length == pytest.approx(500.0)
        assert seg.width == 250
        assert seg.shape == DuctShape.ROUND

    def test_to_dict(self):
        seg = DuctSegment(
            start=Point3D(0, 0, 0),
            end=Point3D(1000, 0, 0),
            width=400, height=200,
            shape=DuctShape.RECT,
        )
        data = seg.to_dict()
        assert data["width"] == 400
        assert data["shape"] == "прямокутний"  # українське значення enum


class TestVentilationTrunk:
    """Тести для траси вентиляції."""

    def test_creation(self):
        trunk = VentilationTrunk(name="Т-1", floor="Поверх 1")
        assert trunk.name == "Т-1"
        assert trunk.floor == "Поверх 1"
        assert trunk.segments == []

    def test_add_segment(self):
        trunk = VentilationTrunk(name="Т-1")
        seg = DuctSegment(
            start=Point3D(0, 0, 0),
            end=Point3D(1000, 0, 0),
            width=400, height=200, shape=DuctShape.RECT,
        )
        trunk.segments.append(seg)
        assert len(trunk.segments) == 1
        assert trunk.total_length == pytest.approx(1000.0)

    def test_total_length_multiple(self):
        trunk = VentilationTrunk(name="Т-1")
        trunk.segments.append(DuctSegment(
            start=Point3D(0, 0, 0), end=Point3D(500, 0, 0),
            width=400, height=200, shape=DuctShape.RECT,
        ))
        trunk.segments.append(DuctSegment(
            start=Point3D(500, 0, 0), end=Point3D(1500, 0, 0),
            width=400, height=200, shape=DuctShape.RECT,
        ))
        assert trunk.total_length == pytest.approx(1500.0)


class TestVentilationSystem:
    """Тести для вентиляційної системи."""

    def test_creation(self):
        sys = VentilationSystem(name="С-1", system_type="припливна")
        assert sys.name == "С-1"
        assert sys.system_type == "припливна"
        assert sys.trunks == []

    def test_add_trunk(self):
        sys = VentilationSystem(name="С-1")
        trunk = VentilationTrunk(name="Т-1")
        sys.trunks.append(trunk)
        assert len(sys.trunks) == 1

    def test_total_air_flow(self):
        sys = VentilationSystem(name="С-1", total_air_flow=2500)
        assert sys.total_air_flow == 2500


class TestVentProject:
    """Тести для моделі проєкту."""

    def test_creation(self):
        proj = VentProject(name="Тестовий проєкт")
        assert proj.name == "Тестовий проєкт"
        assert proj.ventilation_systems == []
        assert proj.arch_context is not None

    def test_add_system(self):
        proj = VentProject(name="Тест")
        sys = VentilationSystem(name="С-1")
        proj.ventilation_systems.append(sys)
        assert len(proj.ventilation_systems) == 1

    def test_total_air_flow(self):
        proj = VentProject(name="Тест")
        proj.ventilation_systems.append(VentilationSystem(name="С-1", total_air_flow=2000))
        proj.ventilation_systems.append(VentilationSystem(name="С-2", total_air_flow=3000))
        assert proj.total_air_flow == 5000

    def test_total_duct_length(self):
        proj = VentProject(name="Тест")
        sys = VentilationSystem(name="С-1")
        trunk = VentilationTrunk(name="Т-1")
        trunk.segments.append(DuctSegment(
            start=Point3D(0, 0, 0), end=Point3D(1000, 0, 0),
            width=400, height=200, shape=DuctShape.RECT,
        ))
        sys.trunks.append(trunk)
        proj.ventilation_systems.append(sys)
        assert proj.total_duct_length == pytest.approx(1000.0)

    def test_to_dict_roundtrip(self):
        proj = VentProject(name="Тест")
        proj.ventilation_systems.append(VentilationSystem(name="С-1", total_air_flow=1000))
        data = proj.to_dict()
        assert data["name"] == "Тест"
        assert "ventilation_systems" in data
        assert len(data["ventilation_systems"]) == 1

    def test_create_sample_project(self):
        proj = VentProject(name="Демо")
        proj.create_sample_project()
        assert proj.name == "Демо: Офісна будівля"
        assert len(proj.ventilation_systems) > 0
        assert proj.total_air_flow > 0


class TestCollisionDetector:
    """Тести для детектора зіткнень."""

    def test_no_collisions_empty(self):
        proj = VentProject(name="Тест")
        detector = CollisionDetector(proj)
        collisions = detector.check_all()
        assert collisions == []

    def test_segment_hits_wall(self):
        proj = VentProject(name="Тест")
        floor = Floor(name="Поверх 1", level=0)
        wall = Wall(
            name="Стіна 1",
            start=Point3D(0, 0, 0),
            end=Point3D(0, 1000, 0),
            thickness=200,
            height=3000,
        )
        floor.walls.append(wall)
        proj.arch_context.floors.append(floor)

        sys = VentilationSystem(name="С-1")
        trunk = VentilationTrunk(name="Т-1")
        trunk.segments.append(DuctSegment(
            start=Point3D(-100, 500, 1500),
            end=Point3D(100, 500, 1500),
            width=400, height=200, shape=DuctShape.RECT,
        ))
        sys.trunks.append(trunk)
        proj.ventilation_systems.append(sys)

        detector = CollisionDetector(proj)
        collisions = detector.check_all()
        assert len(collisions) >= 1

    def test_no_collision_far_away(self):
        proj = VentProject(name="Тест")
        floor = Floor(name="Поверх 1", level=0)
        floor.walls.append(Wall(
            name="Стіна 1",
            start=Point3D(0, 0, 0),
            end=Point3D(0, 1000, 0),
            thickness=200, height=3000,
        ))
        proj.arch_context.floors.append(floor)

        sys = VentilationSystem(name="С-1")
        trunk = VentilationTrunk(name="Т-1")
        trunk.segments.append(DuctSegment(
            start=Point3D(5000, 5000, 1500),
            end=Point3D(6000, 5000, 1500),
            width=400, height=200, shape=DuctShape.RECT,
        ))
        sys.trunks.append(trunk)
        proj.ventilation_systems.append(sys)

        detector = CollisionDetector(proj)
        collisions = detector.check_all()
        assert len(collisions) == 0
