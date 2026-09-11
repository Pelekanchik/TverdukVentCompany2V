"""Dedicated GUI launcher for VentCompany."""

from __future__ import annotations

import logging
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ventilation_company.gui_pyside6.login_dialog import LoginDialog
from ventilation_company.gui_pyside6.main_window import MainWindow
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.paths import LOGS_DIR

os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    filename=str(LOGS_DIR / "ventcompany_error.log"),
    level=logging.ERROR,
    format="%(asctime)s %(levelname)s %(message)s",
)


def _log_unhandled(exc_type, exc, tb):
    logging.error("Unhandled exception", exc_info=(exc_type, exc, tb))
    sys.__excepthook__(exc_type, exc, tb)


sys.excepthook = _log_unhandled


def main() -> None:
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


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Fatal error in launch_gui")
        raise
