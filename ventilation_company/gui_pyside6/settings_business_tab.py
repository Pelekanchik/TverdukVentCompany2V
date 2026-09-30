"""Вкладка редагування бізнес-налаштувань (BusinessSettings).

Редагує:
  • ставку ПДВ
  • ціни на комплектуючі (вентилятори, фільтри, клапани тощо)
  • типові роботи (монтаж, доставка, виїзд на замір тощо)
  • додаткові матеріали (ізоляція)
  • посади та ставки зарплат

Дані зберігаються у data/business_settings.json (див. services/business_settings.py).
Редагування доступне тільки для admin/director; іншим — режим перегляду.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.gui_pyside6.table_utils import setup_table
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.services.audit_service import log_action
from ventilation_company.services.business_settings import BusinessSettings

COLUMNS_KEY_VALUE_UNIT = ["Назва (ключ)", "Ціна, грн", "Одиниця"]
COLUMNS_POSITIONS = ["Посада (ключ)", "Ставка, грн/міс", "Премія, %"]
COLUMNS_FLANGES = ["Профіль", "Ціна, грн/шт"]

# Поля реквізитів фірми: (ключ у JSON, підпис, placeholder).
COMPANY_FIELDS = [
    ("name", "Назва фірми:", "ТОВ «ВентКомпані»"),
    ("edrpou", "ЄДРПОУ:", "12345678"),
    ("address", "Адреса:", "м. Київ, вул. Промислова, 15"),
    ("phone", "Телефон:", "+38 (044) 123-45-67"),
    ("email", "E-mail:", "info@ventcompany.ua"),
    ("website", "Сайт:", "www.ventcompany.ua"),
    (
        "signatory",
        "Підписант (посада, П.І.Б.):",
        "Директор Іваненко І.І.",
    ),
    ("city", "Місто (для договору):", "м. Київ"),
    ("bank_name", "Банк:", "АТ «Ощадбанк»"),
    ("iban", "IBAN (р/р):", "UA00 0000 0000 0000 0000 0000 00"),
    ("mfo", "МФО:", "300465"),
]


class BusinessSettingsTab(QWidget):
    """Редактор бізнес-налаштувань: ПДВ, комплектуючі, ізоляція, посади."""

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.can_edit = current_user is not None and current_user.role in ("admin", "director")
        self._build_ui()
        self.load()

    # ── UI ──

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        root.addWidget(scroll)

        container = QWidget()
        vlay = QVBoxLayout(container)
        vlay.setAlignment(Qt.AlignmentFlag.AlignTop)
        vlay.setSpacing(12)

        header = QLabel("💼 Бізнес-налаштування: ПДВ, ціни, ставки")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        vlay.addWidget(header)

        if not self.can_edit:
            note = QLabel("🔒 Режим перегляду: редагування доступне тільки admin/director.")
            note.setStyleSheet(f"color: {Theme.WARNING};")
            vlay.addWidget(note)

        # ── ПДВ ──
        grp_vat = QGroupBox("Податки")
        h_vat = QHBoxLayout(grp_vat)
        lbl_vat = QLabel("Ставка ПДВ, %:")
        lbl_vat.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        h_vat.addWidget(lbl_vat)
        self.spin_vat = QDoubleSpinBox()
        self.spin_vat.setRange(0, 100)
        self.spin_vat.setDecimals(1)
        self.spin_vat.setSingleStep(1.0)
        self.spin_vat.setMinimumWidth(120)
        h_vat.addWidget(self.spin_vat)
        h_vat.addStretch()
        vlay.addWidget(grp_vat)

        # ── Реквізити фірми ──
        grp_company = QGroupBox("🏢 Реквізити фірми (підставляються у КП, договір, акти)")
        form_company = QFormLayout(grp_company)
        self.company_edits: dict[str, QLineEdit] = {}
        for key, label, placeholder in COMPANY_FIELDS:
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            self.company_edits[key] = edit
            form_company.addRow(label, edit)
        vlay.addWidget(grp_company)

        # ── Комплектуючі ──
        self.tbl_components = self._make_table(COLUMNS_KEY_VALUE_UNIT)
        vlay.addWidget(
            self._table_group(
                "Комплектуючі (вентилятори, фільтри, клапани...)", self.tbl_components
            )
        )

        # ── Типові роботи ──
        self.tbl_works = self._make_table(COLUMNS_KEY_VALUE_UNIT)
        vlay.addWidget(
            self._table_group("Типові роботи (монтаж, доставка, виїзд на замір...)", self.tbl_works)
        )

        # ── Додаткові матеріали ──
        self.tbl_materials = self._make_table(COLUMNS_KEY_VALUE_UNIT)
        vlay.addWidget(self._table_group("Додаткові матеріали (ізоляція)", self.tbl_materials))

        # ── Посади ──
        self.tbl_positions = self._make_table(COLUMNS_POSITIONS)
        vlay.addWidget(self._table_group("Посади та ставки зарплат", self.tbl_positions))

        # ── Фланці ──
        self.tbl_flanges = self._make_table(COLUMNS_FLANGES)
        vlay.addWidget(self._table_group("Ціни фланців за профілем", self.tbl_flanges))

        scroll.setWidget(container)

        if not self.can_edit:
            for w in (
                self.spin_vat,
                self.tbl_components,
                self.tbl_works,
                self.tbl_materials,
                self.tbl_positions,
                self.tbl_flanges,
                *self.company_edits.values(),
            ):
                w.setEnabled(False)

    def _make_table(self, headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        setup_table(table, select_rows=True, stretch_last=False)
        table.setMinimumHeight(160)
        return table

    def _table_group(self, title: str, table: QTableWidget) -> QGroupBox:
        grp = QGroupBox(title)
        v = QVBoxLayout(grp)
        v.addWidget(table)

        if self.can_edit:
            row = QHBoxLayout()
            btn_add = QPushButton("➕ Додати рядок")
            btn_add.setMinimumHeight(30)
            btn_add.clicked.connect(lambda: table.insertRow(table.rowCount()))
            btn_del = QPushButton("➖ Видалити обраний")
            btn_del.setMinimumHeight(30)
            btn_del.clicked.connect(lambda: self._remove_selected_row(table))
            row.addWidget(btn_add)
            row.addWidget(btn_del)
            row.addStretch()
            v.addLayout(row)
        return grp

    def _remove_selected_row(self, table: QTableWidget):
        row = table.currentRow()
        if row >= 0:
            table.removeRow(row)

    # ── Завантаження / збереження ──

    def load(self):
        s = BusinessSettings.get_instance()
        self.spin_vat.setValue(s.get_vat_rate())
        company = s.get_company()
        for key, edit in self.company_edits.items():
            edit.setText(str(company.get(key, "")))
        self._fill_table(self.tbl_components, s.components, ("ціна", "одиниця"))
        self._fill_table(self.tbl_works, s.work_rates, ("ціна", "одиниця"))
        self._fill_table(self.tbl_materials, s.extra_materials, ("ціна_за_м2", "одиниця"))
        self._fill_table(self.tbl_positions, s.positions, ("ставка", "премія_%"))
        self._fill_table(self.tbl_flanges, s.flange_prices, ("ціна",))

    def _fill_table(self, table: QTableWidget, data: dict, fields: tuple[str, ...]):
        table.setRowCount(0)
        for key, values in data.items():
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(str(key)))
            for col, field in enumerate(fields, start=1):
                table.setItem(row, col, QTableWidgetItem(str(values.get(field, ""))))

    def save(self) -> bool:
        """Зберегти таблиці у BusinessSettings. Повертає True при успіху."""
        if not self.can_edit:
            return False

        try:
            s = BusinessSettings.get_instance()
            s.vat_rate = float(self.spin_vat.value())
            s.components = self._read_table(self.tbl_components, ("ціна", "одиниця"))
            s.work_rates = self._read_table(self.tbl_works, ("ціна", "одиниця"))
            s.extra_materials = self._read_table(self.tbl_materials, ("ціна_за_м2", "одиниця"))
            s.positions = self._read_table(
                self.tbl_positions, ("ставка", "премія_%"), numeric=("ставка", "премія_%")
            )
            s.flange_prices = self._read_table(self.tbl_flanges, ("ціна",), numeric=("ціна",))
            s.company = {key: edit.text().strip() for key, edit in self.company_edits.items()}
            s.save()
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти бізнес-налаштування:\n{e}")
            return False

        log_action(
            "settings.business_update",
            entity_type="settings",
            details={
                "vat_rate": s.vat_rate,
                "components": len(s.components),
                "work_rates": len(s.work_rates),
                "extra_materials": len(s.extra_materials),
                "positions": len(s.positions),
                "flange_prices": len(s.flange_prices),
                "company_fields": len(s.company),
            },
            actor=self.current_user,
        )
        return True

    def _read_table(
        self, table: QTableWidget, fields: tuple[str, ...], numeric: tuple[str, ...] = ("ціна",)
    ) -> dict:
        """Перетворити таблицю у dict. Порожні ключі пропускаються."""
        result = {}
        for row in range(table.rowCount()):
            key_item = table.item(row, 0)
            if key_item is None:
                continue
            key = key_item.text().strip()
            if not key:
                continue

            def cell(col: int, _row: int = row) -> str:
                item = table.item(_row, col)
                return item.text().strip() if item else ""

            record = {}
            for col, field in enumerate(fields, start=1):
                raw = cell(col)
                if field in numeric:
                    try:
                        value: float | int | str = float(raw) if "." in raw else int(raw)
                    except ValueError:
                        value = 0
                else:
                    value = raw
                record[field] = value
            result[key] = record
        return result
