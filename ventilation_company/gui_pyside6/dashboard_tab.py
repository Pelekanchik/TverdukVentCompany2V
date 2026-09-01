"""Вкладка дашборду (PySide6) — реальні дані з PostgreSQL.

ВИПРАВЛЕННЯ: refresh() тепер завантажує реальні дані з БД замість фейкових чисел.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
)

from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.database.db import get_db
from ventilation_company.database.models.project import Project
from ventilation_company.database.models.product_item import ProductItem
from sqlalchemy import func


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
    """Головна сторінка зі статистикою — реальні дані з БД."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        lbl_title = QLabel("📊 Дашборд")
        lbl_title.setObjectName("title")
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Огляд ключових показників компанії")
        lbl_sub.setObjectName("subtitle")
        layout.addWidget(lbl_sub)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.card_projects = StatCard("📁", "—", "Активні проєкти", Theme.ACCENT)
        self.card_revenue = StatCard("💰", "—", "Прибуток (міс)", Theme.SUCCESS)
        self.card_products = StatCard("🔧", "—", "Виробів у роботі", Theme.WARNING)
        self.card_clients = StatCard("👥", "—", "Унікальних клієнтів", Theme.INFO)

        cards_layout.addWidget(self.card_projects)
        cards_layout.addWidget(self.card_revenue)
        cards_layout.addWidget(self.card_products)
        cards_layout.addWidget(self.card_clients)
        layout.addLayout(cards_layout)

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

        self.lbl_chart_value = QLabel("Завантаження...")
        self.lbl_chart_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_chart_value.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        chart_layout.addWidget(self.lbl_chart_value)

        layout.addWidget(chart_frame)
        layout.addStretch()

    def refresh(self):
        """Оновити дані дашборду з БД."""
        try:
            with get_db() as session:
                # 1. Активні проєкти (не 'Закрито')
                active = session.query(Project).filter(Project.status != "Закрито").count()
                self.card_projects.findChild(QLabel, "stat_value").setText(str(active))

                # 2. Загальна сума всіх виробів (прибуток)
                total_revenue = session.query(func.sum(ProductItem.total_price)).scalar() or 0
                self.card_revenue.findChild(QLabel, "stat_value").setText(f"₴ {float(total_revenue):,.0f}")

                # 3. Кількість виробів
                products_count = session.query(ProductItem).count()
                self.card_products.findChild(QLabel, "stat_value").setText(str(products_count))

                # 4. Унікальних клієнтів
                clients = session.query(Project.client).filter(Project.client != None).distinct().count()
                self.card_clients.findChild(QLabel, "stat_value").setText(str(clients))

                # Графік — підсумок по місяцях
                from sqlalchemy import extract
                monthly = session.query(
                    extract('month', Project.created_at).label('month'),
                    func.count(Project.id).label('cnt')
                ).group_by('month').order_by('month').all()

                if monthly:
                    lines = [f"Місяць {int(m)}: {int(c)} проєктів" for m, c in monthly]
                    self.lbl_chart_value.setText("\n".join(lines))
                else:
                    self.lbl_chart_value.setText("Немає даних для графіка")

        except Exception as e:
            self.card_projects.findChild(QLabel, "stat_value").setText("—")
            self.card_revenue.findChild(QLabel, "stat_value").setText("—")
            self.card_products.findChild(QLabel, "stat_value").setText("—")
            self.card_clients.findChild(QLabel, "stat_value").setText("—")
            self.lbl_chart_value.setText(f"Помилка завантаження: {e}")
