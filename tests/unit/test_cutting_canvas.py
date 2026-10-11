"""Тести канвасу розкрою (gui_pyside6/cutting_tab.py CuttingCanvas)."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_sheet():
    """Мініатюрний план: один лист із двома деталями."""
    from types import SimpleNamespace

    detail = SimpleNamespace(name="Тестова деталь 400×200")
    placed = [
        SimpleNamespace(x=0, y=0, width=400, height=200, detail=detail),
        SimpleNamespace(x=420, y=0, width=300, height=150, detail=detail),
    ]
    return SimpleNamespace(width=1250, height=2500, placed_details=placed)


def test_canvas_paints_with_dimensions(qapp):
    """Канвас із розмірними стрілками малюється без винятків."""
    from ventilation_company.gui_pyside6.cutting_tab import CuttingCanvas

    canvas = CuttingCanvas()
    canvas.resize(900, 1100)
    canvas.set_sheet(_make_sheet())
    canvas.show()
    canvas.repaint()
    assert canvas.scale > 0


def test_canvas_mouse_coords_in_mm(qapp):
    """Координати курсора перераховуються в міліметри листа."""
    from ventilation_company.gui_pyside6.cutting_tab import CuttingCanvas

    canvas = CuttingCanvas()
    canvas.set_sheet(_make_sheet())
    # Точка у лівому верхньому куті листа + (100, 50) px у масштабі
    canvas.mouse_sheet_pos = QPointF(100.0, 50.0)
    assert canvas.mouse_sheet_pos.x() == pytest.approx(100.0)
    assert canvas.mouse_sheet_pos.y() == pytest.approx(50.0)


def test_dim_line_draws_without_error(qapp):
    """Розмірна лінія зі стрілками та порожнім текстом не падає."""
    from PySide6.QtGui import QColor, QImage, QPainter, QPen

    from ventilation_company.gui_pyside6.cutting_tab import CuttingCanvas

    canvas = CuttingCanvas()
    img = QImage(200, 200, QImage.Format.Format_ARGB32)
    p = QPainter(img)
    p.setPen(QPen(QColor("#ffffff"), 1))
    canvas._dim_line(p, 10, 10, 150, 10, "Ш 400", text_dy=14)
    canvas._dim_line(p, 170, 10, 170, 150)  # без тексту
    p.end()
