"""Головне вікно VentCompany (PySide6)."""

import sys
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from ventilation_company.gui_pyside6.crm_tab import CRMTab
from ventilation_company.gui_pyside6.cutting_tab import CuttingTab
from ventilation_company.gui_pyside6.dashboard_tab import DashboardTab
from ventilation_company.gui_pyside6.documents_tab import DocumentsTab
from ventilation_company.gui_pyside6.global_search_dialog import GlobalSearchDialog
from ventilation_company.gui_pyside6.login_dialog import LoginDialog
from ventilation_company.gui_pyside6.money_tab import MoneyTab
from ventilation_company.gui_pyside6.pricing_tab import PricingTab
from ventilation_company.gui_pyside6.products_tab import ProductsTab
from ventilation_company.gui_pyside6.program_settings_tab import ProgramSettingsTab
from ventilation_company.gui_pyside6.projects_tab import ProjectsTab
from ventilation_company.gui_pyside6.schedule_tab import ScheduleTab
from ventilation_company.gui_pyside6.sidebar import Sidebar, can_open_tab
from ventilation_company.gui_pyside6.specification_tab import SpecificationTab
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.gui_pyside6.update_checker import UpdateChecker
from ventilation_company.gui_pyside6.warehouse_tab import WarehouseTab
from ventilation_company.gui_pyside6.workers import FunctionWorker
from ventilation_company.services.auth_service import AuthUser
from ventilation_company.services.project_notifications import check_stuck_projects

_SETTINGS_ORG = "VentCompany"
_SETTINGS_APP = "VentCompany"


def _auto_backup_on_exit() -> None:
    """Автобекап БД при закритті програми (якщо увімкнено в налаштуваннях).

    Не більше однієї копії на день; старі копії ротаційно видаляються
    згідно з «Зберігати останніх» у налаштуваннях бекапу.
    """
    try:
        from datetime import date

        from ventilation_company.database.repositories.app_settings_repository import (
            AppSettingsRepository,
        )
        from ventilation_company.utils.backup import create_backup, list_backups

        settings = AppSettingsRepository()
        if settings.get("app.backup_auto", "0") != "1":
            return
        keep = int(settings.get("app.backup_keep", "10") or "10")
        today = date.today().isoformat()
        if any(today in Path(b).stem for b in list_backups()):
            return  # сьогодні вже створювали
        path = create_backup()
        if path:
            backups = sorted(list_backups())
            for old in backups[:-keep] if keep > 0 else backups:
                Path(old).unlink(missing_ok=True)
    except Exception:  # noqa: BLE001 — бекап не має блокувати вихід
        pass


def add_tab_shortcuts(parent: QWidget, tab_ids: list[str], on_activate) -> list[QShortcut]:
    """Ctrl+1..Ctrl+9 — перейти на вкладку за порядком у sidebar.

    Повертає створені shortcuts (тримати посилання, щоб не зібрались GC).
    """
    shortcuts = []
    for i, tab_id in enumerate(tab_ids[:9]):
        shortcut = QShortcut(QKeySequence(f"Ctrl+{i + 1}"), parent)
        shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        shortcut.activated.connect(lambda tid=tab_id: on_activate(tid))
        shortcuts.append(shortcut)
    return shortcuts


class MainWindow(QMainWindow):
    def __init__(self, user: AuthUser):
        super().__init__()
        self.user = user
        self.active_project_id = None
        self.setWindowTitle(f"VentCompany — {user.full_name} ({user.role})")
        self.setMinimumSize(1280, 800)
        self.resize(1400, 900)
        self._settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
        self._build_ui()
        # Ctrl+1..9 — перемикання вкладок
        self._tab_shortcuts = add_tab_shortcuts(self, list(self.tabs.keys()), self._activate_tab)
        # Ctrl+G — глобальний пошук
        self._search_shortcut = QShortcut(QKeySequence("Ctrl+G"), self)
        self._search_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self._search_shortcut.activated.connect(self._open_global_search)
        # Відновлення розміру/положення вікна з попереднього запуску
        geometry = self._settings.value("mainwindow/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        self.update_checker = UpdateChecker(self)
        self.update_checker.start()
        # ⏰ Нагадування про «завислі» проєкти: при старті і раз на годину
        self._stuck_timer = QTimer(self)
        self._stuck_timer.setInterval(60 * 60 * 1000)
        self._stuck_timer.timeout.connect(self._check_stuck_projects)
        self._stuck_timer.start()
        QTimer.singleShot(30_000, self._check_stuck_projects)

    def _check_stuck_projects(self):
        """Фонова перевірка проєктів без руху → Telegram (тихо при помилках)."""
        worker = FunctionWorker(check_stuck_projects)
        worker.error.connect(lambda _msg: None)
        self._stuck_worker = worker  # захист від збирання сміття
        worker.finished.connect(lambda: setattr(self, "_stuck_worker", None))
        worker.start()

    def _activate_tab(self, tab_id: str):
        self.sidebar.set_active(tab_id)
        self._on_tab_changed(tab_id)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._settings.setValue("mainwindow/geometry", self.saveGeometry())
        _auto_backup_on_exit()
        super().closeEvent(event)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar(self.user)
        self.sidebar.tab_changed.connect(self._on_tab_changed)
        self.sidebar.search_requested.connect(self._open_global_search)
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        tab_factories = {
            "dashboard": lambda: DashboardTab(),
            "projects": lambda: ProjectsTab(main_window=self),
            "products": lambda: ProductsTab(main_window=self),
            "specification": lambda: SpecificationTab(main_window=self),
            "cutting": lambda: CuttingTab(),
            "schedule": lambda: ScheduleTab(),
            "pricing": lambda: PricingTab(),
            "documents": lambda: DocumentsTab(main_window=self),
            "money": lambda: MoneyTab(),
            "warehouse": lambda: WarehouseTab(current_user=self.user),
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

    def _open_global_search(self):
        """Відкрити діалог глобального пошуку (Ctrl+G / кнопка в sidebar)."""
        dlg = GlobalSearchDialog(parent=self)
        dlg.exec()

    def _on_tab_changed(self, tab_name):
        if tab_name in self.tabs:
            self.stack.setCurrentWidget(self.tabs[tab_name])
            refresh = getattr(self.tabs[tab_name], "refresh", None)
            if callable(refresh):
                refresh()

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
    login.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
    if login.exec() != LoginDialog.DialogCode.Accepted:
        sys.exit(0)
    user = login.authenticated_user
    if not user:
        sys.exit(0)
    login.hide()

    window = MainWindow(user)
    window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    window.destroyed.connect(app.quit)
    window.show()
    sys.exit(app.exec())
