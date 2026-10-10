"""Тести сервісу імпорту DXF у розкрій."""

from pathlib import Path

import pytest

ezdxf = pytest.importorskip("ezdxf")

from ventilation_company.services.dxf_import_service import (  # noqa: E402
    parse_dxf_parts,
    parts_to_products,
)


def _rect(msp, x, y, w, h, closed=True):
    """Додати замкнений прямокутник як LWPOLYLINE."""
    pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    msp.add_lwpolyline(pts, close=closed)


@pytest.fixture()
def dxf_file(tmp_path: Path) -> Path:
    """Тестовий DXF: 3 унікальні деталі + шум + незамкнений контур."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    # Деталь 500×300, 2 однакових (одна повернута — має згрупуватися)
    _rect(msp, 0, 0, 500, 300)
    _rect(msp, 1000, 0, 300, 500)
    # Деталь 400×250, 1 шт
    _rect(msp, 0, 500, 400, 250)
    # Шум: дрібна засічка 10×5 — має бути відфільтрована
    _rect(msp, 0, 0, 10, 5)
    # Незамкнений контур — має бути проігнорований
    _rect(msp, 2000, 0, 600, 200, closed=False)
    path = tmp_path / "detali.dxf"
    doc.saveas(str(path))
    return path


def test_parse_dxf_parts_groups_and_filters(dxf_file):
    parts = parse_dxf_parts(dxf_file)
    by_size = {(p["width"], p["height"]): p["quantity"] for p in parts}

    # Канонічний порядок — менший розмір першим (300×500, а не 500×300)
    assert by_size == {(300, 500): 2, (250, 400): 1}
    # Сортування за спаданням площі
    assert [(p["width"], p["height"]) for p in parts] == [(300, 500), (250, 400)]


def test_parse_dxf_missing_file(tmp_path):
    with pytest.raises(ValueError, match="не знайдено"):
        parse_dxf_parts(tmp_path / "nema.dxf")


def test_parse_dxf_no_parts(tmp_path):
    doc = ezdxf.new("R2010")
    doc.modelspace().add_line((0, 0), (100, 100))
    path = tmp_path / "pusto.dxf"
    doc.saveas(str(path))
    with pytest.raises(ValueError, match="замкнутих контурів"):
        parse_dxf_parts(path)


def test_parts_to_products_format():
    parts = [{"width": 500, "height": 300, "quantity": 2}]
    products = parts_to_products(parts, prefix="Кожух")

    assert len(products) == 1
    p = products[0]
    assert p["name"] == "Кожух 500×300"
    assert p["type"] == "деталь з DXF"
    assert p["width"] == 500
    assert p["height"] == 300
    assert p["length"] == 0
    assert p["quantity"] == 2


def test_parts_to_products_default_prefix():
    products = parts_to_products([{"width": 200, "height": 150, "quantity": 1}])
    assert products[0]["name"] == "Деталь 200×150"
