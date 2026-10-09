"""Регресійні тести візуальних багів дашборду (QSS-рамки, @value, обрізаний текст)."""

import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets", reason="потрібен Qt")
QApplication = QtWidgets.QApplication


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def test_stat_card_has_objectname_scoped_stylesheet(qapp):
    """QSS селектор QFrame без objectName ліпить рамки на всі QLabel-компоненти."""
    from ventilation_company.gui_pyside6.dashboard_tab import StatCard

    card = StatCard("📁", "12 (7)", "Проєктів (активних)", "#2563eb")
    assert card.objectName() == "statCard"
    assert "QFrame#statCard" in card.styleSheet()
    assert "\n            QFrame {\n" not in card.styleSheet()


def test_chart_card_scoped_stylesheet(qapp):
    from ventilation_company.gui_pyside6.dashboard_tab import _ChartCard

    card = _ChartCard("📈 Тест")
    assert card.objectName() == "chartCard"
    assert "QFrame#chartCard" in card.styleSheet()


def test_bar_chart_uses_lowercase_value_tag(qapp):
    """Qt 6 друкує буквально «@Value»; правильний тег — «@value»."""
    from ventilation_company.gui_pyside6.dashboard_tab import DashboardTab, _ChartCard

    card = _ChartCard("t")
    DashboardTab._build_bar_chart(card, ["Вер"], [123.4], "#2563eb")
    chart = card.chart_view.chart()
    series = chart.series()[0]
    assert series.labelsFormat() == "@value"
    assert series.isLabelsVisible()
