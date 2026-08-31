"""Вкладка "Розкрій" (PySide6) — з реальним MetalCutter + канвас.

Використовує ventilation_company.metal_cutting для розрахунку розгорток.
"""

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QComboBox, QMessageBox, QAbstractItemView,
    QSplitter, QSpinBox, QDoubleSpinBox, QLineEdit,
    QDialog, QFormLayout, QDialogButtonBox
)
from PySide6.QtGui import (
    QStandardItemModel, QStandardItem, QPainter, QPen, QBrush,
    QColor, QFont, QFontMetrics, QWheelEvent, QMouseEvent
)

from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.metal_cutting import MetalCutter


class AddProductDialog(QDialog):
    """Діалог додавання виробу для розкрою."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("➕ Додати виріб")
        self.setMinimumWidth(400)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("Напр.: Повітропровід 400×200×1000")
        layout.addRow("Назва", self.edit_name)

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
        layout.addRow("Тип", self.combo_type)

        sizes = QHBoxLayout()
        self.spin_a = QDoubleSpinBox()
        self.spin_a.setRange(50, 5000)
        self.spin_a.setSuffix(" мм")
        self.spin_a.setDecimals(0)
        sizes.addWidget(QLabel("A/Ш:"))
        sizes.addWidget(self.spin_a)

        self.spin_b = QDoubleSpinBox()
        self.spin_b.setRange(50, 5000)
        self.spin_b.setSuffix(" мм")
        self.spin_b.setDecimals(0)
        sizes.addWidget(QLabel("B/В:"))
        sizes.addWidget(self.spin_b)

        self.spin_l = QDoubleSpinBox()
        self.spin_l.setRange(0, 10000)
        self.spin_l.setSuffix(" мм")
        self.spin_l.setDecimals(0)
        sizes.addWidget(QLabel("L/Д:"))
        sizes.addWidget(self.spin_l)
        layout.addRow("Розміри", sizes)

        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 999)
        self.spin_qty.setValue(1)
        layout.addRow("Кількість", self.spin_qty)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_save(self):
        if not self.edit_name.text().strip():
            QMessageBox.warning(self, "Помилка", "Введіть назву")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.edit_name.text().strip(),
            "type": self.combo_type.currentText(),
            "width": self.spin_a.value(),
            "height": self.spin_b.value(),
            "length": self.spin_l.value(),
            "quantity": self.spin_qty.value(),
        }


class CuttingCanvas(QWidget):
    """Канвас для візуалізації плану розкрою."""

    DETAIL_COLORS = [
        "#89b4fa", "#a6e3a1", "#f9e2af", "#f38ba8",
        "#cba6f7", "#74c7ec", "#fab387", "#94e2d5",
        "#b4befe", "#f5e0dc", "#a6adc8", "#f2cdcd",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sheet_w = 1250.0
        self.sheet_h = 2500.0
        self.placed_details = []
        self.scale = 0.25
        self.offset_x = 20.0
        self.offset_y = 20.0
        self.dragging = False
        self.last_mouse = QPointF()
        self.setMinimumSize(500, 800)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setStyleSheet(f"background-color: {Theme.BG_DARK}; border-radius: 8px;")

    def set_sheet(self, sheet):
        self.sheet_w = sheet.width
        self.sheet_h = sheet.height
        self.placed_details = sheet.placed_details
        self._fit_to_view()
        self.update()

    def _fit_to_view(self):
        margin = 20
        avail_w = max(self.width() - margin, 100)
        avail_h = max(self.height() - margin, 100)
        sc_w = avail_w / self.sheet_w
        sc_h = avail_h / self.sheet_h
        self.scale = min(sc_w, sc_h) * 0.98
        self.offset_x = (self.width() - self.sheet_w * self.scale) / 2
        self.offset_y = (self.height() - self.sheet_h * self.scale) / 2

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(Theme.BG_DARK))

        sw = self.sheet_w * self.scale
        sh = self.sheet_h * self.scale
        ox = self.offset_x
        oy = self.offset_y

        # Тінь
        painter.fillRect(int(ox + 3), int(oy + 3), int(sw), int(sh), QColor(0, 0, 0, 60))
        # Лист
        pen_sheet = QPen(QColor("#45475a"), 2)
        brush_sheet = QBrush(QColor("#1e1e2e"))
        painter.setPen(pen_sheet)
        painter.setBrush(brush_sheet)
        painter.drawRect(int(ox), int(oy), int(sw), int(sh))

        # Сітка 100 мм
        pen_grid = QPen(QColor(Theme.BORDER), 1)
        painter.setPen(pen_grid)
        step = 100 * self.scale
        for i in range(1, int(self.sheet_w / 100) + 1):
            x = ox + i * step
            painter.drawLine(int(x), int(oy), int(x), int(oy + sh))
        for i in range(1, int(self.sheet_h / 100) + 1):
            y = oy + i * step
            painter.drawLine(int(ox), int(y), int(ox + sw), int(y))

        # Розміри листа
        font_dim = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font_dim)
        painter.setPen(QColor(Theme.TEXT_MUTED))
        painter.drawText(int(ox + sw / 2 - 30), int(oy + sh + 18), f"{self.sheet_w:.0f} мм")
        painter.save()
        painter.translate(int(ox + sw + 18), int(oy + sh / 2 + 30))
        painter.rotate(-90)
        painter.drawText(0, 0, f"{self.sheet_h:.0f} мм")
        painter.restore()

        # Деталі
        fm = QFontMetrics(QFont("Segoe UI", 9))
        for i, p in enumerate(self.placed_details):
            idx = i + 1
            dx = ox + p.x * self.scale
            dy = oy + p.y * self.scale
            dw = p.width * self.scale
            dh = p.height * self.scale

            if dw < 2 or dh < 2:
                continue

            color = QColor(self.DETAIL_COLORS[i % len(self.DETAIL_COLORS)])
            color_dark = color.darker(130)
            color_light = QColor(color)
            color_light.setAlpha(90)

            # Заливка
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color_light))
            painter.drawRect(int(dx), int(dy), int(dw), int(dh))

            # Рамка
            pen_frame = QPen(color_dark, max(1.5, self.scale * 0.8))
            painter.setPen(pen_frame)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(int(dx), int(dy), int(dw), int(dh))

            # Номер позиції
            font_num = QFont("Segoe UI", max(8, int(min(dw, dh) / 6)), QFont.Weight.Bold)
            painter.setFont(font_num)
            num_text = str(idx)
            tw = fm.horizontalAdvance(num_text)
            th = fm.height()
            tx = dx + dw / 2 - tw / 2
            ty = dy + dh / 2 + th / 4
            bg_rect = QRectF(tx - 4, ty - th + 2, tw + 8, th + 4)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(bg_rect, 4, 4)
            painter.setPen(QColor(Theme.BG_DARK))
            painter.drawText(int(tx), int(ty), num_text)

            # Назва + розміри
            if dw > 60 and dh > 40:
                font_text = QFont("Segoe UI", max(7, int(min(dw, dh) / 10)))
                painter.setFont(font_text)
                painter.setPen(QColor(Theme.BG_DARK))
                name = p.detail.name[:18]
                size_txt = f"{p.width:.0f}×{p.height:.0f}"
                painter.drawText(int(dx + 4), int(dy + 14), name)
                painter.drawText(int(dx + 4), int(dy + 26), size_txt)

        # Підказка
        font_info = QFont("Segoe UI", 9)
        painter.setFont(font_info)
        painter.setPen(QColor(Theme.TEXT_MUTED))
        painter.drawText(10, self.height() - 10, f"Масштаб: 1:{1/self.scale:.0f}  |  ЛКМ — перетягування  |  Колесо — масштаб")
        painter.end()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 0.87
        old_scale = self.scale
        self.scale *= factor
        self.scale = max(0.05, min(self.scale, 2.0))
        mouse_pos = event.position()
        self.offset_x = mouse_pos.x() - (mouse_pos.x() - self.offset_x) * (self.scale / old_scale)
        self.offset_y = mouse_pos.y() - (mouse_pos.y() - self.offset_y) * (self.scale / old_scale)
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.last_mouse = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            delta = event.position() - self.last_mouse
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self.last_mouse = event.position()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_to_view()
        self.update()


class CuttingTab(QWidget):
    """Вкладка розкрою з реальним MetalCutter + канвас."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._products = []
        self._plan = None
        self._current_sheet_idx = 0
        self._build_ui()
        self._load_default_products()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Заголовок
        header = QHBoxLayout()
        lbl_title = QLabel("✂️ Розкрій металу")
        lbl_title.setObjectName("title")
        header.addWidget(lbl_title)
        header.addStretch()

        lbl_sheet = QLabel("Лист:")
        lbl_sheet.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        header.addWidget(lbl_sheet)

        self.combo_sheet = QComboBox()
        self.combo_sheet.addItems(["1250×2500 мм", "1000×2000 мм", "1500×3000 мм", "1250×3000 мм"])
        header.addWidget(self.combo_sheet)

        lbl_thick = QLabel("Товщина:")
        lbl_thick.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        header.addWidget(lbl_thick)

        self.combo_thick = QComboBox()
        self.combo_thick.addItems(["0.5", "0.7", "1.0", "1.2", "1.5", "2.0"])
        self.combo_thick.setCurrentText("0.7")
        header.addWidget(self.combo_thick)

        lbl_mat = QLabel("Матеріал:")
        lbl_mat.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        header.addWidget(lbl_mat)

        self.combo_material = QComboBox()
        self.combo_material.addItems(["оцинкована сталь", "нержавіюча сталь", "алюміній"])
        header.addWidget(self.combo_material)

        btn_calc = QPushButton("🧮 Розрахувати")
        btn_calc.setObjectName("primary")
        btn_calc.setMinimumHeight(32)
        btn_calc.clicked.connect(self._calculate)
        header.addWidget(btn_calc)

        layout.addLayout(header)

        # Замовлення
        order = QHBoxLayout()
        order.setSpacing(12)

        order_left = QVBoxLayout()
        lbl_order = QLabel("📋 Замовлення")
        lbl_order.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-weight: bold; padding: 4px;")
        order_left.addWidget(lbl_order)

        self.table_order = QTableView()
        self.table_order.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_order.setAlternatingRowColors(True)
        self.table_order.horizontalHeader().setStretchLastSection(True)
        self.table_order.verticalHeader().setVisible(False)
        self.table_order.setMaximumHeight(200)
        order_left.addWidget(self.table_order)

        self.model_order = QStandardItemModel()
        self.model_order.setHorizontalHeaderLabels(["Назва", "Тип", "A", "B", "L", "К-ть"])
        self.table_order.setModel(self.model_order)

        for i, w in enumerate([200, 150, 55, 55, 55, 50]):
            self.table_order.setColumnWidth(i, w)

        order_btns = QHBoxLayout()
        btn_add = QPushButton("➕ Додати")
        btn_add.clicked.connect(self._on_add_product)
        order_btns.addWidget(btn_add)

        btn_del = QPushButton("🗑️ Видалити")
        btn_del.setStyleSheet(f"color: {Theme.DANGER};")
        btn_del.clicked.connect(self._on_del_product)
        order_btns.addWidget(btn_del)

        btn_clear = QPushButton("♻️ Очистити")
        btn_clear.clicked.connect(self._on_clear_products)
        order_btns.addWidget(btn_clear)
        order_btns.addStretch()
        order_left.addLayout(order_btns)

        order.addLayout(order_left, 1)

        # Результати
        order_right = QVBoxLayout()
        lbl_res = QLabel("📊 Результати")
        lbl_res.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-weight: bold; padding: 4px;")
        order_right.addWidget(lbl_res)

        self.lbl_sheets = QLabel("Листів: —")
        self.lbl_sheets.setStyleSheet(f"color: {Theme.TEXT}; padding: 8px 12px; background: {Theme.BG_CARD}; border-radius: 8px;")
        order_right.addWidget(self.lbl_sheets)

        self.lbl_util = QLabel("Використання: — %")
        self.lbl_util.setStyleSheet(f"color: {Theme.SUCCESS}; font-weight: bold; padding: 8px 12px; background: {Theme.BG_CARD}; border-radius: 8px;")
        order_right.addWidget(self.lbl_util)

        self.lbl_waste = QLabel("Відходи: — %")
        self.lbl_waste.setStyleSheet(f"color: {Theme.WARNING}; padding: 8px 12px; background: {Theme.BG_CARD}; border-radius: 8px;")
        order_right.addWidget(self.lbl_waste)

        self.lbl_area = QLabel("Площа деталей: — м²")
        self.lbl_area.setStyleSheet(f"color: {Theme.ACCENT}; padding: 8px 12px; background: {Theme.BG_CARD}; border-radius: 8px;")
        order_right.addWidget(self.lbl_area)

        order_right.addStretch()
        order.addLayout(order_right, 0)
        layout.addLayout(order)

        # Спліттер
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        lbl_tbl = QLabel("📋 Деталі на листі")
        lbl_tbl.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-weight: bold; padding: 4px;")
        left_layout.addWidget(lbl_tbl)

        self.table = QTableView()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumWidth(440)
        left_layout.addWidget(self.table)

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["№", "Назва", "Шир.", "Вис.", "X", "Y", "Повернуто"])
        self.table.setModel(self.model)

        for i, w in enumerate([40, 190, 55, 55, 50, 50, 70]):
            self.table.setColumnWidth(i, w)

        left_layout.addWidget(self.table)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        lbl_vis = QLabel("🎨 Візуалізація плану розкрою")
        lbl_vis.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-weight: bold; padding: 4px;")
        right_layout.addWidget(lbl_vis)

        self.canvas = CuttingCanvas()
        right_layout.addWidget(self.canvas, 1)

        splitter.addWidget(right)
        splitter.setSizes([480, 720])

        layout.addWidget(splitter, 1)

        # Навігація
        nav = QHBoxLayout()
        nav.addStretch()

        btn_fit = QPushButton("🔍 Вмістити в екран")
        btn_fit.clicked.connect(self._fit_view)
        nav.addWidget(btn_fit)

        btn_prev = QPushButton("◀ Попередній лист")
        btn_prev.clicked.connect(self._prev_sheet)
        nav.addWidget(btn_prev)

        self.lbl_sheet_num = QLabel("Лист 1 / 1")
        self.lbl_sheet_num.setStyleSheet(f"color: {Theme.TEXT}; padding: 0 12px;")
        nav.addWidget(self.lbl_sheet_num)

        btn_next = QPushButton("Наступний лист ▶")
        btn_next.clicked.connect(self._next_sheet)
        nav.addWidget(btn_next)

        nav.addSpacing(24)

        btn_export = QPushButton("📤 Експорт PNG")
        btn_export.clicked.connect(self._on_export)
        nav.addWidget(btn_export)

        layout.addLayout(nav)

    def _load_default_products(self):
        self._products = [
            {"name": "Повітропровід 400×200×500", "type": "повітропровід прямокутний", "width": 400, "height": 200, "length": 500, "quantity": 4},
            {"name": "Відвод 400×200 90°", "type": "відвод прямокутний", "width": 400, "height": 200, "length": 0, "quantity": 2},
            {"name": "Трійник 400×200", "type": "трійник прямокутний", "width": 400, "height": 200, "length": 300, "quantity": 1, "branch_width": 200, "branch_height": 200, "branch_length": 200},
            {"name": "Фланець 400×200", "type": "фланець прямокутний", "width": 400, "height": 200, "length": 0, "quantity": 8, "flange_border": 30},
            {"name": "Заглушка 400×200", "type": "заглушка прямокутна", "width": 400, "height": 200, "length": 0, "quantity": 2, "flange_border": 25},
            {"name": "Повітропровід Ø315×500", "type": "повітропровід круглий", "width": 315, "height": 315, "length": 500, "quantity": 2},
        ]
        self._refresh_order_table()

    def _refresh_order_table(self):
        self.model_order.removeRows(0, self.model_order.rowCount())
        for p in self._products:
            row = [
                QStandardItem(p.get("name", "")),
                QStandardItem(p.get("type", "")),
                QStandardItem(str(p.get("width", 0))),
                QStandardItem(str(p.get("height", 0))),
                QStandardItem(str(p.get("length", 0))),
                QStandardItem(str(p.get("quantity", 1))),
            ]
            for cell in row:
                cell.setEditable(False)
            self.model_order.appendRow(row)

    def _on_add_product(self):
        dlg = AddProductDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._products.append(dlg.get_data())
            self._refresh_order_table()

    def _on_del_product(self):
        idx = self.table_order.currentIndex()
        if not idx.isValid():
            QMessageBox.warning(self, "Увага", "Виберіть виріб для видалення")
            return
        self._products.pop(idx.row())
        self._refresh_order_table()

    def _on_clear_products(self):
        self._products.clear()
        self._refresh_order_table()

    def _calculate(self):
        if not self._products:
            QMessageBox.warning(self, "Увага", "Додайте вироби для розкрою")
            return

        try:
            sheet_text = self.combo_sheet.currentText()
            sheet_size = {
                "1250×2500 мм": (1250, 2500),
                "1000×2000 мм": (1000, 2000),
                "1500×3000 мм": (1500, 3000),
                "1250×3000 мм": (1250, 3000),
            }.get(sheet_text, (1250, 2500))

            cutter = MetalCutter(
                sheet_width=sheet_size[0],
                sheet_height=sheet_size[1],
                thickness=float(self.combo_thick.currentText()),
                material=self.combo_material.currentText(),
            )

            self._plan = cutter.calculate_from_products(self._products, allow_rotation=True)
            self._current_sheet_idx = 0
            self._update_display()

        except Exception as e:
            QMessageBox.critical(self, "Помилка розрахунку", str(e))

    def _update_display(self):
        if not self._plan or not self._plan.sheets:
            return

        s = self._plan.get_summary()
        self.lbl_sheets.setText(f"Листів: {s['total_sheets']}")
        self.lbl_util.setText(f"Використання: {s['utilization_percent']:.1f} %")
        self.lbl_waste.setText(f"Відходи: {s['waste_percent']:.1f} %")
        self.lbl_area.setText(f"Площа деталей: {s['used_area_m2']:.3f} м²")

        self._show_sheet(self._current_sheet_idx)

    def _show_sheet(self, idx: int):
        if not self._plan or idx < 0 or idx >= len(self._plan.sheets):
            return

        sheet = self._plan.sheets[idx]
        self.lbl_sheet_num.setText(f"Лист {idx + 1} / {len(self._plan.sheets)}")

        self.model.removeRows(0, self.model.rowCount())
        for i, p in enumerate(sheet.placed_details, 1):
            row = [
                QStandardItem(str(i)),
                QStandardItem(p.detail.name),
                QStandardItem(f"{p.width:.0f}"),
                QStandardItem(f"{p.height:.0f}"),
                QStandardItem(f"{p.x:.0f}"),
                QStandardItem(f"{p.y:.0f}"),
                QStandardItem("Так" if p.rotated else "Ні"),
            ]
            for cell in row:
                cell.setEditable(False)
            self.model.appendRow(row)

        self.canvas.set_sheet(sheet)

    def _fit_view(self):
        self.canvas._fit_to_view()
        self.canvas.update()

    def _prev_sheet(self):
        if self._plan and self._current_sheet_idx > 0:
            self._current_sheet_idx -= 1
            self._show_sheet(self._current_sheet_idx)

    def _next_sheet(self):
        if self._plan and self._current_sheet_idx < len(self._plan.sheets) - 1:
            self._current_sheet_idx += 1
            self._show_sheet(self._current_sheet_idx)

    def _on_export(self):
        QMessageBox.information(self, "Експорт", "Експорт плану розкрою (PNG/PDF) буде тут")

    def refresh(self):
        pass
