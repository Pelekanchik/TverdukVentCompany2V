"""Вікно входу в систему (PySide6)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QSpacerItem, QSizePolicy
)

from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.services.auth_service import AuthService, AuthUser


class LoginDialog(QDialog):
    """Модальне вікно автентифікації."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔐 VentCompany — Вхід")
        self.setFixedSize(420, 520)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self._user: AuthUser | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        # Логотип
        lbl_icon = QLabel("🏭")
        lbl_icon.setStyleSheet("font-size: 48px;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_icon)

        lbl_title = QLabel("VentCompany")
        lbl_title.setObjectName("title")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Система управління вентиляційними проєктами")
        lbl_sub.setObjectName("subtitle")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_sub)

        layout.addSpacing(20)

        # Логін
        lbl_user = QLabel("👤 Логін")
        lbl_user.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        layout.addWidget(lbl_user)

        self.edit_user = QLineEdit()
        self.edit_user.setPlaceholderText("Введіть логін...")
        self.edit_user.setMinimumHeight(36)
        layout.addWidget(self.edit_user)

        # Пароль
        lbl_pass = QLabel("🔒 Пароль")
        lbl_pass.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        layout.addWidget(lbl_pass)

        self.edit_pass = QLineEdit()
        self.edit_pass.setPlaceholderText("Введіть пароль...")
        self.edit_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_pass.setMinimumHeight(36)
        layout.addWidget(self.edit_pass)

        # Кнопка входу
        layout.addSpacing(16)
        self.btn_login = QPushButton("Увійти в систему")
        self.btn_login.setObjectName("primary")
        self.btn_login.setMinimumHeight(44)
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.clicked.connect(self._do_login)
        layout.addWidget(self.btn_login)

        # Enter = вхід
        self.edit_pass.returnPressed.connect(self._do_login)
        self.edit_user.returnPressed.connect(self.edit_pass.setFocus)

        # Статус
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet(f"color: {Theme.DANGER}; font-size: 12px;")
        layout.addWidget(self.lbl_status)

        layout.addStretch()

        # Підказка
        hint = QLabel("💡 За замовчуванням: admin / admin123")
        hint.setObjectName("subtitle")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    def _do_login(self):
        username = self.edit_user.text().strip()
        password = self.edit_pass.text().strip()

        if not username or not password:
            self.lbl_status.setText("⚠️ Введіть логін та пароль")
            return

        user = AuthService.authenticate(username, password)
        if user:
            self._user = user
            self.accept()
        else:
            self.lbl_status.setText("❌ Невірний логін або пароль")
            self.edit_pass.clear()
            self.edit_pass.setFocus()

    @property
    def authenticated_user(self) -> AuthUser | None:
        return self._user
