"""Головне вікно VentCompany (PySide6)."""

import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QStackedWidget
)

from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.gui_pyside6.sidebar import Sidebar
from ventilation_company.gui_pyside6.login_dialog import LoginDialog
from ventilation_company.gui_pyside6.dashboard_tab import DashboardTab
from ventilation_company.gui_pyside6.projects_tab import ProjectsTab
from ventilation_company.gui_pyside6.products_tab import ProductsTab
from ventilation_company.gui_pyside6.specification_tab import SpecificationTab
from ventilation_company.gui_pyside6.cutting_tab import CuttingTab
from ventilation_company.gui_pyside6.crm_tab import CRMTab
from ventilation_company.gui_pyside6.pricing_tab import PricingTab
from ventilation_company.services.auth_service import AuthService, AuthUser


class MainWindow(QMainWindow):
    """Головне вікно програми."""

    def __init__(self, user: AuthUser):
        super().__init__()
        self.user = user
        self.active_project_id: int | None = None
        self.setWindowTitle(f"🏭 VentCompany — {user.full_name} ({user.role})")
        self.setMinimumSize(1280, 800)
        self.resize(1400, 900)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Бічна панель
        self.sidebar = Sidebar(self.user)
        self.sidebar.tab_changed.connect(self._on_tab_changed)
        layout.addWidget(self.sidebar)

        # Контент
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        # Вкладки
        self.tabs = {
            "dashboard": DashboardTab(),
            "projects": ProjectsTab(main_window=self),
            "products": ProductsTab(main_window=self),
            "specification": SpecificationTab(main_window=self),
            "cutting": CuttingTab(),
            "crm": CRMTab(),
            "pricing": PricingTab(),
        }

        for key, tab in self.tabs.items():
            self.stack.addWidget(tab)

        # Показати дашборд
        self._on_tab_changed("dashboard")

    def _on_tab_changed(self, tab_name: str):
        if tab_name in self.tabs:
            self.stack.setCurrentWidget(self.tabs[tab_name])
            # Оновлюємо вкладку при переході
            if hasattr(self.tabs[tab_name], "refresh"):
                self.tabs[tab_name].refresh()

    def set_active_project(self, project_id: int | None):
        """Встановити активний проєкт."""
        self.active_project_id = project_id
        # Оновлюємо заголовок
        if project_id:
            self.setWindowTitle(f"🏭 VentCompany — {self.user.full_name} — Проєкт #{project_id}")
        else:
            self.setWindowTitle(f"🏭 VentCompany — {self.user.full_name}")
        # Оповіщаємо вкладки
        for tab in self.tabs.values():
            if hasattr(tab, "on_project_changed"):
                tab.on_project_changed(project_id)


def run_app():
    app = QApplication(sys.argv)
    Theme.apply(app)

    # Логін
    login = LoginDialog()
    if login.exec() != LoginDialog.DialogCode.Accepted:
        sys.exit(0)

    user = login.authenticated_user
    if not user:
        sys.exit(0)

    # Головне вікно
    window = MainWindow(user)
    window.show()
    sys.exit(app.exec())
