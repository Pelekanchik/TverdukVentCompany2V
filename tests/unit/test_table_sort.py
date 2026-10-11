"""Тест числового сортування NumericSortModel.

Регресія: QStandardItemModel сортує за текстом, тому «₴ 1 000» < «₴ 200».
NumericSortModel має сортувати за числовим UserRole від numeric_item().
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem
from PySide6.QtWidgets import QApplication

from ventilation_company.gui_pyside6.table_sort import NumericSortModel, numeric_item


def _model_with_prices() -> NumericSortModel:
    app = QApplication.instance() or QApplication([])
    model = NumericSortModel()
    model.appendRow([numeric_item(1000, "\u20b4 1 000")])
    model.appendRow([numeric_item(200, "\u20b4 200")])
    model.appendRow([numeric_item(50, "\u20b4 50")])
    return model


def test_numeric_ascending():
    model = _model_with_prices()
    model.sort(0, Qt.SortOrder.AscendingOrder)
    values = [model.item(r, 0).data(Qt.ItemDataRole.UserRole) for r in range(model.rowCount())]
    assert values == [50, 200, 1000]


def test_numeric_descending():
    model = _model_with_prices()
    model.sort(0, Qt.SortOrder.DescendingOrder)
    values = [model.item(r, 0).data(Qt.ItemDataRole.UserRole) for r in range(model.rowCount())]
    assert values == [1000, 200, 50]


def test_text_column_falls_back_to_default_sort():
    app = QApplication.instance() or QApplication([])
    model = NumericSortModel()
    model.appendRow([QStandardItem("бета")])
    model.appendRow([QStandardItem("альфа")])
    model.sort(0, Qt.SortOrder.AscendingOrder)
    assert model.item(0, 0).text() == "альфа"
