"""Users admin tab extracted from ProgramSettingsTab."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.auth.service import auth
from ventilation_company.database.repositories.app_settings_repository import get_role_label
from ventilation_company.gui_pyside6.theme import Theme


class UsersAdminTab(QWidget):
    """Users CRUD tab for admin/director."""

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.is_director = current_user is not None and current_user.role in ("admin", "director")
        self._build_ui()

    def _build_ui(self):
        vlay = QVBoxLayout(self)

        if not self.is_director:
            lbl = QLabel("🚫 Доступ тільки для адміністратора")
            lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
            lbl.setStyleSheet(f"color: {Theme.DANGER};")
            vlay.addWidget(lbl, alignment=Qt.AlignCenter)
            return

        btn_row = QHBoxLayout()
        for text, slot in [
            ("📜 Audit Log", self._show_audit_log),
            ("➕ Додати", self._add_user_dialog),
            ("✏️ Редагувати", self._edit_user_dialog),
            ("🗑️ Видалити", self._delete_user),
            ("🔄 Оновити", self._refresh_users),
        ]:
            btn = QPushButton(text)
            btn.setMinimumHeight(32)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)
        btn_row.addStretch()
        vlay.addLayout(btn_row)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(6)
        self.users_table.setHorizontalHeaderLabels(
            ["ID", "Логін", "ПІБ", "Роль", "Активний", "Останній вхід"]
        )
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setEditTriggers(QTableWidget.NoEditTriggers)
        vlay.addWidget(self.users_table)

        self._refresh_users()

    def _show_audit_log(self):
        from ventilation_company.gui_pyside6.audit_log_dialog import AuditLogDialog

        dlg = AuditLogDialog(self.current_user, self)
        dlg.exec()

    def _refresh_users(self):
        self.users_table.setRowCount(0)
        for u in auth.list_users():
            row = self.users_table.rowCount()
            self.users_table.insertRow(row)
            self.users_table.setItem(row, 0, QTableWidgetItem(str(u.id)))
            self.users_table.setItem(row, 1, QTableWidgetItem(u.username))
            self.users_table.setItem(row, 2, QTableWidgetItem(u.full_name or "—"))
            self.users_table.setItem(row, 3, QTableWidgetItem(get_role_label(u.role)))
            self.users_table.setItem(row, 4, QTableWidgetItem("Так" if u.is_active else "Ні"))
            self.users_table.setItem(row, 5, QTableWidgetItem(u.last_login or "—"))

    def _selected_user(self):
        row = self.users_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Увага", "Оберіть користувача")
            return None
        username = self.users_table.item(row, 1).text()
        return auth.get_user_by_username(username)

    def _add_user_dialog(self):
        self._user_dialog(None)

    def _edit_user_dialog(self):
        user = self._selected_user()
        if user:
            self._user_dialog(user)

    def _user_dialog(self, user):
        is_edit = user is not None
        dlg = QDialog(self)
        dlg.setWindowTitle("Редагування користувача" if is_edit else "Новий користувач")
        dlg.setMinimumSize(400, 380)

        lay = QFormLayout(dlg)

        login_edit = QLineEdit(user.username if is_edit else "")
        if is_edit:
            login_edit.setReadOnly(True)
        lay.addRow("👤 Логін *", login_edit)

        name_edit = QLineEdit(user.full_name if is_edit else "")
        lay.addRow("📝 Повне ім'я *", name_edit)

        pass_edit = QLineEdit()
        pass_edit.setEchoMode(QLineEdit.Password)
        lay.addRow("🔒 Пароль" + ("" if is_edit else " *"), pass_edit)
        if is_edit:
            lay.addRow(QLabel("(залиште порожнім, щоб не змінювати)"))

        pass2_edit = QLineEdit()
        pass2_edit.setEchoMode(QLineEdit.Password)
        lay.addRow("🔒 Підтвердіть пароль", pass2_edit)

        role_combo = QComboBox()
        role_combo.addItems(
            ["Адміністратор", "Менеджер", "Інженер", "Майстер", "Бухгалтер", "Перегляд"]
        )
        if is_edit:
            role_combo.setCurrentText(get_role_label(user.role))
        lay.addRow("🛡️ Посада *", role_combo)

        status_lbl = QLabel("")
        status_lbl.setStyleSheet(f"color: {Theme.DANGER};")
        lay.addRow(status_lbl)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        lay.addRow(btns)

        def save():
            role_map = {
                "Адміністратор": "admin",
                "Менеджер": "manager",
                "Інженер": "engineer",
                "Майстер": "master",
                "Бухгалтер": "accountant",
                "Перегляд": "viewer",
            }
            new_role = role_map.get(role_combo.currentText(), "viewer")

            if is_edit:
                kwargs = {"full_name": name_edit.text(), "role": new_role}
                if pass_edit.text():
                    if pass_edit.text() != pass2_edit.text():
                        status_lbl.setText("❌ Паролі не співпадають")
                        return
                    kwargs["password"] = pass_edit.text()
                auth.update_user(user.id, **kwargs)
                self._refresh_users()
                dlg.accept()
                QMessageBox.information(self, "Успіх", f"Користувача {user.username} оновлено")
            else:
                login = login_edit.text().strip()
                name = name_edit.text().strip()
                password = pass_edit.text()
                if not all([login, name, password]):
                    status_lbl.setText("⚠️ Заповніть обов'язкові поля")
                    return
                if password != pass2_edit.text():
                    status_lbl.setText("❌ Паролі не співпадають")
                    return
                if len(password) < 4:
                    status_lbl.setText("❌ Пароль мінімум 4 символи")
                    return
                try:
                    auth.create_user(login, password, name, new_role)
                    self._refresh_users()
                    dlg.accept()
                    QMessageBox.information(self, "Успіх", f"Користувача {login} створено")
                except ValueError as e:
                    status_lbl.setText(f"❌ {e}")

        btns.accepted.connect(save)
        btns.rejected.connect(dlg.reject)
        dlg.exec()

    def _delete_user(self):
        user = self._selected_user()
        if not user:
            return
        if self.current_user and user.username == self.current_user.username:
            QMessageBox.critical(self, "Помилка", "Не можна видалити самого себе")
            return
        reply = QMessageBox.question(
            self, "Підтвердження", f'Видалити користувача "{user.username}"?'
        )
        if reply == QMessageBox.Yes:
            auth.delete_user(user.id)
            self._refresh_users()
            QMessageBox.information(self, "Успіх", f"Користувача {user.username} видалено")
