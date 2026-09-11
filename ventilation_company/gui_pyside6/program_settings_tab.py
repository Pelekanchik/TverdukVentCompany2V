"""Вкладка ⚙️ Налаштування програми VentCompany — PySide6 Edition.

Інтеграція:
  • Catppuccin Mocha (через ventilation_company.gui_pyside6.theme.Theme)
  • Немає hardcoded QSS — наслідує глобальну тему
  • Пароль у DATABASE_URL замасковано

Модулі:
  • 🏢 Компанія     — реквізити, контакти, логотип
  • 🗄️ База даних   — PostgreSQL: статус, тест, пул, міграції
  • 🎨 Тема         — збереження налаштування теми
  • 👥 Користувачі  — CRUD користувачів (тільки admin/director)
  • 💾 Бекап        — резервне копіювання БД
  • ℹ️ Система      — версії, статистика, шляхи
"""

import os
import platform

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.database.db import (
    DATABASE_URL,
    MAX_OVERFLOW,
    POOL_RECYCLE,
    POOL_SIZE,
)
from ventilation_company.database.repositories.app_settings_repository import (
    AppSettingsRepository,
    _mask_url,
)
from ventilation_company.gui_pyside6.settings_backup_tab import BackupSettingsTab
from ventilation_company.gui_pyside6.settings_theme_tab import ThemeSettingsTab
from ventilation_company.gui_pyside6.settings_users_tab import UsersAdminTab
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.services.audit_service import log_action
from ventilation_company.services.system_service import SystemService

# Зворотна сумісність — QSS константи (тепер не використовуються, тема через Theme)
INDUSTRIAL_QSS = ""
LIGHT_QSS = ""


# ═══════════════════════════════════════════════════════════════════
# Репозиторій налаштувань програми (key-value в PostgreSQL)
# ═══════════════════════════════════════════════════════════════════
class ProgramSettingsTab(QWidget):
    """Вкладка '⚙️ Налаштування' — інтегрована з Catppuccin Mocha."""

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.is_director = current_user is not None and current_user.role in ("admin", "director")
        self.settings = AppSettingsRepository()
        self._build_ui()
        self._load_all()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("⚙️ Налаштування програми")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {Theme.ACCENT};")
        top.addWidget(title)
        top.addStretch()

        self.btn_save = QPushButton("💾 Зберегти все")
        self.btn_save.setObjectName("primary")
        self.btn_save.setMinimumHeight(36)
        self.btn_save.clicked.connect(self._save_all)
        top.addWidget(self.btn_save)

        self.btn_refresh = QPushButton("🔄 Оновити")
        self.btn_refresh.setMinimumHeight(36)
        self.btn_refresh.clicked.connect(self._load_all)
        top.addWidget(self.btn_refresh)

        layout.addLayout(top)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tab_company = QWidget()
        self.tabs.addTab(self.tab_company, "🏢 Компанія")
        self._build_company_tab()

        self.tab_db = QWidget()
        self.tabs.addTab(self.tab_db, "🗄️ База даних")
        self._build_db_tab()

        self.tab_theme = QWidget()
        self.tabs.addTab(self.tab_theme, "🎨 Тема")
        self._build_theme_tab()

        self.tab_users = QWidget()
        self.tabs.addTab(self.tab_users, "👥 Користувачі")
        self._build_users_tab()

        self.tab_backup = QWidget()
        self.tabs.addTab(self.tab_backup, "💾 Бекап")
        self._build_backup_tab()

        self.tab_sys = QWidget()
        self.tabs.addTab(self.tab_sys, "ℹ️ Система")
        self._build_system_tab()

    # ═══════════════════════════════════════════════════════════════
    # 1. КОМПАНІЯ
    # ═══════════════════════════════════════════════════════════════
    def _build_company_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        vlay = QVBoxLayout(container)
        vlay.setAlignment(Qt.AlignTop)

        grp = QGroupBox("Основні реквізити")
        grid = QGridLayout(grp)
        grid.setSpacing(10)
        self.company_vars = {}

        fields = [
            ("app.company_name", "Назва компанії:"),
            ("app.company_address", "Юридична адреса:"),
            ("app.company_phone", "Телефон:"),
            ("app.company_email", "Email:"),
            ("app.company_edrpou", "ЄДРПОУ:"),
            ("app.company_ipn", "ІПН / ДРФО:"),
            ("app.company_bank", "Банк:"),
            ("app.company_account", "Р/р:"),
            ("app.company_logo_path", "Шлях до логотипу:"),
        ]
        for i, (key, label) in enumerate(fields):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
            grid.addWidget(lbl, i, 0)
            edit = QLineEdit()
            edit.setMinimumWidth(350)
            grid.addWidget(edit, i, 1)
            self.company_vars[key] = edit

        btn_browse = QPushButton("📂 Огляд...")
        btn_browse.setMinimumHeight(32)
        btn_browse.clicked.connect(self._browse_logo)
        grid.addWidget(btn_browse, 8, 2)
        grid.setColumnStretch(1, 1)

        vlay.addWidget(grp)

        grp2 = QGroupBox("Підписи в документах")
        grid2 = QGridLayout(grp2)
        grid2.setSpacing(10)
        sign_fields = [
            ("app.sign_director", "Директор (ПІБ):"),
            ("app.sign_accountant", "Головний бухгалтер (ПІБ):"),
            ("app.sign_engineer", "Головний інженер (ПІБ):"),
        ]
        for i, (key, label) in enumerate(sign_fields):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
            grid2.addWidget(lbl, i, 0)
            edit = QLineEdit()
            grid2.addWidget(edit, i, 1)
            self.company_vars[key] = edit
        grid2.setColumnStretch(1, 1)

        vlay.addWidget(grp2)
        vlay.addStretch()

        scroll.setWidget(container)
        lay = QVBoxLayout(self.tab_company)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)

    def _browse_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Обрати логотип", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.company_vars["app.company_logo_path"].setText(path)

    # ═══════════════════════════════════════════════════════════════
    # 2. БАЗА ДАНИХ
    # ═══════════════════════════════════════════════════════════════
    def _build_db_tab(self):
        hlay = QHBoxLayout(self.tab_db)

        left = QVBoxLayout()

        grp_status = QGroupBox("Статус підключення")
        v = QVBoxLayout(grp_status)
        self.lbl_db_status = QLabel("⏳ Перевірка...")
        self.lbl_db_status.setFont(QFont("Segoe UI", 11, QFont.Bold))
        v.addWidget(self.lbl_db_status)
        self.lbl_db_info = QLabel("")
        self.lbl_db_info.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px;")
        self.lbl_db_info.setWordWrap(True)
        v.addWidget(self.lbl_db_info)
        btn_test = QPushButton("🔄 Перевірити з'єднання")
        btn_test.setMinimumHeight(32)
        btn_test.clicked.connect(self._test_db_connection)
        v.addWidget(btn_test)
        left.addWidget(grp_status)

        grp_pool = QGroupBox("Параметри пулу")
        v2 = QVBoxLayout(grp_pool)
        for label, value in [
            ("URL:", _mask_url(DATABASE_URL)),
            ("Pool size:", str(POOL_SIZE)),
            ("Max overflow:", str(MAX_OVERFLOW)),
            ("Pool recycle (с):", str(POOL_RECYCLE)),
        ]:
            row = QHBoxLayout()
            lbl_key = QLabel(f"<b>{label}</b>")
            lbl_key.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
            row.addWidget(lbl_key)
            lbl_val = QLabel(value)
            lbl_val.setStyleSheet(f"color: {Theme.ACCENT}; font-family: Consolas, monospace;")
            lbl_val.setWordWrap(True)
            row.addWidget(lbl_val, 1)
            v2.addLayout(row)
        left.addWidget(grp_pool)

        btn_row = QHBoxLayout()
        btn_create = QPushButton("🏗️ Створити таблиці (create_all)")
        btn_create.setMinimumHeight(32)
        btn_create.clicked.connect(self._create_tables)
        btn_row.addWidget(btn_create)
        btn_stats = QPushButton("📊 Оновити статистику")
        btn_stats.setMinimumHeight(32)
        btn_stats.clicked.connect(self._refresh_db_stats)
        btn_row.addWidget(btn_stats)
        left.addLayout(btn_row)
        left.addStretch()

        hlay.addLayout(left, 1)

        grp_stats = QGroupBox("Статистика бази даних")
        v3 = QVBoxLayout(grp_stats)
        self.txt_db_stats = QTextEdit()
        self.txt_db_stats.setReadOnly(True)
        v3.addWidget(self.txt_db_stats)
        hlay.addWidget(grp_stats, 1)

    def _test_db_connection(self):
        ok, info = SystemService.test_connection()
        if ok:
            self.lbl_db_status.setText("✅ Підключено до PostgreSQL")
            self.lbl_db_status.setStyleSheet(f"color: {Theme.SUCCESS};")
            self.lbl_db_info.setText(info)
        else:
            self.lbl_db_status.setText("❌ Немає з'єднання з PostgreSQL")
            self.lbl_db_status.setStyleSheet(f"color: {Theme.DANGER};")
            self.lbl_db_info.setText(info)

    def _create_tables(self):
        reply = QMessageBox.question(
            self,
            "Підтвердження",
            "Створити всі таблиці (create_all)?\n\n" "Існуючі таблиці НЕ будуть видалені.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                SystemService.create_tables()
                QMessageBox.information(self, "Успіх", "Таблиці створено / оновлено.")
                self._refresh_db_stats()
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося створити таблиці:\n{e}")

    def _refresh_db_stats(self):
        self.txt_db_stats.setPlainText(SystemService.db_stats())

    def _build_theme_tab(self):
        lay = QVBoxLayout(self.tab_theme)
        lay.setContentsMargins(0, 0, 0, 0)
        self.theme_tab = ThemeSettingsTab()
        lay.addWidget(self.theme_tab)

    def _build_users_tab(self):
        lay = QVBoxLayout(self.tab_users)
        lay.setContentsMargins(0, 0, 0, 0)
        self.users_tab = UsersAdminTab(self.current_user)
        lay.addWidget(self.users_tab)

    def _build_backup_tab(self):
        lay = QVBoxLayout(self.tab_backup)
        lay.setContentsMargins(0, 0, 0, 0)
        self.backup_tab = BackupSettingsTab(self.current_user)
        lay.addWidget(self.backup_tab)

    def _build_system_tab(self):
        vlay = QVBoxLayout(self.tab_sys)
        vlay.setAlignment(Qt.AlignTop)

        lbl = QLabel("ℹ️ Інформація про систему")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        vlay.addWidget(lbl)
        vlay.addSpacing(10)

        info_lines = [
            f"🐍 Python: {platform.python_version()}",
            f"💻 ОС: {platform.system()} {platform.release()}",
            f"🗄️ SQLAlchemy: {self._pkg_version('sqlalchemy')}",
            f"🐘 psycopg: {self._pkg_version('psycopg')}",
            f"📁 Базова директорія: {os.path.abspath('.')}",
            f"📂 Дані: data/",
            f"🔗 DATABASE_URL: {_mask_url(DATABASE_URL)}",
        ]
        for line in info_lines:
            lbl = QLabel(line)
            lbl.setFont(QFont("Consolas", 10))
            vlay.addWidget(lbl)

        stats = QGroupBox("Статистика")
        v = QVBoxLayout(stats)
        self.lbl_sys_stats = QLabel("⏳ Завантаження...")
        v.addWidget(self.lbl_sys_stats)
        vlay.addWidget(stats)

        btn_refresh = QPushButton("🔄 Оновити статистику")
        btn_refresh.setMinimumHeight(32)
        btn_refresh.clicked.connect(self._refresh_system_stats)
        vlay.addWidget(btn_refresh)

        license_grp = QGroupBox("Ліцензія")
        v2 = QVBoxLayout(license_grp)
        v2.addWidget(
            QLabel("VentCompany v2.0 — MIT License\n© Pelekanchik", alignment=Qt.AlignCenter)
        )
        vlay.addWidget(license_grp)
        vlay.addStretch()

        self._refresh_system_stats()

    def _pkg_version(self, pkg: str) -> str:
        return SystemService.package_version(pkg)

    def _refresh_system_stats(self):
        self.lbl_sys_stats.setText(SystemService.system_stats())

    def _load_all(self):
        for key, edit in self.company_vars.items():
            edit.setText(self.settings.get(key, ""))

        self.backup_tab.load_settings(self.settings)

        self.theme_tab.set_theme(self.settings.get("app.theme", "industrial"))

        self._test_db_connection()
        self._refresh_db_stats()

    def _save_all(self):
        for key, edit in self.company_vars.items():
            self.settings.set(key, edit.text())

        self.backup_tab.save_settings(self.settings)

        theme_name = self.theme_tab.theme_name()
        self.settings.set("app.theme", theme_name)

        log_action(
            "settings.update",
            entity_type="settings",
            details={"company_keys": len(self.company_vars)},
            actor=self.current_user,
        )
        QMessageBox.information(self, "Успіх", "✅ Усі налаштування збережено в PostgreSQL")
