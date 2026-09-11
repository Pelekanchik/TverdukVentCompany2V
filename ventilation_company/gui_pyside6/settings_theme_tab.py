"""Theme settings tab extracted from ProgramSettingsTab."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.gui_pyside6.theme import Theme


class ThemeSettingsTab(QWidget):
    """Theme selector tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        vlay = QVBoxLayout(self)
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

    def theme_name(self) -> str:
        return "light" if self.radio_light.isChecked() else "industrial"

    def set_theme(self, theme_name: str) -> None:
        if theme_name == "light":
            self.radio_light.setChecked(True)
        else:
            self.radio_industrial.setChecked(True)

    def _apply_theme(self):
        QMessageBox.information(
            self, "Готово", "Тему збережено.\nПерезапустіть програму для повного ефекту."
        )
