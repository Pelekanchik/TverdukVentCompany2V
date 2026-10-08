"""Product dialog widgets extracted from products_tab."""

import contextlib
import json
import math

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.calculations.cost_engine import (
    CostBreakdown,
    CostEngine,
)
from ventilation_company.gui_pyside6.calc_details_dialog import CalcDetailsDialog
from ventilation_company.gui_pyside6.pricing_tab import get_markup_categories
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.services.business_settings import BusinessSettings
from ventilation_company.services.pricing_settings import (
    DEFAULT_MARKUP_PERCENT,
    DEFAULT_MATERIAL_PRICES,
    PricingSettings,
)

SCHEMAS = {
    "Відвод круглий": "",
    "Відвод прямокутний": "",
    "Трійник круглий": "",
    "Трійник прямокутний": "",
    "Перехід круглий": "",
    "Перехід прямокутний": "",
    "Повітропровід круглий": "",
    "Повітропровід прямокутний": "",
    "Фланець круглий": "",
    "Фланець прямокутний": "",
    "Заглушка кругла": "",
    "Заглушка прямокутна": "",
    "Гнучка вставка": "",
}


class SchemaWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.setMaximumHeight(280)
        self._product_type = ""
        self._params = {}

    def show_schema(self, product_type: str, params: dict | None = None):
        self._product_type = product_type
        self._params = params or {}
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        painter.fillRect(self.rect(), QColor("#1a1a2e"))
        pen = QPen(QColor("#a0c4ff"))
        pen.setWidth(2)
        painter.setPen(pen)
        font = QFont("Segoe UI", 10)
        painter.setFont(font)
        pt = self._product_type.lower()

        if "повітропровід круглий" in pt or "труба кругла" in pt:
            self._draw_round_pipe(painter, cx, cy)
        elif "повітропровід прямокутний" in pt or "труба прямокутна" in pt:
            self._draw_rect_pipe(painter, cx, cy)
        elif "відвод круглий" in pt:
            self._draw_round_bend(painter, cx, cy)
        elif "відвод прямокутний" in pt:
            self._draw_rect_bend(painter, cx, cy)
        elif "трійник круглий" in pt:
            self._draw_round_tee(painter, cx, cy)
        elif "трійник прямокутний" in pt:
            self._draw_rect_tee(painter, cx, cy)
        elif "перехід" in pt:
            self._draw_transition(painter, cx, cy)
        elif "фланець круглий" in pt:
            self._draw_round_flange(painter, cx, cy)
        elif "фланець прямокутний" in pt:
            self._draw_rect_flange(painter, cx, cy)
        elif "заглушка кругла" in pt:
            self._draw_round_cap(painter, cx, cy)
        elif "заглушка прямокутна" in pt:
            self._draw_rect_cap(painter, cx, cy)
        elif "гнучка" in pt:
            self._draw_flexible(painter, cx, cy)
        else:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Схема недоступна")
        painter.end()

    def _draw_round_pipe(self, p, cx, cy):
        p.drawEllipse(cx - 60, cy - 60, 120, 120)
        p.drawLine(cx - 70, cy, cx + 70, cy)
        p.drawText(cx - 10, cy - 75, "Ø")
        p.drawText(cx - 40, cy + 85, "Довжина: L")

    def _draw_rect_pipe(self, p, cx, cy):
        p.drawRect(cx - 80, cy - 40, 160, 80)
        p.drawText(cx - 90, cy - 50, "Ш")
        p.drawText(cx + 85, cy, "В")
        p.drawText(cx - 40, cy + 65, "Довжина: L")

    def _draw_round_bend(self, p, cx, cy):
        p.drawArc(cx - 80, cy - 80, 160, 160, 0, 90 * 16)
        p.drawLine(cx + 80, cy, cx + 80, cy - 80)
        p.drawLine(cx, cy + 80, cx + 80, cy + 80)
        p.drawText(cx + 85, cy - 40, "Ø")
        p.drawText(cx - 50, cy + 95, "Кут: 90°")

    def _draw_rect_bend(self, p, cx, cy):
        p.drawLine(cx - 80, cy - 80, cx + 20, cy - 80)
        p.drawLine(cx + 20, cy - 80, cx + 20, cy + 80)
        p.drawLine(cx - 80, cy - 80, cx - 80, cy + 20)
        p.drawLine(cx - 80, cy + 20, cx + 80, cy + 20)
        p.drawText(cx - 90, cy - 90, "Ш")
        p.drawText(cx + 30, cy, "В")
        p.drawText(cx - 50, cy + 95, "Кут: 90°")

    def _draw_round_tee(self, p, cx, cy):
        p.drawEllipse(cx - 80, cy - 20, 160, 40)
        p.drawEllipse(cx - 20, cy - 80, 40, 120)
        p.drawText(cx - 90, cy, "Ø основний")
        p.drawText(cx + 25, cy - 50, "Ø відгал.")

    def _draw_rect_tee(self, p, cx, cy):
        p.drawRect(cx - 80, cy - 20, 160, 40)
        p.drawRect(cx - 20, cy - 80, 40, 100)
        p.drawText(cx - 90, cy, "Ш x В")
        p.drawText(cx + 25, cy - 50, "Ш_в x В_в")

    def _draw_transition(self, p, cx, cy):
        points = [(cx - 60, cy - 60), (cx + 60, cy - 60), (cx + 40, cy + 60), (cx - 40, cy + 60)]
        polygon = QPolygon([QPoint(x, y) for x, y in points])
        p.drawPolygon(polygon)
        p.drawText(cx - 70, cy - 70, "Ш1 x В1")
        p.drawText(cx - 30, cy + 80, "Ш2 x В2")

    def _draw_round_flange(self, p, cx, cy):
        p.drawEllipse(cx - 60, cy - 60, 120, 120)
        for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
            rad = math.radians(angle)
            x = cx + int(45 * math.cos(rad))
            y = cy + int(45 * math.sin(rad))
            p.drawEllipse(x - 4, y - 4, 8, 8)
        p.drawText(cx - 10, cy - 75, "Ø")
        p.drawText(cx - 40, cy + 85, "8 отворів")

    def _draw_rect_flange(self, p, cx, cy):
        p.drawRect(cx - 70, cy - 50, 140, 100)
        for dx, dy in [(-55, -35), (55, -35), (55, 35), (-55, 35)]:
            p.drawEllipse(cx + dx - 4, cy + dy - 4, 8, 8)
        p.drawText(cx - 80, cy - 60, "Ш x В")
        p.drawText(cx - 40, cy + 75, "4 отвори")

    def _draw_round_cap(self, p, cx, cy):
        p.drawEllipse(cx - 60, cy - 60, 120, 120)
        p.drawArc(cx - 70, cy - 70, 140, 140, 0, 180 * 16)
        p.drawText(cx - 10, cy - 75, "Ø")
        p.drawText(cx - 50, cy + 85, "Загин: 20 мм")

    def _draw_rect_cap(self, p, cx, cy):
        p.drawRect(cx - 70, cy - 50, 140, 100)
        p.drawLine(cx - 80, cy - 60, cx - 70, cy - 50)
        p.drawLine(cx + 70, cy - 50, cx + 80, cy - 60)
        p.drawText(cx - 80, cy - 70, "Ш x В")
        p.drawText(cx - 50, cy + 75, "Загин: 20 мм")

    def _draw_flexible(self, p, cx, cy):
        points = []
        for i in range(20):
            x = cx - 100 + i * 10
            y = cy + int(20 * math.sin(i * 0.5))
            points.append(QPoint(x, y))
        for i in range(len(points) - 1):
            p.drawLine(points[i], points[i + 1])
        p.drawText(cx - 10, cy - 35, "Ø")
        p.drawText(cx - 40, cy + 45, "Тканина: ПВХ")


def calc_surface_area(
    product_type: str,
    width: float,
    height: float,
    length: float,
    bend_angle: float = 90,
    radius: float = 0,
    branch_width: float = 0,
    branch_height: float = 0,
    branch_length: float = 0,
) -> float:
    pt = product_type.lower()
    if "повітропровід круглий" in pt or "труба кругла" in pt:
        return math.pi * width * length / 1_000_000
    elif "повітропровід прямокутний" in pt or "труба прямокутна" in pt:
        return 2 * (width + height) * length / 1_000_000
    elif "відвод круглий" in pt:
        base = math.pi * width * width * 1.5 / 1_000_000
        if bend_angle != 90:
            base *= bend_angle / 90
        if radius > 0:
            base *= 1 + radius / width
        return base
    elif "відвод прямокутний" in pt:
        base = 2 * (width + height) * width * 1.5 / 1_000_000
        if bend_angle != 90:
            base *= bend_angle / 90
        return base
    elif "трійник круглий" in pt:
        base = math.pi * width * width * 2.0 / 1_000_000
        if branch_width > 0:
            base += math.pi * branch_width * branch_length / 1_000_000
        return base
    elif "трійник прямокутний" in pt:
        base = 2 * (width + height) * width * 2.0 / 1_000_000
        if branch_width > 0:
            base += 2 * (branch_width + branch_height) * branch_length / 1_000_000
        return base
    elif "перехід круглий" in pt:
        return (math.pi * width * width + math.pi * height * height) / 2 / 1_000_000
    elif "перехід прямокутний" in pt:
        return (2 * (width + height) + 2 * (width + height)) * length / 2 / 1_000_000
    elif "фланець круглий" in pt:
        return math.pi * width * width / 4 / 1_000_000
    elif "фланець прямокутний" in pt:
        return width * height / 1_000_000
    elif "заглушка кругла" in pt:
        return math.pi * width * width / 4 / 1_000_000
    elif "заглушка прямокутна" in pt:
        return width * height / 1_000_000
    elif "гнучка" in pt:
        return math.pi * width * length / 1_000_000
    return 0.0


class ProductDialog(QDialog):
    """Діалог з правильними параметрами, схемою та знижкою у %."""

    def __init__(self, product_data: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔧 Редагувати виріб" if product_data else "➕ Новий виріб")
        self.setMinimumWidth(900)
        self.setMinimumHeight(750)
        self._data = product_data or {}
        self._calc_result: CostBreakdown | None = None
        self._engine = CostEngine()
        self._build_ui()
        self._on_type_changed(self.combo_type.currentText())
        self._apply_params_to_fields()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setMinimumWidth(480)
        layout.addWidget(left_scroll)

        left_widget = QWidget()
        form = QFormLayout(left_widget)
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)

        self.edit_name = QLineEdit(self._data.get("name", ""))
        self.edit_name.setPlaceholderText("Напр.: Відвод круглий Ø250мм 90°")
        form.addRow("Назва *", self.edit_name)

        self.combo_type = QComboBox()
        self.combo_type.addItems(list(SCHEMAS.keys()))
        self.combo_type.setCurrentText(self._data.get("product_type", "Повітропровід круглий"))
        self.combo_type.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Тип", self.combo_type)

        self.group_sizes = QGroupBox("Розміри (мм)")
        sizes_layout = QGridLayout(self.group_sizes)
        self.spin_width = QDoubleSpinBox()
        self.spin_width.setRange(50, 2000)
        self.spin_width.setSuffix(" мм")
        self.spin_width.setValue(self._data.get("width", 250))
        sizes_layout.addWidget(QLabel("Ø/Ш:"), 0, 0)
        sizes_layout.addWidget(self.spin_width, 0, 1)
        self.spin_height = QDoubleSpinBox()
        # 0 = круглий переріз (висота не використовується) — показуємо «—»
        self.spin_height.setRange(0, 2000)
        self.spin_height.setSpecialValueText("—")
        self.spin_height.setSuffix(" мм")
        self.spin_height.setToolTip(
            "Висота перерізу (мм). Для круглих виробів не використовується — поле показує «—»"
        )
        self.spin_height.setValue(self._data.get("height", 0) or 0)
        sizes_layout.addWidget(QLabel("В:"), 0, 2)
        sizes_layout.addWidget(self.spin_height, 0, 3)
        self.spin_length = QDoubleSpinBox()
        self.spin_length.setRange(0, 5000)
        self.spin_length.setSuffix(" мм")
        self.spin_length.setValue(self._data.get("length", 1000))
        sizes_layout.addWidget(QLabel("Д:"), 1, 0)
        sizes_layout.addWidget(self.spin_length, 1, 1)
        form.addRow(self.group_sizes)

        self.group_dynamic = QGroupBox("Додаткові параметри")
        self.dynamic_layout = QGridLayout(self.group_dynamic)
        self.group_dynamic.setVisible(False)
        form.addRow(self.group_dynamic)

        self.group_material = QGroupBox("Матеріал")
        mat_layout = QVBoxLayout(self.group_material)
        mat_row = QHBoxLayout()
        self.combo_material = QComboBox()
        self._material_price_map = self._load_material_prices()
        material_names = [m.capitalize() for m in self._material_price_map]
        self.combo_material.addItems(material_names)
        saved_material = str(self._data.get("material", "Оцинкована сталь"))
        if saved_material.lower() not in [m.lower() for m in material_names]:
            # Матеріалу немає в «Ціноутворенні» — додаємо, щоб не втратити дані
            self.combo_material.addItem(saved_material)
        self.combo_material.setCurrentText(saved_material)
        mat_row.addWidget(self.combo_material)
        self.combo_thickness = QComboBox()
        mat_row.addWidget(QLabel("Товщина:"))
        mat_row.addWidget(self.combo_thickness)
        mat_layout.addLayout(mat_row)
        self.lbl_metal_price = QLabel("")
        self.lbl_metal_price.setStyleSheet("font-size: 12px;")
        mat_layout.addWidget(self.lbl_metal_price)
        form.addRow(self.group_material)
        self._on_material_changed()
        self.combo_material.currentTextChanged.connect(self._on_material_changed)
        self.combo_thickness.currentTextChanged.connect(self._on_thickness_changed)

        self.group_flanges = QGroupBox("Фланці")
        fl_layout = QHBoxLayout(self.group_flanges)
        self.chk_with_flanges = QCheckBox("З фланцями")
        self.chk_with_flanges.stateChanged.connect(self._on_flange_changed)
        fl_layout.addWidget(self.chk_with_flanges)
        self.spin_flange_count = QSpinBox()
        self.spin_flange_count.setRange(0, 10)
        self.spin_flange_count.setValue(0)
        self.spin_flange_count.setEnabled(False)
        fl_layout.addWidget(QLabel("К-ть:"))
        fl_layout.addWidget(self.spin_flange_count)
        self.combo_flange_profile = QComboBox()
        self.combo_flange_profile.addItems(["P30", "P40"])
        self.combo_flange_profile.setEnabled(False)
        fl_layout.addWidget(QLabel("Профіль:"))
        fl_layout.addWidget(self.combo_flange_profile)
        form.addRow(self.group_flanges)

        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 9999)
        self.spin_qty.setValue(self._data.get("quantity", 1))
        form.addRow("Кількість", self.spin_qty)

        self.combo_category = QComboBox()
        # Категорії з поточних налаштувань «Ціноутворення → Націнки» —
        # щоб зміна націнок одразу відображалася тут.
        self._markups = get_markup_categories()
        self.combo_category.addItems([f"{name} ({value:g}%)" for name, value in self._markups])
        form.addRow("Категорія", self.combo_category)

        btn_calc = QPushButton("🧮 Розрахувати ціну")
        btn_calc.setObjectName("primary")
        btn_calc.setMinimumHeight(36)
        btn_calc.clicked.connect(self._on_calc)
        form.addRow(btn_calc)

        btn_details = QPushButton("📊 Деталі розрахунку")
        btn_details.setMinimumHeight(32)
        btn_details.clicked.connect(self._on_show_details)
        form.addRow(btn_details)

        # Результат
        self.result_box = QGroupBox("💰 Розрахунок")
        self.result_box.setVisible(False)
        result_layout = QVBoxLayout(self.result_box)
        self.lbl_result = QLabel("Натисніть 'Розрахувати ціну'")
        self.lbl_result.setWordWrap(True)
        self.lbl_result.setStyleSheet("font-size: 12px; line-height: 1.5;")
        result_layout.addWidget(self.lbl_result)
        form.addRow(self.result_box)

        # ── v2.4b: Знижка у % ──
        self.group_discount = QGroupBox("🏷️ Знижка")
        disc_layout = QHBoxLayout(self.group_discount)
        self.spin_discount_percent = QDoubleSpinBox()
        self.spin_discount_percent.setRange(0, 99)
        self.spin_discount_percent.setSuffix(" %")
        self.spin_discount_percent.setDecimals(1)
        self.spin_discount_percent.setValue(0)
        self.spin_discount_percent.setStyleSheet(
            "QDoubleSpinBox { background-color: #2a2a3e; color: #f9e2af; font-weight: bold; }"
        )
        self.spin_discount_percent.valueChanged.connect(self._calc_product_profit)
        disc_layout.addWidget(self.spin_discount_percent)

        self.lbl_discounted_price = QLabel("Кінцева: —")
        self.lbl_discounted_price.setStyleSheet("font-weight: bold; color: #89b4fa;")
        disc_layout.addWidget(self.lbl_discounted_price)

        disc_layout.addWidget(QLabel("0 = без знижки"))
        self.group_discount.setVisible(False)
        form.addRow(self.group_discount)

        # Прибуток по виробу
        self.lbl_product_profit = QLabel("Прибуток: —")
        self.lbl_product_profit.setStyleSheet("font-size: 12px; font-weight: bold;")
        form.addRow(self.lbl_product_profit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        left_scroll.setWidget(left_widget)

        right_widget = QWidget()
        right_widget.setMinimumWidth(350)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(12)
        right_layout.setContentsMargins(0, 0, 0, 0)
        lbl_schema = QLabel("📐 Схема виробу")
        lbl_schema.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 14px;")
        right_layout.addWidget(lbl_schema)
        self.schema_widget = SchemaWidget()
        right_layout.addWidget(self.schema_widget)
        lbl_desc = QLabel("📝 Опис параметрів")
        lbl_desc.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 14px;")
        right_layout.addWidget(lbl_desc)
        self.lbl_description = QLabel()
        self.lbl_description.setWordWrap(True)
        self.lbl_description.setStyleSheet(
            "font-size: 12px; padding: 8px; background: #1a1a2e; border-radius: 8px;"
        )
        right_layout.addWidget(self.lbl_description)
        right_layout.addStretch()
        layout.addWidget(right_widget)

    def _clear_dynamic(self):
        while self.dynamic_layout.count():
            item = self.dynamic_layout.takeAt(0)
            if item is None:
                break
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.group_dynamic.setVisible(False)

    def _add_dynamic_field(self, label: str, widget, row: int, col: int = 0):
        self.dynamic_layout.addWidget(QLabel(label), row, col)
        self.dynamic_layout.addWidget(widget, row, col + 1)

    # ── Матеріал і товщина: автопідтягування цін з «Ціноутворення» ──

    @staticmethod
    def _load_material_prices() -> dict[str, dict]:
        """Ціни на метал з «Ціноутворення» (material → {thickness: price})."""
        try:
            pricing = PricingSettings.get_instance()
            with contextlib.suppress(Exception):
                pricing.reload()
            data = pricing.material_prices or {}
        except Exception:  # noqa: BLE001 — при будь-якій помилці працюємо на дефолтах
            data = {}
        if not data:
            data = DEFAULT_MATERIAL_PRICES
        return {
            str(mat): {str(th): price for th, price in ths.items()}
            for mat, ths in data.items()
            if isinstance(ths, dict)
        }

    def _current_material_key(self) -> str:
        text = self.combo_material.currentText().lower()
        for key in self._material_price_map:
            if key.lower() == text:
                return key
        return text

    @staticmethod
    def _to_price(value: object) -> float:
        try:
            return float(str(value).replace(",", ".").replace(" ", ""))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _material_density(material: str) -> float:
        """Густина матеріалу з «Ціноутворення» (кг/м³); резерв — сталь."""
        try:
            return float(PricingSettings.get_instance().get_material_density(material))
        except Exception:  # noqa: BLE001 — тестові стаби без методу
            from ventilation_company.materials import resolve_density

            return resolve_density({}, material)

    def _current_metal_price(self) -> float:
        ths = self._material_price_map.get(self._current_material_key(), {})
        return self._to_price(ths.get(self.combo_thickness.currentText(), 0))

    def _update_metal_price_label(self):
        price = self._current_metal_price()
        if price > 0:
            self.lbl_metal_price.setText(f"💰 Ціна металу: ₴ {price:,.2f}/м² (з «Ціноутворення»)")
            self.lbl_metal_price.setStyleSheet("font-size: 12px; color: #16a34a;")
        else:
            self.lbl_metal_price.setText(
                "⚠️ Ціну для цієї пари матеріал/товщина не знайдено в «Ціноутворенні» — "
                "у розрахунку буде резервна ціна"
            )
            self.lbl_metal_price.setStyleSheet("font-size: 12px; color: #d97706;")

    def _on_material_changed(self, *_args):
        """Матеріал змінився: оновлюємо список товщин і ціну."""
        ths = self._material_price_map.get(self._current_material_key(), {})
        prev = self.combo_thickness.currentText()
        self.combo_thickness.clear()
        thicknesses = sorted(ths, key=lambda t: self._to_price(t))
        if not thicknesses:
            thicknesses = ["0.5", "0.7", "0.9", "1.0", "1.2", "1.5", "2.0"]
        self.combo_thickness.addItems(thicknesses)
        if not getattr(self, "_material_initialized", False):
            # Перше заповнення — відновлюємо товщину з даних виробу
            self._material_initialized = True
            saved = str(self._data.get("thickness", "0.7"))
            target = saved if saved in thicknesses else "0.7"
        else:
            # Подальші зміни матеріалу — намагаємось зберегти поточну товщину
            target = prev if prev in thicknesses else "0.7"
        if target not in thicknesses:
            # Найближча до попередньої доступна товщина
            target = min(thicknesses, key=lambda t: abs(self._to_price(t) - self._to_price(prev)))
        self.combo_thickness.setCurrentText(target)
        self._update_metal_price_label()

    def _on_thickness_changed(self, *_args):
        self._update_metal_price_label()
        # Якщо розрахунок уже виконано — автоматично перераховуємо з новою ціною
        if self._calc_result is not None:
            self._on_calc()

    def _on_type_changed(self, text: str):
        self._clear_dynamic()
        pt = text.lower()
        self.schema_widget.show_schema(text, {})
        descriptions = {
            "Відвод круглий": "Ø — діаметр відводу. Кут згину (15-180°). Радіус — радіус згину (0 = гострий кут). Подовження — додаткові прямі відрізки.",
            "Відвод прямокутний": "Ш × В — розміри перерізу. Кут згину. Радіус. Подовження — додаткові прямі відрізки.",
            "Трійник круглий": "Ø — основний діаметр. Відгалуження: Ø_відг, Д_відг — діаметр і довжина бокової гілки. Відстань від краю — зміщення відгалуження.",
            "Трійник прямокутний": "Ш × В — основний переріз. Відгалуження: Ш_відг × В_відг, Д_відг. Відстань від краю.",
            "Перехід круглий": "Ø₁ — початковий діаметр. Ø₂ — кінцевий діаметр. Довжина переходу.",
            "Перехід прямокутний": "Ш₁ × В₁ — початковий переріз. Ш₂ × В₂ — кінцевий переріз. Довжина переходу.",
            "Повітропровід круглий": "Ø — діаметр труби. Д — довжина труби. Можна додати фланці.",
            "Повітропровід прямокутний": "Ш × В — переріз. Д — довжина. Можна додати фланці.",
            "Фланець круглий": "Ø — діаметр фланця. К-ть отворів (4-24). Профіль P30/P40.",
            "Фланець прямокутний": "Ш × В — розміри фланця. К-ть отворів. Профіль P30/P40.",
            "Заглушка кругла": "Ø — діаметр. Ширина загину — ширина загнутого краю. Глибина — глибина заглушки.",
            "Заглушка прямокутна": "Ш × В — розміри. Ширина загину. Глибина.",
            "Гнучка вставка": "Ø — діаметр. Д — довжина. Тканина — тип матеріалу (ПВХ, тефлон, силікон).",
        }
        self.lbl_description.setText(descriptions.get(text, ""))

        if "кругл" in pt or "фланець кругл" in pt or "заглушка кругл" in pt:
            self.spin_width.setPrefix("Ø ")
            self.spin_height.setEnabled(False)
            self.spin_height.setValue(0)
        else:
            self.spin_width.setPrefix("")
            self.spin_height.setEnabled(True)

        if "відвод" in pt:
            self.spin_length.setEnabled(False)
            self.spin_length.setValue(0)
            self.spin_length.setSuffix(" (не використовується)")
        else:
            self.spin_length.setEnabled(True)
            self.spin_length.setSuffix(" мм")

        row = 0
        if "відвод" in pt:
            self.group_dynamic.setVisible(True)
            self.spin_bend_angle = QDoubleSpinBox()
            self.spin_bend_angle.setRange(15, 180)
            self.spin_bend_angle.setSuffix("°")
            self.spin_bend_angle.setValue(90)
            self._add_dynamic_field("Кут згину:", self.spin_bend_angle, row)
            row += 1
            self.spin_radius = QDoubleSpinBox()
            self.spin_radius.setRange(0, 500)
            self.spin_radius.setSuffix(" мм")
            self.spin_radius.setValue(0)
            self._add_dynamic_field("Радіус згину:", self.spin_radius, row)
            row += 1
            self.spin_ext_top = QDoubleSpinBox()
            self.spin_ext_top.setRange(0, 500)
            self.spin_ext_top.setSuffix(" мм")
            self.spin_ext_top.setValue(0)
            self._add_dynamic_field("Подовж. верх:", self.spin_ext_top, row)
            row += 1
            self.spin_ext_bottom = QDoubleSpinBox()
            self.spin_ext_bottom.setRange(0, 500)
            self.spin_ext_bottom.setSuffix(" мм")
            self.spin_ext_bottom.setValue(0)
            self._add_dynamic_field("Подовж. низ:", self.spin_ext_bottom, row)
        elif "трійник" in pt:
            self.group_dynamic.setVisible(True)
            self.spin_branch_dist = QDoubleSpinBox()
            self.spin_branch_dist.setRange(0, 1000)
            self.spin_branch_dist.setSuffix(" мм")
            self.spin_branch_dist.setValue(0)
            self._add_dynamic_field("Відстань від краю:", self.spin_branch_dist, row)
            row += 1
            self.spin_branch_width = QDoubleSpinBox()
            self.spin_branch_width.setRange(50, 2000)
            self.spin_branch_width.setSuffix(" мм")
            self.spin_branch_width.setValue(0)
            self._add_dynamic_field("Ш/Ø відгал.:", self.spin_branch_width, row)
            row += 1
            self.spin_branch_height = QDoubleSpinBox()
            self.spin_branch_height.setRange(50, 2000)
            self.spin_branch_height.setSuffix(" мм")
            self.spin_branch_height.setValue(0)
            self._add_dynamic_field("В відгал.:", self.spin_branch_height, row)
            row += 1
            self.spin_branch_length = QDoubleSpinBox()
            self.spin_branch_length.setRange(100, 2000)
            self.spin_branch_length.setSuffix(" мм")
            self.spin_branch_length.setValue(200)
            self._add_dynamic_field("Довжина відгал.:", self.spin_branch_length, row)
        elif "перехід" in pt:
            self.group_dynamic.setVisible(True)
            self.spin_end_width = QDoubleSpinBox()
            self.spin_end_width.setRange(50, 2000)
            self.spin_end_width.setSuffix(" мм")
            self.spin_end_width.setValue(0)
            self._add_dynamic_field("Кінцева ширина/Ø:", self.spin_end_width, row)
            row += 1
            self.spin_end_height = QDoubleSpinBox()
            self.spin_end_height.setRange(50, 2000)
            self.spin_end_height.setSuffix(" мм")
            self.spin_end_height.setValue(0)
            self._add_dynamic_field("Кінцева висота:", self.spin_end_height, row)
        elif "заглушка" in pt:
            self.group_dynamic.setVisible(True)
            self.spin_bend_width = QDoubleSpinBox()
            self.spin_bend_width.setRange(0, 100)
            self.spin_bend_width.setSuffix(" мм")
            self.spin_bend_width.setValue(20)
            self._add_dynamic_field("Ширина загину:", self.spin_bend_width, row)
            row += 1
            self.spin_depth = QDoubleSpinBox()
            self.spin_depth.setRange(0, 500)
            self.spin_depth.setSuffix(" мм")
            self.spin_depth.setValue(0)
            self._add_dynamic_field("Глибина:", self.spin_depth, row)
        elif "гнучка" in pt:
            self.group_dynamic.setVisible(True)
            self.combo_fabric = QComboBox()
            self.combo_fabric.addItems(["ПВХ стандарт", "ПВХ термостійкий", "Тефлон", "Силікон"])
            self._add_dynamic_field("Тканина:", self.combo_fabric, row)
        elif "фланець" in pt:
            self.group_dynamic.setVisible(True)
            self.spin_holes = QSpinBox()
            self.spin_holes.setRange(4, 24)
            self.spin_holes.setValue(8)
            self._add_dynamic_field("К-ть отворів:", self.spin_holes, row)

    def _on_flange_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.spin_flange_count.setEnabled(enabled)
        self.combo_flange_profile.setEnabled(enabled)
        if enabled and self.spin_flange_count.value() == 0:
            self.spin_flange_count.setValue(2)

    def _apply_params_to_fields(self):
        try:
            params = json.loads(self._data.get("notes") or "{}")
        except Exception:
            params = {}

        def set_spin(widget_name: str, key: str):
            widget = getattr(self, widget_name, None)
            if widget is not None and key in params:
                with contextlib.suppress(Exception):
                    widget.setValue(float(params.get(key) or 0))

        set_spin("spin_bend_angle", "bend_angle")
        set_spin("spin_radius", "radius")
        set_spin("spin_ext_top", "ext_top")
        set_spin("spin_ext_bottom", "ext_bottom")
        set_spin("spin_branch_dist", "branch_dist")
        set_spin("spin_branch_width", "branch_width")
        set_spin("spin_branch_height", "branch_height")
        set_spin("spin_branch_length", "branch_length")
        set_spin("spin_end_width", "end_width")
        set_spin("spin_end_height", "end_height")
        set_spin("spin_bend_width", "bend_width")
        set_spin("spin_depth", "depth")

        if params.get("category") and hasattr(self, "combo_category"):
            text = str(params["category"])
            idx = self.combo_category.findText(text)
            if idx < 0 and " (" in text:
                # Старий формат «Стандартна (30%)» при нових значеннях —
                # шукаємо за назвою без відсотка.
                idx = self.combo_category.findText(
                    text.split(" (")[0], Qt.MatchFlag.MatchStartsWith
                )
            if idx >= 0:
                self.combo_category.setCurrentIndex(idx)

        if hasattr(self, "chk_with_flanges") and "with_flanges" in params:
            self.chk_with_flanges.setChecked(bool(params.get("with_flanges")))
            self._on_flange_changed(self.chk_with_flanges.checkState())
        if hasattr(self, "spin_flange_count") and "flange_count" in params:
            self.spin_flange_count.setValue(int(params.get("flange_count") or 0))
        if hasattr(self, "combo_flange_profile") and params.get("flange_profile"):
            self.combo_flange_profile.setCurrentText(str(params.get("flange_profile")))
        if hasattr(self, "combo_fabric") and params.get("fabric"):
            self.combo_fabric.setCurrentText(str(params.get("fabric")))
        if hasattr(self, "spin_holes") and "holes" in params:
            self.spin_holes.setValue(int(params.get("holes") or 0))

        total = float(self._data.get("total_price") or 0)
        discounted = float(self._data.get("discounted_price") or 0)
        if total > 0 and discounted > 0 and hasattr(self, "spin_discount_percent"):
            self.spin_discount_percent.setValue(round((1 - discounted / total) * 100, 1))

    def _on_calc(self):
        try:
            self._on_calc_impl()
        except RuntimeError:
            # Qt іноді тримає stale widget після зміни типу виробу.
            # Перебудовуємо dynamic fields і пробуємо ще раз.
            try:
                self._on_type_changed(self.combo_type.currentText())
                self._on_calc_impl()
            except Exception as e:
                QMessageBox.critical(
                    self, "Помилка розрахунку", f"Не вдалося розрахувати ціну: {e}"
                )

    def _on_calc_impl(self):
        pt = self.combo_type.currentText()
        mat = self.combo_material.currentText()
        thick = float(self.combo_thickness.currentText())
        w = self.spin_width.value()
        h = self.spin_height.value() if self.spin_height.isEnabled() else 0
        l = self.spin_length.value() if self.spin_length.isEnabled() else 0
        qty = self.spin_qty.value()
        bend_angle = 90.0
        radius = 0.0
        branch_w = 0.0
        branch_h = 0.0
        branch_l = 0.0
        if hasattr(self, "spin_bend_angle"):
            bend_angle = self.spin_bend_angle.value()
        if hasattr(self, "spin_radius"):
            radius = self.spin_radius.value()
        if hasattr(self, "spin_branch_width"):
            branch_w = self.spin_branch_width.value()
        if hasattr(self, "spin_branch_height"):
            branch_h = self.spin_branch_height.value()
        if hasattr(self, "spin_branch_length"):
            branch_l = self.spin_branch_length.value()

        surface = calc_surface_area(pt, w, h, l, bend_angle, radius, branch_w, branch_h, branch_l)
        from ventilation_company.manufacturing_params import (
            blank_area,
            material_area_from_blank,
        )

        blank = blank_area(surface)
        material_area = material_area_from_blank(blank)
        markup_map = {f"{name} ({value:g}%)": value for name, value in self._markups}
        custom_markup = markup_map.get(self.combo_category.currentText(), DEFAULT_MARKUP_PERCENT)
        flange_count = 0
        flange_price = 0.0
        if self.chk_with_flanges.isChecked():
            flange_count = self.spin_flange_count.value()
            flange_price = BusinessSettings.get_instance().get_flange_price(
                self.combo_flange_profile.currentText()
            )

        result = self._engine.calculate(
            product_type=pt,
            material_name=mat,
            thickness_mm=thick,
            surface_area_m2=surface,
            blank_area_m2=blank,
            material_area_m2=material_area,
            quantity=qty,
            flange_count=flange_count,
            flange_price=flange_price,
            custom_markup_percent=custom_markup,
        )
        self._calc_result = result

        text = f"""<b>📐 Площі:</b>
  • Поверхня: {result.surface_area_m2:.4f} м²
  • Заготовка: {result.blank_area_m2:.4f} м²
  • Матеріал: {result.material_area_m2:.4f} м²

<b>💰 Собівартість:</b>
  • Матеріал: ₴ {result.material_cost:.2f}
  • Робота: ₴ {result.labor_cost:.2f}
  • Накладні: ₴ {result.overhead_cost:.2f}
  • Амортизація: ₴ {result.depreciation_cost:.2f}
  • Фланці: ₴ {result.flange_cost:.2f}
  <b>Базова: ₴ {result.base_cost:.2f}</b>

<b>📊 Ціноутворення:</b>
  • Прибуток ({result.markup_percent}%): ₴ {result.profit:.2f}
  <b>Ціна без ПДВ: ₴ {result.price_no_vat:.2f}</b>
  • ПДВ ({result.vat_rate}%): ₴ {result.vat_amount:.2f}

<b>🎯 КІНЦЕВА ЦІНА: ₴ {result.final_price:.2f}</b>
  (за 1 шт: ₴ {result.per_unit().final_price:.2f})
"""
        self.lbl_result.setText(text)
        self.result_box.setVisible(True)
        self.group_discount.setVisible(True)
        self._calc_product_profit()

    def _calc_product_profit(self):
        """Прибуток по виробу = кінцева ціна (з урахуванням знижки %) − собівартість."""
        cost = round(self._calc_result.base_cost, 2) if self._calc_result else 0
        base = self._calc_result.final_price if self._calc_result else 0
        discount_percent = self.spin_discount_percent.value()
        # Кінцева ціна = базова × (1 − знижка/100)
        discounted_price = round(base * (1 - discount_percent / 100), 2)
        self.lbl_discounted_price.setText(f"Кінцева: ₴ {discounted_price:,.2f}")
        profit = discounted_price - cost
        if profit >= 0:
            self.lbl_product_profit.setText(f"Прибуток: {profit:,.2f} ₴ ✅")
            self.lbl_product_profit.setStyleSheet(
                "font-size: 12px; font-weight: bold; color: #a6e3a1;"
            )
        else:
            self.lbl_product_profit.setText(f"Прибуток: {profit:,.2f} ₴ ⚠️ ЗБИТОК")
            self.lbl_product_profit.setStyleSheet(
                "font-size: 12px; font-weight: bold; color: #f38ba8;"
            )

    def _on_show_details(self):
        if not self._calc_result:
            QMessageBox.warning(self, "Увага", "Спочатку розрахуйте ціну")
            return
        dlg = CalcDetailsDialog(
            product_type=self.combo_type.currentText(),
            material=self.combo_material.currentText(),
            thickness=float(self.combo_thickness.currentText()),
            width=self.spin_width.value(),
            height=self.spin_height.value() if self.spin_height.isEnabled() else 0,
            length=self.spin_length.value() if self.spin_length.isEnabled() else 0,
            qty=self.spin_qty.value(),
            surface=self._calc_result.surface_area_m2 / max(self._calc_result.quantity, 1),
            blank=self._calc_result.blank_area_m2 / max(self._calc_result.quantity, 1),
            material_area=self._calc_result.material_area_m2 / max(self._calc_result.quantity, 1),
            with_flanges=self.chk_with_flanges.isChecked(),
            flange_count=self.spin_flange_count.value() if self.chk_with_flanges.isChecked() else 0,
            flange_price=BusinessSettings.get_instance().get_flange_price(
                self.combo_flange_profile.currentText()
            ),
            markup_name=self.combo_category.currentText(),
            parent=self,
        )
        dlg.exec()

    def _on_save(self):
        if not self.edit_name.text().strip():
            QMessageBox.warning(self, "Помилка", "Введіть назву виробу")
            return
        if not self._calc_result:
            reply = QMessageBox.question(
                self,
                "Розрахунок",
                "Ціну не розраховано. Розрахувати зараз?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_calc()
                return
        self.accept()

    def get_data(self) -> dict:
        qty = self.spin_qty.value()
        price = self._calc_result.final_price if self._calc_result else 0
        cost = round(self._calc_result.base_cost, 2) if self._calc_result else 0
        discount_percent = self.spin_discount_percent.value()
        # Кінцева ціна з урахуванням знижки %
        discounted_price = round(price * (1 - discount_percent / 100), 2)

        params = {
            "with_flanges": self.chk_with_flanges.isChecked(),
            "flange_count": (
                self.spin_flange_count.value() if self.chk_with_flanges.isChecked() else 0
            ),
            "flange_profile": (
                self.combo_flange_profile.currentText() if self.chk_with_flanges.isChecked() else ""
            ),
            "category": self.combo_category.currentText(),
        }
        if hasattr(self, "spin_bend_angle"):
            params["bend_angle"] = self.spin_bend_angle.value()
        if hasattr(self, "spin_radius"):
            params["radius"] = self.spin_radius.value()
        if hasattr(self, "spin_ext_top"):
            params["ext_top"] = self.spin_ext_top.value()
        if hasattr(self, "spin_ext_bottom"):
            params["ext_bottom"] = self.spin_ext_bottom.value()
        if hasattr(self, "spin_branch_dist"):
            params["branch_dist"] = self.spin_branch_dist.value()
        if hasattr(self, "spin_branch_width"):
            params["branch_width"] = self.spin_branch_width.value()
        if hasattr(self, "spin_branch_height"):
            params["branch_height"] = self.spin_branch_height.value()
        if hasattr(self, "spin_branch_length"):
            params["branch_length"] = self.spin_branch_length.value()
        if hasattr(self, "spin_end_width"):
            params["end_width"] = self.spin_end_width.value()
        if hasattr(self, "spin_end_height"):
            params["end_height"] = self.spin_end_height.value()
        if hasattr(self, "spin_bend_width"):
            params["bend_width"] = self.spin_bend_width.value()
        if hasattr(self, "spin_depth"):
            params["depth"] = self.spin_depth.value()
        if hasattr(self, "combo_fabric"):
            params["fabric"] = self.combo_fabric.currentText()
        if hasattr(self, "spin_holes"):
            params["holes"] = self.spin_holes.value()

        if self._calc_result:
            calc_qty = self._calc_result.quantity if self._calc_result.quantity > 0 else 1
            params["metal_area_m2"] = round(self._calc_result.surface_area_m2 / calc_qty, 4)
            params["blank_area_m2"] = round(self._calc_result.blank_area_m2 / calc_qty, 4)
            params["material_area_m2"] = round(self._calc_result.material_area_m2 / calc_qty, 4)
            density = self._material_density(self.combo_material.currentText())
            thickness_m = float(self.combo_thickness.currentText()) / 1000
            params["weight_kg"] = round(
                (self._calc_result.material_area_m2 / calc_qty) * thickness_m * density, 4
            )

        parent = self.parent()
        main_window = getattr(parent, "main_window", None) if parent is not None else None
        project_id = main_window.active_project_id if main_window is not None else None

        return {
            "name": self.edit_name.text().strip(),
            "product_type": self.combo_type.currentText(),
            "project_id": project_id,
            "width": self.spin_width.value(),
            "height": self.spin_height.value() if self.spin_height.isEnabled() else 0,
            "length": self.spin_length.value() if self.spin_length.isEnabled() else 0,
            "material": self.combo_material.currentText(),
            "thickness": float(self.combo_thickness.currentText()),
            "quantity": qty,
            "cost_price": cost,
            "unit_price": round(price / qty, 2) if qty > 1 else price,
            "total_price": price,
            "discounted_price": discounted_price,
            "notes": json.dumps(params) if params else "",
        }
