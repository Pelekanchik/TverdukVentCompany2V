"""Світла тема VentCompany для PySide6.

Використання:
    from ventilation_company.gui_pyside6.theme import Theme
    Theme.apply(app)
"""

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication


class Theme:
    """Світла тема для VentCompany."""

    # Кольори
    BG = "#f5f7fb"  # Фон вікна
    BG_DARK = "#e9edf5"  # Темніший фон
    BG_CARD = "#ffffff"  # Фон карток/панелей
    BG_HOVER = "#e8eefc"  # Hover ефект
    BG_ACTIVE = "#d7e4fb"  # Активний елемент

    TEXT = "#1f2937"  # Основний текст
    TEXT_MUTED = "#6b7280"  # Приглушений текст
    TEXT_BRIGHT = "#111827"  # Яскравий текст

    ACCENT = "#2563eb"  # Основний акцент (синій)
    ACCENT_HOVER = "#1d4ed8"  # Акцент hover
    SUCCESS = "#16a34a"  # Зелений
    WARNING = "#d97706"  # Жовтий
    DANGER = "#dc2626"  # Червоний
    INFO = "#0891b2"  # Блакитний

    BORDER = "#d1d5db"  # Рамки
    BORDER_LIGHT = "#e5e7eb"  # Світлі рамки

    SIDEBAR_BG = "#ffffff"
    SIDEBAR_ACTIVE = "#e8eefc"
    SIDEBAR_ACTIVE_TEXT = "#1d4ed8"

    @classmethod
    def apply(cls, app: QApplication):
        """Застосувати тему до додатку."""
        app.setStyle("Fusion")

        # Шрифт
        font = QFont("Segoe UI", 10)
        font.setStyleHint(QFont.StyleHint.SansSerif)
        app.setFont(font)

        # Палітра
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(cls.BG))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(cls.TEXT))
        palette.setColor(QPalette.ColorRole.Base, QColor(cls.BG_CARD))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(cls.BG_HOVER))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(cls.BG_DARK))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(cls.TEXT))
        palette.setColor(QPalette.ColorRole.Text, QColor(cls.TEXT))
        palette.setColor(QPalette.ColorRole.Button, QColor(cls.BG_HOVER))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(cls.TEXT))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(cls.TEXT_BRIGHT))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(cls.ACCENT))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(cls.TEXT_MUTED))
        app.setPalette(palette)

        # QSS — додаткові стилі
        app.setStyleSheet(cls._stylesheet())

    @classmethod
    def _stylesheet(cls) -> str:
        return f"""
        QMainWindow {{
            background-color: {cls.BG};
        }}
        QDialog {{
            background-color: {cls.BG};
        }}
        QPushButton {{
            background-color: {cls.BG_HOVER};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {cls.BG_ACTIVE};
            border-color: {cls.ACCENT};
        }}
        QPushButton:pressed {{
            background-color: {cls.ACCENT};
            color: #ffffff;
        }}
        QPushButton#primary {{
            background-color: {cls.ACCENT};
            color: {cls.BG_DARK};
            font-weight: bold;
        }}
        QPushButton#primary:hover {{
            background-color: {cls.ACCENT_HOVER};
        }}
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
            background-color: {cls.BG_CARD};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            border-radius: 6px;
            padding: 6px 10px;
        }}
        QLineEdit:focus, QComboBox:focus {{
            border-color: {cls.ACCENT};
        }}
        QTableView {{
            background-color: {cls.BG_CARD};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            border-radius: 8px;
            gridline-color: {cls.BORDER};
            selection-background-color: {cls.ACCENT};
            selection-color: #ffffff;
        }}
        QTableView::item {{
            padding: 6px 10px;
            border-bottom: 1px solid {cls.BORDER};
        }}
        QTableView::item:selected {{
            background-color: {cls.ACCENT};
            color: {cls.BG_DARK};
        }}
        QHeaderView::section {{
            background-color: {cls.BG_HOVER};
            color: {cls.TEXT};
            padding: 8px 10px;
            border: none;
            border-bottom: 2px solid {cls.ACCENT};
            font-weight: bold;
        }}
        QTabWidget::pane {{
            border: 1px solid {cls.BORDER};
            border-radius: 8px;
            background-color: {cls.BG_CARD};
        }}
        QTabBar::tab {{
            background-color: {cls.BG_HOVER};
            color: {cls.TEXT_MUTED};
            padding: 8px 16px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            margin-right: 4px;
        }}
        QTabBar::tab:selected {{
            background-color: {cls.BG_CARD};
            color: {cls.ACCENT};
            font-weight: bold;
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {cls.BG_ACTIVE};
            color: {cls.TEXT};
        }}
        QGroupBox {{
            border: 1px solid {cls.BORDER};
            border-radius: 10px;
            margin-top: 12px;
            padding-top: 12px;
            font-weight: bold;
            color: {cls.TEXT_BRIGHT};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
        }}
        QScrollBar:vertical {{
            background-color: {cls.BG};
            width: 10px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {cls.BG_HOVER};
            border-radius: 5px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {cls.BG_ACTIVE};
        }}
        QLabel#title {{
            font-size: 18px;
            font-weight: bold;
            color: {cls.TEXT_BRIGHT};
        }}
        QLabel#subtitle {{
            font-size: 12px;
            color: {cls.TEXT_MUTED};
        }}
        QLabel#stat_value {{
            font-size: 28px;
            font-weight: bold;
            color: {cls.ACCENT};
        }}
        QLabel#stat_label {{
            font-size: 11px;
            color: {cls.TEXT_MUTED};
            text-transform: uppercase;
        }}
        """
