"""Вкладка "💰 Ціноутворення" (PySide6).

Налаштування цін:
  • Ціни на метал (матеріал × товщина)
  • Накладні витрати (%)
  • Амортизація обладнання (%)
  • Ставки робіт (грн/м²)
  • Націнки по категоріях (%)

Зміни зберігаються в data/pricing_settings.json
"""

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QComboBox, QMessageBox, QAbstractItemView,
    QDialog, QFormLayout, QDialogButtonBox, QSpinBox,
    QDoubleSpinBox, QGroupBox, QGridLayout,
    QTabWidget, QFrame, QScrollArea, QSplitter
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

from ventilation_company.gui_pyside6.theme import Theme


SETTINGS_PATH = Path(__file__).parent.parent.parent / "data" / "pricing_settings.json"


def load_settings() -> dict:
    """Завантажити налаштування цін."""
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return get_default_settings()


def save_settings(data: dict):
    """Зберегти налаштування цін і скинути кеш розрахунків."""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # ── ВИПРАВЛЕННЯ: скидаємо кеш, щоб CostEngine бачив нові ціни одразу ──
    try:
        from ventilation_company.manufacturing_params import clear_cache as clear_manuf_cache
        from ventilation_company.calculations.cost_engine import clear_cache as clear_cost_cache
        clear_manuf_cache()
        clear_cost_cache()
    except Exception:
        pass


def get_default_settings() -> dict:
    """Початкові налаштування."""
    return {
        "material_prices": {
            "оцинкована сталь": {
                "0.5": 450.0, "0.7": 580.0, "0.9": 650.0,
                "1.0": 750.0, "1.2": 850.0, "1.5": 950.0, "2.0": 1200.0,
            },
            "нержавіюча сталь": {
                "0.5": 950.0, "0.7": 1100.0, "0.9": 1200.0,
                "1.0": 1200.0, "1.2": 1400.0, "1.5": 1600.0, "2.0": 2000.0,
            },
            "алюміній": {
                "0.5": 320.0, "0.7": 380.0, "0.9": 420.0,
                "1.0": 450.0, "1.2": 500.0, "1.5": 600.0, "2.0": 750.0,
            },
        },
        "overhead": {
            "waste_percent": 8.0,
            "electricity_per_kg": 2.5,
            "rent_per_month": 15000.0,
            "transport_per_project": 500.0,
        },
        "depreciation": {
            "guillotine_percent": 5.0,
            "bending_percent": 4.0,
            "welding_percent": 3.0,
            "plasma_percent": 6.0,
        },
        "labor_rates": {
            "повітропровід прямокутний": {"rate_per_m2": 120.0, "difficulty": 0.0},
            "повітропровід круглий": {"rate_per_m2": 130.0, "difficulty": 5.0},
            "відвод прямокутний": {"rate_per_m2": 180.0, "difficulty": 20.0},
            "відвод круглий": {"rate_per_m2": 200.0, "difficulty": 25.0},
            "трійник прямокутний": {"rate_per_m2": 250.0, "difficulty": 25.0},
            "трійник круглий": {"rate_per_m2": 280.0, "difficulty": 30.0},
            "перехід прямокутний": {"rate_per_m2": 180.0, "difficulty": 15.0},
            "перехід круглий": {"rate_per_m2": 200.0, "difficulty": 20.0},
            "фланець прямокутний": {"rate_per_m2": 200.0, "difficulty": 15.0},
            "фланець круглий": {"rate_per_m2": 180.0, "difficulty": 10.0},
            "заглушка прямокутна": {"rate_per_m2": 150.0, "difficulty": 5.0},
            "заглушка кругла": {"rate_per_m2": 150.0, "difficulty": 5.0},
            "гнучка вставка": {"rate_per_m2": 100.0, "difficulty": 0.0},
        },
        "markup_percent": 30.0,
        "markup_matrix": {
            "Стандартна": 30.0,
            "Преміум": 40.0,
            "Економ": 20.0,
            "Спецзамовлення": 50.0,
        },
        "flange_price": {
            "P30": 150.0,
            "P40": 200.0,
        },
    }


# ═══════════════════════════════════════════════════════════
# Вкладка "Ціни на метал"
# ═══════════════════════════════════════════════════════════

class MetalPricesTab(QWidget):
    """Таблиця цін на метал (матеріал × товщина)."""

    THICKNESSES = ["0.5", "0.7", "0.9", "1.0", "1.2", "1.5", "2.0"]

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl = QLabel("📊 Ціни на метал (₴/м²)")
        lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 14px;")
        layout.addWidget(lbl)

        self.table = QTableView()
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Матеріал"] + self.THICKNESSES)
        self.table.setModel(self.model)

        self._load_data()

        btn_save = QPushButton("💾 Зберегти зміни")
        btn_save.setObjectName("primary")
        btn_save.clicked.connect(self._on_save)
        layout.addWidget(btn_save)

    def _load_data(self):
        self.model.removeRows(0, self.model.rowCount())
        prices = self.settings.get("material_prices", {})
        for material in ["оцинкована сталь", "нержавіюча сталь", "алюміній"]:
            row = [QStandardItem(material)]
            for thick in self.THICKNESSES:
                price = prices.get(material, {}).get(thick, 0)
                item = QStandardItem(f"{price:.2f}")
                item.setEditable(True)
                row.append(item)
            self.model.appendRow(row)

    def _on_save(self):
        prices = {}
        for row in range(self.model.rowCount()):
            material = self.model.item(row, 0).text()
            prices[material] = {}
            for col, thick in enumerate(self.THICKNESSES, 1):
                try:
                    price = float(self.model.item(row, col).text().replace(",", "."))
                    prices[material][thick] = price
                except ValueError:
                    QMessageBox.warning(self, "Помилка", f"Невірна ціна для {material} {thick}мм")
                    return
        self.settings["material_prices"] = prices
        save_settings(self.settings)
        QMessageBox.information(self, "Успіх", "Ціни на метал збережено! Тепер розрахунок використовує нові ціни одразу.")


# ═══════════════════════════════════════════════════════════
# Вкладка "Накладні та амортизація"
# ═══════════════════════════════════════════════════════════

class OverheadTab(QWidget):
    """Накладні витрати та амортизація."""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        group_overhead = QGroupBox("📊 Накладні витрати")
        oh_layout = QGridLayout(group_overhead)

        self.spin_waste = QDoubleSpinBox()
        self.spin_waste.setRange(0, 50)
        self.spin_waste.setSuffix(" %")
        self.spin_waste.setValue(self.settings.get("overhead", {}).get("waste_percent", 8.0))
        oh_layout.addWidget(QLabel("Відходи:"), 0, 0)
        oh_layout.addWidget(self.spin_waste, 0, 1)

        self.spin_electricity = QDoubleSpinBox()
        self.spin_electricity.setRange(0, 50)
        self.spin_electricity.setSuffix(" ₴/кг")
        self.spin_electricity.setValue(self.settings.get("overhead", {}).get("electricity_per_kg", 2.5))
        oh_layout.addWidget(QLabel("Електроенергія:"), 1, 0)
        oh_layout.addWidget(self.spin_electricity, 1, 1)

        self.spin_rent = QDoubleSpinBox()
        self.spin_rent.setRange(0, 100000)
        self.spin_rent.setSuffix(" ₴/міс")
        self.spin_rent.setValue(self.settings.get("overhead", {}).get("rent_per_month", 15000.0))
        oh_layout.addWidget(QLabel("Оренда:"), 2, 0)
        oh_layout.addWidget(self.spin_rent, 2, 1)

        self.spin_transport = QDoubleSpinBox()
        self.spin_transport.setRange(0, 10000)
        self.spin_transport.setSuffix(" ₴/проєкт")
        self.spin_transport.setValue(self.settings.get("overhead", {}).get("transport_per_project", 500.0))
        oh_layout.addWidget(QLabel("Транспорт:"), 3, 0)
        oh_layout.addWidget(self.spin_transport, 3, 1)

        layout.addWidget(group_overhead)

        group_dep = QGroupBox("🔧 Амортизація обладнання")
        dep_layout = QGridLayout(group_dep)

        dep = self.settings.get("depreciation", {})

        self.spin_guillotine = QDoubleSpinBox()
        self.spin_guillotine.setRange(0, 50)
        self.spin_guillotine.setSuffix(" %")
        self.spin_guillotine.setValue(dep.get("guillotine_percent", 5.0))
        dep_layout.addWidget(QLabel("Гільйотина:"), 0, 0)
        dep_layout.addWidget(self.spin_guillotine, 0, 1)

        self.spin_bending = QDoubleSpinBox()
        self.spin_bending.setRange(0, 50)
        self.spin_bending.setSuffix(" %")
        self.spin_bending.setValue(dep.get("bending_percent", 4.0))
        dep_layout.addWidget(QLabel("Гнуття:"), 1, 0)
        dep_layout.addWidget(self.spin_bending, 1, 1)

        self.spin_welding = QDoubleSpinBox()
        self.spin_welding.setRange(0, 50)
        self.spin_welding.setSuffix(" %")
        self.spin_welding.setValue(dep.get("welding_percent", 3.0))
        dep_layout.addWidget(QLabel("Зварювання:"), 2, 0)
        dep_layout.addWidget(self.spin_welding, 2, 1)

        self.spin_plasma = QDoubleSpinBox()
        self.spin_plasma.setRange(0, 50)
        self.spin_plasma.setSuffix(" %")
        self.spin_plasma.setValue(dep.get("plasma_percent", 6.0))
        dep_layout.addWidget(QLabel("Плазма:"), 3, 0)
        dep_layout.addWidget(self.spin_plasma, 3, 1)

        layout.addWidget(group_dep)

        btn_save = QPushButton("💾 Зберегти")
        btn_save.setObjectName("primary")
        btn_save.clicked.connect(self._on_save)
        layout.addWidget(btn_save)
        layout.addStretch()

    def _on_save(self):
        self.settings["overhead"] = {
            "waste_percent": self.spin_waste.value(),
            "electricity_per_kg": self.spin_electricity.value(),
            "rent_per_month": self.spin_rent.value(),
            "transport_per_project": self.spin_transport.value(),
        }
        self.settings["depreciation"] = {
            "guillotine_percent": self.spin_guillotine.value(),
            "bending_percent": self.spin_bending.value(),
            "welding_percent": self.spin_welding.value(),
            "plasma_percent": self.spin_plasma.value(),
        }
        save_settings(self.settings)
        QMessageBox.information(self, "Успіх", "Налаштування збережено!")


# ═══════════════════════════════════════════════════════════
# Вкладка "Ставки робіт"
# ═══════════════════════════════════════════════════════════

class LaborRatesTab(QWidget):
    """Ставки робіт (грн/м²) по типах виробів."""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl = QLabel("🔧 Ставки робіт (грн/м²)")
        lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 14px;")
        layout.addWidget(lbl)

        self.table = QTableView()
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Тип виробу", "Ставка (₴/м²)", "Коеф. важкості (%)"])
        self.table.setModel(self.model)

        self.table.setColumnWidth(0, 250)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 150)

        self._load_data()

        btn_save = QPushButton("💾 Зберегти")
        btn_save.setObjectName("primary")
        btn_save.clicked.connect(self._on_save)
        layout.addWidget(btn_save)

    def _load_data(self):
        self.model.removeRows(0, self.model.rowCount())
        rates = self.settings.get("labor_rates", {})
        for product_type, data in rates.items():
            row = [
                QStandardItem(product_type),
                QStandardItem(f"{data.get('rate_per_m2', 0):.2f}"),
                QStandardItem(f"{data.get('difficulty', 0):.1f}"),
            ]
            for cell in row[1:]:
                cell.setEditable(True)
            self.model.appendRow(row)

    def _on_save(self):
        rates = {}
        for row in range(self.model.rowCount()):
            ptype = self.model.item(row, 0).text()
            try:
                rate = float(self.model.item(row, 1).text().replace(",", "."))
                diff = float(self.model.item(row, 2).text().replace(",", "."))
                rates[ptype] = {"rate_per_m2": rate, "difficulty": diff}
            except ValueError:
                QMessageBox.warning(self, "Помилка", f"Невірне значення для {ptype}")
                return
        self.settings["labor_rates"] = rates
        save_settings(self.settings)
        QMessageBox.information(self, "Успіх", "Ставки робіт збережено!")


# ═══════════════════════════════════════════════════════════
# Вкладка "Націнки"
# ═══════════════════════════════════════════════════════════

class MarkupTab(QWidget):
    """Націнки по категоріях."""

    CATEGORIES = ["Стандартна", "Преміум", "Економ", "Спецзамовлення"]
    DEFAULTS = {"Стандартна": 30.0, "Преміум": 40.0, "Економ": 20.0, "Спецзамовлення": 50.0}

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        group_base = QGroupBox("📐 Загальна націнка")
        base_layout = QHBoxLayout(group_base)

        self.spin_base_markup = QDoubleSpinBox()
        self.spin_base_markup.setRange(0, 200)
        self.spin_base_markup.setSuffix(" %")
        self.spin_base_markup.setValue(self.settings.get("markup_percent", 30.0))
        base_layout.addWidget(QLabel("Базова націнка:"))
        base_layout.addWidget(self.spin_base_markup)
        base_layout.addStretch()

        layout.addWidget(group_base)

        group_matrix = QGroupBox("📂 Категорії націнок")
        mat_layout = QGridLayout(group_matrix)

        matrix = self.settings.get("markup_matrix", self.DEFAULTS)
        self.markup_spins = {}

        for i, name in enumerate(self.CATEGORIES):
            value = matrix.get(name, self.DEFAULTS[name])
            spin = QDoubleSpinBox()
            spin.setRange(0, 200)
            spin.setSuffix(" %")
            spin.setValue(float(value))
            mat_layout.addWidget(QLabel(f"{name}:"), i, 0)
            mat_layout.addWidget(spin, i, 1)
            self.markup_spins[name] = spin

        layout.addWidget(group_matrix)

        group_flange = QGroupBox("🔩 Ціни фланців")
        fl_layout = QHBoxLayout(group_flange)

        flange_prices = self.settings.get("flange_price", {})

        self.spin_p30 = QDoubleSpinBox()
        self.spin_p30.setRange(0, 1000)
        self.spin_p30.setSuffix(" ₴")
        self.spin_p30.setValue(flange_prices.get("P30", 150.0))
        fl_layout.addWidget(QLabel("P30:"))
        fl_layout.addWidget(self.spin_p30)

        self.spin_p40 = QDoubleSpinBox()
        self.spin_p40.setRange(0, 1000)
        self.spin_p40.setSuffix(" ₴")
        self.spin_p40.setValue(flange_prices.get("P40", 200.0))
        fl_layout.addWidget(QLabel("P40:"))
        fl_layout.addWidget(self.spin_p40)
        fl_layout.addStretch()

        layout.addWidget(group_flange)

        btn_save = QPushButton("💾 Зберегти")
        btn_save.setObjectName("primary")
        btn_save.clicked.connect(self._on_save)
        layout.addWidget(btn_save)
        layout.addStretch()

    def _on_save(self):
        self.settings["markup_percent"] = self.spin_base_markup.value()

        matrix = {}
        for name, spin in self.markup_spins.items():
            matrix[name] = spin.value()
        self.settings["markup_matrix"] = matrix

        self.settings["flange_price"] = {
            "P30": self.spin_p30.value(),
            "P40": self.spin_p40.value(),
        }

        save_settings(self.settings)
        QMessageBox.information(self, "Успіх", "Націнки збережено!")


# ═══════════════════════════════════════════════════════════
# Головна вкладка "Ціноутворення"
# ═══════════════════════════════════════════════════════════

class PricingTab(QWidget):
    """Вкладка ціноутворення з підвкладками."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_settings()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        lbl_title = QLabel("💰 Ціноутворення")
        lbl_title.setObjectName("title")
        header.addWidget(lbl_title)
        header.addStretch()

        btn_reset = QPushButton("♻️ Скинути до стандартних")
        btn_reset.clicked.connect(self._on_reset)
        header.addWidget(btn_reset)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(MetalPricesTab(self.settings), "📊 Ціни на метал")
        self.tabs.addTab(OverheadTab(self.settings), "📋 Накладні та амортизація")
        self.tabs.addTab(LaborRatesTab(self.settings), "🔧 Ставки робіт")
        self.tabs.addTab(MarkupTab(self.settings), "📐 Націнки")
        layout.addWidget(self.tabs)

        hint = QLabel("💡 Зміни в цих налаштуваннях впливають на розрахунок ціни виробів у вкладці 'Вироби' одразу після збереження")
        hint.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; padding: 8px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def _on_reset(self):
        reply = QMessageBox.question(
            self, "Скидання",
            "Скинути всі ціни до стандартних значень?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings = get_default_settings()
            save_settings(self.settings)
            self.tabs.clear()
            self.tabs.addTab(MetalPricesTab(self.settings), "📊 Ціни на метал")
            self.tabs.addTab(OverheadTab(self.settings), "📋 Накладні та амортизація")
            self.tabs.addTab(LaborRatesTab(self.settings), "🔧 Ставки робіт")
            self.tabs.addTab(MarkupTab(self.settings), "📐 Націнки")
            QMessageBox.information(self, "Успіх", "Ціни скинуто до стандартних!")
