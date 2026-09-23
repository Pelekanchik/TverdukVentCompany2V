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

        actions = QHBoxLayout()
        btn_export = QPushButton("💾 Експорт CSV")
        btn_export.clicked.connect(self._export_csv)
        actions.addWidget(btn_export)
        btn_import = QPushButton("📥 Імпорт CSV")
        btn_import.clicked.connect(self._import_csv)
        actions.addWidget(btn_import)
        btn_template = QPushButton("📄 Шаблон CSV")
        btn_template.clicked.connect(self._download_csv_template)
        actions.addWidget(btn_template)
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
