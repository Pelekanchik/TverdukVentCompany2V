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

    def load_settings(self, settings) -> None:
        self._settings = settings
        self.edit_backup_path.setText(settings.get("app.backup_path", str(BACKUP_DIR)))
        self.chk_auto_backup.setChecked(settings.get("app.backup_auto", "1") == "1")
        with contextlib.suppress(ValueError):
            self.spin_auto_backup.setValue(int(settings.get("app.backup_keep", "7")))
        self._refresh_backup_list()

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

    def _save_backup_settings(self):
        if not self._settings:
            return
        self.save_settings(self._settings)
        self._settings.clear_cache()
        QMessageBox.information(self, "Успіх", "✅ Налаштування бекапу збережено")

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
