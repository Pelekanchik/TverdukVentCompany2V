"""Бічна панель навігації (PySide6)."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QPushButton, QLabel
)

from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.services.auth_service import AuthUser


class SidebarItem(QPushButton):
    def __init__(self, icon, label, tab_id, parent=None):
        super().__init__(f"{icon}  {label}", parent)
        self.tab_id = tab_id
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(42)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Theme.TEXT_MUTED};
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                text-align: left;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {Theme.SIDEBAR_ACTIVE};
                color: {Theme.TEXT};
            }}
            QPushButton:checked {{
                background-color: {Theme.SIDEBAR_ACTIVE};
                color: {Theme.SIDEBAR_ACTIVE_TEXT};
                font-weight: bold;
            }}
        """)


class Sidebar(QFrame):
    tab_changed = Signal(str)

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self._buttons = []
        self._build_ui()

    def _build_ui(self):
        self.setFixedWidth(220)
        self.setStyleSheet(f"background-color: {Theme.SIDEBAR_BG}; border-right: 1px solid {Theme.BORDER};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(4)

        lbl_logo = QLabel("VentCompany")
        lbl_logo.setStyleSheet(f"color: {Theme.ACCENT}; font-size: 15px; font-weight: bold; padding: 4px;")
        layout.addWidget(lbl_logo)

        lbl_user = QLabel(f"{self.user.full_name}")
        lbl_user.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; padding: 4px;")
        layout.addWidget(lbl_user)

        lbl_role = QLabel(f"{self.user.role.upper()}")
        lbl_role.setStyleSheet(f"color: {Theme.ACCENT}; font-size: 10px; padding: 4px;")
        layout.addWidget(lbl_role)

        layout.addSpacing(16)

        # РОБОТА
        lbl_work = QLabel("РОБОТА")
        lbl_work.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 10px; font-weight: bold; padding: 8px 4px;")
        layout.addWidget(lbl_work)

        self._add_item("📊", "Дашборд", "dashboard")
        self._add_item("📁", "Проєкти", "projects")
        self._add_item("🔧", "Вироби", "products")
        self._add_item("📋", "Специфікація", "specification")
        self._add_item("✂️", "Розкрій", "cutting")

        layout.addSpacing(12)

        # ФІНАНСИ
        lbl_fin = QLabel("ФІНАНСИ")
        lbl_fin.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 10px; font-weight: bold; padding: 8px 4px;")
        layout.addWidget(lbl_fin)

        self._add_item("💰", "Ціноутворення", "pricing")
        self._add_item("📄", "Документи", "documents")

        layout.addSpacing(12)

        # АНАЛІТИКА
        lbl_an = QLabel("АНАЛІТИКА")
        lbl_an.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 10px; font-weight: bold; padding: 8px 4px;")
        layout.addWidget(lbl_an)

        self._add_item("👥", "CRM", "crm")
        self._add_item("⚙️", "Налаштування", "settings")

        layout.addStretch()

        btn_logout = QPushButton("Вихід")
        btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_logout.setMinimumHeight(36)
        btn_logout.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Theme.DANGER};
                border: 1px solid {Theme.BORDER};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {Theme.DANGER};
                color: {Theme.BG_DARK};
            }}
        """)
        btn_logout.clicked.connect(self._on_logout)
        layout.addWidget(btn_logout)

    def _add_item(self, icon, label, tab_id):
        btn = SidebarItem(icon, label, tab_id)
        btn.clicked.connect(lambda: self._on_tab_clicked(btn))
        self._buttons.append(btn)
        self.layout().addWidget(btn)

    def _on_tab_clicked(self, clicked):
        for btn in self._buttons:
            btn.setChecked(btn == clicked)
        self.tab_changed.emit(clicked.tab_id)

    def _on_logout(self):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Вихід", "Вийти з системи?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.window().close()

    def set_active(self, tab_id):
        for btn in self._buttons:
            btn.setChecked(btn.tab_id == tab_id)
