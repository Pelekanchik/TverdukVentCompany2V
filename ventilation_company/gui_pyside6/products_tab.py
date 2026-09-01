"""Вкладка "Вироби" (PySide6) з правильними параметрами та візуальною схемою.

Для кожного типу виробу показується схема з позначенням параметрів.
"""

import math
import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QLineEdit, QComboBox, QMessageBox, QAbstractItemView,
    QDialog, QFormLayout, QSpinBox, QDoubleSpinBox, QDialogButtonBox,
    QGroupBox, QSplitter, QFrame, QScrollArea, QGridLayout, QTextEdit,
    QCheckBox
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QPainter, QPen, QColor, QFont, QPolygon
from PySide6.QtCore import QPoint
from PySide6.QtCore import QRect

from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.database.repositories.product_repo import ProductRepository
from ventilation_company.calculations.cost_engine import CostEngine, CostBreakdown


# ═══════════════════════════════════════════════════════════
# Схеми параметрів (SVG-like описи)
# ═══════════════════════════════════════════════════════════

SCHEMAS = {
    "Відвод круглий": """
    ┌─────────────────────────────┐
    │         ВІДВОД КРУГЛИЙ      │
    │                              │
    │           ┌───┐              │
    │          /     \\             │
    │    ─────┤  Ø  ├─────        │  ← Ø: діаметр
    │          \\     /             │
    │           └───┘              │
    │             │                │
    │             │                │
    │             ↓                │
    │           [кут]              │  ← Кут згину
    │                              │
    │    Подовж.верх: ___ мм      │
    │    Подовж.низ:  ___ мм      │
    │    Радіус:      ___ мм      │
    └─────────────────────────────┘
    """,
    "Відвод прямокутний": """
    ┌─────────────────────────────┐
    │      ВІДВОД ПРЯМОКУТНИЙ     │
    │                              │
    │    ┌─────────┐              │
    │    │ Ш x В   │              │  ← Ш: ширина, В: висота
    │    └────┬────┘              │
    │         │                   │
    │         ↓ [кут]             │  ← Кут згину
    │                              │
    │    Подовж.верх: ___ мм      │
    │    Подовж.низ:  ___ мм      │
    │    Радіус:      ___ мм      │
    └─────────────────────────────┘
    """,
    "Трійник круглий": """
    ┌─────────────────────────────┐
    │       ТРІЙНИК КРУГЛИЙ       │
    │                              │
    │           │                  │
    │           │ відгалуження     │  ← Ш_відг, В_відг, Д_відг
    │           ↓                  │
    │    ─────┬───┬─────          │
    │         │ Ø │                │  ← Ø: основний діаметр
    │    ─────┴───┴─────          │
    │                              │
    │    Відстань від краю: ___   │
    └─────────────────────────────┘
    """,
    "Трійник прямокутний": """
    ┌─────────────────────────────┐
    │     ТРІЙНИК ПРЯМОКУТНИЙ    │
    │                              │
    │           │                  │
    │           │ відгалуження     │  ← Ш_відг x В_відг, Д_відг
    │           ↓                  │
    │    ┌─────┬─────┐            │
    │    │  Ш  │  В  │            │  ← Ш x В: основний
    │    └─────┴─────┘            │
    │                              │
    │    Відстань від краю: ___   │
    └─────────────────────────────┘
    """,
    "Перехід круглий": """
    ┌─────────────────────────────┐
    │      ПЕРЕХІД КРУГЛИЙ       │
    │                              │
    │    ─────┐   ┌─────          │
    │         │   │                │
    │         └───┘                │
    │         Ø1 -> Ø2             │  ← Ø1 (початковий), Ø2 (кінцевий)
    │                              │
    │    Початковий Ø: ___ мм     │
    │    Кінцевий Ø:   ___ мм     │
    └─────────────────────────────┘
    """,
    "Перехід прямокутний": """
    ┌─────────────────────────────┐
    │    ПЕРЕХІД ПРЯМОКУТНИЙ     │
    │                              │
    │    ┌─────────┐              │
    │    │ Ш1 x В1 │              │  ← Ш1 x В1: початкові
    │    └────┬────┘              │
    │         │                   │
    │         ↓                   │
    │    ┌────┴────┐              │
    │    │ Ш2 x В2 │              │  ← Ш2 x В2: кінцеві
    │    └─────────┘              │
    └─────────────────────────────┘
    """,
    "Повітропровід круглий": """
    ┌─────────────────────────────┐
    │   ПОВІТРОПРОВІД КРУГЛИЙ    │
    │                              │
    │    ======================    │  ← Д: довжина труби
    │         ↑                    │
    │         Ø                    │  ← Ø: діаметр
    │                              │
    │    Довжина: ___ мм          │
    └─────────────────────────────┘
    """,
    "Повітропровід прямокутний": """
    ┌─────────────────────────────┐
    │ ПОВІТРОПРОВІД ПРЯМОКУТНИЙ  │
    │                              │
    │    ┌──────────────────┐     │  ← Д: довжина
    │    │      Ш x В       │     │  ← Ш: ширина, В: висота
    │    └──────────────────┘     │
    │                              │
    │    Довжина: ___ мм          │
    └─────────────────────────────┘
    """,
    "Фланець круглий": """
    ┌─────────────────────────────┐
    │      ФЛАНЕЦЬ КРУГЛИЙ       │
    │                              │
    │         ┌─────┐             │
    │        /   Ø   \\            │  ← Ø: діаметр
    │       │  ooooo  │           │  ← отвори
    │        \\       /             │
    │         └─────┘             │
    │                              │
    │    К-ть отворів: ___        │
    │    Профіль: P30/P40         │
    └─────────────────────────────┘
    """,
    "Фланець прямокутний": """
    ┌─────────────────────────────┐
    │    ФЛАНЕЦЬ ПРЯМОКУТНИЙ     │
    │                              │
    │    ┌─────────────┐          │
    │    │   Ш x В     │          │  ← Ш: ширина, В: висота
    │    │  o     o    │          │  ← отвори
    │    └─────────────┘          │
    │                              │
    │    К-ть отворів: ___        │
    │    Профіль: P30/P40         │
    └─────────────────────────────┘
    """,
    "Заглушка кругла": """
    ┌─────────────────────────────┐
    │      ЗАГЛУШКА КРУГЛА       │
    │                              │
    │         ┌─────┐             │
    │        │  Ø   │             │  ← Ø: діаметр
    │        │      │             │
    │         └──┬──┘             │
    │            │                │
    │            ↓ загин          │  ← Ширина загину
    │                              │
    │    Ширина загину: ___ мм    │
    │    Глибина:       ___ мм    │
    └─────────────────────────────┘
    """,
    "Заглушка прямокутна": """
    ┌─────────────────────────────┐
    │    ЗАГЛУШКА ПРЯМОКУТНА     │
    │                              │
    │    ┌─────────┐              │
    │    │  Ш x В  │              │  ← Ш: ширина, В: висота
    │    │         │              │
    │    └───┬─────┘              │
    │        │ загин               │  ← Ширина загину
    │        ↓                    │
    │                              │
    │    Ширина загину: ___ мм    │
    │    Глибина:       ___ мм    │
    └─────────────────────────────┘
    """,
    "Гнучка вставка": """
    ┌─────────────────────────────┐
    │      ГНУЧКА ВСТАВКА        │
    │                              │
    │    /\\/\\/\\/\\/\\/\\/\\/\\/\\/\\    │  ← тканина
    │         ↑                    │
    │         Ø                    │  ← Ø: діаметр
    │                              │
    │    Довжина: ___ мм          │
    │    Тканина: ПВХ/Тефлон...   │
    └─────────────────────────────┘
    """,
}


# ═══════════════════════════════════════════════════════════
# Віджет схеми (текстова)
# ═══════════════════════════════════════════════════════════

class SchemaWidget(QWidget):
    """Віджет для відображення 2D-схеми виробу через QPainter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.setMaximumHeight(280)
        self._product_type = ""
        self._params = {}

    def show_schema(self, product_type: str, params: dict = None):
        self._product_type = product_type
        self._params = params or {}
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        # Фон
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
        # Коло з діаметром
        p.drawEllipse(cx - 60, cy - 60, 120, 120)
        p.drawLine(cx - 70, cy, cx + 70, cy)
        p.drawText(cx - 10, cy - 75, "Ø")
        p.drawText(cx - 40, cy + 85, "Довжина: L")

    def _draw_rect_pipe(self, p, cx, cy):
        # Прямокутник
        p.drawRect(cx - 80, cy - 40, 160, 80)
        p.drawText(cx - 90, cy - 50, "Ш")
        p.drawText(cx + 85, cy, "В")
        p.drawText(cx - 40, cy + 65, "Довжина: L")

    def _draw_round_bend(self, p, cx, cy):
        # Кут (чверть кола)
        p.drawArc(cx - 80, cy - 80, 160, 160, 0, 90 * 16)
        p.drawLine(cx + 80, cy, cx + 80, cy - 80)
        p.drawLine(cx, cy + 80, cx + 80, cy + 80)
        p.drawText(cx + 85, cy - 40, "Ø")
        p.drawText(cx - 50, cy + 95, "Кут: 90°")

    def _draw_rect_bend(self, p, cx, cy):
        # Прямокутний кут
        p.drawLine(cx - 80, cy - 80, cx + 20, cy - 80)
        p.drawLine(cx + 20, cy - 80, cx + 20, cy + 80)
        p.drawLine(cx - 80, cy - 80, cx - 80, cy + 20)
        p.drawLine(cx - 80, cy + 20, cx + 80, cy + 20)
        p.drawText(cx - 90, cy - 90, "Ш")
        p.drawText(cx + 30, cy, "В")
        p.drawText(cx - 50, cy + 95, "Кут: 90°")

    def _draw_round_tee(self, p, cx, cy):
        # Трійник круглий
        p.drawEllipse(cx - 80, cy - 20, 160, 40)  # горизонтальна труба
        p.drawEllipse(cx - 20, cy - 80, 40, 120)  # вертикальна труба
        p.drawText(cx - 90, cy, "Ø основний")
        p.drawText(cx + 25, cy - 50, "Ø відгал.")

    def _draw_rect_tee(self, p, cx, cy):
        # Трійник прямокутний
        p.drawRect(cx - 80, cy - 20, 160, 40)   # горизонталь
        p.drawRect(cx - 20, cy - 80, 40, 100)   # вертикаль
        p.drawText(cx - 90, cy, "Ш x В")
        p.drawText(cx + 25, cy - 50, "Ш_в x В_в")

    def _draw_transition(self, p, cx, cy):
        # Перехід (трапеція)
        points = [
            (cx - 60, cy - 60), (cx + 60, cy - 60),
            (cx + 40, cy + 60), (cx - 40, cy + 60)
        ]
        polygon = QPolygon([QPoint(x, y) for x, y in points])
        p.drawPolygon(polygon)
        p.drawText(cx - 70, cy - 70, "Ш1 x В1")
        p.drawText(cx - 30, cy + 80, "Ш2 x В2")

    def _draw_round_flange(self, p, cx, cy):
        # Фланець круглий
        p.drawEllipse(cx - 60, cy - 60, 120, 120)
        # Отвори
        for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
            import math
            rad = math.radians(angle)
            x = cx + int(45 * math.cos(rad))
            y = cy + int(45 * math.sin(rad))
            p.drawEllipse(x - 4, y - 4, 8, 8)
        p.drawText(cx - 10, cy - 75, "Ø")
        p.drawText(cx - 40, cy + 85, "8 отворів")

    def _draw_rect_flange(self, p, cx, cy):
        # Фланець прямокутний
        p.drawRect(cx - 70, cy - 50, 140, 100)
        # Отвори по кутах
        for dx, dy in [(-55, -35), (55, -35), (55, 35), (-55, 35)]:
            p.drawEllipse(cx + dx - 4, cy + dy - 4, 8, 8)
        p.drawText(cx - 80, cy - 60, "Ш x В")
        p.drawText(cx - 40, cy + 75, "4 отвори")

    def _draw_round_cap(self, p, cx, cy):
        # Заглушка кругла
        p.drawEllipse(cx - 60, cy - 60, 120, 120)
        p.drawArc(cx - 70, cy - 70, 140, 140, 0, 180 * 16)
        p.drawText(cx - 10, cy - 75, "Ø")
        p.drawText(cx - 50, cy + 85, "Загин: 20 мм")

    def _draw_rect_cap(self, p, cx, cy):
        # Заглушка прямокутна
        p.drawRect(cx - 70, cy - 50, 140, 100)
        p.drawLine(cx - 80, cy - 60, cx - 70, cy - 50)
        p.drawLine(cx + 70, cy - 50, cx + 80, cy - 60)
        p.drawText(cx - 80, cy - 70, "Ш x В")
        p.drawText(cx - 50, cy + 75, "Загин: 20 мм")

    def _draw_flexible(self, p, cx, cy):
        # Гнучка вставка (хвиляста лінія)
        import math
        points = []
        for i in range(20):
            x = cx - 100 + i * 10
            y = cy + int(20 * math.sin(i * 0.5))
            points.append(QPoint(x, y))
        for i in range(len(points) - 1):
            p.drawLine(points[i], points[i + 1])
        p.drawText(cx - 10, cy - 35, "Ø")
        p.drawText(cx - 40, cy + 45, "Тканина: ПВХ")



# ═══════════════════════════════════════════════════════════
# Діалог додавання/редагування
# ═══════════════════════════════════════════════════════════

class ProductDialog(QDialog):
    """Діалог з правильними параметрами та схемою."""

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

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── ЛІВА ПАНЕЛЬ: Форма ──
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setMinimumWidth(480)
        layout.addWidget(left_scroll)

        left_widget = QWidget()
        form = QFormLayout(left_widget)
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)

        # Назва
        self.edit_name = QLineEdit(self._data.get("name", ""))
        self.edit_name.setPlaceholderText("Напр.: Відвод круглий Ø250мм 90°")
        form.addRow("Назва *", self.edit_name)

        # Тип
        self.combo_type = QComboBox()
        self.combo_type.addItems(list(SCHEMAS.keys()))
        self.combo_type.setCurrentText(self._data.get("product_type", "Повітропровід круглий"))
        self.combo_type.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Тип", self.combo_type)

        # Основні розміри
        self.group_sizes = QGroupBox("Розміри (мм)")
        sizes_layout = QGridLayout(self.group_sizes)

        self.spin_width = QDoubleSpinBox()
        self.spin_width.setRange(50, 2000)
        self.spin_width.setSuffix(" мм")
        self.spin_width.setValue(self._data.get("width", 250))
        sizes_layout.addWidget(QLabel("Ø/Ш:"), 0, 0)
        sizes_layout.addWidget(self.spin_width, 0, 1)

        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(50, 2000)
        self.spin_height.setSuffix(" мм")
        self.spin_height.setValue(self._data.get("height", 0))
        sizes_layout.addWidget(QLabel("В:"), 0, 2)
        sizes_layout.addWidget(self.spin_height, 0, 3)

        self.spin_length = QDoubleSpinBox()
        self.spin_length.setRange(0, 5000)
        self.spin_length.setSuffix(" мм")
        self.spin_length.setValue(self._data.get("length", 1000))
        sizes_layout.addWidget(QLabel("Д:"), 1, 0)
        sizes_layout.addWidget(self.spin_length, 1, 1)

        form.addRow(self.group_sizes)

        # Динамічні поля
        self.group_dynamic = QGroupBox("Додаткові параметри")
        self.dynamic_layout = QGridLayout(self.group_dynamic)
        self.group_dynamic.setVisible(False)
        form.addRow(self.group_dynamic)

        # Матеріал
        self.group_material = QGroupBox("Матеріал")
        mat_layout = QHBoxLayout(self.group_material)

        self.combo_material = QComboBox()
        self.combo_material.addItems(["Оцинкована сталь", "Нержавіюча сталь", "Алюміній"])
        self.combo_material.setCurrentText(self._data.get("material", "Оцинкована сталь"))
        mat_layout.addWidget(self.combo_material)

        self.combo_thickness = QComboBox()
        self.combo_thickness.addItems(["0.5", "0.7", "0.9", "1.0", "1.2", "1.5", "2.0"])
        self.combo_thickness.setCurrentText(str(self._data.get("thickness", "0.7")))
        mat_layout.addWidget(QLabel("Товщина:"))
        mat_layout.addWidget(self.combo_thickness)

        form.addRow(self.group_material)

        # Фланці
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

        # Кількість
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 9999)
        self.spin_qty.setValue(self._data.get("quantity", 1))
        form.addRow("Кількість", self.spin_qty)

        # Категорія
        self.combo_category = QComboBox()
        self.combo_category.addItems([
            "Стандартна (30%)", "Преміум (40%)", "Економ (20%)", "Спецзамовлення (50%)"
        ])
        form.addRow("Категорія", self.combo_category)

        # Кнопка розрахунку
        btn_calc = QPushButton("🧮 Розрахувати ціну")
        btn_calc.setObjectName("primary")
        btn_calc.setMinimumHeight(36)
        btn_calc.clicked.connect(self._on_calc)
        form.addRow(btn_calc)

        # Результат
        self.result_box = QGroupBox("💰 Розрахунок")
        self.result_box.setVisible(False)
        result_layout = QVBoxLayout(self.result_box)

        self.lbl_result = QLabel("Натисніть 'Розрахувати ціну'")
        self.lbl_result.setWordWrap(True)
        self.lbl_result.setStyleSheet("font-size: 12px; line-height: 1.5;")
        result_layout.addWidget(self.lbl_result)

        form.addRow(self.result_box)

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        left_scroll.setWidget(left_widget)

        # ── ПРАВА ПАНЕЛЬ: Схема + опис ──
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
        self.lbl_description.setStyleSheet("font-size: 12px; padding: 8px; background: #1a1a2e; border-radius: 8px;")
        right_layout.addWidget(self.lbl_description)
        right_layout.addStretch()

        layout.addWidget(right_widget)

    def _clear_dynamic(self):
        while self.dynamic_layout.count():
            item = self.dynamic_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.group_dynamic.setVisible(False)

    def _add_dynamic_field(self, label: str, widget, row: int, col: int = 0):
        self.dynamic_layout.addWidget(QLabel(label), row, col)
        self.dynamic_layout.addWidget(widget, row, col + 1)

    def _on_type_changed(self, text: str):
        self._clear_dynamic()
        pt = text.lower()

        # Оновлюємо схему
        self.schema_widget.show_schema(text, self._params if hasattr(self, "_params") else {})

        # Опис параметрів
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

        # Налаштування базових полів
        if "кругл" in pt or "фланець кругл" in pt or "заглушка кругл" in pt:
            self.spin_width.setPrefix("Ø ")
            self.spin_height.setEnabled(False)
            self.spin_height.setValue(0)
        else:
            self.spin_width.setPrefix("")
            self.spin_height.setEnabled(True)

        # Для відводу — довжина не потрібна
        if "відвод" in pt:
            self.spin_length.setEnabled(False)
            self.spin_length.setValue(0)
            self.spin_length.setSuffix(" (не використовується)")
        else:
            self.spin_length.setEnabled(True)
            self.spin_length.setSuffix(" мм")

        # Динамічні поля
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

    def _on_calc(self):
        """Розрахувати ціну."""
        pt = self.combo_type.currentText()
        mat = self.combo_material.currentText()
        thick = float(self.combo_thickness.currentText())
        w = self.spin_width.value()
        h = self.spin_height.value() if self.spin_height.isEnabled() else 0
        l = self.spin_length.value() if self.spin_length.isEnabled() else 0
        qty = self.spin_qty.value()

        bend_angle = 90
        radius = 0
        branch_w = 0
        branch_h = 0
        branch_l = 0

        if hasattr(self, 'spin_bend_angle'):
            bend_angle = self.spin_bend_angle.value()
        if hasattr(self, 'spin_radius'):
            radius = self.spin_radius.value()
        if hasattr(self, 'spin_branch_width'):
            branch_w = self.spin_branch_width.value()
        if hasattr(self, 'spin_branch_height'):
            branch_h = self.spin_branch_height.value()
        if hasattr(self, 'spin_branch_length'):
            branch_l = self.spin_branch_length.value()

        surface = calc_surface_area(pt, w, h, l, bend_angle, radius, branch_w, branch_h, branch_l)
        blank = surface * 1.15
        material_area = blank * 1.05

        markup_map = {"Стандартна (30%)": 30, "Преміум (40%)": 40, "Економ (20%)": 20, "Спецзамовлення (50%)": 50}
        custom_markup = markup_map.get(self.combo_category.currentText(), 30)

        flange_count = 0
        flange_price = 0
        if self.chk_with_flanges.isChecked():
            flange_count = self.spin_flange_count.value()
            flange_price = 150.0 if self.combo_flange_profile.currentText() == "P30" else 200.0

        result = self._engine.calculate(
            product_type=pt, material_name=mat, thickness_mm=thick,
            surface_area_m2=surface, blank_area_m2=blank, material_area_m2=material_area,
            quantity=qty, flange_count=flange_count, flange_price=flange_price,
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

    def _on_save(self):
        if not self.edit_name.text().strip():
            QMessageBox.warning(self, "Помилка", "Введіть назву виробу")
            return
        if not self._calc_result:
            reply = QMessageBox.question(
                self, "Розрахунок", "Ціну не розраховано. Розрахувати зараз?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_calc()
                return
        self.accept()

    def get_data(self) -> dict:
        qty = self.spin_qty.value()
        price = self._calc_result.final_price if self._calc_result else 0

        params = {
            "with_flanges": self.chk_with_flanges.isChecked(),
            "flange_count": self.spin_flange_count.value() if self.chk_with_flanges.isChecked() else 0,
            "flange_profile": self.combo_flange_profile.currentText() if self.chk_with_flanges.isChecked() else "",
            "category": self.combo_category.currentText(),
        }

        if hasattr(self, 'spin_bend_angle'):
            params["bend_angle"] = self.spin_bend_angle.value()
        if hasattr(self, 'spin_radius'):
            params["radius"] = self.spin_radius.value()
        if hasattr(self, 'spin_ext_top'):
            params["ext_top"] = self.spin_ext_top.value()
        if hasattr(self, 'spin_ext_bottom'):
            params["ext_bottom"] = self.spin_ext_bottom.value()
        if hasattr(self, 'spin_branch_dist'):
            params["branch_dist"] = self.spin_branch_dist.value()
        if hasattr(self, 'spin_branch_width'):
            params["branch_width"] = self.spin_branch_width.value()
        if hasattr(self, 'spin_branch_height'):
            params["branch_height"] = self.spin_branch_height.value()
        if hasattr(self, 'spin_branch_length'):
            params["branch_length"] = self.spin_branch_length.value()
        if hasattr(self, 'spin_end_width'):
            params["end_width"] = self.spin_end_width.value()
        if hasattr(self, 'spin_end_height'):
            params["end_height"] = self.spin_end_height.value()
        if hasattr(self, 'spin_bend_width'):
            params["bend_width"] = self.spin_bend_width.value()
        if hasattr(self, 'spin_depth'):
            params["depth"] = self.spin_depth.value()
        if hasattr(self, 'combo_fabric'):
            params["fabric"] = self.combo_fabric.currentText()
        if hasattr(self, 'spin_holes'):
            params["holes"] = self.spin_holes.value()

        project_id = self.parent().main_window.active_project_id if self.parent() and hasattr(self.parent(), "main_window") else None
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
            "unit_price": round(price / qty, 2) if qty > 1 else price,
            "total_price": price,
            "notes": json.dumps(params) if params else "",
        }


# ═══════════════════════════════════════════════════════════
# Головна вкладка
# ═══════════════════════════════════════════════════════════

class ProductsTab(QWidget):
    """Вкладка управління виробами."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self._all_data: list[dict] = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Ліва панель
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(12)
        left_layout.setContentsMargins(0, 0, 0, 0)

        lbl_title = QLabel("🔧 Вироби")
        lbl_title.setObjectName("title")
        left_layout.addWidget(lbl_title)

        btn_new = QPushButton("➕ Додати виріб")
        btn_new.setObjectName("primary")
        btn_new.setMinimumHeight(36)
        btn_new.clicked.connect(self._on_add)
        left_layout.addWidget(btn_new)

        filters_group = QGroupBox("🔍 Фільтри")
        filters_layout = QVBoxLayout(filters_group)

        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Пошук за назвою...")
        self.edit_search.textChanged.connect(self._apply_filters)
        filters_layout.addWidget(self.edit_search)

        filter_row = QHBoxLayout()
        self.filter_type = QComboBox()
        self.filter_type.addItem("Всі типи")
        self.filter_type.addItems(list(SCHEMAS.keys()))
        self.filter_type.currentTextChanged.connect(self._apply_filters)
        filter_row.addWidget(QLabel("Тип:"))
        filter_row.addWidget(self.filter_type)
        filters_layout.addLayout(filter_row)

        mat_row = QHBoxLayout()
        self.filter_material = QComboBox()
        self.filter_material.addItem("Всі матеріали")
        self.filter_material.addItems(["Оцинкована сталь", "Нержавіюча сталь", "Алюміній"])
        self.filter_material.currentTextChanged.connect(self._apply_filters)
        mat_row.addWidget(QLabel("Мат.:"))
        mat_row.addWidget(self.filter_material)
        filters_layout.addLayout(mat_row)

        btn_reset = QPushButton("♻️ Скинути")
        btn_reset.clicked.connect(self._reset_filters)
        filters_layout.addWidget(btn_reset)

        left_layout.addWidget(filters_group)
        left_layout.addStretch()
        splitter.addWidget(left_panel)

        # Права панель
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(12)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableView()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._on_edit)
        right_layout.addWidget(self.table)

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "ID", "Назва", "Тип", "Розміри", "Мат.", "Товщ.", "К-ть", "Ціна", "Сума"
        ])
        self.table.setModel(self.model)

        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 110)
        self.table.setColumnWidth(5, 50)
        self.table.setColumnWidth(6, 50)
        self.table.setColumnWidth(7, 80)
        self.table.setColumnWidth(8, 80)

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

        right_layout.addLayout(actions)

        self.lbl_summary = QLabel("Всього: 0 виробів | Сума: ₴ 0")
        self.lbl_summary.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 12px; padding: 4px;")
        right_layout.addWidget(self.lbl_summary)

        splitter.addWidget(right_panel)
        splitter.setSizes([350, 750])

    def _load_data(self):
        try:
            project_id = self.main_window.active_project_id if self.main_window else None
            self._all_data = ProductRepository.get_all(project_id=project_id)
            self._populate_table(self._all_data)
        except Exception as e:
            QMessageBox.critical(self, "Помилка БД", f"Не вдалося завантажити вироби: {e}")

    def _populate_table(self, items: list[dict]):
        self.model.removeRows(0, self.model.rowCount())
        total_sum = 0
        for item in items:
            sizes = f"{item.get('width') or 0}×{item.get('height') or 0}×{item.get('length') or 0}"
            row = [
                QStandardItem(str(item.get("id", ""))),
                QStandardItem(item.get("name", "")),
                QStandardItem(item.get("product_type", "")),
                QStandardItem(sizes),
                QStandardItem(item.get("material", "")),
                QStandardItem(str(item.get("thickness", ""))),
                QStandardItem(str(item.get("quantity", 1))),
                QStandardItem(f"{float(item.get('unit_price', 0)):.2f}"),
                QStandardItem(f"{float(item.get('total_price', 0)):.2f}"),
            ]
            for cell in row:
                cell.setEditable(False)
            self.model.appendRow(row)
            total_sum += float(item.get("total_price", 0))

        self.lbl_summary.setText(f"Всього: {len(items)} виробів | Сума: ₴ {total_sum:,.2f}")

    def _apply_filters(self):
        try:
            project_id = self.main_window.active_project_id if self.main_window else None
            items = ProductRepository.search(
                query=self.edit_search.text().strip(),
                product_type=self.filter_type.currentText(),
                material=self.filter_material.currentText(),
                project_id=project_id,
            )
            self._populate_table(items)
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Фільтрація не вдалася: {e}")

    def _reset_filters(self):
        self.edit_search.clear()
        self.filter_type.setCurrentIndex(0)
        self.filter_material.setCurrentIndex(0)
        self._load_data()

    def _get_selected_id(self) -> int | None:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        row = idx.row()
        id_val = self.model.item(row, 0).text()
        return int(id_val) if id_val.isdigit() else None

    def _on_add(self):
        dlg = ProductDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                ProductRepository.create(data)
                self._load_data()
                QMessageBox.information(self, "Успіх", "Виріб додано!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти: {e}")

    def _on_edit(self):
        item_id = self._get_selected_id()
        if not item_id:
            QMessageBox.warning(self, "Увага", "Виберіть виріб для редагування")
            return
        try:
            item = ProductRepository.get_by_id(item_id)
            if not item:
                QMessageBox.warning(self, "Увага", "Виріб не знайдено")
                return
            dlg = ProductDialog(item, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                new_data = dlg.get_data()
                ProductRepository.update(item_id, new_data)
                self._load_data()
                QMessageBox.information(self, "Успіх", "Виріб оновлено!")
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося оновити: {e}")

    def _on_delete(self):
        item_id = self._get_selected_id()
        if not item_id:
            QMessageBox.warning(self, "Увага", "Виберіть виріб для видалення")
            return
        reply = QMessageBox.question(
            self, "Видалення", f"Видалити виріб #{item_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                ProductRepository.delete(item_id)
                self._load_data()
                QMessageBox.information(self, "Успіх", "Виріб видалено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити: {e}")

    def on_project_changed(self, project_id: int | None):
        self._load_data()

    def refresh(self):
        self._load_data()
