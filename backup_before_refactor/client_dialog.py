"""Client dialog extracted from CRMTab."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTextEdit,
)


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

        self.edit_name = QLineEdit(self._data.get("name", ""))
        self.edit_name.setPlaceholderText("ТОВ 'Будівельник' або Іванов І.І.")
        layout.addRow("Назва / ПІБ *", self.edit_name)

        self.edit_contact = QLineEdit(self._data.get("contact_person", ""))
        self.edit_contact.setPlaceholderText("Петренко Петро Петрович")
        layout.addRow("Контактна особа", self.edit_contact)

        self.edit_phone = QLineEdit(self._data.get("phone", ""))
        self.edit_phone.setPlaceholderText("+38 (067) 123-45-67")
        layout.addRow("Телефон", self.edit_phone)

        self.edit_email = QLineEdit(self._data.get("email", ""))
        self.edit_email.setPlaceholderText("info@company.ua")
        layout.addRow("Email", self.edit_email)

        self.edit_address = QLineEdit(self._data.get("address", ""))
        self.edit_address.setPlaceholderText("м. Київ, вул. Будівельна, 15")
        layout.addRow("Адреса", self.edit_address)

        self.combo_status = QComboBox()
        self.combo_status.addItems(["Активний", "Потенційний", "Неактивний", "Чорний список"])
        self.combo_status.setCurrentText(self._data.get("status", "Активний"))
        layout.addRow("Статус", self.combo_status)

        self.edit_notes = QTextEdit(self._data.get("notes", ""))
        self.edit_notes.setPlaceholderText("Додаткова інформація про клієнта...")
        self.edit_notes.setMaximumHeight(80)
        layout.addRow("Примітки", self.edit_notes)

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
