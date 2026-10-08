"""Допоміжні діалоги картки проєкту (роботи, витрати, комплектуючі, оплати).

Механічно винесено з project_card_dialog.py (рефакторинг v2.10) — логіка
не змінювалася. Імена реекспортуються з project_card_dialog для зворотної
сумісності імпортів.
"""

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ventilation_company.gui_pyside6.calendar_picker import DatePicker
from ventilation_company.gui_pyside6.table_utils import setup_table
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.services.business_settings import BusinessSettings


class WorkEditDialog(QDialog):
    def __init__(self, project_id: int, work_data=None, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.work_id = work_data.get("id") if work_data else None
        self.setWindowTitle("Редагувати роботу" if work_data else "Нова робота")
        self.setMinimumWidth(350)
        self._build_ui(work_data)

    def _build_ui(self, work_data):
        layout = QFormLayout(self)

        self.combo_work = QComboBox()
        self.combo_work.addItem("— Вручну —", None)
        self._work_rates = BusinessSettings.get_instance().work_rates
        for key in self._work_rates:
            self.combo_work.addItem(key.replace("_", " "), key)
        self.combo_work.currentIndexChanged.connect(self._on_work_selected)
        layout.addRow("Типова робота (з Бізнес)", self.combo_work)

        self.edit_name = QLineEdit()
        self.edit_name.setText(work_data.get("work_name", "") if work_data else "")
        layout.addRow("Назва роботи *", self.edit_name)
        self.spin_qty = QDoubleSpinBox()
        self.spin_qty.setRange(0.01, 99999)
        self.spin_qty.setValue(work_data.get("quantity", 1) if work_data else 1)
        layout.addRow("Кількість", self.spin_qty)
        self.edit_unit = QLineEdit()
        self.edit_unit.setText(work_data.get("unit", "год") if work_data else "год")
        layout.addRow("Од. виміру", self.edit_unit)
        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0, 999999)
        self.spin_price.setSuffix(" ₴")
        self.spin_price.setDecimals(2)
        self.spin_price.setValue(work_data.get("unit_price", 0) if work_data else 0)
        layout.addRow("Ціна за од.", self.spin_price)
        # Планування (v2.9): дата виконання/монтажу та бригада.
        # DatePicker = поле дати + власний календар (стандартний
        # QCalendarWidget ламається при наявності stylesheet).
        date_row = QHBoxLayout()
        self.chk_has_date = QCheckBox("Запланована дата:")
        self.date_edit = DatePicker(QDate.currentDate())
        date_row.addWidget(self.chk_has_date)
        date_row.addWidget(self.date_edit, 1)
        layout.addRow(date_row)

        def _toggle_date(checked: bool):
            self.date_edit.setEnabled(checked)

        self.chk_has_date.toggled.connect(_toggle_date)
        if work_data:
            raw_date = str(work_data.get("work_date") or "")
            has_date = bool(raw_date)
            self.chk_has_date.setChecked(has_date)
            if has_date:
                self.date_edit.setDate(QDate.fromString(raw_date, "yyyy-MM-dd"))
        else:
            # Для нової роботи дата — основне поле (монтажі), тож увімкнена
            self.chk_has_date.setChecked(True)
        _toggle_date(self.chk_has_date.isChecked())

        self.edit_crew = QLineEdit()
        self.edit_crew.setPlaceholderText("напр. Бригада №2")
        if work_data:
            self.edit_crew.setText(str(work_data.get("crew") or ""))
        layout.addRow("Бригада / виконавець", self.edit_crew)
        btn = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btn.accepted.connect(self.accept)
        btn.rejected.connect(self.reject)
        layout.addRow(btn)

        if work_data:
            self._preselect_work(work_data.get("work_name", ""))

    def _normalize_date(self) -> str:
        """Повертає '' (без дати) або YYYY-MM-DD з QDateEdit."""
        if not self.chk_has_date.isChecked():
            return ""
        return self.date_edit.date().toString("yyyy-MM-dd")

    def _on_work_selected(self, index: int):
        key = self.combo_work.itemData(index)
        if not key:
            return
        rate = BusinessSettings.get_instance().get_work_rate(key)
        self.edit_name.setText(key.replace("_", " "))
        self.edit_unit.setText(str(rate.get("одиниця", "год")))
        self.spin_price.setValue(float(rate.get("ціна", 0) or 0))

    def _preselect_work(self, work_name: str):
        """Якщо назва роботи збігається з типовою — підсвітити її у списку."""
        self.combo_work.blockSignals(True)
        for i in range(self.combo_work.count()):
            key = self.combo_work.itemData(i)
            if key and key.replace("_", " ") == work_name:
                self.combo_work.setCurrentIndex(i)
                break
        self.combo_work.blockSignals(False)

    def get_data(self):
        qty = self.spin_qty.value()
        price = self.spin_price.value()
        return {
            "project_id": self.project_id,
            "work_name": self.edit_name.text().strip(),
            "quantity": qty,
            "unit": self.edit_unit.text().strip(),
            "unit_price": price,
            "total_price": round(qty * price, 2),
            "work_date": self._normalize_date(),
            "crew": self.edit_crew.text().strip(),
        }


class ExpenseEditDialog(QDialog):
    def __init__(self, project_id: int, expense_data=None, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.expense_id = expense_data.get("id") if expense_data else None
        self.setWindowTitle("Редагувати витрату" if expense_data else "Нова витрата")
        self.setMinimumWidth(350)
        self._build_ui(expense_data)

    def _build_ui(self, expense_data):
        layout = QFormLayout(self)
        self.direction_combo = QComboBox()
        self.direction_combo.addItem("➖ Витрата", "minus")
        self.direction_combo.addItem("➕ Плюс", "plus")
        current_direction = expense_data.get("direction", "minus") if expense_data else "minus"
        self.direction_combo.setCurrentIndex(1 if current_direction == "plus" else 0)
        layout.addRow("Тип:", self.direction_combo)
        self.edit_name = QLineEdit()
        self.edit_name.setText(expense_data.get("expense_name", "") if expense_data else "")
        layout.addRow("Назва витрати *", self.edit_name)
        self.spin_qty = QDoubleSpinBox()
        self.spin_qty.setRange(0.01, 99999)
        self.spin_qty.setValue(expense_data.get("quantity", 1) if expense_data else 1)
        layout.addRow("Кількість", self.spin_qty)
        self.edit_unit = QLineEdit()
        self.edit_unit.setText(expense_data.get("unit", "шт") if expense_data else "шт")
        layout.addRow("Од. виміру", self.edit_unit)
        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0, 999999)
        self.spin_price.setSuffix(" ₴")
        self.spin_price.setDecimals(2)
        self.spin_price.setValue(expense_data.get("unit_price", 0) if expense_data else 0)
        layout.addRow("Ціна за од.", self.spin_price)
        btn = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btn.accepted.connect(self.accept)
        btn.rejected.connect(self.reject)
        layout.addRow(btn)

    def get_data(self):
        qty = self.spin_qty.value()
        price = self.spin_price.value()
        return {
            "project_id": self.project_id,
            "expense_name": self.edit_name.text().strip(),
            "quantity": qty,
            "unit": self.edit_unit.text().strip(),
            "unit_price": price,
            "total_price": round(qty * price, 2),
            "direction": self.direction_combo.currentData(),
        }


class ComponentPickerDialog(QDialog):
    """Вибір комплектуючої з бізнес-налаштувань для додавання у витрати проєкту."""

    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle("Комплектуючі системи вентиляції")
        self.setMinimumSize(480, 380)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        lbl = QLabel("Оберіть комплектуючу зі списку (ціни — з «Налаштування → Бізнес»):")
        lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        layout.addWidget(lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Назва", "Ціна, грн", "Од."])
        setup_table(self.table, select_rows=True, single_selection=True, read_only=True)
        layout.addWidget(self.table)

        self._keys: list[str] = []
        components = BusinessSettings.get_instance().components
        for key, data in components.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(key.replace("_", " ")))
            self.table.setItem(row, 1, QTableWidgetItem(str(data.get("ціна", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(data.get("одиниця", ""))))
            self._keys.append(key)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        if self.table.rowCount():
            self.table.selectRow(0)

        form = QFormLayout()
        self.spin_qty = QDoubleSpinBox()
        self.spin_qty.setRange(0.01, 99999)
        self.spin_qty.setValue(1)
        form.addRow("Кількість", self.spin_qty)
        layout.addLayout(form)

        btn = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn.accepted.connect(self.accept)
        btn.rejected.connect(self.reject)
        layout.addWidget(btn)

    def get_data(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._keys):
            return None
        key = self._keys[row]
        data = BusinessSettings.get_instance().get_component(key)
        qty = self.spin_qty.value()
        price = float(data.get("ціна", 0) or 0)
        return {
            "project_id": self.project_id,
            "expense_name": key.replace("_", " "),
            "quantity": qty,
            "unit": str(data.get("одиниця", "шт")),
            "unit_price": price,
            "total_price": round(qty * price, 2),
            "direction": "minus",
        }


# Типові призначення оплат (випадаючий список у діалозі оплати).
PAYMENT_PURPOSES = [
    "Аванс",
    "Проміжна оплата",
    "Фінальний розрахунок",
    "Повернення коштів",
    "Оплата за проєкт",
]


class PaymentEditDialog(QDialog):
    def __init__(self, project_id: int, payment_data=None, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.payment_data = payment_data or {}
        self.setWindowTitle("Редагувати оплату" if payment_data else "Нова оплата")
        self.setMinimumWidth(380)
        layout = QFormLayout(self)
        self.date_edit = DatePicker(QDate.currentDate())
        value = self.payment_data.get("date")
        if value:
            try:
                self.date_edit.setDate(QDate(value.year, value.month, value.day))
            except Exception:
                self.date_edit.setDate(QDate.fromString(str(value)[:10], "yyyy-MM-dd"))
        layout.addRow("Дата:", self.date_edit)
        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0, 999999999)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(" ₴")
        self.spin_amount.setValue(float(self.payment_data.get("amount") or 0))
        layout.addRow("Сума:", self.spin_amount)
        self.combo_type = QComboBox()
        self.combo_type.addItems(["вхідний", "вихідний"])
        self.combo_type.setCurrentText(self.payment_data.get("type") or "вхідний")
        layout.addRow("Тип:", self.combo_type)
        self.edit_purpose = QComboBox()
        self.edit_purpose.setEditable(True)
        self.edit_purpose.addItems(PAYMENT_PURPOSES)
        current_purpose = self.payment_data.get("purpose") or "Оплата за проєкт"
        self.edit_purpose.setCurrentText(current_purpose)
        layout.addRow("Призначення:", self.edit_purpose)
        self.edit_notes = QLineEdit(self.payment_data.get("notes") or "")
        layout.addRow("Нотатки:", self.edit_notes)
        btn = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btn.accepted.connect(self.accept)
        btn.rejected.connect(self.reject)
        layout.addRow(btn)

    def get_data(self):
        return {
            "project_id": self.project_id,
            "date": self.date_edit.date().toPython(),
            "amount": self.spin_amount.value(),
            "currency": "UAH",
            "type": self.combo_type.currentText(),
            "purpose": self.edit_purpose.currentText().strip(),
            "notes": self.edit_notes.text().strip(),
        }


class DrawingsTable(QTableWidget):
    """Таблиця креслень із підтримкою drag-and-drop файлів."""

    filesDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.filesDropped.emit(paths)
            event.acceptProposedAction()


DRAWING_FILE_FILTER = (
    "Креслення та моделі (*.dwg *.dxf *.pdf *.rvt *.rfa *.ifc "
    "*.fcstd *.step *.stp);;Всі файли (*)"
)
