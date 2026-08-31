"""Вкладка "CRM" (PySide6).

Таблиця клієнтів з пошуком, фільтрами, діалогом додавання/редагування.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QLineEdit, QComboBox, QMessageBox, QAbstractItemView,
    QDialog, QFormLayout, QDialogButtonBox, QTextEdit
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor

from ventilation_company.gui_pyside6.theme import Theme


class ClientDialog(QDialog):
    """Діалог додавання/редагування клієнта."""

    def __init__(self, client_data: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("👥 Редагувати клієнта" if client_data else "➕ Новий клієнт")
        self.setMinimumWidth(450)
        self._data = client_data or {}
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Назва компанії / ПІБ
        self.edit_name = QLineEdit(self._data.get("name", ""))
        self.edit_name.setPlaceholderText("ТОВ 'Будівельник' або Іванов І.І.")
        layout.addRow("Назва / ПІБ *", self.edit_name)

        # Контактна особа
        self.edit_contact = QLineEdit(self._data.get("contact_person", ""))
        self.edit_contact.setPlaceholderText("Петренко Петро Петрович")
        layout.addRow("Контактна особа", self.edit_contact)

        # Телефон
        self.edit_phone = QLineEdit(self._data.get("phone", ""))
        self.edit_phone.setPlaceholderText("+38 (067) 123-45-67")
        layout.addRow("Телефон", self.edit_phone)

        # Email
        self.edit_email = QLineEdit(self._data.get("email", ""))
        self.edit_email.setPlaceholderText("info@company.ua")
        layout.addRow("Email", self.edit_email)

        # Адреса
        self.edit_address = QLineEdit(self._data.get("address", ""))
        self.edit_address.setPlaceholderText("м. Київ, вул. Будівельна, 15")
        layout.addRow("Адреса", self.edit_address)

        # Статус
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Активний", "Потенційний", "Неактивний", "Чорний список"])
        self.combo_status.setCurrentText(self._data.get("status", "Активний"))
        layout.addRow("Статус", self.combo_status)

        # Примітки
        self.edit_notes = QTextEdit(self._data.get("notes", ""))
        self.edit_notes.setPlaceholderText("Додаткова інформація про клієнта...")
        self.edit_notes.setMaximumHeight(80)
        layout.addRow("Примітки", self.edit_notes)

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_save(self):
        if not self.edit_name.text().strip():
            QMessageBox.warning(self, "Помилка", "Введіть назву клієнта")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.edit_name.text().strip(),
            "contact_person": self.edit_contact.text().strip(),
            "phone": self.edit_phone.text().strip(),
            "email": self.edit_email.text().strip(),
            "address": self.edit_address.text().strip(),
            "status": self.combo_status.currentText(),
            "notes": self.edit_notes.toPlainText().strip(),
        }


class CRMTab(QWidget):
    """Вкладка CRM — управління клієнтами."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_clients: list[dict] = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ── Заголовок ──
        header = QHBoxLayout()
        lbl_title = QLabel("👥 CRM — Клієнти")
        lbl_title.setObjectName("title")
        header.addWidget(lbl_title)
        header.addStretch()

        btn_new = QPushButton("➕ Додати клієнта")
        btn_new.setObjectName("primary")
        btn_new.setMinimumHeight(32)
        btn_new.clicked.connect(self._on_add)
        header.addWidget(btn_new)

        layout.addLayout(header)

        # ── Фільтри ──
        filters = QHBoxLayout()
        filters.setSpacing(12)

        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("🔍 Пошук за назвою, телефоном, email...")
        self.edit_search.setFixedWidth(280)
        self.edit_search.setMinimumHeight(32)
        self.edit_search.textChanged.connect(self._apply_filters)
        filters.addWidget(self.edit_search)

        filters.addSpacing(16)

        lbl_status = QLabel("Статус:")
        lbl_status.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        filters.addWidget(lbl_status)

        self.filter_status = QComboBox()
        self.filter_status.addItem("Всі")
        self.filter_status.addItems(["Активний", "Потенційний", "Неактивний", "Чорний список"])
        self.filter_status.currentTextChanged.connect(self._apply_filters)
        filters.addWidget(self.filter_status)

        filters.addStretch()

        btn_reset = QPushButton("♻️ Скинути")
        btn_reset.setMinimumHeight(28)
        btn_reset.clicked.connect(self._reset_filters)
        filters.addWidget(btn_reset)

        layout.addLayout(filters)

        # ── Таблиця ──
        self.table = QTableView()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(400)
        self.table.doubleClicked.connect(self._on_edit)
        layout.addWidget(self.table)

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "ID", "Назва / ПІБ", "Контакт", "Телефон", "Email", "Статус", "Примітка"
        ])
        self.table.setModel(self.model)

        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 220)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 180)
        self.table.setColumnWidth(5, 100)
        self.table.setColumnWidth(6, 200)

        # ── Кнопки дій ──
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

        layout.addLayout(actions)

        # ── Підсумок ──
        self.lbl_summary = QLabel("Всього: 0 клієнтів")
        self.lbl_summary.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 12px; padding: 4px;")
        layout.addWidget(self.lbl_summary)

    def _load_data(self):
        """Завантажити демо-дані клієнтів."""
        self._all_clients = [
            {"id": 1, "name": "ТОВ 'Будівельник'", "contact_person": "Іванов І.І.", "phone": "+38 (067) 111-22-33", "email": "info@budivelnyk.ua", "address": "м. Київ, вул. Будівельна, 15", "status": "Активний", "notes": "Постійний клієнт, 5 проєктів"},
            {"id": 2, "name": "ТОВ 'Смак' (ресторан)", "contact_person": "Петренко П.П.", "phone": "+38 (050) 444-55-66", "email": "smak@restaurant.ua", "address": "м. Львів, пл. Ринок, 1", "status": "Активний", "notes": "Витяжна система кухні"},
            {"id": 3, "name": "Складський комплекс №5", "contact_person": "Сидоренко С.С.", "phone": "+38 (063) 777-88-99", "email": "sklad5@logistics.ua", "address": "м. Одеса, вул. Портова, 42", "status": "Потенційний", "notes": "Приточна установка, чекаємо ТЗ"},
            {"id": 4, "name": "ЖК 'Сонячний'", "contact_person": "Коваленко К.К.", "phone": "+38 (068) 000-11-22", "email": "info@sonyachny.ua", "address": "м. Дніпро, пр. Гагаріна, 100", "status": "Активний", "notes": "Вентиляція підвалів, 3 під'їзди"},
            {"id": 5, "name": "ТОВ 'Холод'", "contact_person": "Морозенко М.М.", "phone": "+38 (095) 333-44-55", "email": "cold@refrigeration.ua", "address": "м. Харків, вул. Холодна, 7", "status": "Неактивний", "notes": "Не відповідає на дзвінки з 2024"},
            {"id": 6, "name": "АТБ-Маркет (філія №12)", "contact_person": "Гриценко Г.Г.", "phone": "+38 (096) 666-77-88", "email": "atb12@market.ua", "address": "м. Запоріжжя, вул. Центральна, 25", "status": "Активний", "notes": "Щомісячне обслуговування"},
            {"id": 7, "name": "Приватна особа: Ковальчук В.В.", "contact_person": "Ковальчук В.В.", "phone": "+38 (097) 999-00-11", "email": "", "address": "м. Київ, вул. Лісова, 5, кв. 12", "status": "Потенційний", "notes": "Квартира, витяжка в санвузол"},
            {"id": 8, "name": "ТОВ 'Шахтар'", "contact_person": "", "phone": "+38 (099) 222-33-44", "email": "shakhtar@mine.ua", "address": "м. Донецьк, вул. Шахтарська, 1", "status": "Чорний список", "notes": "Не платить, 3 проєкти в борг"},
        ]
        self._apply_filters()

    def _apply_filters(self):
        search = self.edit_search.text().lower()
        f_status = self.filter_status.currentText()

        filtered = []
        for c in self._all_clients:
            if search and search not in c.get("name", "").lower() and search not in c.get("phone", "").lower() and search not in c.get("email", "").lower():
                continue
            if f_status != "Всі" and f_status != c.get("status", ""):
                continue
            filtered.append(c)

        self._fill_table(filtered)
        self._update_summary(filtered)

    def _fill_table(self, data: list[dict]):
        self.model.removeRows(0, self.model.rowCount())
        for c in data:
            # Колір статусу
            status = c.get("status", "")
            status_color = {
                "Активний": Theme.SUCCESS,
                "Потенційний": Theme.ACCENT,
                "Неактивний": Theme.TEXT_MUTED,
                "Чорний список": Theme.DANGER,
            }.get(status, Theme.TEXT)

            row = [
                QStandardItem(str(c.get("id", "—"))),
                QStandardItem(c.get("name", "—")),
                QStandardItem(c.get("contact_person", "—")),
                QStandardItem(c.get("phone", "—")),
                QStandardItem(c.get("email", "—")),
                QStandardItem(status),
                QStandardItem(c.get("notes", "—")),
            ]
            # Зафарбувати статус
            row[5].setForeground(QColor(status_color))
            if status == "Чорний список":
                row[5].setBackground(QColor(Theme.DANGER))
                row[5].setForeground(QColor(Theme.BG_DARK))

            for cell in row:
                cell.setEditable(False)
            self.model.appendRow(row)

    def _update_summary(self, data: list[dict]):
        active = sum(1 for c in data if c.get("status") == "Активний")
        potential = sum(1 for c in data if c.get("status") == "Потенційний")
        self.lbl_summary.setText(f"Всього: {len(data)} клієнтів | Активних: {active} | Потенційних: {potential}")

    def _reset_filters(self):
        self.edit_search.clear()
        self.filter_status.setCurrentIndex(0)

    def _get_selected_id(self) -> int | None:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        try:
            return int(self.model.item(idx.row(), 0).text())
        except ValueError:
            return None

    def _get_client_by_id(self, cid: int) -> dict | None:
        for c in self._all_clients:
            if c.get("id") == cid:
                return c
        return None

    def _on_add(self):
        dlg = ClientDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            data["id"] = max((c.get("id", 0) for c in self._all_clients), default=0) + 1
            self._all_clients.append(data)
            self._apply_filters()

    def _on_edit(self):
        cid = self._get_selected_id()
        if not cid:
            QMessageBox.warning(self, "Увага", "Виберіть клієнта для редагування")
            return
        client = self._get_client_by_id(cid)
        if not client:
            return
        dlg = ClientDialog(client, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_data = dlg.get_data()
            new_data["id"] = cid
            for i, c in enumerate(self._all_clients):
                if c.get("id") == cid:
                    self._all_clients[i] = new_data
                    break
            self._apply_filters()

    def _on_delete(self):
        cid = self._get_selected_id()
        if not cid:
            QMessageBox.warning(self, "Увага", "Виберіть клієнта для видалення")
            return
        client = self._get_client_by_id(cid)
        name = client.get("name", "") if client else ""
        reply = QMessageBox.question(
            self, "Видалення",
            f'Видалити клієнта "{name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._all_clients = [c for c in self._all_clients if c.get("id") != cid]
            self._apply_filters()

    def refresh(self):
        self._load_data()
