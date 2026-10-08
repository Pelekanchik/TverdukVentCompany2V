"""E2E-тести діалогів логіна та проєкту через pytest-qt (qtbot).

Реальні дії користувача: ввід логіна/пароля, кліки по кнопках.
AuthService підмінено стабами — перевіряється сама інтеракція GUI.
"""

from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLineEdit,
)


def _type(qtbot, widget: QLineEdit, text: str) -> None:
    """Див. test_product_dialog_e2e._type — QTest.keyClick падає з кирилицею,
    а буфер обміну на Windows спрацьовує лише раз (Qt bug) → insert()."""
    widget.setFocus()
    qtbot.waitUntil(widget.hasFocus, timeout=2000)
    if text.isascii():
        qtbot.keyClicks(widget, text)
    else:
        widget.insert(text)


@pytest.fixture
def login(qtbot):
    from ventilation_company.gui_pyside6.login_dialog import LoginDialog

    dlg = LoginDialog()
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitUntil(dlg.isVisible, timeout=2000)
    yield dlg
    dlg.close()


class TestLoginDialog:
    def test_empty_fields_show_hint_and_stay_open(self, qtbot, login):
        qtbot.mouseClick(login.btn_login, Qt.MouseButton.LeftButton)
        assert "Введіть логін та пароль" in login.lbl_status.text()
        assert login.result() != QDialog.DialogCode.Accepted

    def test_wrong_credentials_show_error_and_clear_password(self, qtbot, login, monkeypatch):
        monkeypatch.setattr(
            "ventilation_company.gui_pyside6.login_dialog.AuthService.authenticate",
            staticmethod(lambda u, p: None),
        )
        _type(qtbot, login.edit_user, "admin")
        _type(qtbot, login.edit_pass, "wrongpass")
        qtbot.mouseClick(login.btn_login, Qt.MouseButton.LeftButton)
        assert "Невірний логін або пароль" in login.lbl_status.text()
        assert login.edit_pass.text() == ""
        assert login.result() != QDialog.DialogCode.Accepted

    def test_successful_login_accepts(self, qtbot, login, monkeypatch):
        fake_user = SimpleNamespace(username="admin", role="admin")
        monkeypatch.setattr(
            "ventilation_company.gui_pyside6.login_dialog.AuthService.authenticate",
            staticmethod(lambda u, p: fake_user if (u, p) == ("admin", "secret") else None),
        )
        _type(qtbot, login.edit_user, "admin")
        _type(qtbot, login.edit_pass, "secret")
        qtbot.mouseClick(login.btn_login, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: login.result() == QDialog.DialogCode.Accepted, timeout=2000)
        assert login.authenticated_user is fake_user

    def test_enter_in_password_triggers_login(self, qtbot, login, monkeypatch):
        """returnPressed у полі пароля теж логінить."""
        fake_user = SimpleNamespace(username="oper", role="operator")
        monkeypatch.setattr(
            "ventilation_company.gui_pyside6.login_dialog.AuthService.authenticate",
            staticmethod(lambda u, p: fake_user),
        )
        _type(qtbot, login.edit_user, "oper")
        _type(qtbot, login.edit_pass, "any")
        qtbot.keyClick(login.edit_pass, Qt.Key.Key_Return)
        qtbot.waitUntil(lambda: login.result() == QDialog.DialogCode.Accepted, timeout=2000)


@pytest.fixture
def project_dlg(qtbot):
    from ventilation_company.gui_pyside6.projects_tab import ProjectEditDialog

    dlg = ProjectEditDialog()
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitUntil(dlg.isVisible, timeout=2000)
    yield dlg
    dlg.close()


def _save(dlg) -> QDialogButtonBox:
    box = dlg.findChild(QDialogButtonBox)
    assert box is not None
    return box


class TestProjectEditDialog:
    def test_create_project_end_to_end(self, qtbot, project_dlg):
        _type(qtbot, project_dlg.edit_name, "Вентиляція кафе «Смак»")
        _type(qtbot, project_dlg.edit_number, "PRJ-TEST-1")
        _type(qtbot, project_dlg.edit_contract, "ДГ-20260101-007")
        box = _save(project_dlg)
        qtbot.mouseClick(
            box.button(QDialogButtonBox.StandardButton.Save), Qt.MouseButton.LeftButton
        )
        qtbot.waitUntil(lambda: project_dlg.result() == QDialog.DialogCode.Accepted, timeout=2000)
        data = project_dlg.get_data()
        assert data["name"] == "Вентиляція кафе «Смак»"
        assert data["project_number"] == "PRJ-TEST-1"
        assert data["contract_number"] == "ДГ-20260101-007"
        assert data["status"] == "Новий"

    def test_cancel_rejects(self, qtbot, project_dlg):
        box = _save(project_dlg)
        qtbot.mouseClick(
            box.button(QDialogButtonBox.StandardButton.Cancel), Qt.MouseButton.LeftButton
        )
        qtbot.waitUntil(lambda: project_dlg.result() == QDialog.DialogCode.Rejected, timeout=2000)

    def test_discount_recalculates_profit(self, qtbot, project_dlg):
        """Зміна знижки → прибуток перераховується автоматично (сигнали живі)."""
        assert "0.00" in project_dlg.lbl_profit.text()
        project_dlg.spin_discounted.setValue(5000)
        assert "5,000.00 ₴  ✅" in project_dlg.lbl_profit.text()
        data = project_dlg.get_data()
        assert data["profit"] == pytest.approx(5000.0)

    def test_edit_existing_project_prefills(self, qtbot):
        from ventilation_company.gui_pyside6.projects_tab import ProjectEditDialog

        dlg = ProjectEditDialog(
            {
                "name": "Склад ТОВ «Логіст»",
                "project_number": "PRJ-77",
                "contract_number": "ДГ-20260101-042",
                "status": "В роботі",
                "discounted_price": 12000,
            }
        )
        qtbot.addWidget(dlg)
        assert dlg.edit_name.text() == "Склад ТОВ «Логіст»"
        assert dlg.edit_number.text() == "PRJ-77"
        assert dlg.edit_contract.text() == "ДГ-20260101-042"
        assert dlg.combo_status.currentText() == "В роботі"
        assert dlg.spin_discounted.value() == 12000
        data = dlg.get_data()
        assert data["profit"] == pytest.approx(12000.0)
        assert data["contract_number"] == "ДГ-20260101-042"
        dlg.close()


class TestProjectsTable:
    def test_contract_number_column(self, qtbot, monkeypatch):
        """Колонка «Договір» у списку проєктів заповнюється з даних."""
        from ventilation_company.gui_pyside6.projects_tab import ProjectsTab

        monkeypatch.setattr(
            "ventilation_company.gui_pyside6.projects_tab.ProjectRepository.list_all",
            staticmethod(
                lambda: [
                    {
                        "id": 1,
                        "name": "Кафе «Смак»",
                        "project_number": "PRJ-1",
                        "client": "ТОВ «Смак»",
                        "status": "В роботі",
                        "contract_number": "ДГ-20261008-001",
                        "created_at": "2026-10-01",
                        "discounted_price": 0,
                    },
                    {
                        "id": 2,
                        "name": "Без договору",
                        "project_number": "PRJ-2",
                        "client": "",
                        "status": "Новий",
                        "contract_number": None,
                        "created_at": "2026-10-02",
                        "discounted_price": 0,
                    },
                ]
            ),
        )
        monkeypatch.setattr(
            "ventilation_company.gui_pyside6.projects_tab.ProductRepository.get_all",
            staticmethod(lambda project_id: []),
        )
        tab = ProjectsTab()
        qtbot.addWidget(tab)
        headers = [
            tab.model.headerData(i, Qt.Orientation.Horizontal)
            for i in range(tab.model.columnCount())
        ]
        col = headers.index("Договір")
        assert tab.model.item(0, col).text() == "ДГ-20261008-001"
        assert tab.model.item(1, col).text() == "—"
