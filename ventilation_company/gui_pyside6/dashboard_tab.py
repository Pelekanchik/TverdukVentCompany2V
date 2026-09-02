"""Вкладка дашборду (PySide6) — дані з ЗАВЕРШЕНИХ проєктів.

ВИПРАВЛЕННЯ: тепер агрегує дані з таблиці projects (завершені проєкти),
а не з product_items (незавершена специфікація).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
)

from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.database.db import get_db
from ventilation_company.database.models.project import Project
from ventilation_company.database.repositories.product_repo import ProductRepository
from sqlalchemy import func, extract


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
        lbl_value.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")
        layout.addWidget(lbl_value)

        lbl_label = QLabel(label)
        lbl_label.setObjectName("stat_label")
        lbl_label.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(lbl_label)


class DashboardTab(QWidget):
    """Головна сторінка зі статистикою — дані з ЗАВЕРШЕНИХ проєктів."""

    # Статуси, які вважаються "завершеними"
    DONE_STATUSES = ["Завершено", "Відвантажено", "Закрито"]

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

        lbl_sub = QLabel("Огляд завершених проєктів компанії")
        lbl_sub.setObjectName("subtitle")
        layout.addWidget(lbl_sub)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.card_projects = StatCard("📁", "—", "Завершені проєкти", Theme.ACCENT)
        self.card_revenue = StatCard("💰", "—", "Виручка (завершені)", Theme.SUCCESS)
        self.card_profit = StatCard("📈", "—", "Прибуток (завершені)", Theme.WARNING)
        self.card_clients = StatCard("👥", "—", "Унікальних клієнтів", Theme.INFO)

        cards_layout.addWidget(self.card_projects)
        cards_layout.addWidget(self.card_revenue)
        cards_layout.addWidget(self.card_profit)
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

        lbl_chart = QLabel("📈 Динаміка завершених проєктів по місяцях")
        lbl_chart.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-weight: bold; font-size: 14px;")
        chart_layout.addWidget(lbl_chart)

        self.lbl_chart_value = QLabel("Завантаження...")
        self.lbl_chart_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_chart_value.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        chart_layout.addWidget(self.lbl_chart_value)

        layout.addWidget(chart_frame)
        layout.addStretch()

    def refresh(self):
        """Оновити дані дашборду з БД — тільки завершені проєкти."""
        try:
            with get_db() as session:
                # 1. Завершені проєкти
                done_projects = session.query(Project).filter(
                    Project.status.in_(self.DONE_STATUSES)
                ).all()

                done_count = len(done_projects)
                self.card_projects.findChild(QLabel, "stat_value").setText(str(done_count))

                # 2. Виручка та прибуток — сума всіх виробів у завершених проєктах
                total_revenue = 0
                total_cost = 0
                for p in done_projects:
                    try:
                        products = ProductRepository.get_all(project_id=p.id)
                        for item in products:
                            total_revenue += item.get("total_price", 0)
                            # Собівартість = base_cost (без націнки та ПДВ)
                            # Приблизно: total_price / 1.3 / 1.2 (зворотній розрахунок)
                            # Або просто беремо unit_price * quantity
                            total_cost += item.get("unit_price", 0) * item.get("quantity", 1)
                    except Exception:
                        pass

                self.card_revenue.findChild(QLabel, "stat_value").setText(f"₴ {total_revenue:,.0f}")

                profit = total_revenue - total_cost
                self.card_profit.findChild(QLabel, "stat_value").setText(f"₴ {profit:,.0f}")

                # 3. Унікальних клієнтів (тільки у завершених проєктів)
                clients = session.query(Project.client).filter(
                    Project.status.in_(self.DONE_STATUSES),
                    Project.client != None
                ).distinct().count()
                self.card_clients.findChild(QLabel, "stat_value").setText(str(clients))

                # 4. Графік — динаміка завершених проєктів по місяцях
                monthly = session.query(
                    extract('month', Project.created_at).label('month'),
                    func.count(Project.id).label('cnt'),
                    func.sum(Project.customer_price).label('sum')
                ).filter(
                    Project.status.in_(self.DONE_STATUSES)
                ).group_by('month').order_by('month').all()

                if monthly:
                    lines = []
                    for m, c, s in monthly:
                        month_name = ["","Січ","Лют","Бер","Кві","Тра","Чер","Лип","Сер","Вер","Жов","Лис","Гру"][int(m)]
                        lines.append(f"{month_name}: {int(c)} проєктів, ₴ {float(s or 0):,.0f}")
                    self.lbl_chart_value.setText("\n".join(lines))
                else:
                    self.lbl_chart_value.setText("Немає завершених проєктів")

        except Exception as e:
            self.card_projects.findChild(QLabel, "stat_value").setText("—")
            self.card_revenue.findChild(QLabel, "stat_value").setText("—")
            self.card_profit.findChild(QLabel, "stat_value").setText("—")
            self.card_clients.findChild(QLabel, "stat_value").setText("—")
            self.lbl_chart_value.setText(f"Помилка: {e}")
