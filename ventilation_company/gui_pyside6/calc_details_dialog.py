"""Діалог детального розрахунку вартості виробу — з прокруткою.

ВИПРАВЛЕННЯ: CostEngine тепер сам читає material_prices з pricing_settings.json
"""

from copy import deepcopy
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QDoubleSpinBox, QGroupBox, QMessageBox, QWidget,
    QScrollArea
)

from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.calculations.cost_engine import CostEngine, CostBreakdown


class CalcDetailsDialog(QDialog):
    """Діалог з детальним розбивом розрахунку та редагуванням коефіцієнтів."""

    def __init__(self, product_type, material, thickness,
                 width, height, length,
                 qty, surface, blank, material_area,
                 with_flanges, flange_count, flange_price,
                 markup_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 Деталі розрахунку вартості")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.resize(750, 600)

        self._product_type = product_type
        self._material = material
        self._thickness = thickness
        self._width = width
        self._height = height
        self._length = length
        self._qty = qty
        self._surface = surface
        self._blank = blank
        self._material_area = material_area
        self._with_flanges = with_flanges
        self._flange_count = flange_count
        self._flange_price = flange_price
        self._markup_name = markup_name

        from ventilation_company.gui_pyside6.pricing_tab import load_settings
        self._settings = load_settings()

        self._engine = CostEngine()
        self._result = None

        self._build_ui()
        self._recalculate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        lbl_title = QLabel("📊 Деталі розрахунку")
        lbl_title.setObjectName("title")
        layout.addWidget(lbl_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        layout.addWidget(scroll, 1)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(scroll_content)

        coeffs = QGroupBox("⚙️ Коефіцієнти (змінюйте і натисніть Перерахувати)")
        coeffs_layout = QFormLayout(coeffs)

        self.spin_waste = QDoubleSpinBox()
        self.spin_waste.setRange(0, 100)
        self.spin_waste.setSuffix(" %")
        self.spin_waste.setValue(self._settings.get("overhead", {}).get("waste_percent", 8.0))
        coeffs_layout.addRow("Відходи металу:", self.spin_waste)

        self.spin_depreciation = QDoubleSpinBox()
        self.spin_depreciation.setRange(0, 100)
        self.spin_depreciation.setSuffix(" %")
        dep = self._settings.get("depreciation", {})
        total_dep = sum(dep.get(k, 0) for k in ["guillotine_percent", "bending_percent", "welding_percent", "plasma_percent"])
        self.spin_depreciation.setValue(total_dep)
        coeffs_layout.addRow("Амортизація обладнання:", self.spin_depreciation)

        self.spin_markup = QDoubleSpinBox()
        self.spin_markup.setRange(0, 500)
        self.spin_markup.setSuffix(" %")
        matrix = self._settings.get("markup_matrix", {})
        base_name = self._markup_name.replace(" (", "").split("%")[0].strip() if "(" in self._markup_name else self._markup_name
        markup_val = matrix.get(base_name, 30.0)
        self.spin_markup.setValue(markup_val)
        coeffs_layout.addRow("Націнка прибутку:", self.spin_markup)

        self.spin_vat = QDoubleSpinBox()
        self.spin_vat.setRange(0, 100)
        self.spin_vat.setSuffix(" %")
        self.spin_vat.setValue(20.0)
        coeffs_layout.addRow("ПДВ:", self.spin_vat)

        scroll_layout.addWidget(coeffs)

        btn_recalc = QPushButton("🔄 Перерахувати")
        btn_recalc.setObjectName("primary")
        btn_recalc.setMinimumHeight(36)
        btn_recalc.clicked.connect(self._recalculate)
        scroll_layout.addWidget(btn_recalc)

        self.result_box = QGroupBox("💰 Результат розрахунку")
        self.result_layout = QVBoxLayout(self.result_box)
        scroll_layout.addWidget(self.result_box)

        scroll_layout.addStretch()

        btn_close = QPushButton("✅ Закрити")
        btn_close.setMinimumHeight(36)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _recalculate(self):
        # Глибока копія налаштувань
        custom_pricing = deepcopy(self._engine.pricing)
        custom_pricing["overhead"] = dict(custom_pricing.get("overhead", {}))
        custom_pricing["overhead"]["waste_percent"] = self.spin_waste.value()
        custom_pricing["depreciation"] = {
            "guillotine_percent": self.spin_depreciation.value() * 0.25,
            "bending_percent": self.spin_depreciation.value() * 0.25,
            "welding_percent": self.spin_depreciation.value() * 0.25,
            "plasma_percent": self.spin_depreciation.value() * 0.25,
        }
        custom_pricing["markup_percent"] = self.spin_markup.value()

        # ВИПРАВЛЕННЯ: CostEngine тепер сам читає material_prices з pricing_settings.json
        # через _get_material_price(). Тут тільки передаємо overhead/depreciation/markup.
        engine = CostEngine()
        engine.pricing = custom_pricing

        self._result = engine.calculate(
            product_type=self._product_type,
            material_name=self._material,
            thickness_mm=self._thickness,
            surface_area_m2=self._surface,
            blank_area_m2=self._blank,
            material_area_m2=self._material_area,
            quantity=self._qty,
            flange_count=self._flange_count,
            flange_price=self._flange_price,
            custom_markup_percent=self.spin_markup.value(),
        )
        self._show_result()

    def _show_result(self):
        while self.result_layout.count():
            item = self.result_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        r = self._result
        if not r:
            self.result_layout.addWidget(QLabel("Немає даних"))
            return

        steps = [
            ("1. Площа поверхні", f"{r.surface_area_m2:.4f} м²", "Площа готового виробу (без припусків)"),
            ("2. Площа заготовки", f"{r.blank_area_m2:.4f} м²", f"{r.surface_area_m2:.4f} x 1.15 (припуск на обробку)"),
            ("3. Площа матеріалу", f"{r.material_area_m2:.4f} м²", f"{r.blank_area_m2:.4f} x 1.05 (KIM + припуски)"),
            ("4. Ціна матеріалу", f"₴ {r.material_cost:.2f}", f"{r.material_area_m2:.4f} м² x {r.material_price_per_m2:.2f} ₴/м²"),
            ("5. Вартість роботи", f"₴ {r.labor_cost:.2f}", f"{r.surface_area_m2:.4f} м² x {r.labor_rate_per_m2:.2f} ₴/м² x (1 + {r.labor_difficulty_percent:.1f}%)"),
            ("6. Фланці", f"₴ {r.flange_cost:.2f}", f"{self._flange_count} шт x {self._flange_price:.2f} ₴" if self._flange_count else "—"),
            ("7. Накладні витрати", f"₴ {r.overhead_cost:.2f}", f"(матеріал + робота + фланці) x {r.overhead_percent:.1f}%"),
            ("8. Амортизація", f"₴ {r.depreciation_cost:.2f}", f"(матеріал + робота + фланці) x {r.depreciation_percent:.1f}%"),
            ("9. Базова собівартість", f"₴ {r.base_cost:.2f}", "матеріал + робота + фланці + накладні + амортизація"),
            ("10. Прибуток", f"₴ {r.profit:.2f}", f"{r.base_cost:.2f} x {r.markup_percent:.1f}%"),
            ("11. Ціна без ПДВ", f"₴ {r.price_no_vat:.2f}", f"{r.base_cost:.2f} + {r.profit:.2f}"),
            ("12. ПДВ", f"₴ {r.vat_amount:.2f}", f"{r.price_no_vat:.2f} x {r.vat_rate:.1f}%"),
            ("13. КІНЦЕВА ЦІНА", f"₴ {r.final_price:.2f}", f"{r.price_no_vat:.2f} + {r.vat_amount:.2f}"),
        ]

        for title, value, formula in steps:
            row = QHBoxLayout()
            lbl_title = QLabel(f"<b>{title}</b>")
            lbl_title.setMinimumWidth(200)
            row.addWidget(lbl_title)

            lbl_value = QLabel(f"<b>{value}</b>")
            lbl_value.setStyleSheet(f"color: {Theme.ACCENT}; font-size: 13px;")
            lbl_value.setMinimumWidth(120)
            row.addWidget(lbl_value)

            lbl_formula = QLabel(f"<span style=\'color: {Theme.TEXT_MUTED};\'>{formula}</span>")
            lbl_formula.setWordWrap(True)
            row.addWidget(lbl_formula, 1)

            container = QWidget()
            container.setLayout(row)
            container.setStyleSheet("padding: 4px; border-bottom: 1px solid #333;")
            self.result_layout.addWidget(container)

        total = QLabel(f"<h2>💰 Кінцева ціна: ₴ {r.final_price:.2f}</h2>"
                       f"<br><small>За 1 шт: ₴ {r.per_unit().final_price:.2f} | Кількість: {r.quantity}</small>")
        total.setStyleSheet(f"color: {Theme.SUCCESS}; padding: 12px; background: {Theme.BG_CARD}; border-radius: 8px;")
        total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_layout.addWidget(total)

    def get_result(self):
        return self._result
