"""Вкладка дашборду (PySide6)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
)

from ventilation_company.gui_pyside6.theme import Theme


class StatCard(QFrame):
    """Картка статистики."""

    def __init__(self, icon: str, value: str, label: str, color: str, parent=None):
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
        lbl_value.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")
        layout.addWidget(lbl_value)

        lbl_label = QLabel(label)
        lbl_label.setObjectName("stat_label")
        lbl_label.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(lbl_label)


class DashboardTab(QWidget):
    """Головна сторінка зі статистикою."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Заголовок
        lbl_title = QLabel("📊 Дашборд")
        lbl_title.setObjectName("title")
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Огляд ключових показників компанії")
        lbl_sub.setObjectName("subtitle")
        layout.addWidget(lbl_sub)

        # Картки статистики
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.card_projects = StatCard("📁", "—", "Активні проєкти", Theme.ACCENT)
        self.card_revenue = StatCard("💰", "—", "Прибуток (міс)", Theme.SUCCESS)
        self.card_products = StatCard("🔧", "—", "Виробів у роботі", Theme.WARNING)
        self.card_clients = StatCard("👥", "—", "Клієнтів", Theme.INFO)

        cards_layout.addWidget(self.card_projects)
        cards_layout.addWidget(self.card_revenue)
        cards_layout.addWidget(self.card_products)
        cards_layout.addWidget(self.card_clients)
        layout.addLayout(cards_layout)

        # Місце для графіків (буде QChartView)
        chart_frame = QFrame()
        chart_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.BG_CARD};
                border: 1px solid {Theme.BORDER};
                border-radius: 12px;
            }}
        """)
        chart_frame.setMinimumHeight(300)
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(16, 16, 16, 16)

        lbl_chart = QLabel("📈 Динаміка прибутку")
        lbl_chart.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-weight: bold; font-size: 14px;")
        chart_layout.addWidget(lbl_chart)

        lbl_placeholder = QLabel("(тут буде графік QtCharts)")
        lbl_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_placeholder.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        chart_layout.addWidget(lbl_placeholder)

        layout.addWidget(chart_frame)
        layout.addStretch()

    def refresh(self):
        """Оновити дані дашборду (викликається при відкритті)."""
        # TODO: Завантажити реальні дані з БД
        self.card_projects.findChild(QLabel, "stat_value").setText("12")
        self.card_revenue.findChild(QLabel, "stat_value").setText("₴ 145 000")
        self.card_products.findChild(QLabel, "stat_value").setText("48")
        self.card_clients.findChild(QLabel, "stat_value").setText("7")
