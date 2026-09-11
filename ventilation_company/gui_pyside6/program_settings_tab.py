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

import contextlib
import os
import platform
import subprocess
from datetime import datetime
from urllib.parse import urlparse

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.auth.service import auth
from ventilation_company.database.db import (
    DATABASE_URL,
    MAX_OVERFLOW,
    POOL_RECYCLE,
    POOL_SIZE,
)
from ventilation_company.database.repositories.app_settings_repository import (
    AppSettingsRepository,
    _mask_url,
    get_role_label,
)
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.gui_pyside6.workers import FunctionWorker
from ventilation_company.services.audit_service import log_action
from ventilation_company.services.system_service import SystemService
from ventilation_company.utils.backup import create_backup, restore_backup

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
        vlay = QVBoxLayout(self.tab_theme)
        vlay.setAlignment(Qt.AlignTop)

        lbl = QLabel("🎨 Оформлення інтерфейсу")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        vlay.addWidget(lbl)
        vlay.addSpacing(10)

        self.radio_industrial = QRadioButton("🏭 Industrial Orange (темна)")
        self.radio_light = QRadioButton("☀️ Light (світла)")
        self.radio_industrial.setChecked(True)

        vlay.addWidget(self.radio_industrial)
        vlay.addWidget(self.radio_light)

        grp = QGroupBox("Preview кольорів")
        h = QHBoxLayout(grp)
        self.preview_frames = []
        for name, color in [
            ("bg", Theme.BG),
            ("accent", Theme.ACCENT),
            ("frame", Theme.BG_CARD),
            ("button", Theme.BG_HOVER),
            ("select", Theme.ACCENT),
        ]:
            f = QFrame()
            f.setFixedSize(60, 40)
            f.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
            f.setToolTip(name)
            h.addWidget(f)
            self.preview_frames.append((name, f))
        h.addStretch()
        vlay.addWidget(grp)

        btn_apply = QPushButton("✨ Застосувати тему")
        btn_apply.setObjectName("primary")
        btn_apply.setMinimumHeight(36)
        btn_apply.clicked.connect(self._apply_theme)
        vlay.addWidget(btn_apply)
        vlay.addStretch()

    def _apply_theme(self):
        QMessageBox.information(
            self, "Готово", "Тему збережено.\nПерезапустіть програму для повного ефекту."
        )

    # ═══════════════════════════════════════════════════════════════
    # 4. КОРИСТУВАЧІ
    # ═══════════════════════════════════════════════════════════════
    def _build_users_tab(self):
        vlay = QVBoxLayout(self.tab_users)

        if not self.is_director:
            lbl = QLabel("🚫 Доступ тільки для адміністратора")
            lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
            lbl.setStyleSheet(f"color: {Theme.DANGER};")
            vlay.addWidget(lbl, alignment=Qt.AlignCenter)
            return

        btn_row = QHBoxLayout()
        for text, slot in [
            ("📜 Audit Log", self._show_audit_log),
            ("➕ Додати", self._add_user_dialog),
            ("✏️ Редагувати", self._edit_user_dialog),
            ("🗑️ Видалити", self._delete_user),
            ("🔄 Оновити", self._refresh_users),
        ]:
            btn = QPushButton(text)
            btn.setMinimumHeight(32)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)
        btn_row.addStretch()
        vlay.addLayout(btn_row)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(6)
        self.users_table.setHorizontalHeaderLabels(
            ["ID", "Логін", "ПІБ", "Роль", "Активний", "Останній вхід"]
        )
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setEditTriggers(QTableWidget.NoEditTriggers)
        vlay.addWidget(self.users_table)

        self._refresh_users()

    def _show_audit_log(self):
        from ventilation_company.gui_pyside6.audit_log_dialog import AuditLogDialog

        dlg = AuditLogDialog(self.current_user, self)
        dlg.exec()

    def _refresh_users(self):
        self.users_table.setRowCount(0)
        for u in auth.list_users():
            row = self.users_table.rowCount()
            self.users_table.insertRow(row)
            self.users_table.setItem(row, 0, QTableWidgetItem(str(u.id)))
            self.users_table.setItem(row, 1, QTableWidgetItem(u.username))
            self.users_table.setItem(row, 2, QTableWidgetItem(u.full_name or "—"))
            self.users_table.setItem(row, 3, QTableWidgetItem(get_role_label(u.role)))
            self.users_table.setItem(row, 4, QTableWidgetItem("Так" if u.is_active else "Ні"))
            self.users_table.setItem(row, 5, QTableWidgetItem(u.last_login or "—"))

    def _selected_user(self):
        row = self.users_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Увага", "Оберіть користувача")
            return None
        username = self.users_table.item(row, 1).text()
        return auth.get_user_by_username(username)

    def _add_user_dialog(self):
        self._user_dialog(None)

    def _edit_user_dialog(self):
        user = self._selected_user()
        if user:
            self._user_dialog(user)

    def _user_dialog(self, user):
        is_edit = user is not None
        dlg = QDialog(self)
        dlg.setWindowTitle("Редагування користувача" if is_edit else "Новий користувач")
        dlg.setMinimumSize(400, 380)

        lay = QFormLayout(dlg)

        login_edit = QLineEdit(user.username if is_edit else "")
        if is_edit:
            login_edit.setReadOnly(True)
        lay.addRow("👤 Логін *", login_edit)

        name_edit = QLineEdit(user.full_name if is_edit else "")
        lay.addRow("📝 Повне ім'я *", name_edit)

        pass_edit = QLineEdit()
        pass_edit.setEchoMode(QLineEdit.Password)
        lay.addRow("🔒 Пароль" + ("" if is_edit else " *"), pass_edit)
        if is_edit:
            lay.addRow(QLabel("(залиште порожнім, щоб не змінювати)"))

        pass2_edit = QLineEdit()
        pass2_edit.setEchoMode(QLineEdit.Password)
        lay.addRow("🔒 Підтвердіть пароль", pass2_edit)

        role_combo = QComboBox()
        role_combo.addItems(
            ["Адміністратор", "Менеджер", "Інженер", "Майстер", "Бухгалтер", "Перегляд"]
        )
        if is_edit:
            role_combo.setCurrentText(get_role_label(user.role))
        lay.addRow("🛡️ Посада *", role_combo)

        status_lbl = QLabel("")
        status_lbl.setStyleSheet(f"color: {Theme.DANGER};")
        lay.addRow(status_lbl)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        lay.addRow(btns)

        def save():
            role_map = {
                "Адміністратор": "admin",
                "Менеджер": "manager",
                "Інженер": "engineer",
                "Майстер": "master",
                "Бухгалтер": "accountant",
                "Перегляд": "viewer",
            }
            new_role = role_map.get(role_combo.currentText(), "viewer")

            if is_edit:
                kwargs = {"full_name": name_edit.text(), "role": new_role}
                if pass_edit.text():
                    if pass_edit.text() != pass2_edit.text():
                        status_lbl.setText("❌ Паролі не співпадають")
                        return
                    kwargs["password"] = pass_edit.text()
                auth.update_user(user.id, **kwargs)
                self._refresh_users()
                dlg.accept()
                QMessageBox.information(self, "Успіх", f"Користувача {user.username} оновлено")
            else:
                login = login_edit.text().strip()
                name = name_edit.text().strip()
                password = pass_edit.text()
                if not all([login, name, password]):
                    status_lbl.setText("⚠️ Заповніть обов'язкові поля")
                    return
                if password != pass2_edit.text():
                    status_lbl.setText("❌ Паролі не співпадають")
                    return
                if len(password) < 4:
                    status_lbl.setText("❌ Пароль мінімум 4 символи")
                    return
                try:
                    auth.create_user(login, password, name, new_role)
                    self._refresh_users()
                    dlg.accept()
                    QMessageBox.information(self, "Успіх", f"Користувача {login} створено")
                except ValueError as e:
                    status_lbl.setText(f"❌ {e}")

        btns.accepted.connect(save)
        btns.rejected.connect(dlg.reject)
        dlg.exec()

    def _delete_user(self):
        user = self._selected_user()
        if not user:
            return
        if self.current_user and user.username == self.current_user.username:
            QMessageBox.critical(self, "Помилка", "Не можна видалити самого себе")
            return
        reply = QMessageBox.question(
            self, "Підтвердження", f'Видалити користувача "{user.username}"?'
        )
        if reply == QMessageBox.Yes:
            auth.delete_user(user.id)
            self._refresh_users()
            QMessageBox.information(self, "Успіх", f"Користувача {user.username} видалено")

    # ═══════════════════════════════════════════════════════════════
    # 5. БЕКАП
    # ═══════════════════════════════════════════════════════════════
    def _build_backup_tab(self):
        hlay = QHBoxLayout(self.tab_backup)

        left = QVBoxLayout()

        cfg = QGroupBox("Налаштування бекапу")
        v = QVBoxLayout(cfg)
        v.setSpacing(8)
        v.addWidget(QLabel("Шлях до директорії бекапів:"))
        self.edit_backup_path = QLineEdit("data/backups")
        v.addWidget(self.edit_backup_path)

        v.addWidget(QLabel("Зберігати копій:"))
        self.spin_backup_keep = QSpinBox()
        self.spin_backup_keep.setRange(1, 100)
        self.spin_backup_keep.setValue(10)
        v.addWidget(self.spin_backup_keep)

        self.chk_backup_auto = QCheckBox("Автоматичний бекап при виході")
        v.addWidget(self.chk_backup_auto)

        btn_save_cfg = QPushButton("💾 Зберегти налаштування бекапу")
        btn_save_cfg.setMinimumHeight(32)
        btn_save_cfg.clicked.connect(self._save_backup_settings)
        v.addWidget(btn_save_cfg)
        left.addWidget(cfg)

        ctrl = QGroupBox("Керування")
        v2 = QVBoxLayout(ctrl)
        v2.setSpacing(8)
        btn_create = QPushButton("📦 Створити бекап зараз")
        btn_create.setMinimumHeight(32)
        btn_create.clicked.connect(self._create_backup_now)
        v2.addWidget(btn_create)
        btn_clean = QPushButton("🧹 Очистити старі бекапи")
        btn_clean.setMinimumHeight(32)
        btn_clean.clicked.connect(self._cleanup_backups)
        v2.addWidget(btn_clean)
        left.addWidget(ctrl)
        left.addStretch()

        hlay.addLayout(left, 1)

        right = QGroupBox("Існуючі бекапи")
        v3 = QVBoxLayout(right)
        self.list_backups = QListWidget()
        v3.addWidget(self.list_backups)

        btn_row = QHBoxLayout()
        btn_refresh = QPushButton("🔄 Оновити список")
        btn_refresh.setMinimumHeight(32)
        btn_refresh.clicked.connect(self._refresh_backup_list)
        btn_row.addWidget(btn_refresh)
        btn_restore = QPushButton("↩️ Відновити")
        btn_restore.setMinimumHeight(32)
        btn_restore.clicked.connect(self._restore_selected_backup)
        btn_row.addWidget(btn_restore)
        v3.addLayout(btn_row)

        hlay.addWidget(right, 1)

    def _save_backup_settings(self):
        self.settings.set("app.backup_path", self.edit_backup_path.text())
        self.settings.set("app.backup_keep", str(self.spin_backup_keep.value()))
        self.settings.set("app.backup_auto", "1" if self.chk_backup_auto.isChecked() else "0")
        QMessageBox.information(self, "Успіх", "Налаштування бекапу збережено")

    def _create_backup_now(self):
        path = self.edit_backup_path.text().strip() or "data/backups"
        os.makedirs(path, exist_ok=True)
        self._backup_worker = FunctionWorker(self._create_backup_job, path)
        self._backup_worker.result.connect(
            lambda msg: (
                QMessageBox.information(self, "Успіх", msg),
                log_action(
                    "backup.create",
                    entity_type="database",
                    details={"path": path, "result": msg},
                    actor=self.current_user,
                ),
            )
        )
        self._backup_worker.error.connect(
            lambda err: QMessageBox.critical(self, "Помилка", f"Не вдалося створити бекап: {err}")
        )
        self._backup_worker.finished.connect(self._refresh_backup_list)
        self._backup_worker.start()

    def _create_backup_job(self, path: str) -> str:
        if "postgresql" in DATABASE_URL:
            parsed = urlparse(DATABASE_URL)
            db_name = parsed.path.lstrip("/")
            host = parsed.hostname or "localhost"
            port = parsed.port or 5432
            user = parsed.username or "vent"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dump_file = os.path.join(path, f"ventcompany_backup_{timestamp}.sql")

            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password or ""

            cmd = [
                "pg_dump",
                "-h",
                host,
                "-p",
                str(port),
                "-U",
                user,
                "-d",
                db_name,
                "-f",
                dump_file,
                "-F",
                "p",
            ]
            subprocess.run(cmd, env=env, check=True, capture_output=True)
            return f"Бекап PostgreSQL створено: {dump_file}"

        backup_path = create_backup("data/company.db", path)
        if backup_path:
            return f"Бекап створено: {backup_path}"
        raise RuntimeError("БД не знайдено для бекапу")

    def _restore_selected_backup(self):
        item = self.list_backups.currentItem()
        if not item:
            QMessageBox.warning(self, "Увага", "Оберіть бекап для відновлення")
            return
        filename = item.text()
        path = self.edit_backup_path.text().strip() or "data/backups"
        full_path = os.path.join(path, filename)

        reply = QMessageBox.warning(
            self,
            "⚠️ УВАГА",
            f"Відновити БД з бекапу: {filename}? ПОТОЧНІ ДАНІ МОЖУТЬ БУТИ ВТРАЧЕНІ!",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._restore_worker = FunctionWorker(self._restore_backup_job, full_path)
        self._restore_worker.result.connect(
            lambda msg: (
                QMessageBox.information(self, "Успіх", f"{msg} Перезапустіть програму."),
                log_action(
                    "backup.restore",
                    entity_type="database",
                    details={"path": full_path, "result": msg},
                    actor=self.current_user,
                ),
            )
        )
        self._restore_worker.error.connect(
            lambda err: QMessageBox.critical(self, "Помилка", f"Не вдалося відновити: {err}")
        )
        self._restore_worker.start()

    def _restore_backup_job(self, full_path: str) -> str:
        if full_path.endswith(".sql"):
            parsed = urlparse(DATABASE_URL)
            db_name = parsed.path.lstrip("/")
            host = parsed.hostname or "localhost"
            port = parsed.port or 5432
            user = parsed.username or "vent"
            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password or ""
            cmd = [
                "psql",
                "-h",
                host,
                "-p",
                str(port),
                "-U",
                user,
                "-d",
                db_name,
                "-f",
                full_path,
            ]
            subprocess.run(cmd, env=env, check=True, capture_output=True)
            return "БД відновлено."

        if restore_backup(full_path, "data/company.db"):
            return "БД відновлено."
        raise RuntimeError("Не вдалося відновити бекап")

    def _refresh_backup_list(self):
        self.list_backups.clear()
        path = self.edit_backup_path.text().strip() or "data/backups"
        if not os.path.exists(path):
            return
        files = sorted(os.listdir(path), reverse=True)
        for f in files:
            if "backup" in f:
                self.list_backups.addItem(f)

    def _cleanup_backups(self):
        keep = self.spin_backup_keep.value()
        path = self.edit_backup_path.text().strip() or "data/backups"
        if not os.path.exists(path):
            return
        files = sorted([f for f in os.listdir(path) if "backup" in f], reverse=True)
        deleted = 0
        for old in files[keep:]:
            try:
                os.remove(os.path.join(path, old))
                deleted += 1
            except Exception:
                pass
        QMessageBox.information(self, "Готово", f"Видалено старих бекапів: {deleted}")
        self._refresh_backup_list()

    # ═══════════════════════════════════════════════════════════════
    # 6. СИСТЕМА
    # ═══════════════════════════════════════════════════════════════
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

        self.edit_backup_path.setText(self.settings.get("app.backup_path", "data/backups"))
        with contextlib.suppress(ValueError):
            self.spin_backup_keep.setValue(int(self.settings.get("app.backup_keep", "10")))
        self.chk_backup_auto.setChecked(self.settings.get("app.backup_auto", "0") == "1")

        theme_name = self.settings.get("app.theme", "industrial")
        if theme_name == "light":
            self.radio_light.setChecked(True)
        else:
            self.radio_industrial.setChecked(True)

        self._test_db_connection()
        self._refresh_db_stats()
        self._refresh_backup_list()

    def _save_all(self):
        for key, edit in self.company_vars.items():
            self.settings.set(key, edit.text())

        self.settings.set("app.backup_path", self.edit_backup_path.text())
        self.settings.set("app.backup_keep", str(self.spin_backup_keep.value()))
        self.settings.set("app.backup_auto", "1" if self.chk_backup_auto.isChecked() else "0")

        theme_name = "light" if self.radio_light.isChecked() else "industrial"
        self.settings.set("app.theme", theme_name)

        log_action(
            "settings.update",
            entity_type="settings",
            details={"company_keys": len(self.company_vars)},
            actor=self.current_user,
        )
        QMessageBox.information(self, "Успіх", "✅ Усі налаштування збережено в PostgreSQL")
