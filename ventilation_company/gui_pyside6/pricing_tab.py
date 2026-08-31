"""Вкладка "Ціноутворення" (PySide6).

Інтеграція з CostEngine — розрахунок собівартості та ціни виробу.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QComboBox, QMessageBox, QAbstractItemView,
    QDialog, QFormLayout, QDialogButtonBox, QSpinBox,
    QDoubleSpinBox, QLineEdit, QGroupBox, QGridLayout
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor

from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.calculations.cost_engine import CostEngine


class PriceCalcDialog(QDialog):
    """Діалог розрахунку ціни виробу."""

    def __init__(self, product_data: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🧮 Розрахунок ціни")
        self.setMinimumWidth(420)
        self._data = product_data or {}
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Назва
        self.edit_name = QLineEdit(self._data.get("name", ""))
        layout.addRow("Назва виробу", self.edit_name)

        # Тип
        self.combo_type = QComboBox()
        self.combo_type.addItems([
            "повітропровід прямокутний",
            "повітропровід круглий",
            "відвод прямокутний",
            "відвод круглий",
            "трійник прямокутний",
            "трійник круглий",
            "перехід прямокутний",
            "перехід круглий",
            "фланець прямокутний",
            "фланець круглий",
            "заглушка прямокутна",
            "заглушка кругла",
        ])
        self.combo_type.setCurrentText(self._data.get("type", "повітропровід прямокутний"))
        layout.addRow("Тип", self.combo_type)

        # Розміри
        sizes = QHBoxLayout()
        self.spin_a = QDoubleSpinBox()
        self.spin_a.setRange(1, 5000)
        self.spin_a.setSuffix(" мм")
        self.spin_a.setDecimals(0)
        self.spin_a.setValue(self._data.get("a", 400))
        sizes.addWidget(QLabel("A:"))
        sizes.addWidget(self.spin_a)

        self.spin_b = QDoubleSpinBox()
        self.spin_b.setRange(1, 5000)
        self.spin_b.setSuffix(" мм")
        self.spin_b.setDecimals(0)
        self.spin_b.setValue(self._data.get("b", 200))
        sizes.addWidget(QLabel("B:"))
        sizes.addWidget(self.spin_b)

        self.spin_l = QDoubleSpinBox()
        self.spin_l.setRange(0, 10000)
        self.spin_l.setSuffix(" мм")
        self.spin_l.setDecimals(0)
        self.spin_l.setValue(self._data.get("l", 1000))
        sizes.addWidget(QLabel("L:"))
        sizes.addWidget(self.spin_l)
        layout.addRow("Розміри", sizes)

        # Матеріал
        self.combo_material = QComboBox()
        self.combo_material.addItems(["оцинкована сталь", "нержавіюча сталь", "алюміній"])
        self.combo_material.setCurrentText(self._data.get("material", "оцинкована сталь"))
        layout.addRow("Матеріал", self.combo_material)

        # Товщина
        self.combo_thick = QComboBox()
        self.combo_thick.addItems(["0.5", "0.7", "0.9", "1.0", "1.2", "1.5", "2.0"])
        self.combo_thick.setCurrentText(str(self._data.get("thickness", "0.7")))
        layout.addRow("Товщина", self.combo_thick)

        # Кількість
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 9999)
        self.spin_qty.setValue(self._data.get("quantity", 1))
        layout.addRow("Кількість", self.spin_qty)

        # Фланці
        flanges = QHBoxLayout()
        self.spin_flange_count = QSpinBox()
        self.spin_flange_count.setRange(0, 100)
        flanges.addWidget(QLabel("К-ть:"))
        flanges.addWidget(self.spin_flange_count)

        self.spin_flange_price = QDoubleSpinBox()
        self.spin_flange_price.setRange(0, 9999)
        self.spin_flange_price.setSuffix(" ₴")
        self.spin_flange_price.setDecimals(2)
        self.spin_flange_price.setValue(85.0)
        flanges.addWidget(QLabel("Ціна:"))
        flanges.addWidget(self.spin_flange_price)
        layout.addRow("Фланці", flanges)

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_calc)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_calc(self):
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.edit_name.text().strip(),
            "type": self.combo_type.currentText(),
            "a": self.spin_a.value(),
            "b": self.spin_b.value(),
            "l": self.spin_l.value(),
            "material": self.combo_material.currentText(),
            "thickness": float(self.combo_thick.currentText()),
            "quantity": self.spin_qty.value(),
            "flange_count": self.spin_flange_count.value(),
            "flange_price": self.spin_flange_price.value(),
        }


class PricingTab(QWidget):
    """Вкладка ціноутворення з CostEngine."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._products: list[dict] = []
        self._results: list[dict] = []
        self._build_ui()
        self._load_demo()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Заголовок
        header = QHBoxLayout()
        lbl_title = QLabel("💰 Ціноутворення")
        lbl_title.setObjectName("title")
        header.addWidget(lbl_title)
        header.addStretch()

        btn_calc = QPushButton("🧮 Новий розрахунок")
        btn_calc.setObjectName("primary")
        btn_calc.setMinimumHeight(32)
        btn_calc.clicked.connect(self._on_new_calc)
        header.addWidget(btn_calc)

        btn_clear = QPushButton("♻️ Очистити")
        btn_clear.clicked.connect(self._on_clear)
        header.addWidget(btn_clear)

        layout.addLayout(header)

        # Таблиця розрахунків
        self.table = QTableView()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(300)
        layout.addWidget(self.table)

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "№", "Назва", "Тип", "Матеріал", "Товщ.", "К-ть",
            "Собівартість", "Ціна без ПДВ", "ПДВ", "Кінцева ціна"
        ])
        self.table.setModel(self.model)

        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 130)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 50)
        self.table.setColumnWidth(5, 50)
        self.table.setColumnWidth(6, 100)
        self.table.setColumnWidth(7, 100)
        self.table.setColumnWidth(8, 80)
        self.table.setColumnWidth(9, 100)

        # Підсумок
        self.lbl_summary = QLabel("Всього: 0 позицій | Сума: ₴ 0")
        self.lbl_summary.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 12px; padding: 4px;")
        layout.addWidget(self.lbl_summary)

        # Детальний розбив (при виборі рядка)
        detail = QHBoxLayout()
        detail.setSpacing(12)

        self.card_material = self._create_card("📦 Матеріал", "₴ 0")
        detail.addWidget(self.card_material)

        self.card_labor = self._create_card("🔧 Робота", "₴ 0")
        detail.addWidget(self.card_labor)

        self.card_overhead = self._create_card("📊 Накладні", "₴ 0")
        detail.addWidget(self.card_overhead)

        self.card_profit = self._create_card("💎 Прибуток", "₴ 0")
        detail.addWidget(self.card_profit)

        layout.addLayout(detail)

        # Кнопки
        actions = QHBoxLayout()
        actions.addStretch()

        btn_del = QPushButton("🗑️ Видалити")
        btn_del.setStyleSheet(f"color: {Theme.DANGER};")
        btn_del.clicked.connect(self._on_delete)
        actions.addWidget(btn_del)

        btn_refresh = QPushButton("🔄 Оновити")
        btn_refresh.clicked.connect(self._refresh_table)
        actions.addWidget(btn_refresh)

        layout.addLayout(actions)

    def _create_card(self, title: str, value: str) -> QLabel:
        card = QLabel(f"<b>{title}</b><br><span style=\'font-size:18px; color:{Theme.ACCENT};\'>{value}</span>")
        card.setStyleSheet(f"""
            QLabel {{
                background-color: {Theme.BG_CARD};
                border: 1px solid {Theme.BORDER};
                border-radius: 10px;
                padding: 12px 16px;
                color: {Theme.TEXT};
            }}
        """)
        card.setMinimumWidth(140)
        card.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return card

    def _load_demo(self):
        """Демо-розрахунки."""
        self._products = [
            {"name": "Повітропровід 400×200×1000", "type": "повітропровід прямокутний", "a": 400, "b": 200, "l": 1000, "material": "оцинкована сталь", "thickness": 0.7, "quantity": 1, "flange_count": 2, "flange_price": 85.0},
            {"name": "Відвод 400×200 90°", "type": "відвод прямокутний", "a": 400, "b": 200, "l": 0, "material": "оцинкована сталь", "thickness": 0.7, "quantity": 1, "flange_count": 0, "flange_price": 0},
            {"name": "Трійник 400×200", "type": "трійник прямокутний", "a": 400, "b": 200, "l": 300, "material": "оцинкована сталь", "thickness": 0.7, "quantity": 1, "flange_count": 3, "flange_price": 85.0},
        ]
        self._calculate_all()

    def _calculate_all(self):
        """Розрахувати ціни для всіх виробів через CostEngine."""
        self._results = []
        engine = CostEngine()

        for p in self._products:
            # Приблизні площі для демо (у реальності — з ваших формул)
            a, b, l = p["a"], p["b"], p["l"]
            qty = p["quantity"]

            # Поверхня (площа фарбування / готового виробу)
            if "кругл" in p["type"]:
                import math
                surface = (math.pi * a * l) / 1_000_000 if l > 0 else (math.pi * a * a) / 1_000_000
                blank = surface * 1.15  # припуски
            else:
                if l > 0:
                    surface = (2 * (a + b) * l) / 1_000_000
                    blank = (2 * (a + b) * l * 1.1) / 1_000_000
                else:
                    surface = (a * b) / 1_000_000
                    blank = surface * 1.1

            material_area = blank * 1.2  # KIM + відходи

            try:
                result = engine.calculate(
                    product_type=p["type"],
                    material_name=p["material"],
                    thickness_mm=p["thickness"],
                    surface_area_m2=surface,
                    blank_area_m2=blank,
                    material_area_m2=material_area,
                    quantity=qty,
                    flange_count=p.get("flange_count", 0),
                    flange_price=p.get("flange_price", 0),
                )

                self._results.append({
                    "product": p,
                    "result": result,
                })
            except Exception as e:
                print(f"Помилка розрахунку {p['name']}: {e}")

        self._refresh_table()

    def _refresh_table(self):
        self.model.removeRows(0, self.model.rowCount())
        total = 0.0

        for i, item in enumerate(self._results, 1):
            p = item["product"]
            r = item["result"]

            row = [
                QStandardItem(str(i)),
                QStandardItem(p["name"]),
                QStandardItem(p["type"]),
                QStandardItem(p["material"]),
                QStandardItem(str(p["thickness"])),
                QStandardItem(str(p["quantity"])),
                QStandardItem(f"₴ {r.base_cost:,.2f}"),
                QStandardItem(f"₴ {r.price_no_vat:,.2f}"),
                QStandardItem(f"₴ {r.vat_amount:,.2f}"),
                QStandardItem(f"₴ {r.final_price:,.2f}"),
            ]
            for cell in row:
                cell.setEditable(False)
            self.model.appendRow(row)
            total += r.final_price

        self.lbl_summary.setText(f"Всього: {len(self._results)} позицій | Загальна сума: ₴ {total:,.2f}")

    def _on_new_calc(self):
        dlg = PriceCalcDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self._products.append(data)
            self._calculate_all()

    def _on_delete(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            QMessageBox.warning(self, "Увага", "Виберіть позицію для видалення")
            return
        row = idx.row()
        if row < len(self._results):
            self._products.pop(row)
            self._calculate_all()

    def _on_clear(self):
        self._products.clear()
        self._results.clear()
        self.model.removeRows(0, self.model.rowCount())
        self.lbl_summary.setText("Всього: 0 позицій | Сума: ₴ 0")

    def refresh(self):
        self._calculate_all()
