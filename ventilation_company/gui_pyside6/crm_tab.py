"""Вкладка "CRM" (PySide6).

Таблиця клієнтів з пошуком, фільтрами, діалогом додавання/редагування.
"""

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.database.repositories.client_repo import ClientRepository
from ventilation_company.gui_pyside6.client_card_dialog import ClientCardDialog
from ventilation_company.gui_pyside6.client_dialog import ClientDialog
from ventilation_company.gui_pyside6.client_history_dialog import ClientHistoryDialog
from ventilation_company.gui_pyside6.crm_dashboard_dialog import CRMDashboardDialog
from ventilation_company.gui_pyside6.theme import Theme


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
        btn_card = QPushButton("🪪 Картка")
        btn_card.clicked.connect(self._show_client_card)
        layout.addWidget(btn_card)

        btn_dashboard = QPushButton("📊 Dashboard")
        btn_dashboard.clicked.connect(self._show_crm_dashboard)
        layout.addWidget(btn_dashboard)

        btn_history = QPushButton("📜 Історія")
        btn_history.clicked.connect(self._show_client_history)
        layout.addWidget(btn_history)

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
        self.model.setHorizontalHeaderLabels(
            ["ID", "Назва / ПІБ", "Контакт", "Телефон", "Email", "Статус", "Примітка"]
        )
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

    def _reset_filters(self):
        self.edit_search.clear()
        self.combo_status.setCurrentText("Всі")
        self._apply_filters()

    def _fill_table(self, clients):
        self._visible_clients = clients
        headers = ["ID", "Назва", "Контакт", "Телефон", "Email", "Статус", "Адреса"]
        if hasattr(self, "model") and self.model is not None:
            self.model.clear()
            self.model.setHorizontalHeaderLabels(headers)
            for c in clients:
                self.model.appendRow(
                    [
                        QStandardItem(str(c["id"])),
                        QStandardItem(c["name"]),
                        QStandardItem(c.get("contact_person") or "—"),
                        QStandardItem(c.get("phone") or "—"),
                        QStandardItem(c.get("email") or "—"),
                        QStandardItem(c.get("status") or "—"),
                        QStandardItem(c.get("address") or "—"),
                    ]
                )
            return

        self.table.setRowCount(0)
        for c in clients:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(c["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(c["name"]))
            self.table.setItem(row, 2, QTableWidgetItem(c.get("contact_person") or "—"))
            self.table.setItem(row, 3, QTableWidgetItem(c.get("phone") or "—"))
            self.table.setItem(row, 4, QTableWidgetItem(c.get("email") or "—"))
            self.table.setItem(row, 5, QTableWidgetItem(c.get("status") or "—"))
            self.table.setItem(row, 6, QTableWidgetItem(c.get("address") or "—"))

    def _apply_filters(self):
        search = self.edit_search.text().lower()
        status = self.combo_status.currentText()
        filtered = []
        for c in self._all_clients:
            if status != "Всі" and c.get("status") != status:
                continue
            if search:
                haystacks = [
                    c.get("name", ""),
                    c.get("contact_person") or "",
                    c.get("phone") or "",
                    c.get("email") or "",
                    c.get("address") or "",
                ]
                if not any(search in h.lower() for h in haystacks):
                    continue
            filtered.append(c)
        self._fill_table(filtered)

    def _load_data(self):
        try:
            self._all_clients = ClientRepository.list_all()
        except Exception:
            self._all_clients = []
        self._fill_table(self._all_clients)

    def _get_selected_id(self):
        row = self.table.currentIndex().row()
        clients = getattr(self, "_visible_clients", self._all_clients)
        if row < 0 or row >= len(clients):
            return None
        return clients[row]["id"]

    def _client_name(self, client_id):
        for client in self._all_clients:
            if client["id"] == client_id:
                return client["name"]
        return str(client_id)

    def _show_client_card(self):
        cid = self._get_selected_id()
        if not cid:
            QMessageBox.warning(self, "Увага", "Оберіть клієнта")
            return
        client = next((c for c in self._all_clients if c["id"] == cid), None)
        if not client:
            QMessageBox.warning(self, "Увага", "Клієнта не знайдено")
            return
        dlg = ClientCardDialog(client, self)
        dlg.exec()

    def _show_crm_dashboard(self):
        dlg = CRMDashboardDialog(self)
        dlg.exec()

    def _show_client_history(self):
        cid = self._get_selected_id()
        if not cid:
            QMessageBox.warning(self, "Увага", "Оберіть клієнта")
            return
        name = self._client_name(cid)
        dlg = ClientHistoryDialog(cid, name, self)
        dlg.exec()

    def _on_add(self):
        dlg = ClientDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ClientRepository.create(dlg.get_data())
            self._load_data()
            QMessageBox.information(self, "Успіх", "Клієнта додано")

    def _on_edit(self):
        cid = self._get_selected_id()
        if not cid:
            return
        client = next((c for c in self._all_clients if c["id"] == cid), None)
        if not client:
            return
        dlg = ClientDialog(client_data=client, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ClientRepository.update(cid, dlg.get_data())
            self._load_data()
            QMessageBox.information(self, "Успіх", "Дані клієнта оновлено")

    def _on_delete(self):
        cid = self._get_selected_id()
        if not cid:
            return
        name = self._client_name(cid)
        reply = QMessageBox.question(self, "Підтвердження", f'Видалити клієнта "{name}"?')
        if reply == QMessageBox.Yes:
            ClientRepository.delete(cid)
            self._load_data()
            QMessageBox.information(self, "Успіх", "Клієнта видалено")

    def refresh(self):
        self._load_data()
