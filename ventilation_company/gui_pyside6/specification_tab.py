"""Вкладка "Специфікація" (PySide6).

Вибір проєкту → таблиця виробів у проєкті → підсумки (вага, площа, сума).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QComboBox, QMessageBox, QAbstractItemView, QLineEdit,
    QDialog, QFormLayout, QSpinBox, QDoubleSpinBox, QDialogButtonBox,
    QGroupBox, QSplitter
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

from ventilation_company.gui_pyside6.theme import Theme


class AddProductDialog(QDialog):
    """Діалог додавання виробу у специфікацію проєкту."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle("➕ Додати у специфікацію")
        self.setMinimumWidth(400)
        self._build_ui()

    def _load_from_db(self):
        """Завантажити вироби з БД для активного проєкту."""
        from ventilation_company.database.repositories.product_repo import ProductRepository
        project_id = self.main_window.active_project_id if self.main_window else None
        if not project_id:
            return
        try:
            items = ProductRepository.get_all(project_id=project_id)
            for item in items:
                self._items.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "product_type": item.get("product_type"),
                    "width": item.get("width"),
                    "height": item.get("height"),
                    "length": item.get("length"),
                    "material": item.get("material"),
                    "thickness": item.get("thickness"),
                    "quantity": item.get("quantity"),
                    "unit_price": item.get("unit_price"),
                    "total_price": item.get("total_price"),
                })
            self._populate_table()
        except Exception as e:
            print(f"Помилка завантаження специфікації: {e}")

    def on_project_changed(self, project_id: int | None):
        """При зміні проєкту — оновити специфікацію."""
        self._items.clear()
        self.model.removeRows(0, self.model.rowCount())
        if project_id:
            self._load_from_db()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Назва
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("Напр.: Повітропровід 400×200×1000")
        layout.addRow("Назва *", self.edit_name)

        # Тип
        self.combo_type = QComboBox()
        self.combo_type.addItems([
            "Повітропровід", "Відвод", "Трійник", "Перехід",
            "Фланець", "Заглушка", "Гнучка вставка", "Дифузор", "Решітка"
        ])
        layout.addRow("Тип", self.combo_type)

        # Розміри
        sizes = QHBoxLayout()
        self.spin_a = QDoubleSpinBox()
        self.spin_a.setRange(0, 5000)
        self.spin_a.setSuffix(" мм")
        self.spin_a.setDecimals(0)
        sizes.addWidget(QLabel("A:"))
        sizes.addWidget(self.spin_a)

        self.spin_b = QDoubleSpinBox()
        self.spin_b.setRange(0, 5000)
        self.spin_b.setSuffix(" мм")
        self.spin_b.setDecimals(0)
        sizes.addWidget(QLabel("B:"))
        sizes.addWidget(self.spin_b)

        self.spin_l = QDoubleSpinBox()
        self.spin_l.setRange(0, 10000)
        self.spin_l.setSuffix(" мм")
        self.spin_l.setDecimals(0)
        sizes.addWidget(QLabel("L:"))
        sizes.addWidget(self.spin_l)
        layout.addRow("Розміри (мм)", sizes)

        # Матеріал
        self.combo_material = QComboBox()
        self.combo_material.addItems(["Оцинкована сталь", "Нержавіюча сталь", "Алюміній"])
        layout.addRow("Матеріал", self.combo_material)

        # Товщина
        self.combo_thickness = QComboBox()
        self.combo_thickness.addItems(["0.5", "0.7", "0.9", "1.0", "1.2", "1.5", "2.0"])
        layout.addRow("Товщина", self.combo_thickness)

        # Кількість
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 9999)
        self.spin_qty.setValue(1)
        layout.addRow("Кількість", self.spin_qty)

        # Ціна
        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0, 999999)
        self.spin_price.setSuffix(" ₴")
        self.spin_price.setDecimals(2)
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
            "width": self.spin_a.value(),
            "height": self.spin_b.value(),
            "length": self.spin_l.value(),
            "material": self.combo_material.currentText(),
            "thickness": float(self.combo_thickness.currentText()),
            "quantity": self.spin_qty.value(),
            "unit_price": self.spin_price.value(),
            "total_price": self.spin_price.value() * self.spin_qty.value(),
            "metal_area_m2": 0,
            "blank_area_m2": 0,
            "weight_kg": 0,
        }


class SpecificationTab(QWidget):
    """Вкладка специфікації проєкту."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self._current_project_id: int | None = None
        self._build_ui()
        self._load_projects()

    def _load_from_db(self):
        """Завантажити вироби з БД для активного проєкту."""
        from ventilation_company.database.repositories.product_repo import ProductRepository
        project_id = self.main_window.active_project_id if self.main_window else None
        if not project_id:
            return
        try:
            items = ProductRepository.get_all(project_id=project_id)
            for item in items:
                self._items.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "product_type": item.get("product_type"),
                    "width": item.get("width"),
                    "height": item.get("height"),
                    "length": item.get("length"),
                    "material": item.get("material"),
                    "thickness": item.get("thickness"),
                    "quantity": item.get("quantity"),
                    "unit_price": item.get("unit_price"),
                    "total_price": item.get("total_price"),
                })
            self._populate_table()
        except Exception as e:
            print(f"Помилка завантаження специфікації: {e}")

    def on_project_changed(self, project_id: int | None):
        """При зміні проєкту — оновити специфікацію."""
        self._items.clear()
        self.model.removeRows(0, self.model.rowCount())
        if project_id:
            self._load_from_db()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ── Верхня панель: вибір проєкту ──
        top = QHBoxLayout()

        lbl_title = QLabel("📋 Специфікація")
        lbl_title.setObjectName("title")
        top.addWidget(lbl_title)

        top.addSpacing(24)

        lbl_proj = QLabel("Проєкт:")
        lbl_proj.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        top.addWidget(lbl_proj)

        self.combo_project = QComboBox()
        self.combo_project.setMinimumWidth(300)
        self.combo_project.setMinimumHeight(32)
        self.combo_project.currentIndexChanged.connect(self._on_project_changed)
        top.addWidget(self.combo_project)

        top.addStretch()

        btn_add = QPushButton("➕ Додати виріб")
        btn_add.setObjectName("primary")
        btn_add.setMinimumHeight(32)
        btn_add.clicked.connect(self._on_add_product)
        top.addWidget(btn_add)

        btn_refresh = QPushButton("🔄 Оновити")
        btn_refresh.setMinimumHeight(32)
        btn_refresh.clicked.connect(self._refresh_current)
        top.addWidget(btn_refresh)

        layout.addLayout(top)

        # ── Таблиця виробів ──
        self.table = QTableView()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(400)
        layout.addWidget(self.table)

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "№", "Назва", "Тип", "Розміри", "Матеріал", "Товщ.",
            "К-ть", "Площа м²", "Вага кг", "Ціна", "Сума"
        ])
        self.table.setModel(self.model)

        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 220)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 110)
        self.table.setColumnWidth(5, 50)
        self.table.setColumnWidth(6, 50)
        self.table.setColumnWidth(7, 70)
        self.table.setColumnWidth(8, 70)
        self.table.setColumnWidth(9, 80)
        self.table.setColumnWidth(10, 80)

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

        layout.addLayout(actions)

        # ── Підсумки ──
        summary = QHBoxLayout()
        summary.setSpacing(24)

        self.lbl_count = QLabel("Позицій: 0")
        self.lbl_count.setStyleSheet(f"color: {Theme.TEXT}; font-size: 13px; padding: 8px 16px; background: {Theme.BG_CARD}; border-radius: 8px;")
        summary.addWidget(self.lbl_count)

        self.lbl_qty = QLabel("Кількість: 0 шт")
        self.lbl_qty.setStyleSheet(f"color: {Theme.TEXT}; font-size: 13px; padding: 8px 16px; background: {Theme.BG_CARD}; border-radius: 8px;")
        summary.addWidget(self.lbl_qty)

        self.lbl_area = QLabel("Площа: 0 м²")
        self.lbl_area.setStyleSheet(f"color: {Theme.ACCENT}; font-size: 13px; padding: 8px 16px; background: {Theme.BG_CARD}; border-radius: 8px;")
        summary.addWidget(self.lbl_area)

        self.lbl_weight = QLabel("Вага: 0 кг")
        self.lbl_weight.setStyleSheet(f"color: {Theme.WARNING}; font-size: 13px; padding: 8px 16px; background: {Theme.BG_CARD}; border-radius: 8px;")
        summary.addWidget(self.lbl_weight)

        self.lbl_total = QLabel("Сума: ₴ 0")
        self.lbl_total.setStyleSheet(f"color: {Theme.SUCCESS}; font-size: 14px; font-weight: bold; padding: 8px 16px; background: {Theme.BG_CARD}; border-radius: 8px;")
        summary.addWidget(self.lbl_total)

        summary.addStretch()
        layout.addLayout(summary)

    def _load_projects(self):
        """Завантажити список проєктів (демо)."""
        self._projects = [
            {"id": 1, "name": "ПВ-2024-001 — Вентиляція офісу ТОВ 'Будівельник'"},
            {"id": 2, "name": "ПВ-2024-002 — Система витяжки ресторану 'Смак'"},
            {"id": 3, "name": "ПВ-2024-003 — Приточна установка складу №5"},
        ]
        self.combo_project.blockSignals(True)
        self.combo_project.clear()
        for p in self._projects:
            self.combo_project.addItem(p["name"], p["id"])
        self.combo_project.blockSignals(False)
        self._on_project_changed(0)

    def _on_project_changed(self, index: int):
        self._current_project_id = self.combo_project.itemData(index)
        self._load_specification()

    def _load_specification(self):
        """Завантажити вироби проєкту (демо)."""
        self._items: list[dict] = []

        # Демо-дані залежно від проєкту
        if self._current_project_id == 1:
            self._items = [
                {"pos": 1, "name": "Повітропровід 400×200×1000", "product_type": "Повітропровід",
                 "width": 400, "height": 200, "length": 1000, "material": "Оцинкована сталь",
                 "thickness": 0.7, "quantity": 8, "metal_area_m2": 11.2, "blank_area_m2": 12.5,
                 "weight_kg": 8.4, "unit_price": 450.0, "total_price": 3600.0},
                {"pos": 2, "name": "Відвод 90° 400×200", "product_type": "Відвод",
                 "width": 400, "height": 200, "length": 0, "material": "Оцинкована сталь",
                 "thickness": 0.7, "quantity": 4, "metal_area_m2": 1.8, "blank_area_m2": 2.1,
                 "weight_kg": 1.5, "unit_price": 680.0, "total_price": 2720.0},
                {"pos": 3, "name": "Трійник 400×200/200×200", "product_type": "Трійник",
                 "width": 400, "height": 200, "length": 500, "material": "Оцинкована сталь",
                 "thickness": 0.7, "quantity": 2, "metal_area_m2": 3.2, "blank_area_m2": 3.8,
                 "weight_kg": 2.8, "unit_price": 1200.0, "total_price": 2400.0},
                {"pos": 4, "name": "Фланець прямокутний 400×200", "product_type": "Фланець",
                 "width": 400, "height": 200, "length": 0, "material": "Оцинкована сталь",
                 "thickness": 1.5, "quantity": 16, "metal_area_m2": 0.32, "blank_area_m2": 0.4,
                 "weight_kg": 3.1, "unit_price": 85.0, "total_price": 1360.0},
                {"pos": 5, "name": "Гнучка вставка 400×200", "product_type": "Гнучка вставка",
                 "width": 400, "height": 200, "length": 150, "material": "Алюміній",
                 "thickness": 0.5, "quantity": 4, "metal_area_m2": 0.24, "blank_area_m2": 0.3,
                 "weight_kg": 0.2, "unit_price": 320.0, "total_price": 1280.0},
            ]
        elif self._current_project_id == 2:
            self._items = [
                {"pos": 1, "name": "Витяжний зонт 1200×800", "product_type": "Зонт",
                 "width": 1200, "height": 800, "length": 400, "material": "Нержавіюча сталь",
                 "thickness": 1.0, "quantity": 3, "metal_area_m2": 5.6, "blank_area_m2": 6.2,
                 "weight_kg": 12.5, "unit_price": 3500.0, "total_price": 10500.0},
                {"pos": 2, "name": "Повітропровід Ø315", "product_type": "Повітропровід",
                 "width": 315, "height": 0, "length": 2500, "material": "Нержавіюча сталь",
                 "thickness": 0.7, "quantity": 6, "metal_area_m2": 14.8, "blank_area_m2": 16.5,
                 "weight_kg": 11.2, "unit_price": 780.0, "total_price": 4680.0},
            ]
        else:
            self._items = [
                {"pos": 1, "name": "Повітропровід 500×300×1500", "product_type": "Повітропровід",
                 "width": 500, "height": 300, "length": 1500, "material": "Оцинкована сталь",
                 "thickness": 0.9, "quantity": 5, "metal_area_m2": 12.0, "blank_area_m2": 13.5,
                 "weight_kg": 10.2, "unit_price": 620.0, "total_price": 3100.0},
            ]

        self._fill_table()
        self._update_summary()

    def _fill_table(self):
        self.model.removeRows(0, self.model.rowCount())
        for item in self._items:
            dims = f"{item['width']:.0f}×{item['height']:.0f}" if item.get("height", 0) > 0 else f"Ø{item['width']:.0f}"
            if item.get("length", 0) > 0:
                dims += f" × {item['length']:.0f}"

            row = [
                QStandardItem(str(item.get("pos", "—"))),
                QStandardItem(item.get("name", "—")),
                QStandardItem(item.get("product_type", "—")),
                QStandardItem(dims),
                QStandardItem(item.get("material", "—")),
                QStandardItem(str(item.get("thickness", "—"))),
                QStandardItem(str(item.get("quantity", 1))),
                QStandardItem(f"{item.get('metal_area_m2', 0):.2f}"),
                QStandardItem(f"{item.get('weight_kg', 0):.2f}"),
                QStandardItem(f"₴ {item.get('unit_price', 0):,.2f}"),
                QStandardItem(f"₴ {item.get('total_price', 0):,.2f}"),
            ]
            for cell in row:
                cell.setEditable(False)
            self.model.appendRow(row)

    def _update_summary(self):
        count = len(self._items)
        qty = sum(i.get("quantity", 1) for i in self._items)
        area = sum(i.get("metal_area_m2", 0) * i.get("quantity", 1) for i in self._items)
        weight = sum(i.get("weight_kg", 0) * i.get("quantity", 1) for i in self._items)
        total = sum(i.get("total_price", 0) for i in self._items)

        self.lbl_count.setText(f"Позицій: {count}")
        self.lbl_qty.setText(f"Кількість: {qty} шт")
        self.lbl_area.setText(f"Площа: {area:.2f} м²")
        self.lbl_weight.setText(f"Вага: {weight:.2f} кг")
        self.lbl_total.setText(f"Сума: ₴ {total:,.2f}")

    def _on_add_product(self):
        dlg = AddProductDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            data["pos"] = len(self._items) + 1
            self._items.append(data)
            self._fill_table()
            self._update_summary()

    def _on_edit(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            QMessageBox.warning(self, "Увага", "Виберіть позицію для редагування")
            return
        row = idx.row()
        if row < 0 or row >= len(self._items):
            return
        # TODO: діалог редагування
        QMessageBox.information(self, "Редагування", "Діалог редагування буде тут")

    def _on_delete(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            QMessageBox.warning(self, "Увага", "Виберіть позицію для видалення")
            return
        row = idx.row()
        if row < 0 or row >= len(self._items):
            return
        name = self._items[row].get("name", "")
        reply = QMessageBox.question(
            self, "Видалення",
            f'Видалити позицію "{name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._items.pop(row)
            # Перенумерувати
            for i, item in enumerate(self._items, 1):
                item["pos"] = i
            self._fill_table()
            self._update_summary()

    def _refresh_current(self):
        self._load_specification()

    def refresh(self):
        self._load_projects()
