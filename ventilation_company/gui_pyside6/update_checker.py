"""Background update checker for MainWindow."""

from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

from ventilation_company.gui_pyside6.workers import FunctionWorker
from ventilation_company.paths import APP_ROOT
from ventilation_company.services.update_service import check_for_update, download_release_asset

UPDATER_BAT = r"""@echo off
set PID=%1
set SRC=%2
set TARGET=%3
set EXE=%4

echo Waiting for app to close...
:wait
tasklist /FI "PID eq %PID%" | find "%PID%" >nul
if %errorlevel%==0 (
    timeout /t 2 /nobreak >nul
    goto wait
)

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%i
set BACKUP=%TARGET%\_backup_%TS%
xcopy "%TARGET%" "%BACKUP%" /E /I /Y >nul
xcopy "%SRC%\*" "%TARGET%\" /E /I /Y >nul
start "" "%EXE%"
"""


class UpdateChecker(QObject):
    """Check GitHub Releases shortly after the main window opens."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._pending_release = None

    def start(self, delay_ms: int = 1500) -> None:
        QTimer.singleShot(delay_ms, self._check)

    def _check(self) -> None:
        self._worker = FunctionWorker(check_for_update)
        self._worker.result.connect(self._on_result)
        self._worker.error.connect(lambda _err: None)
        self._worker.start()

    def _on_result(self, info) -> None:
        if not info:
            return
        parent = self.parent()
        answer = QMessageBox.question(
            parent,
            "Доступне оновлення",
            f"Доступна нова версія: {info.get('tag') or info.get('name')}. "
            f"Поточна версія: {info.get('current_version')}. "
            "Завантажити файл оновлення?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            self._download(info)
        else:
            QDesktopServices.openUrl(QUrl(info.get("url", "")))

    def _download(self, info):
        parent = self.parent()
        self._pending_release = info
        QMessageBox.information(parent, "Оновлення", "Завантаження почалося у фоні.")
        self._worker = FunctionWorker(download_release_asset, info)
        self._worker.result.connect(self._on_downloaded)
        self._worker.error.connect(
            lambda err: QMessageBox.critical(
                parent, "Помилка", f"Не вдалося завантажити оновлення: {err}"
            )
        )
        self._worker.start()

    def _on_downloaded(self, path: str):
        parent = self.parent()
        file_path = Path(path)
        if not file_path.exists() or file_path.stat().st_size == 0:
            QMessageBox.critical(parent, "Помилка", "Файл оновлення не завантажився або порожній.")
            return
        if not zipfile.is_zipfile(file_path):
            QMessageBox.critical(parent, "Помилка", "Завантажений файл не є коректним ZIP-архівом.")
            return

        size_mb = file_path.stat().st_size / 1024 / 1024
        msg = QMessageBox(parent)
        msg.setWindowTitle("Оновлення завантажено")
        msg.setIcon(QMessageBox.Information)
        msg.setText(f"Файл оновлення завантажено: {file_path.name} | Розмір: {size_mb:.1f} МБ")
        extract_btn = msg.addButton("Розпакувати", QMessageBox.AcceptRole)
        open_btn = msg.addButton("Відкрити папку", QMessageBox.AcceptRole)
        msg.addButton(QMessageBox.Ok)
        msg.exec()

        if msg.clickedButton() == extract_btn:
            self._extract_update(file_path)
        elif msg.clickedButton() == open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.parent)))

    def _extract_update(self, file_path: Path):
        parent = self.parent()
        tag = (self._pending_release or {}).get("tag") or "update"
        safe_tag = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in tag)
        target_dir = file_path.parent / f"extracted_{safe_tag}"
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(file_path) as zf:
                zf.extractall(target_dir)
        except Exception as exc:
            QMessageBox.critical(parent, "Помилка", f"Не вдалося розпакувати оновлення: {exc}")
            return

        answer = QMessageBox.question(
            parent,
            "Оновлення розпаковано",
            f"Оновлення розпаковано у:\n{target_dir}\n\nВстановити оновлення зараз?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            self._start_self_update(target_dir)
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target_dir)))

    def _start_self_update(self, extracted_dir: Path):
        parent = self.parent()
        if not getattr(sys, "frozen", False):
            QMessageBox.information(
                parent,
                "Ручне оновлення",
                "Автоматичне встановлення доступне тільки в PyInstaller-збірці. "
                "Розпаковані файли можна замінити вручну.",
            )
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(extracted_dir)))
            return

        exe_path = Path(sys.executable)
        target_dir = APP_ROOT
        updates_dir = target_dir / "updates"
        updates_dir.mkdir(parents=True, exist_ok=True)
        bat_path = updates_dir / "updater.bat"
        bat_path.write_text(UPDATER_BAT, encoding="ascii")

        subprocess.Popen(
            [
                "cmd",
                "/c",
                "start",
                "",
                "/min",
                str(bat_path),
                str(os.getpid()),
                str(extracted_dir),
                str(target_dir),
                str(exe_path),
            ],
            close_fds=True,
        )
        QMessageBox.information(
            parent, "Оновлення", "Застосунок буде закрито для встановлення оновлення."
        )
        if parent is not None:
            parent.close()
