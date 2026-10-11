"""Власний вибір дати: MonthPickerDialog + DatePicker.

Стандартний QCalendarWidget (popup у QDateEdit) ламає рендеринг,
коли в застосунку задано stylesheet — сітка дат сплющується, рядки
зникають, заголовки днів тижня не малюються. Це відома проблема Qt,
тож календар реалізовано як власна сітка кнопок, яка рендериться
надійно під будь-якими стилями.

Використання:
    picker = DatePicker(QDate.currentDate())
    ...
    picker.date() / picker.setDate(d)
"""

from PySide6.QtCore import QDate, QSize, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "нд"]
MONTHS = [
    "січень",
    "лютий",
    "березень",
    "квітень",
    "травень",
    "червень",
    "липень",
    "серпень",
    "вересень",
    "жовтень",
    "листопад",
    "грудень",
]


class MonthPickerDialog(QDialog):
    """Модальне вікно з сіткою дат на місяць.

    Один клік по дню обирає дату й закриває діалог.
    Дні поза поточним місяцем показані сірим і теж доступні —
    клік по них одразу обирає ту дату.
    """

    def __init__(self, date: QDate | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Оберіть дату")
        self.setModal(True)
        initial = date if date is not None else QDate.currentDate()
        self._initial = initial
        self.selected_date: QDate | None = None

        root = QVBoxLayout(self)
        root.setSpacing(10)

        # Панель навігації: ◀ | місяць | рік | ▶
        nav = QHBoxLayout()
        nav.setSpacing(6)
        self.btn_prev = QPushButton("◀")
        self.btn_prev.setFixedWidth(44)
        self.btn_prev.setToolTip("Попередній місяць")
        self.combo_month = QComboBox()
        self.combo_month.addItems(MONTHS)
        self.combo_month.setCurrentIndex(initial.month() - 1)
        self.spin_year = QSpinBox()
        self.spin_year.setRange(2000, 2100)
        self.spin_year.setValue(initial.year())
        self.spin_year.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.btn_next = QPushButton("▶")
        self.btn_next.setFixedWidth(44)
        self.btn_next.setToolTip("Наступний місяць")
        nav.addWidget(self.btn_prev)
        nav.addWidget(self.combo_month, 1)
        nav.addWidget(self.spin_year)
        nav.addWidget(self.btn_next)
        root.addLayout(nav)

        # Сітка: заголовки днів тижня + 6 рядів по 7 кнопок
        self.grid = QGridLayout()
        self.grid.setSpacing(4)
        for col, name in enumerate(WEEKDAYS):
            label = QLabel(name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if col >= 5:  # сб/нд — червоним
                label.setStyleSheet("color: #dc2626; font-weight: bold;")
            else:
                label.setStyleSheet("font-weight: bold;")
            self.grid.addWidget(label, 0, col)
        root.addLayout(self.grid)

        self.btn_prev.clicked.connect(lambda: self._shift_month(-1))
        self.btn_next.clicked.connect(lambda: self._shift_month(1))
        self.combo_month.currentIndexChanged.connect(self._rebuild_grid)
        self.spin_year.valueChanged.connect(self._rebuild_grid)

        self._rebuild_grid()

    # --- навігація -------------------------------------------------

    def _shift_month(self, delta: int) -> None:
        month = self.combo_month.currentIndex() + 1 + delta
        year = self.spin_year.value()
        if month < 1:
            month = 12
            self.spin_year.setValue(year - 1)
        elif month > 12:
            month = 1
            self.spin_year.setValue(year + 1)
        self.combo_month.blockSignals(True)
        self.combo_month.setCurrentIndex(month - 1)
        self.combo_month.blockSignals(False)
        self._rebuild_grid()

    # --- сітка дат -------------------------------------------------

    def _rebuild_grid(self) -> None:
        # Видаляємо старі кнопки днів (рядки 1..6)
        for row in range(1, 7):
            for col in range(7):
                item = self.grid.itemAtPosition(row, col)
                if item is not None:
                    widget = item.widget()
                    self.grid.removeItem(item)
                    if widget is not None:
                        widget.deleteLater()

        month = self.combo_month.currentIndex() + 1
        year = self.spin_year.value()
        first = QDate(year, month, 1)
        start = first.addDays(-(first.dayOfWeek() - 1))  # понеділок тижня
        today = QDate.currentDate()

        for index in range(42):
            day = start.addDays(index)
            btn = QPushButton(str(day.day()))
            btn.setMinimumSize(QSize(52, 40))
            btn.setStyleSheet("padding: 2px; font-size: 13px;")
            in_month = day.month() == month
            is_weekend = day.dayOfWeek() >= 6
            colors = []
            if not in_month:
                colors.append("color: #9ca3af;")
            elif is_weekend:
                colors.append("color: #dc2626;")
            if day == self._initial:
                colors.append("background-color: #2563eb; color: #ffffff; font-weight: bold;")
            elif day == today:
                colors.append("border: 2px solid #2563eb;")
            if colors:
                btn.setStyleSheet("padding: 2px; font-size: 13px; " + " ".join(colors))
            btn.clicked.connect(lambda checked=False, d=day: self._pick(d))
            self.grid.addWidget(btn, index // 7 + 1, index % 7)

    def _pick(self, day: QDate) -> None:
        self.selected_date = day
        self.accept()


class DatePicker(QWidget):
    """QDateEdit із кнопкою відкриття власного календаря.

    API сумісний із QDateEdit: date(), setDate(); setEnabled()
    розповсюджується і на поле, і на кнопку.
    """

    def __init__(self, date: QDate | None = None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.edit = QDateEdit(date if date is not None else QDate.currentDate())
        self.edit.setDisplayFormat("yyyy-MM-dd")
        self.btn = QPushButton("Обрати")
        self.btn.setFixedWidth(72)
        self.btn.setToolTip("Обрати дату з календаря")
        self.btn.clicked.connect(self._open_picker)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.btn)

    def _open_picker(self) -> None:
        dlg = MonthPickerDialog(self.edit.date(), self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_date:
            self.edit.setDate(dlg.selected_date)

    def date(self) -> QDate:
        return self.edit.date()

    def setDate(self, date: QDate) -> None:  # noqa: N802 (Qt-стиль API)
        self.edit.setDate(date)

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802 (Qt-стиль API)
        super().setEnabled(enabled)
        self.edit.setEnabled(enabled)
        self.btn.setEnabled(enabled)
