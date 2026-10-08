"""Тести GUI-елементів креслень проєкту."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from ventilation_company.gui_pyside6.project_card_dialog import (
    DRAWING_FILE_FILTER,
    DrawingsTable,
    ProjectCardDialog,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class TestDrawingsTable:
    def test_accepts_drops(self, qapp):
        table = DrawingsTable()
        assert table.acceptDrops()
        assert table.columnCount() == 0  # колонки задає картка проєкту

    def test_file_filter_covers_cad_formats(self, qapp):
        for ext in ("*.dwg", "*.dxf", "*.pdf", "*.rvt", "*.fcstd"):
            assert ext in DRAWING_FILE_FILTER

    def test_file_filter_covers_solidworks_and_revit_family(self, qapp):
        for ext in ("*.sldprt", "*.sldasm", "*.slddrw", "*.rfa", "*.rte"):
            assert ext in DRAWING_FILE_FILTER


class TestGuessDrawingType:
    def test_dwg_is_drawing(self):
        assert ProjectCardDialog._guess_drawing_type("C:/x/план.dwg") == "креслення"

    def test_revit_is_model(self):
        assert ProjectCardDialog._guess_drawing_type("C:/x/модель.rvt") == "модель"

    def test_freecad_is_model(self):
        assert ProjectCardDialog._guess_drawing_type("C:/x/деталь.fcstd") == "модель"

    def test_detailing_by_name(self):
        assert ProjectCardDialog._guess_drawing_type("C:/x/деталювання_вузла.pdf") == "деталювання"

    def test_solidworks_part_and_assembly_are_models(self):
        assert ProjectCardDialog._guess_drawing_type("C:/x/фланець.sldprt") == "модель"
        assert ProjectCardDialog._guess_drawing_type("C:/x/вузол_заслінки.sldasm") == "модель"

    def test_solidworks_drawing_is_drawing(self):
        assert ProjectCardDialog._guess_drawing_type("C:/x/вид_збоку.slddrw") == "креслення"
