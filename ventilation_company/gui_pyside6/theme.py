"""Темна тема VentCompany для PySide6.

Використання:
    from ventilation_company.gui_pyside6.theme import Theme
    Theme.apply(app)
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette, QFont
from PySide6.QtWidgets import QApplication


class Theme:
    """Catppuccin Mocha — сучасна темна тема."""

    # Кольори
    BG = "#1e1e2e"           # Фон вікна
    BG_DARK = "#11111b"      # Темніший фон
    BG_CARD = "#181825"      # Фон карток/панелей
    BG_HOVER = "#313244"     # Hover ефект
    BG_ACTIVE = "#45475a"    # Активний елемент

    TEXT = "#cdd6f4"         # Основний текст
    TEXT_MUTED = "#6c7086"   # Приглушений текст
    TEXT_BRIGHT = "#f5e0dc"  # Яскравий текст

    ACCENT = "#89b4fa"       # Основний акцент (синій)
    ACCENT_HOVER = "#b4befe" # Акцент hover
    SUCCESS = "#a6e3a1"      # Зелений
    WARNING = "#f9e2af"      # Жовтий
    DANGER = "#f38ba8"       # Червоний
    INFO = "#74c7ec"         # Блакитний

    BORDER = "#313244"       # Рамки
    BORDER_LIGHT = "#45475a" # Світлі рамки

    SIDEBAR_BG = "#181825"
    SIDEBAR_ACTIVE = "#313244"
    SIDEBAR_ACTIVE_TEXT = "#89b4fa"

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
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(cls.BG_DARK))
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
            color: {cls.BG_DARK};
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
            selection-color: {cls.BG_DARK};
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
