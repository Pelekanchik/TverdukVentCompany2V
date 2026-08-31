"""Вкладка "Вироби" (PySide6).

Таблиця з фільтрами за типом, матеріалом, товщиною.
Діалог додавання/редагування виробу.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QLineEdit, QComboBox, QMessageBox, QAbstractItemView,
    QDialog, QFormLayout, QSpinBox, QDoubleSpinBox, QDialogButtonBox
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.database.db import get_db


class ProductDialog(QDialog):
    """Діалог додавання/редагування виробу."""

    def __init__(self, product_data: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔧 Редагувати виріб" if product_data else "➕ Новий виріб")
        self.setMinimumWidth(420)
        self._data = product_data or {}
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Назва
        self.edit_name = QLineEdit(self._data.get("name", ""))
        self.edit_name.setPlaceholderText("Напр.: Відвод круглий 250мм")
        layout.addRow("Назва *", self.edit_name)

        # Тип
        self.combo_type = QComboBox()
        self.combo_type.addItems([
            "Труба кругла", "Труба прямокутна",
            "Відвод круглий", "Відвод прямокутний",
            "Трійник круглий", "Трійник прямокутний",
            "Перехід", "Фланець", "Заглушка", "Гнучка вставка"
        ])
        self.combo_type.setCurrentText(self._data.get("product_type", "Труба кругла"))
        layout.addRow("Тип", self.combo_type)

        # Розміри
        sizes = QHBoxLayout()
        self.spin_width = QDoubleSpinBox()
        self.spin_width.setRange(50, 2000)
        self.spin_width.setSuffix(" мм")
        self.spin_width.setValue(self._data.get("width", 250))
        sizes.addWidget(self.spin_width)

        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(50, 2000)
        self.spin_height.setSuffix(" мм")
        self.spin_height.setValue(self._data.get("height", 0))
        sizes.addWidget(self.spin_height)

        self.spin_length = QDoubleSpinBox()
        self.spin_length.setRange(100, 5000)
        self.spin_length.setSuffix(" мм")
        self.spin_length.setValue(self._data.get("length", 1000))
        sizes.addWidget(self.spin_length)
        layout.addRow("Ш/В/Д (мм)", sizes)

        # Матеріал
        self.combo_material = QComboBox()
        self.combo_material.addItems(["Оцинкована сталь", "Нержавіюча сталь", "Алюміній"])
        self.combo_material.setCurrentText(self._data.get("material", "Оцинкована сталь"))
        layout.addRow("Матеріал", self.combo_material)

        # Товщина
        self.combo_thickness = QComboBox()
        self.combo_thickness.addItems(["0.5", "0.7", "0.9", "1.0", "1.2", "1.5", "2.0"])
        self.combo_thickness.setCurrentText(str(self._data.get("thickness", "0.7")))
        layout.addRow("Товщина (мм)", self.combo_thickness)

        # Кількість
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 9999)
        self.spin_qty.setValue(self._data.get("quantity", 1))
        layout.addRow("Кількість", self.spin_qty)

        # Ціна
        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0, 999999)
        self.spin_price.setSuffix(" ₴")
        self.spin_price.setDecimals(2)
        self.spin_price.setValue(self._data.get("unit_price", 0))
        layout.addRow("Ціна за шт.", self.spin_price)

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_save(self):
        if not self.edit_name.text().strip():
            QMessageBox.warning(self, "Помилка", "Введіть назву виробу")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.edit_name.text().strip(),
            "product_type": self.combo_type.currentText(),
            "width": self.spin_width.value(),
            "height": self.spin_height.value(),
            "length": self.spin_length.value(),
            "material": self.combo_material.currentText(),
            "thickness": float(self.combo_thickness.currentText()),
            "quantity": self.spin_qty.value(),
            "unit_price": self.spin_price.value(),
            "total_price": self.spin_price.value() * self.spin_qty.value(),
        }


class ProductsTab(QWidget):
    """Вкладка управління виробами з фільтрами та таблицею."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_data: list[dict] = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ── Заголовок ──
        header = QHBoxLayout()
        lbl_title = QLabel("🔧 Вироби")
        lbl_title.setObjectName("title")
        header.addWidget(lbl_title)
        header.addStretch()

        btn_new = QPushButton("➕ Додати виріб")
        btn_new.setObjectName("primary")
        btn_new.setMinimumHeight(32)
        btn_new.clicked.connect(self._on_add)
        header.addWidget(btn_new)
        layout.addLayout(header)

        # ── Фільтри ──
        filters = QHBoxLayout()
        filters.setSpacing(12)

        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("🔍 Пошук за назвою...")
        self.edit_search.setFixedWidth(220)
        self.edit_search.setMinimumHeight(32)
        self.edit_search.textChanged.connect(self._apply_filters)
        filters.addWidget(self.edit_search)

        filters.addSpacing(16)

        lbl_type = QLabel("Тип:")
        lbl_type.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        filters.addWidget(lbl_type)
        self.filter_type = QComboBox()
        self.filter_type.addItem("Всі")
        self.filter_type.addItems([
            "Труба кругла", "Труба прямокутна",
            "Відвод круглий", "Відвод прямокутний",
            "Трійник", "Перехід", "Фланець", "Заглушка", "Гнучка вставка"
        ])
        self.filter_type.currentTextChanged.connect(self._apply_filters)
        filters.addWidget(self.filter_type)

        lbl_mat = QLabel("Матеріал:")
        lbl_mat.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        filters.addWidget(lbl_mat)
        self.filter_material = QComboBox()
        self.filter_material.addItem("Всі")
        self.filter_material.addItems(["Оцинкована сталь", "Нержавіюча сталь", "Алюміній"])
        self.filter_material.currentTextChanged.connect(self._apply_filters)
        filters.addWidget(self.filter_material)

        lbl_thick = QLabel("Товщина:")
        lbl_thick.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        filters.addWidget(lbl_thick)
        self.filter_thickness = QComboBox()
        self.filter_thickness.addItem("Всі")
        self.filter_thickness.addItems(["0.5", "0.7", "0.9", "1.0", "1.2", "1.5", "2.0"])
        self.filter_thickness.currentTextChanged.connect(self._apply_filters)
        filters.addWidget(self.filter_thickness)

        filters.addStretch()

        btn_reset = QPushButton("♻️ Скинути")
        btn_reset.setMinimumHeight(28)
        btn_reset.clicked.connect(self._reset_filters)
        filters.addWidget(btn_reset)

        layout.addLayout(filters)

        # ── Таблиця ──
        self.table = QTableView()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(400)
        self.table.doubleClicked.connect(self._on_edit)
        layout.addWidget(self.table)

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "ID", "Назва", "Тип", "Розміри (мм)", "Матеріал", "Товщ.", "К-ть", "Ціна", "Сума"
        ])
        self.table.setModel(self.model)

        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 220)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 130)
        self.table.setColumnWidth(5, 60)
        self.table.setColumnWidth(6, 60)
        self.table.setColumnWidth(7, 90)
        self.table.setColumnWidth(8, 90)

        # ── Кнопки дій ──
        actions = QHBoxLayout()
        actions.addStretch()

        btn_edit = QPushButton("✏️ Редагувати")
        btn_edit.clicked.connect(self._on_edit)
        actions.addWidget(btn_edit)

        btn_del = QPushButton("🗑️ Видалити")
        btn_del.setStyleSheet(f"color: {Theme.DANGER};")
        btn_del.clicked.connect(self._on_delete)
        actions.addWidget(btn_del)

        btn_refresh = QPushButton("🔄 Оновити")
        btn_refresh.clicked.connect(self._load_data)
        actions.addWidget(btn_refresh)

        layout.addLayout(actions)

        # ── Підсумок ──
        self.lbl_summary = QLabel("Всього: 0 виробів | Сума: ₴ 0")
        self.lbl_summary.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 12px; padding: 4px;")
        layout.addWidget(self.lbl_summary)

    def _load_data(self):
        """Завантажити демо-дані."""
        self._all_data = [
            {"id": 1, "name": "Труба кругла Ø250", "product_type": "Труба кругла",
             "width": 250, "height": 0, "length": 1000, "material": "Оцинкована сталь",
             "thickness": 0.7, "quantity": 5, "unit_price": 450.0},
            {"id": 2, "name": "Відвод круглий 90° Ø250", "product_type": "Відвод круглий",
             "width": 250, "height": 0, "length": 250, "material": "Оцинкована сталь",
             "thickness": 0.7, "quantity": 3, "unit_price": 680.0},
            {"id": 3, "name": "Труба прямокутна 400×300", "product_type": "Труба прямокутна",
             "width": 400, "height": 300, "length": 1200, "material": "Нержавіюча сталь",
             "thickness": 1.0, "quantity": 2, "unit_price": 1850.0},
            {"id": 4, "name": "Фланець круглий Ø250", "product_type": "Фланець",
             "width": 250, "height": 0, "length": 0, "material": "Оцинкована сталь",
             "thickness": 1.5, "quantity": 10, "unit_price": 120.0},
            {"id": 5, "name": "Гнучка вставка Ø250", "product_type": "Гнучка вставка",
             "width": 250, "height": 0, "length": 150, "material": "Алюміній",
             "thickness": 0.5, "quantity": 4, "unit_price": 320.0},
        ]
        self._apply_filters()

    def _apply_filters(self):
        search = self.edit_search.text().lower()
        f_type = self.filter_type.currentText()
        f_mat = self.filter_material.currentText()
        f_thick = self.filter_thickness.currentText()

        filtered = []
        for item in self._all_data:
            if search and search not in item.get("name", "").lower():
                continue
            if f_type != "Всі" and f_type not in item.get("product_type", ""):
                continue
            if f_mat != "Всі" and f_mat != item.get("material", ""):
                continue
            if f_thick != "Всі" and f_thick != str(item.get("thickness", "")):
                continue
            filtered.append(item)

        self._fill_table(filtered)
        self._update_summary(filtered)

    def _fill_table(self, data: list[dict]):
        self.model.removeRows(0, self.model.rowCount())
        for item in data:
            dims = f"Ø{item['width']:.0f}" if item.get("height", 0) == 0 else f"{item['width']:.0f}×{item['height']:.0f}"
            if item.get("length", 0) > 0:
                dims += f" × {item['length']:.0f}"
            total = item.get("unit_price", 0) * item.get("quantity", 1)
            row = [
                QStandardItem(str(item.get("id", "—"))),
                QStandardItem(item.get("name", "—")),
                QStandardItem(item.get("product_type", "—")),
                QStandardItem(dims),
                QStandardItem(item.get("material", "—")),
                QStandardItem(str(item.get("thickness", "—"))),
                QStandardItem(str(item.get("quantity", 1))),
                QStandardItem(f"₴ {item.get('unit_price', 0):,.2f}"),
                QStandardItem(f"₴ {total:,.2f}"),
            ]
            for cell in row:
                cell.setEditable(False)
            self.model.appendRow(row)

    def _update_summary(self, data: list[dict]):
        total_qty = sum(i.get("quantity", 1) for i in data)
        total_sum = sum(i.get("unit_price", 0) * i.get("quantity", 1) for i in data)
        self.lbl_summary.setText(f"Всього: {len(data)} позицій | Кількість: {total_qty} шт | Сума: ₴ {total_sum:,.2f}")

    def _reset_filters(self):
        self.edit_search.clear()
        self.filter_type.setCurrentIndex(0)
        self.filter_material.setCurrentIndex(0)
        self.filter_thickness.setCurrentIndex(0)

    def _get_selected_row_data(self) -> dict | None:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        row = idx.row()
        id_val = self.model.item(row, 0).text()
        for item in self._all_data:
            if str(item.get("id")) == id_val:
                return item
        return None

    def _on_add(self):
        dlg = ProductDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            data["id"] = len(self._all_data) + 1
            self._all_data.append(data)
            self._apply_filters()

    def _on_edit(self):
        item = self._get_selected_row_data()
        if not item:
            QMessageBox.warning(self, "Увага", "Виберіть виріб для редагування")
            return
        dlg = ProductDialog(item, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_data = dlg.get_data()
            new_data["id"] = item["id"]
            for i, old in enumerate(self._all_data):
                if old.get("id") == item["id"]:
                    self._all_data[i] = new_data
                    break
            self._apply_filters()

    def _on_delete(self):
        item = self._get_selected_row_data()
        if not item:
            QMessageBox.warning(self, "Увага", "Виберіть виріб для видалення")
            return
        reply = QMessageBox.question(
            self, "Видалення",
            f'Видалити виріб "{item.get("name", "")}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._all_data = [i for i in self._all_data if i.get("id") != item.get("id")]
            self._apply_filters()

    def refresh(self):
        self._load_data()
