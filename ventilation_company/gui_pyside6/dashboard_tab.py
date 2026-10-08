"""Вкладка дашборду (PySide6) — огляд усіх проєктів компанії.

Картки: проєкти, договірна вартість, отримані оплати, дебіторка.
Графіки (QtCharts): динаміка по місяцях (стовпчики) та розподіл
проєктів за статусами (кругова діаграма). Дані — з усіх проєктів,
не тільки завершених.
"""

from __future__ import annotations

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QPieSeries,
    QValueAxis,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.services.dashboard_service import DashboardService

MONTH_NAMES = [
    "",
    "Січ",
    "Лют",
    "Бер",
    "Кві",
    "Тра",
    "Чер",
    "Лип",
    "Сер",
    "Вер",
    "Жов",
    "Лис",
    "Гру",
]

# Кольори для сегментів кругової діаграми (циклічно).
_STATUS_COLORS = [
    Theme.ACCENT,
    Theme.SUCCESS,
    Theme.WARNING,
    Theme.INFO,
    Theme.DANGER,
    "#7c3aed",
    "#db2777",
    "#059669",
]


def _fmt_uah(amount: float) -> str:
    return "₴ " + f"{amount:,.0f}".replace(",", " ")


class StatCard(QFrame):
    """Картка статистики."""

    def __init__(self, icon, value, label, color, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.BG_CARD};
                border: 1px solid {Theme.BORDER};
                border-radius: 12px;
                padding: 16px;
            }}
            QFrame:hover {{
                border-color: {color};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 24px;")
        layout.addWidget(lbl_icon)

        lbl_value = QLabel(value)
        lbl_value.setObjectName("stat_value")
        lbl_value.setStyleSheet(f"color: {color}; font-size: 26px; font-weight: bold;")
        layout.addWidget(lbl_value)

        lbl_label = QLabel(label)
        lbl_label.setObjectName("stat_label")
        lbl_label.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(lbl_label)


class _ChartCard(QFrame):
    """Картка з заголовком і QChartView."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.BG_CARD};
                border: 1px solid {Theme.BORDER};
                border-radius: 12px;
            }}
        """)
        self.setMinimumHeight(320)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-weight: bold; font-size: 14px;")
        layout.addWidget(lbl)

        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.chart_view.setMinimumHeight(240)
        layout.addWidget(self.chart_view)

    def set_chart(self, chart: QChart) -> None:
        chart.setBackgroundVisible(False)
        chart.legend().setLabelColor(QColor(Theme.TEXT))
        font = QFont()
        font.setPointSize(9)
        chart.legend().setFont(font)
        self.chart_view.setChart(chart)


class DashboardTab(QWidget):
    """Головна сторінка зі статистикою по всіх проєктах."""

    # Як часто оновлювати дані без переходу на вкладку (1 хвилина).
    REFRESH_INTERVAL_MS = 60_000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()
        self._timer = QTimer(self)
        self._timer.setInterval(self.REFRESH_INTERVAL_MS)
        self._timer.timeout.connect(self._on_timer)
        self._timer.start()

    def _on_timer(self) -> None:
        """Оновлення за таймером — лише коли вкладка видима на екрані."""
        if self.isVisible():
            self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        lbl_title = QLabel("📊 Дашборд")
        lbl_title.setObjectName("title")
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Огляд проєктів, оплат та дебіторки • оновлюється автоматично щохвилини")
        lbl_sub.setObjectName("subtitle")
        layout.addWidget(lbl_sub)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.card_projects = StatCard("📁", "—", "Проєктів (активних)", Theme.ACCENT)
        self.card_revenue = StatCard("💼", "—", "Договірна вартість", Theme.INFO)
        self.card_paid = StatCard("💰", "—", "Отримано оплат", Theme.SUCCESS)
        self.card_debt = StatCard("⏳", "—", "Дебіторка (баланс)", Theme.WARNING)

        for card in (
            self.card_projects,
            self.card_revenue,
            self.card_paid,
            self.card_debt,
        ):
            cards_layout.addWidget(card)
        layout.addLayout(cards_layout)

        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(16)

        self.chart_monthly = _ChartCard("📈 Динаміка проєктів по місяцях (вартість, тис. ₴)")
        self.chart_statuses = _ChartCard("🧭 Розподіл проєктів за статусами")
        charts_layout.addWidget(self.chart_monthly, stretch=3)
        charts_layout.addWidget(self.chart_statuses, stretch=2)

        layout.addLayout(charts_layout)

        self.chart_payments = _ChartCard("💵 Надходження оплат по місяцях (тис. ₴)")
        layout.addWidget(self.chart_payments)

        self.lbl_footer = QLabel("")
        self.lbl_footer.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(self.lbl_footer)
        layout.addStretch()

    @staticmethod
    def _set_stat(card, text: str) -> None:
        lbl = card.findChild(QLabel, "stat_value")
        if lbl is not None:
            lbl.setText(text)

    @staticmethod
    def _build_bar_chart(
        card: _ChartCard, categories: list[str], values: list[float], color: str
    ) -> None:
        """Стовпчова діаграма з підписами значень; порожні дані — чиста картка."""
        if not values:
            card.chart_view.setChart(QChart())
            return
        bar_set = QBarSet("Сума")
        bar_set.setColor(QColor(color))
        bar_set.setBorderColor(QColor(color))
        for value in values:
            bar_set.append(round(value, 1))

        series = QBarSeries()
        series.append(bar_set)
        series.setLabelsVisible(True)
        series.setLabelsFormat("@Value")
        series.setLabelsPosition(QBarSeries.LabelsPosition.LabelsOutsideEnd)

        chart = QChart()
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsColor(QColor(Theme.TEXT))
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelsColor(QColor(Theme.TEXT))
        axis_y.setGridLineColor(QColor(Theme.BORDER_LIGHT))
        axis_y.setLabelFormat("%.0f")
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)
        axis_y.applyNiceNumbers()

        chart.legend().setVisible(False)
        card.set_chart(chart)

    def _build_monthly_chart(self, monthly: list[dict]) -> None:
        categories, values = [], []
        for row in monthly:
            label = MONTH_NAMES[row["month"]]
            if row["count"] != 1:
                label += f" ({row['count']})"
            categories.append(label)
            values.append(row["sum"] / 1000.0)
        self._build_bar_chart(self.chart_monthly, categories, values, Theme.ACCENT)

    def _build_payments_chart(self, payments_monthly: list[dict]) -> None:
        categories = [MONTH_NAMES[row["month"]] for row in payments_monthly]
        values = [row["sum"] / 1000.0 for row in payments_monthly]
        self._build_bar_chart(self.chart_payments, categories, values, Theme.SUCCESS)

    def _build_statuses_chart(self, statuses: list[dict]) -> None:
        if not statuses:
            self.chart_statuses.chart_view.setChart(QChart())
            return
        series = QPieSeries()
        series.setHoleSize(0.45)
        for i, row in enumerate(statuses):
            slice_ = series.append(row["status"], row["count"])
            color = QColor(_STATUS_COLORS[i % len(_STATUS_COLORS)])
            slice_.setColor(color)
            slice_.setBorderColor(color)
            slice_.setLabel(f'{row["status"]}: {row["count"]}')
            slice_.setLabelColor(QColor(Theme.TEXT))
            slice_.setLabelVisible(True)

        chart = QChart()
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setVisible(False)
        self.chart_statuses.set_chart(chart)

    def refresh(self):
        """Оновити дані дашборду через DashboardService."""
        try:
            stats = DashboardService.overview()
            self._set_stat(self.card_projects, f"{stats['total_count']} ({stats['active_count']})")
            self._set_stat(self.card_revenue, _fmt_uah(stats["total_revenue"]))
            self._set_stat(self.card_paid, _fmt_uah(stats["paid"]))
            self._set_stat(self.card_debt, _fmt_uah(stats["debt"]))

            self._build_monthly_chart(stats["monthly"])
            self._build_statuses_chart(stats["statuses"])
            self._build_payments_chart(stats.get("payments_monthly", []))

            self.lbl_footer.setText(
                f"Клієнтів: {stats['clients']}  •  Завершено проєктів: {stats['done_count']}"
                + (
                    f"  •  Передоплати: {_fmt_uah(stats['overpaid'])}"
                    if stats["overpaid"] > 0
                    else ""
                )
            )
        except Exception as e:  # noqa: BLE001 — дашборд не повинен падати
            self._set_stat(self.card_projects, "—")
            self._set_stat(self.card_revenue, "—")
            self._set_stat(self.card_paid, "—")
            self._set_stat(self.card_debt, "—")
            self.lbl_footer.setText(f"Помилка завантаження даних: {e}")
