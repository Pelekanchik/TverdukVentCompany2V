"""Вкладка "Вироби" (PySide6) з правильними параметрами, візуальною схемою та знижкою у %.

v2.4b: знижка вводиться у відсотках, кінцева ціна рахується автоматично.
"""

import csv

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.database.repositories.product_repo import ProductRepository
from ventilation_company.gui_pyside6.product_dialog import SCHEMAS, ProductDialog
from ventilation_company.gui_pyside6.theme import Theme

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
        self.model.setHorizontalHeaderLabels(
            [
                "ID",
                "Назва",
                "Тип",
                "Розміри",
                "Мат.",
                "Товщ.",
                "К-ть",
                "Ціна",
                "Знижка %",
                "Кінцева",
            ]
        )
        self.table.setModel(self.model)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 180)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 110)
        self.table.setColumnWidth(5, 50)
        self.table.setColumnWidth(6, 50)
        self.table.setColumnWidth(7, 80)
        self.table.setColumnWidth(8, 70)
        self.table.setColumnWidth(9, 80)

        actions = QGridLayout()
        action_buttons = [
            (QPushButton("💾 Експорт CSV"), self._export_csv),
            (QPushButton("📥 Імпорт CSV"), self._import_csv),
            (QPushButton("📄 Шаблон CSV"), self._download_csv_template),
            (QPushButton("📚 Пресети"), self._show_presets),
            (QPushButton("⭐ У пресети"), self._save_selected_as_preset),
            (QPushButton("🔄 Перерахувати ціни"), self._recalculate_all_prices),
            (QPushButton("✏️ Редагувати"), self._on_edit),
            (QPushButton("🗑️ Видалити"), self._on_delete),
            (QPushButton("🔄 Оновити"), self._load_data),
        ]
        action_buttons[-3][0].setStyleSheet(f"color: {Theme.DANGER};")
        for idx, (btn, slot) in enumerate(action_buttons):
            btn.clicked.connect(slot)
            actions.addWidget(btn, idx // 5, idx % 5)
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
            disc = item.get("discounted_price", 0)
            total = item.get("total_price", 0)
            # Розрахунок знижки % для відображення
            discount_pct = round((1 - disc / total) * 100, 1) if disc > 0 and total > 0 else 0
            effective = disc if disc > 0 else total
            row = [
                QStandardItem(str(item.get("id", ""))),
                QStandardItem(item.get("name", "")),
                QStandardItem(item.get("product_type", "")),
                QStandardItem(sizes),
                QStandardItem(item.get("material", "")),
                QStandardItem(str(item.get("thickness", ""))),
                QStandardItem(str(item.get("quantity", 1))),
                QStandardItem(f"{float(item.get('unit_price', 0)):.2f}"),
                QStandardItem(f"{discount_pct:.1f}%" if discount_pct > 0 else "—"),
                QStandardItem(f"{effective:.2f}"),
            ]
            for cell in row:
                cell.setEditable(False)
            if discount_pct > 0:
                row[8].setForeground(QBrush(QColor(Theme.WARNING)))
                row[9].setForeground(QBrush(QColor(Theme.ACCENT)))
            self.model.appendRow(row)
            total_sum += effective
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

    def _export_csv(self):
        project_id = self.main_window.active_project_id if self.main_window else None
        items = ProductRepository.get_all(project_id=project_id)
        path, _ = QFileDialog.getSaveFileName(
            self, "Експорт виробів", "products.csv", "CSV (*.csv)"
        )
        if not path:
            return
        fieldnames = [
            "name",
            "product_type",
            "width",
            "height",
            "length",
            "thickness",
            "material",
            "quantity",
            "cost_price",
            "unit_price",
            "total_price",
            "discounted_price",
            "notes",
            "project_id",
        ]
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for item in items:
                    row = {k: item.get(k, "") for k in fieldnames}
                    writer.writerow(row)
            QMessageBox.information(self, "Успіх", f"Експортовано виробів: {len(items)}")
        except Exception as exc:
            QMessageBox.critical(self, "Помилка", f"Не вдалося експортувати CSV: {exc}")

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Імпорт виробів", "", "CSV (*.csv)")
        if not path:
            return
        project_id = self.main_window.active_project_id if self.main_window else None

        def fnum(value, default=0.0):
            try:
                return float(str(value or "").replace(",", "."))
            except Exception:
                return default

        created = 0
        errors = 0
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        data = {
                            "name": row.get("name") or row.get("Назва") or "Імпортований виріб",
                            "product_type": row.get("product_type")
                            or row.get("Тип")
                            or "Повітропровід прямокутний",
                            "width": fnum(row.get("width") or row.get("Ширина")),
                            "height": fnum(row.get("height") or row.get("Висота")),
                            "length": fnum(row.get("length") or row.get("Довжина")),
                            "thickness": str(row.get("thickness") or row.get("Товщина") or "0.7"),
                            "material": row.get("material")
                            or row.get("Матеріал")
                            or "Оцинкована сталь",
                            "quantity": int(fnum(row.get("quantity") or row.get("Кількість"), 1)),
                            "cost_price": fnum(row.get("cost_price")),
                            "unit_price": fnum(row.get("unit_price")),
                            "total_price": fnum(row.get("total_price")),
                            "discounted_price": fnum(row.get("discounted_price")),
                            "notes": row.get("notes") or "",
                            "project_id": project_id,
                        }
                        ProductRepository.create(data)
                        created += 1
                    except Exception:
                        errors += 1
            self._load_data()
            QMessageBox.information(
                self, "Імпорт завершено", f"Створено: {created}. Помилок: {errors}."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Помилка", f"Не вдалося імпортувати CSV: {exc}")

    def _download_csv_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Зберегти шаблон CSV",
            "products_template.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        fieldnames = [
            "name",
            "product_type",
            "width",
            "height",
            "length",
            "thickness",
            "material",
            "quantity",
            "cost_price",
            "unit_price",
            "total_price",
            "discounted_price",
            "notes",
            "project_id",
        ]
        sample = {
            "name": "Повітропровід прямокутний 400x200x1000",
            "product_type": "Повітропровід прямокутний",
            "width": 400,
            "height": 200,
            "length": 1000,
            "thickness": "0.7",
            "material": "Оцинкована сталь",
            "quantity": 1,
            "cost_price": 0,
            "unit_price": 0,
            "total_price": 0,
            "discounted_price": 0,
            "notes": "",
            "project_id": "",
        }
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(sample)
            QMessageBox.information(self, "Успіх", f"Шаблон збережено: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти шаблон: {exc}")

    def _save_selected_as_preset(self):
        import json

        from ventilation_company.paths import APP_ROOT

        row = self.table.currentIndex().row()
        if row < 0:
            QMessageBox.warning(self, "Увага", "Оберіть виріб")
            return
        id_item = self.model.item(row, 0)
        if id_item is None:
            QMessageBox.warning(self, "Увага", "Оберіть виріб")
            return
        try:
            product_id = int(id_item.text())
        except Exception:
            QMessageBox.warning(self, "Увага", "Не вдалося визначити виріб")
            return
        data = next(
            (item for item in getattr(self, "_all_data", []) if item.get("id") == product_id), None
        )
        if not data:
            QMessageBox.warning(self, "Увага", "Не вдалося знайти дані виробу")
            return
        try:
            custom_file = APP_ROOT / "data" / "custom_product_presets.json"
            custom_file.parent.mkdir(parents=True, exist_ok=True)
            rows = []
            if custom_file.exists():
                rows = json.loads(custom_file.read_text(encoding="utf-8"))
            rows.append(data)
            custom_file.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
            QMessageBox.information(self, "Успіх", f"Виріб збережено у пресети: {data.get('name')}")
        except Exception as exc:
            QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти пресет: {exc}")

    def _show_presets(self):
        from ventilation_company.gui_pyside6.product_presets_dialog import ProductPresetsDialog

        dlg = ProductPresetsDialog(self)
        dlg.exec()

    def _recalculate_all_prices(self):
        import json

        from ventilation_company.calculations.cost_engine import CostEngine, clear_cache
        from ventilation_company.gui_pyside6.product_dialog import calc_surface_area
        from ventilation_company.services.pricing_settings import PricingSettings

        PricingSettings.get_instance().load()
        clear_cache()
        engine = CostEngine()

        items = list(getattr(self, "_all_data", []))
        if not items:
            QMessageBox.information(self, "Інформація", "Немає виробів для перерахунку")
            return

        answer = QMessageBox.question(
            self,
            "Перерахунок цін",
            f"Перерахувати ціни для {len(items)} виробів за поточними налаштуваннями?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        markup_map = {
            "Стандартна (30%)": 30,
            "Преміум (40%)": 40,
            "Економ (20%)": 20,
            "Спецзамовлення (50%)": 50,
        }

        updated = 0
        errors = 0
        for item in items:
            try:
                params = {}
                try:
                    params = json.loads(item.get("notes") or "{}")
                except Exception:
                    params = {}

                product_type = item.get("product_type") or ""
                width = float(item.get("width") or 0)
                height = float(item.get("height") or 0)
                length = float(item.get("length") or 0)
                thickness = float(item.get("thickness") or 0.7)
                quantity = int(float(item.get("quantity") or 1))
                material = item.get("material") or "Оцинкована сталь"

                bend_angle = float(params.get("bend_angle") or 90)
                radius = float(params.get("radius") or 0)
                branch_w = float(params.get("branch_width") or 0)
                branch_h = float(params.get("branch_height") or 0)
                branch_l = float(params.get("branch_length") or 0)

                surface = calc_surface_area(
                    product_type,
                    width,
                    height,
                    length,
                    bend_angle=bend_angle,
                    radius=radius,
                    branch_width=branch_w,
                    branch_height=branch_h,
                    branch_length=branch_l,
                )
                blank = surface * 1.15
                material_area = blank * 1.05

                with_flanges = bool(params.get("with_flanges"))
                flange_count = int(params.get("flange_count") or 0) if with_flanges else 0
                flange_profile = params.get("flange_profile") or "P30"
                flange_price = 150.0 if flange_profile == "P30" else 200.0
                markup = markup_map.get(params.get("category"), 30)

                breakdown = engine.calculate(
                    product_type=product_type,
                    material_name=material,
                    thickness_mm=thickness,
                    surface_area_m2=surface,
                    blank_area_m2=blank,
                    material_area_m2=material_area,
                    quantity=quantity,
                    flange_count=flange_count,
                    flange_price=flange_price,
                    custom_markup_percent=markup,
                )

                new_total = round(float(breakdown.final_price or 0), 2)
                old_total = float(item.get("total_price") or 0)
                old_discounted = float(item.get("discounted_price") or 0)
                if old_total > 0 and old_discounted > 0:
                    discount_ratio = old_discounted / old_total
                    new_discounted = round(new_total * discount_ratio, 2)
                else:
                    new_discounted = old_discounted

                data = {
                    "cost_price": round(float(breakdown.base_cost or 0), 2),
                    "unit_price": round(float(breakdown.price_no_vat or 0), 2),
                    "total_price": new_total,
                    "discounted_price": new_discounted,
                }
                ProductRepository.update(item["id"], data)
                updated += 1
            except Exception:
                errors += 1

        self._load_data()
        QMessageBox.information(self, "Готово", f"Оновлено: {updated}. Помилок: {errors}.")

    def _on_add(self):
        dlg = ProductDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            duplicate = self._find_duplicate_product(data)
            if duplicate:
                answer = QMessageBox.question(
                    self,
                    "Можливий дублікат",
                    f"Схожий виріб уже є: {duplicate.get('name')}. Додати ще один?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if answer != QMessageBox.Yes:
                    return
            try:
                ProductRepository.create(data)
                self._load_data()
                QMessageBox.information(self, "Успіх", "Виріб додано!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти: {e}")

    def _find_duplicate_product(self, data: dict):
        name = (data.get("name") or "").strip().lower()
        product_type = (data.get("product_type") or "").strip().lower()
        width = float(data.get("width") or 0)
        height = float(data.get("height") or 0)
        length = float(data.get("length") or 0)
        thickness = str(data.get("thickness") or "").strip()
        for item in getattr(self, "_all_data", []):
            if name and (item.get("name") or "").lower() == name:
                if product_type and (item.get("product_type") or "").lower() != product_type:
                    continue
                if abs(float(item.get("width") or 0) - width) > 0.001:
                    continue
                if abs(float(item.get("height") or 0) - height) > 0.001:
                    continue
                if abs(float(item.get("length") or 0) - length) > 0.001:
                    continue
                if thickness and str(item.get("thickness") or "").strip() != thickness:
                    continue
                return item
        return None

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
            self,
            "Видалення",
            f"Видалити виріб #{item_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
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
