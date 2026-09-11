"""Головне вікно VentCompany (PySide6)."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from ventilation_company.gui_pyside6.crm_tab import CRMTab
from ventilation_company.gui_pyside6.cutting_tab import CuttingTab
from ventilation_company.gui_pyside6.dashboard_tab import DashboardTab
from ventilation_company.gui_pyside6.documents_tab import DocumentsTab
from ventilation_company.gui_pyside6.login_dialog import LoginDialog
from ventilation_company.gui_pyside6.pricing_tab import PricingTab
from ventilation_company.gui_pyside6.products_tab import ProductsTab
from ventilation_company.gui_pyside6.program_settings_tab import ProgramSettingsTab
from ventilation_company.gui_pyside6.projects_tab import ProjectsTab
from ventilation_company.gui_pyside6.sidebar import Sidebar, can_open_tab
from ventilation_company.gui_pyside6.specification_tab import SpecificationTab
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.gui_pyside6.update_checker import UpdateChecker
from ventilation_company.services.auth_service import AuthUser


class MainWindow(QMainWindow):
    def __init__(self, user: AuthUser):
        super().__init__()
        self.user = user
        self.active_project_id = None
        self.setWindowTitle(f"VentCompany — {user.full_name} ({user.role})")
        self.setMinimumSize(1280, 800)
        self.resize(1400, 900)
        self._build_ui()
        self.update_checker = UpdateChecker(self)
        self.update_checker.start()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar(self.user)
        self.sidebar.tab_changed.connect(self._on_tab_changed)
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        tab_factories = {
            "dashboard": lambda: DashboardTab(),
            "projects": lambda: ProjectsTab(main_window=self),
            "products": lambda: ProductsTab(main_window=self),
            "specification": lambda: SpecificationTab(main_window=self),
            "cutting": lambda: CuttingTab(),
            "pricing": lambda: PricingTab(),
            "documents": lambda: DocumentsTab(main_window=self),
            "crm": lambda: CRMTab(),
            "settings": lambda: ProgramSettingsTab(current_user=self.user),
        }

        self.tabs = {}
        for tab_id, factory in tab_factories.items():
            if can_open_tab(self.user, tab_id):
                self.tabs[tab_id] = factory()
                self.stack.addWidget(self.tabs[tab_id])

        default_tab = "dashboard" if "dashboard" in self.tabs else next(iter(self.tabs), None)
        if default_tab:
            self._on_tab_changed(default_tab)

    def _on_tab_changed(self, tab_name):
        if tab_name in self.tabs:
            self.stack.setCurrentWidget(self.tabs[tab_name])
            if hasattr(self.tabs[tab_name], "refresh"):
                self.tabs[tab_name].refresh()

    def set_active_project(self, project_id):
        self.active_project_id = project_id
        if project_id:
            self.setWindowTitle(f"VentCompany — {self.user.full_name} — Проєкт #{project_id}")
        else:
            self.setWindowTitle(f"VentCompany — {self.user.full_name}")
        for tab in self.tabs.values():
            if hasattr(tab, "on_project_changed"):
                tab.on_project_changed(project_id)


def run_app():
    app = QApplication(sys.argv)
    Theme.apply(app)
    app.setQuitOnLastWindowClosed(False)

    login = LoginDialog()
    login.setAttribute(Qt.WA_QuitOnClose, False)
    if login.exec() != LoginDialog.DialogCode.Accepted:
        sys.exit(0)
    user = login.authenticated_user
    if not user:
        sys.exit(0)
    login.hide()

    window = MainWindow(user)
    window.setAttribute(Qt.WA_DeleteOnClose, True)
    window.destroyed.connect(app.quit)
    window.show()
    sys.exit(app.exec())
