"""Тести PDF-звіту плану розкрою (cutting_pdf_generator.py)."""

from types import SimpleNamespace

import pytest

fpdf = pytest.importorskip("fpdf")


def _make_plan():
    detail = SimpleNamespace(name="Повітропровід 400×200×500")
    sheet = SimpleNamespace(
        width=1250,
        height=2500,
        placed_details=[
            SimpleNamespace(x=0, y=0, width=1204, height=510, rotated=False, detail=detail),
            SimpleNamespace(x=0, y=510, width=404, height=210, rotated=True, detail=detail),
        ],
    )
    return SimpleNamespace(
        sheets=[sheet],
        get_summary=lambda: {
            "total_sheets": 1,
            "utilization_percent": 82.7,
            "waste_percent": 17.3,
            "used_area_m2": 5.167,
        },
    )


def test_generate_pdf_creates_file(tmp_path):
    from ventilation_company.cutting_pdf_generator import generate_cutting_pdf

    out = tmp_path / "plan.pdf"
    result = generate_cutting_pdf(
        _make_plan(),
        str(out),
        meta={"sheet_size": "1250×2500 мм", "material": "Оцинкована сталь", "thickness": "0.7"},
    )
    assert result == str(out)
    data = out.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 5000  # не порожній: схема + таблиця


def test_hex_rgb():
    from ventilation_company.cutting_pdf_generator import _hex_rgb

    assert _hex_rgb("#89b4fa") == (0x89, 0xB4, 0xFA)
    assert _hex_rgb("f38ba8") == (0xF3, 0x8B, 0xA8)
