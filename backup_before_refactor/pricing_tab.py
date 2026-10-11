"""Вкладка "💰 Ціноутворення" (PySide6).

Налаштування цін:
  • Ціни на метал (матеріал × товщина)
  • Накладні витрати (%)
  • Амортизація обладнання (%)
  • Ставки робіт (грн/м²)
  • Націнки по категоріях (%)

Єдине джерело правди — сервіс PricingSettings
(ventilation_company/services/pricing_settings.py, файл data/pricing_settings.json).
Функції load_settings/save_settings нижче — тонкі адаптери між GUI і сервісом.
"""

import copy
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.gui_pyside6.table_utils import setup_table
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.services import pricing_settings as _pricing

PricingSettings = _pricing.PricingSettings

# Категорії націнок (назва, значення за замовчуванням, %) — реекспорт з сервісу.
MARKUP_CATEGORIES = list(_pricing.MARKUP_CATEGORY_NAMES)
MARKUP_DEFAULTS = dict(_pricing.DEFAULT_MARKUP_CATEGORIES)


def load_settings() -> dict:
    """Завантажити налаштування цін через єдиний сервіс PricingSettings."""
    pricing = PricingSettings.get_instance()
    pricing.reload()
    labor_rates = {}
    for name, data in (pricing.labor_rates or {}).items():
        if isinstance(data, dict):
            labor_rates[name] = {
                "rate_per_m2": data.get("rate_per_m2", 0.0),
                "difficulty_percent": data.get("difficulty_percent", data.get("difficulty", 0.0)),
            }
    return {
        "material_prices": copy.deepcopy(pricing.material_prices),
        "material_densities": copy.deepcopy(pricing.material_densities),
        "overhead": copy.deepcopy(pricing.overhead),
        "depreciation": copy.deepcopy(pricing.depreciation),
        "markup_percent": pricing.markup_percent,
        "labor_rates": labor_rates,
        "markup_categories": {
            name: float(pricing.markup_categories.get(name, MARKUP_DEFAULTS[name]))
            for name in MARKUP_CATEGORIES
        },
    }


def get_markup_categories() -> list[tuple[str, float]]:
    """Категорії націнок (назва, %) з поточних збережених налаштувань.

    Делегує до сервісу — це обгортка для зворотної сумісності імпортів.
    """
    return _pricing.get_markup_categories()


def save_settings(data: dict):
    """Зберегти налаштування цін через сервіс і скинути кеш розрахунків."""
    pricing = PricingSettings.get_instance()
    for attr in (
        "material_prices",
        "material_densities",
        "overhead",
        "depreciation",
        "markup_percent",
    ):
        if attr in data:
            setattr(pricing, attr, data[attr])
    pricing.sync_material_densities()
    if "labor_rates" in data:
        pricing.labor_rates = {
            name: {
                "rate_per_m2": d.get("rate_per_m2", 0.0),
                "difficulty_percent": d.get("difficulty_percent", d.get("difficulty", 0.0)),
            }
            for name, d in data["labor_rates"].items()
            if isinstance(d, dict)
        }
    if "markup_categories" in data:
        pricing.markup_categories = {
            name: float(value) for name, value in data["markup_categories"].items()
        }
    pricing.save()

    # ── Скидаємо кеш, щоб CostEngine бачив нові ціни одразу ──
    try:
        from ventilation_company.calculations.cost_engine import clear_cache as clear_cost_cache
        from ventilation_company.manufacturing_params import clear_cache as clear_manuf_cache

        clear_manuf_cache()
        clear_cost_cache()
    except Exception:
        pass


def get_default_settings() -> dict:
    """Початкові налаштування (з канонічних дефолтів сервісу)."""
    return {
        "material_prices": copy.deepcopy(_pricing.DEFAULT_MATERIAL_PRICES),
        "material_densities": copy.deepcopy(_pricing.DEFAULT_MATERIAL_DENSITIES),
        "overhead": copy.deepcopy(_pricing.DEFAULT_OVERHEAD),
        "depreciation": copy.deepcopy(_pricing.DEFAULT_DEPRECIATION),
        "markup_percent": _pricing.DEFAULT_MARKUP_PERCENT,
        "labor_rates": copy.deepcopy(_pricing.DEFAULT_LABOR_RATES),
        "markup_categories": dict(_pricing.DEFAULT_MARKUP_CATEGORIES),
    }


# ═══════════════════════════════════════════════════════════
# Вкладка "Ціни на метал"
# ═══════════════════════════════════════════════════════════


def parse_price_grid(text: str, thicknesses: list[str]) -> tuple[dict[str, dict[str, float]], int]:
    """Розібрати таблицю цін з буфера обміну (TSV/CSV із Excel).

    Кожен рядок: матеріал у першій колонці, далі ціни за товщинами
    позиційно у порядку thicknesses. Приймає кому чи крапку, пробіли.
    Повертає (дані, кількість пропущених нечислових комірок).
    """
    data: dict[str, dict[str, float]] = {}
    skipped = 0
    for line in text.replace("\r", "").split("\n"):
        if not line.strip():
            continue
        cells = line.split("\t") if "\t" in line else line.split(";")
        material = cells[0].strip()
        if not material:
            continue
        entry = data.setdefault(material, {})
        for thick, raw in zip(thicknesses, cells[1:], strict=False):
            raw = raw.strip().replace(" ", "").replace(",", ".")
            if not raw:
                continue
            try:
                entry[thick] = float(raw)
            except ValueError:
                skipped += 1
    return data, skipped


def metal_prices_to_csv(model: QStandardItemModel, thicknesses: list[str]) -> str:
    """Звести модель цін у текст CSV (роздільник «;», для українського Excel)."""
    lines = ["Матеріал;" + ";".join(thicknesses)]
    for row in range(model.rowCount()):
        cells = [model.item(row, 0).text() if model.item(row, 0) else ""]
        for col in range(1, 1 + len(thicknesses)):
            item = model.item(row, col)
            cells.append(item.text() if item else "")
        lines.append(";".join(cells))
    return "\n".join(lines)


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
        setup_table(self.table, excel_keys=True)
        layout.addWidget(self.table)

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Матеріал"] + self.THICKNESSES)
        self.table.setModel(self.model)

        self._load_data()

        actions = QHBoxLayout()
        btn_add = QPushButton("➕ Додати матеріал")
        btn_add.setToolTip(
            "Новий матеріал (напр. мідь, титан) — з'явиться у всіх списках "
            "програми: вироби, розкрій, фільтри"
        )
        btn_add.clicked.connect(self._on_add_material)
        actions.addWidget(btn_add)
        btn_del = QPushButton("✖ Видалити матеріал")
        btn_del.setToolTip("Видалити вибраний рядок матеріалу (з цінами)")
        btn_del.clicked.connect(self._on_remove_material)
        actions.addWidget(btn_del)
        actions.addStretch()
        btn_paste = QPushButton("📋 Вставити з Excel")
        btn_paste.setToolTip(
            "Скопіюйте у Excel блок: перший стовпець — матеріал, "
            "далі ціни за товщинами (0.5; 0.7; 0.9; …) — і натисніть"
        )
        btn_paste.clicked.connect(self._on_paste)
        actions.addWidget(btn_paste)
        btn_export = QPushButton("⬇ Експорт CSV")
        btn_export.setToolTip("Зберегти ціни у CSV-файлі (відкривається в Excel)")
        btn_export.clicked.connect(self._on_export)
        actions.addWidget(btn_export)
        actions.addStretch()
        btn_save = QPushButton("💾 Зберегти зміни")
        btn_save.setObjectName("primary")
        btn_save.clicked.connect(self._on_save)
        actions.addWidget(btn_save)
        layout.addLayout(actions)

    def _on_paste(self):
        text = QGuiApplication.clipboard().text()
        if not text.strip():
            QMessageBox.information(
                self, "Вставка з Excel", "Буфер обміну порожній. Скопіюйте блок цін у Excel."
            )
            return
        data, skipped = parse_price_grid(text, self.THICKNESSES)
        if not data:
            QMessageBox.warning(
                self,
                "Вставка з Excel",
                "Не вдалося розпізнати дані. Потрібен формат: матеріал у першому "
                "стовпці, далі ціни за товщинами.",
            )
            return
        by_key = {k.casefold(): v for k, v in data.items()}
        applied = 0
        for row in range(self.model.rowCount()):
            name_item = self.model.item(row, 0)
            if name_item is None:
                continue
            entry = by_key.get(name_item.text().casefold())
            if not entry:
                continue
            for col, thick in enumerate(self.THICKNESSES, 1):
                if thick in entry:
                    item = self.model.item(row, col)
                    if item is not None:
                        item.setText(f"{entry[thick]:.2f}")
                        applied += 1
        msg = f"Вставлено цін: {applied}."
        if skipped:
            msg += f" Пропущено нечислових комірок: {skipped}."
        if not applied:
            msg += " Матеріали у буфері не збігаються з таблицею."
        QMessageBox.information(self, "Вставка з Excel", msg)

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Експорт цін на метал", "ціни_метал.csv", "CSV (*.csv)"
        )
        if not path:
            return
        Path(path).write_text(
            metal_prices_to_csv(self.model, self.THICKNESSES),
            encoding="utf-8-sig",
        )
        QMessageBox.information(self, "Експорт", f"Ціни збережено у файл:\n{path}")

    def _load_data(self):
        self.model.removeRows(0, self.model.rowCount())
        # Порожні налаштування (тести/перший запуск) → стандартні три матеріали
        # з цінами 0.00; порядок рядків — як у налаштуваннях, нові — в кінець.
        saved = self.settings.get("material_prices") or {}
        names = [m for m in saved if str(m).strip()] or list(_pricing.DEFAULT_MATERIAL_PRICES)
        for material in names:
            self._append_material_row(material, saved.get(material, {}))

    def _append_material_row(self, material: str, prices: dict) -> None:
        name_item = QStandardItem(material)
        name_item.setEditable(False)  # назву матеріалу не змінюємо (видалення — кнопкою)
        row = [name_item]
        for thick in self.THICKNESSES:
            try:
                price = float(prices.get(thick, 0) or 0)
            except (TypeError, ValueError):
                price = 0.0
            item = QStandardItem(f"{price:.2f}")
            item.setEditable(True)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.append(item)
        self.model.appendRow(row)

    def _on_add_material(self):
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "Новий матеріал", "Назва матеріалу:")
        name = name.strip()
        if not ok or not name:
            return
        existing = {self.model.item(r, 0).text().casefold() for r in range(self.model.rowCount())}
        if name.casefold() in existing:
            QMessageBox.warning(self, "Дублікат", f"Матеріал «{name}» уже є у таблиці.")
            return
        density, ok = QInputDialog.getDouble(
            self,
            "Густина матеріалу",
            f"Густина «{name}», кг/м³\n(потрібна для розрахунку ваги виробу)",
            7850.0,
            1.0,
            30000.0,
            0,
        )
        if not ok:
            return
        self._append_material_row(name, {})
        densities = self.settings.setdefault("material_densities", {})
        densities[name] = float(density)
        self.model.layoutChanged.emit()

    def _on_remove_material(self):
        row = self.table.currentIndex().row()
        if row < 0:
            QMessageBox.information(self, "Видалення", "Спочатку виділіть рядок матеріалу.")
            return
        material = self.model.item(row, 0).text()
        reply = QMessageBox.question(
            self,
            "Видалення матеріалу",
            f"Видалити «{material}» зі списку цін?\n\n"
            "У виробах, де він використовується, назва залишиться, "
            "але цін для розрахунку не буде.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.model.removeRow(row)
        self.settings.get("material_densities", {}).pop(material, None)

    def _on_save(self):
        prices: dict[str, dict[str, float]] = {}
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
        QMessageBox.information(
            self,
            "Успіх",
            "Ціни на метал збережено! Нові матеріали доступні у всіх вкладках.",
        )


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
        self.spin_electricity.setValue(
            self.settings.get("overhead", {}).get("electricity_per_kg", 2.5)
        )
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
        self.spin_transport.setValue(
            self.settings.get("overhead", {}).get("transport_per_project", 500.0)
        )
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
        setup_table(self.table, excel_keys=True)
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
            name_item = QStandardItem(product_type)
            name_item.setEditable(False)  # тип виробу не змінюємо
            row = [
                name_item,
                QStandardItem(f"{data.get('rate_per_m2', 0):.2f}"),
                QStandardItem(f"{data.get('difficulty_percent', data.get('difficulty', 0)):.1f}"),
            ]
            for cell in row[1:]:
                cell.setEditable(True)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.model.appendRow(row)

    def _on_save(self):
        rates = {}
        for row in range(self.model.rowCount()):
            ptype = self.model.item(row, 0).text()
            try:
                rate = float(self.model.item(row, 1).text().replace(",", "."))
                diff = float(self.model.item(row, 2).text().replace(",", "."))
                rates[ptype] = {"rate_per_m2": rate, "difficulty_percent": diff}
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

    CATEGORIES = MARKUP_CATEGORIES
    DEFAULTS = MARKUP_DEFAULTS

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

        matrix = self.settings.get("markup_categories", self.DEFAULTS)
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
        self.settings["markup_categories"] = matrix

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

        hint = QLabel(
            "💡 Зміни в цих налаштуваннях впливають на розрахунок ціни виробів у вкладці 'Вироби' одразу після збереження"
        )
        hint.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; padding: 8px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def _on_reset(self):
        reply = QMessageBox.question(
            self,
            "Скидання",
            "Скинути всі ціни до стандартних значень?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
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
