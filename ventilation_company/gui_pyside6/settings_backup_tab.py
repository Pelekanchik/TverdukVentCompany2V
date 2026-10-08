"""Backup settings tab extracted from ProgramSettingsTab.

Вся робота з бекапами делегує до ventilation_company.utils.backup —
єдиного джерела правди (той самий код, що й автобекап при старті).
"""

from __future__ import annotations

import contextlib
import os
from datetime import datetime
from urllib.parse import urlparse

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.bootstrap import BACKUP_DIR
from ventilation_company.database.db import DATABASE_URL
from ventilation_company.gui_pyside6.workers import FunctionWorker
from ventilation_company.services.audit_service import log_action
from ventilation_company.utils.backup import (
    cleanup_old_backups,
    create_backup,
    find_pg_tool,
    restore_backup,
)


def _format_size(size_bytes: int) -> str:
    """Людиночитаний розмір файлу."""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} МБ"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} КБ"
    return f"{size_bytes} Б"


class BackupSettingsTab(QWidget):
    """Backup/restore tab."""

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._settings = None
        self._build_backup_tab()

    def _build_backup_tab(self):
        vlay = QVBoxLayout(self)

        grp_auto = QGroupBox("Автоматичний бекап")
        f1 = QFormLayout(grp_auto)
        self.chk_auto_backup = QCheckBox("Створювати бекап автоматично")
        self.chk_auto_backup.setChecked(True)
        self.spin_auto_backup = QSpinBox()
        self.spin_auto_backup.setRange(1, 100)
        self.spin_auto_backup.setValue(7)
        self.spin_auto_backup.setSuffix(" копій")
        f1.addRow(self.chk_auto_backup)
        f1.addRow("Зберігати останніх:", self.spin_auto_backup)
        btn_save_backup_settings = QPushButton("💾 Зберегти налаштування бекапу")
        btn_save_backup_settings.setMinimumHeight(32)
        btn_save_backup_settings.clicked.connect(self._save_backup_settings)
        f1.addRow(btn_save_backup_settings)
        vlay.addWidget(grp_auto)

        grp_cloud = QGroupBox("☁️ Хмарний бекап")
        f3 = QFormLayout(grp_cloud)
        self.chk_cloud_backup = QCheckBox("Надсилати копію бекапу у хмару")
        f3.addRow(self.chk_cloud_backup)
        self.edit_tg_token = QLineEdit()
        self.edit_tg_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_tg_token.setPlaceholderText("123456:ABC-DEF…")
        f3.addRow("🤖 Токен бота:", self.edit_tg_token)
        self.edit_tg_chat = QLineEdit()
        self.edit_tg_chat.setPlaceholderText("123456789")
        f3.addRow("💬 Chat ID:", self.edit_tg_chat)
        self.lbl_cloud_status = QLabel("")
        self.lbl_cloud_status.setWordWrap(True)
        f3.addRow(self.lbl_cloud_status)
        h3 = QHBoxLayout()
        btn_test_cloud = QPushButton("📤 Тестова відправка")
        btn_test_cloud.setMinimumHeight(32)
        btn_test_cloud.clicked.connect(self._test_cloud_backup)
        h3.addWidget(btn_test_cloud)
        btn_refresh_cloud = QPushButton("🔎 Знайти хмарні теки")
        btn_refresh_cloud.setMinimumHeight(32)
        btn_refresh_cloud.clicked.connect(self._refresh_cloud_status)
        h3.addWidget(btn_refresh_cloud)
        f3.addRow(h3)
        vlay.addWidget(grp_cloud)

        grp_manual = QGroupBox("Ручний бекап / відновлення")
        f2 = QFormLayout(grp_manual)
        self.edit_backup_path = QLineEdit(str(BACKUP_DIR))
        btn_browse_backup = QPushButton("📂")
        btn_browse_backup.setFixedWidth(40)
        btn_browse_backup.clicked.connect(self._browse_backup_path)
        h1 = QHBoxLayout()
        h1.addWidget(self.edit_backup_path)
        h1.addWidget(btn_browse_backup)
        f2.addRow("📁 Папка бекапів:", h1)
        self.list_backups = QListWidget()
        self.list_backups.setMinimumHeight(130)
        f2.addRow("📋 Бекапи:", self.list_backups)
        h2 = QHBoxLayout()
        for text, slot in [
            ("🔄 Оновити", self._refresh_backup_list),
            ("💾 Створити бекап", self._create_backup_now),
            ("📥 Відновити", self._restore_selected_backup),
            ("🧹 Очистити старі", self._cleanup_backups),
        ]:
            btn = QPushButton(text)
            btn.setMinimumHeight(32)
            btn.clicked.connect(slot)
            h2.addWidget(btn)
        f2.addRow(h2)
        vlay.addWidget(grp_manual)
        lbl = QLabel(
            "💡 Бекап PostgreSQL — pg_dump (custom-формат .dump), відновлення — pg_restore. "
            "Поруч із дампом автоматично копіюються ціни та реквізити (JSON). "
            "Після відновлення перезапустіть програму."
        )
        lbl.setWordWrap(True)
        vlay.addWidget(lbl)
        lbl_cloud_hint = QLabel(
            "💡 Хмарний бекап: створіть бота через @BotFather у Telegram (команда /newbot) "
            "і вставте токен. Свій chat ID дізнайтеся через @userinfobot. "
            "Бекап надходитиме файлом у ваш чат при кожному автобекапі. "
            "Якщо встановлено OneDrive / Google Drive / Dropbox — копія додатково "
            "потрапить у теку VentCompanyBackups (синхронізується автоматично)."
        )
        lbl_cloud_hint.setWordWrap(True)
        vlay.addWidget(lbl_cloud_hint)

    def load_settings(self, settings) -> None:
        self._settings = settings
        self.edit_backup_path.setText(settings.get("app.backup_path", str(BACKUP_DIR)))
        self.chk_auto_backup.setChecked(settings.get("app.backup_auto", "1") == "1")
        with contextlib.suppress(ValueError):
            self.spin_auto_backup.setValue(int(settings.get("app.backup_keep", "7")))
        self.chk_cloud_backup.setChecked(settings.get("app.cloud_backup_enabled", "0") == "1")
        self.edit_tg_token.setText(settings.get("app.cloud_backup_telegram_token", ""))
        self.edit_tg_chat.setText(settings.get("app.cloud_backup_telegram_chat", ""))
        self._refresh_backup_list()
        self._refresh_cloud_status()

    def backup_settings(self):
        return (
            self.edit_backup_path.text().strip() or str(BACKUP_DIR),
            self.chk_auto_backup.isChecked(),
            self.spin_auto_backup.value(),
        )

    def save_settings(self, settings) -> None:
        path, auto_backup, keep_count = self.backup_settings()
        settings.set("app.backup_path", path)
        settings.set("app.backup_keep", str(keep_count))
        settings.set("app.backup_auto", "1" if auto_backup else "0")
        settings.set("app.cloud_backup_enabled", "1" if self.chk_cloud_backup.isChecked() else "0")
        settings.set("app.cloud_backup_telegram_token", self.edit_tg_token.text().strip())
        settings.set("app.cloud_backup_telegram_chat", self.edit_tg_chat.text().strip())

    def _save_backup_settings(self):
        if not self._settings:
            return
        self.save_settings(self._settings)
        self._settings.clear_cache()
        QMessageBox.information(self, "Успіх", "✅ Налаштування бекапу збережено")

    def _refresh_cloud_status(self):
        """Показати знайдені хмарні теки та стан налаштування Telegram."""
        try:
            from ventilation_company.utils import cloud_backup

            folders = cloud_backup.detect_cloud_folders()
        except Exception:  # noqa: BLE001 — статус некритичний
            folders = []
        parts = []
        if folders:
            names = ", ".join(name for name, _path in folders)
            parts.append(f"Знайдено теки синхронізації: {names} ✅")
        else:
            parts.append("Теки синхронізації (OneDrive/Drive/Dropbox) не знайдено")
        token = self.edit_tg_token.text().strip()
        chat = self.edit_tg_chat.text().strip()
        if token and chat:
            parts.append("Telegram: налаштовано ✅")
        elif self.chk_cloud_backup.isChecked():
            parts.append("Telegram: не заповнено токен/chat ID ⚠️")
        self.lbl_cloud_status.setText("\n".join(parts))

    def _test_cloud_backup(self):
        """Створити дамп і надіслати його у хмару (перевірка налаштувань)."""
        token = self.edit_tg_token.text().strip()
        chat = self.edit_tg_chat.text().strip()
        if not token or not chat:
            QMessageBox.warning(
                self,
                "Увага",
                "Спочатку заповніть токен бота та chat ID — інструкція внизу вкладки.",
            )
            return
        path = self.edit_backup_path.text().strip() or str(BACKUP_DIR)
        os.makedirs(path, exist_ok=True)
        self._cloud_worker = FunctionWorker(self._test_cloud_job, path, token, chat)
        self._cloud_worker.result.connect(self._on_cloud_test_done)
        self._cloud_worker.error.connect(
            lambda err: QMessageBox.critical(
                self, "Помилка", f"Тестова відправка не вдалася: {err}"
            )
        )
        self._cloud_worker.start()

    def _test_cloud_job(self, path: str, token: str, chat: str) -> str:
        backup_path = create_backup(backup_dir=path)
        if not backup_path:
            raise RuntimeError("Не вдалося створити бекап — перевірте PostgreSQL")
        from ventilation_company.utils import cloud_backup

        result = cloud_backup.upload_backup(backup_path, token=token, chat=chat)
        ok_tg = result["telegram"]
        folders = result["folders"]
        if ok_tg is False and not folders:
            raise RuntimeError(
                "Ні Telegram, ні хмарні теки не прийняли файл. Перевірте токен/chat ID та інтернет."
            )
        parts = [f"Бекап створено: {backup_path}"]
        if ok_tg:
            parts.append("✅ Надіслано у Telegram")
        if folders:
            parts.append("✅ Скопійовано: " + "; ".join(folders))
        log_action(
            "backup.cloud_test",
            entity_type="database",
            details=cloud_backup.summary_json(result),
            actor=self.current_user,
        )
        return "\n".join(parts)

    def _on_cloud_test_done(self, msg: str) -> None:
        QMessageBox.information(self, "Успіх", msg)
        self._refresh_backup_list()

    def _browse_backup_path(self):
        path = QFileDialog.getExistingDirectory(
            self, "Оберіть папку для бекапів", self.edit_backup_path.text()
        )
        if path:
            self.edit_backup_path.setText(path)

    def _on_backup_created(self, msg: str, path: str) -> None:
        QMessageBox.information(self, "Успіх", msg)
        log_action(
            "backup.create",
            entity_type="database",
            details={"path": path, "result": msg},
            actor=self.current_user,
        )

    def _create_backup_now(self):
        path = self.edit_backup_path.text().strip() or str(BACKUP_DIR)
        os.makedirs(path, exist_ok=True)
        self._backup_worker = FunctionWorker(self._create_backup_job, path)
        self._backup_worker.result.connect(lambda msg: self._on_backup_created(msg, path))
        self._backup_worker.error.connect(
            lambda err: QMessageBox.critical(self, "Помилка", f"Не вдалося створити бекап: {err}")
        )
        self._backup_worker.finished.connect(self._refresh_backup_list)
        self._backup_worker.start()

    def _create_backup_job(self, path: str) -> str:
        """Створити бекап через utils.backup (той самий код, що й автобекап)."""
        backup_path = create_backup(backup_dir=path)
        if backup_path:
            from ventilation_company.utils import cloud_backup

            enabled, token, chat = cloud_backup.cloud_backup_preferences()
            if enabled:
                result = cloud_backup.upload_backup(backup_path, token=token, chat=chat)
                log_action(
                    "backup.cloud_upload",
                    entity_type="database",
                    details=cloud_backup.summary_json(result),
                    actor=self.current_user,
                )
            return f"Бекап створено: {backup_path}"
        raise RuntimeError(
            "Бекап не створено — перевірте, що PostgreSQL запущено, "
            "а pg_dump доступний (див. лог)."
        )

    def _restore_selected_backup(self):
        item = self.list_backups.currentItem()
        if not item:
            QMessageBox.warning(self, "Увага", "Оберіть бекап для відновлення")
            return
        filename = item.data(Qt.ItemDataRole.UserRole) or item.text()
        path = self.edit_backup_path.text().strip() or str(BACKUP_DIR)
        full_path = os.path.join(path, filename)
        reply = QMessageBox.warning(
            self,
            "⚠️ УВАГА",
            f"Відновити БД з бекапу: {filename}?\n\n"
            "ПОТОЧНІ ДАНІ БУДУТЬ ПЕРЕЗАПИСАНІ! Перед відновленням автоматично "
            "створиться бекап поточної бази.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._restore_worker = FunctionWorker(self._restore_backup_job, full_path)
        self._restore_worker.result.connect(lambda msg: self._on_backup_restored(msg, full_path))
        self._restore_worker.error.connect(
            lambda err: QMessageBox.critical(self, "Помилка", f"Не вдалося відновити: {err}")
        )
        self._restore_worker.start()

    def _on_backup_restored(self, msg: str, full_path: str) -> None:
        QMessageBox.information(self, "Успіх", f"{msg} Перезапустіть програму.")
        log_action(
            "backup.restore",
            entity_type="database",
            details={"path": full_path, "result": msg},
            actor=self.current_user,
        )

    def _restore_backup_job(self, full_path: str) -> str:
        """Відновити через utils.backup; legacy .sql — через psql (з резолвінгом шляху)."""
        if full_path.endswith(".sql"):
            import subprocess

            parsed = urlparse(DATABASE_URL)
            db_name = parsed.path.lstrip("/")
            host = parsed.hostname or "localhost"
            port = parsed.port or 5432
            user = parsed.username or "vent"
            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password or ""
            tool = find_pg_tool("psql")
            if tool is None:
                raise RuntimeError("psql не знайдено (встановіть PostgreSQL клієнт)")
            cmd = [tool, "-h", host, "-p", str(port), "-U", user, "-d", db_name, "-f", full_path]
            subprocess.run(cmd, env=env, check=True, capture_output=True)
            return "БД відновлено."
        if restore_backup(full_path, "data/company.db"):
            return "БД відновлено."
        raise RuntimeError("Не вдалося відновити бекап")

    def _refresh_backup_list(self):
        self.list_backups.clear()
        path = self.edit_backup_path.text().strip() or str(BACKUP_DIR)
        if not os.path.exists(path):
            return
        entries = []
        for name in os.listdir(path):
            if not name.endswith((".db", ".sqlite", ".sql", ".dump")):
                continue
            full = os.path.join(path, name)
            try:
                stat = os.stat(full)
            except OSError:
                continue
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")
            entries.append((stat.st_mtime, name, modified, stat.st_size))
        # Найновіші — перші; settings-JSON не показуємо (службові копії)
        entries.sort(reverse=True)
        for _mtime, name, modified, size in entries:
            item = QListWidgetItem(f"{name}  —  {modified}  —  {_format_size(size)}")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list_backups.addItem(item)

    def _cleanup_backups(self):
        path = self.edit_backup_path.text().strip() or str(BACKUP_DIR)
        keep = self.spin_auto_backup.value()
        if not os.path.exists(path):
            QMessageBox.information(self, "Інформація", "Папка бекапів не існує")
            return
        deleted = cleanup_old_backups(backup_dir=path, keep=keep)
        QMessageBox.information(
            self, "Успіх", f"Видалено файлів: {deleted}. Залишено комплектів: {keep}."
        )
        self._refresh_backup_list()
