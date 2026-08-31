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
            "projects": ProjectsTab(),
            "products": ProductsTab(),
            "specification": SpecificationTab(),
            "cutting": CuttingTab(),
            "crm": CRMTab(),
            "pricing": PricingTab(),
        }

        for tab_id, widget in self.tabs.items():
            self.stack.addWidget(widget)

        # Показати дашборд за замовчуванням
        self._show_tab("dashboard")

    def _on_tab_changed(self, tab_id: str):
        self._show_tab(tab_id)

    def _show_tab(self, tab_id: str):
        if tab_id in self.tabs:
            self.stack.setCurrentWidget(self.tabs[tab_id])
            self.sidebar.set_active(tab_id)
            if hasattr(self.tabs[tab_id], "refresh"):
                self.tabs[tab_id].refresh()


def run_app():
    """Точка входу."""
    app = QApplication(sys.argv)
    Theme.apply(app)

    login = LoginDialog()
    if login.exec() != LoginDialog.DialogCode.Accepted:
        sys.exit(0)

    user = login.authenticated_user
    if not user:
        sys.exit(0)

    window = MainWindow(user)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
