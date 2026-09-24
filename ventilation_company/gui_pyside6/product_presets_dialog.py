"""Product presets browser dialog."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ventilation_company.calculations.cost_engine import CostEngine
from ventilation_company.database.repositories.product_repo import ProductRepository
from ventilation_company.paths import APP_ROOT
from ventilation_company.product_presets_manager import PresetsManager
from ventilation_company.standard_products import StandardProduct


class ProductPresetsDialog(QDialog):
    """Browse standard and custom presets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = PresetsManager()
        self.custom_file = APP_ROOT / "data" / "custom_product_presets.json"
        self._standard_presets = self.manager.get_all()
        self._custom_presets = self._load_custom_presets()
        self._all_presets = self._custom_presets + self._standard_presets
        self._visible = []
        self.setWindowTitle("📚 Бібліотека типових виробів")
        self.resize(940, 580)
        self._build_ui()
        self.refresh()

    def _load_custom_presets(self):
        if not self.custom_file.exists():
            return []
        try:
            return [
                StandardProduct.from_dict(row)
                for row in json.loads(self.custom_file.read_text(encoding="utf-8"))
            ]
        except Exception:
            return []

    def _reload_custom_presets(self):
        self._custom_presets = self._load_custom_presets()
        self._all_presets = self._custom_presets + self._standard_presets

    def _build_ui(self):
        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        left.addWidget(QLabel("Папки:"))
        self.list_categories = QListWidget()
        self.list_categories.addItem("⭐ Мої пресети")
        self.list_categories.addItem("📦 Стандартні")
        for category in sorted(self.manager.get_by_category().keys()):
            self.list_categories.addItem(category)
        self.list_categories.setCurrentRow(0)
        self.list_categories.currentRowChanged.connect(self.refresh)
        left.addWidget(self.list_categories)
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Пошук пресета...")
        self.edit_search.textChanged.connect(self.refresh)
        right.addWidget(self.edit_search)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Назва", "Тип", "Розміри", "Матеріал"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        right.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("➕ Додати до виробів")
        btn_delete_preset = QPushButton("🗑 Видалити")
        btn_refresh = QPushButton("🔄 Оновити")
        btn_close = QPushButton("Закрити")
        btn_add.clicked.connect(self._add_selected)
        btn_delete_preset.clicked.connect(self._delete_selected_preset)
        btn_refresh.clicked.connect(self.refresh)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_delete_preset)
        btn_row.addWidget(btn_refresh)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        right.addLayout(btn_row)

        layout.addLayout(right, 3)

    @staticmethod
    def _dims(product) -> str:
        w = getattr(product, "width", 0) or 0
        h = getattr(product, "height", 0) or 0
        l = getattr(product, "length", 0) or 0
        if h and h != w:
            return f"{w}×{h}×{l}"
        if w:
            return f"Ø{w}×{l}" if l else f"Ø{w}"
        return "—"

    def refresh(self):
        category = (
            self.list_categories.currentItem().text()
            if self.list_categories.currentItem()
            else "⭐ Мої пресети"
        )
        search = self.edit_search.text().strip().lower()

        if category == "⭐ Мої пресети":
            source = self._custom_presets
        elif category == "📦 Стандартні":
            source = self._standard_presets
        else:
            source = [
                p for p in self._standard_presets if self.manager._get_category(p) == category
            ]

        self._visible = []
        for product in source:
            if search and search not in (product.name or "").lower():
                continue
            self._visible.append(product)

        self.table.setRowCount(0)
        for product in self._visible:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                product.name,
                product.product_type,
                self._dims(product),
                getattr(product, "material", None) or "—",
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))

    def _add_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._visible):
            QMessageBox.warning(self, "Увага", "Оберіть пресет")
            return
        product = self._visible[row]
        data = product.to_dict()
        breakdown = CostEngine().calculate_from_product(product)
        data.update(
            {
                "quantity": 1,
                "cost_price": round(float(breakdown.base_cost or 0), 2),
                "unit_price": round(float(breakdown.price_no_vat or 0), 2),
                "total_price": round(float(breakdown.final_price or 0), 2),
                "discounted_price": 0,
                "notes": f"preset:{product.name}",
            }
        )
        parent = self.parent()
        main_window = getattr(parent, "main_window", None)
        data["project_id"] = getattr(main_window, "active_project_id", None)
        try:
            ProductRepository.create(data)
            if parent is not None and hasattr(parent, "_load_data"):
                parent._load_data()
            QMessageBox.information(self, "Успіх", f"Пресет додано: {product.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Помилка", f"Не вдалося додати пресет: {exc}")

    def _delete_selected_preset(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._visible):
            QMessageBox.warning(self, "Увага", "Оберіть пресет")
            return

        category = (
            self.list_categories.currentItem().text() if self.list_categories.currentItem() else ""
        )
        if category != "⭐ Мої пресети":
            QMessageBox.information(
                self, "Інформація", "Це стандартний пресет. Його не можна видалити."
            )
            return

        product = self._visible[row]
        custom_index = next(
            (idx for idx, item in enumerate(self._custom_presets) if item is product),
            None,
        )
        if custom_index is None:
            QMessageBox.warning(self, "Увага", "Не вдалося знайти custom-пресет")
            return

        if not self.custom_file.exists():
            QMessageBox.warning(self, "Увага", "Файл custom-пресетів не знайдено")
            return

        try:
            rows = json.loads(self.custom_file.read_text(encoding="utf-8"))
        except Exception:
            rows = []

        if custom_index >= len(rows):
            QMessageBox.warning(
                self, "Увага", "Не вдалося знайти запис у custom_product_presets.json"
            )
            return

        deleted_name = rows[custom_index].get("name") or product.name
        del rows[custom_index]
        self.custom_file.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._reload_custom_presets()
        self.refresh()
        QMessageBox.information(self, "Успіх", f"Пресет видалено: {deleted_name}")
