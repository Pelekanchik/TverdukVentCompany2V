"""Тести для FreeCAD-геометрії та прев'ю."""

import pytest
import math

from ventilation_company.freecad_geometry import (
    MeshData, VentGeometry, ProductLayout,
)


class TestMeshData:
    """Тести для 3D-сітки."""

    def test_creation(self):
        mesh = MeshData(
            vertices=[(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
            edges=[(0, 1), (1, 2), (2, 3), (3, 0)],
            faces=[(0, 1, 2, 3)],
            color="steelblue",
        )
        assert len(mesh.vertices) == 4
        assert len(mesh.edges) == 4
        assert len(mesh.faces) == 1
        assert mesh.color == "steelblue"

    def test_empty_mesh(self):
        mesh = MeshData(vertices=[], edges=[], faces=[])
        assert mesh.vertices == []
        assert mesh.edges == []
        assert mesh.faces == []


class TestVentGeometry:
    """Тести для генерації геометрії виробів."""

    def test_detect_type_rect_duct(self):
        vg = VentGeometry()
        product = {"product_type": "прямокутний повітропровід", "width": 400, "height": 200, "length": 1000}
        result = vg.detect_type(product)
        assert isinstance(result, str)

    def test_detect_type_round_duct(self):
        vg = VentGeometry()
        product = {"product_type": "круглий повітропровід", "diameter": 250, "length": 500}
        result = vg.detect_type(product)
        assert isinstance(result, str)

    def test_build_rect_duct(self):
        vg = VentGeometry()
        product = {"product_type": "прямокутний повітропровід", "width": 400, "height": 200, "length": 1000}
        mesh = vg.build(product)
        assert mesh is not None
        assert isinstance(mesh, MeshData)
        assert len(mesh.vertices) > 0
        assert len(mesh.faces) > 0

    def test_build_round_duct(self):
        vg = VentGeometry()
        product = {"product_type": "круглий повітропровід", "diameter": 200, "length": 800}
        mesh = vg.build(product)
        assert mesh is not None
        assert isinstance(mesh, MeshData)

    def test_build_unknown_type(self):
        vg = VentGeometry()
        product = {"product_type": "невідомий тип"}
        mesh = vg.build(product)
        assert mesh is not None
        assert isinstance(mesh, MeshData)

    def test_get_bounds(self):
        vg = VentGeometry()
        product = {"product_type": "прямокутний повітропровід", "width": 400, "height": 200, "length": 1000}
        mesh = vg.build(product)
        bounds = mesh.bounds
        assert len(bounds) == 3
        assert all(b > 0 for b in bounds)


class TestProductLayout:
    """Тести для розміщення виробів."""

    def test_creation(self):
        layout = ProductLayout(spacing=50)
        assert layout.spacing == 50

    def test_layout_returns_positions(self):
        layout = ProductLayout(spacing=50)
        product = {"product_type": "прямокутний повітропровід", "width": 400, "height": 200, "length": 1000}
        positions = layout.layout([product])
        assert isinstance(positions, list)
        assert len(positions) == 1
        assert isinstance(positions[0], tuple)
        assert len(positions[0]) == 3

    def test_layout_multiple_offsets(self):
        layout = ProductLayout(spacing=50)
        p1 = {"product_type": "прямокутний повітропровід", "width": 400, "height": 200, "length": 1000}
        p2 = {"product_type": "прямокутний повітропровід", "width": 300, "height": 150, "length": 800}
        positions = layout.layout([p1, p2])
        assert isinstance(positions, list)
        assert len(positions) == 2
        assert positions[1][2] > positions[0][2]

    def test_build_all(self):
        layout = ProductLayout(spacing=50)
        products = [
            {"product_type": "прямокутний повітропровід", "width": 400, "height": 200, "length": 1000},
            {"product_type": "круглий повітропровід", "diameter": 200, "length": 800},
        ]
        meshes = layout.build_all(products)
        assert isinstance(meshes, list)
        assert len(meshes) == 2
        assert all(isinstance(m, MeshData) for m in meshes)
