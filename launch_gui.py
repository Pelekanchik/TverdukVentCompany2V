"""Dedicated GUI launcher for VentCompany."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ventilation_company.gui_pyside6.login_dialog import LoginDialog
from ventilation_company.gui_pyside6.main_window import MainWindow
from ventilation_company.gui_pyside6.theme import Theme


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
    main()
