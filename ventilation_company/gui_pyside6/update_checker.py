"""Background update checker for MainWindow."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

from ventilation_company.gui_pyside6.workers import FunctionWorker
from ventilation_company.services.update_service import check_for_update


class UpdateChecker(QObject):
    """Check GitHub Releases shortly after the main window opens."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None

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
            "Перейти на сторінку завантаження?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes and info.get("url"):
            QDesktopServices.openUrl(QUrl(info["url"]))
