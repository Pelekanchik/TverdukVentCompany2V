"""E2E-тести діалогу виробу через pytest-qt (qtbot).

Імітують реальні дії користувача: кліки по кнопках, ввід тексту з клавіатури,
перемикання чекбоксів. Ловлять регресії інтеракції, які unit-тести не бачать
(зламані connect(), неактивні кнопки, модальні діалоги).
"""

import json

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QMessageBox,
    QPushButton,
)

CUSTOM_PRICES = {
    "оцинкована сталь": {"0.5": "450", "0.7": 580, "1.0": 750},
    "нержавіюча сталь": {"0.5": 950, "1.5": "1 600,00"},
    "мідь": {"0.8": 2100},
}

MATERIAL_DENSITIES = {
    "оцинкована сталь": 7850.0,
    "нержавіюча сталь": 7900.0,
    "мідь": 8900.0,
}


class _PricingStub:
    material_prices = CUSTOM_PRICES
    material_densities = MATERIAL_DENSITIES
    markup_categories = {
        "Стандартна": 30.0,
        "Преміум": 40.0,
        "Економ": 20.0,
        "Спецзамовлення": 50.0,
    }

    def reload(self):
        return None

    def get_material_density(self, material):
        return MATERIAL_DENSITIES.get(str(material).lower(), 7850.0)

    def list_materials(self):
        return list(CUSTOM_PRICES)


@pytest.fixture(autouse=True)
def _stub_pricing(monkeypatch):
    monkeypatch.setattr(
        "ventilation_company.services.pricing_settings.PricingSettings.get_instance",
        staticmethod(lambda: _PricingStub()),
    )


@pytest.fixture
def dlg(qtbot, monkeypatch):
    """Діалог виробу, показаний немодально (можна клікати через qtbot)."""
    from ventilation_company.gui_pyside6.product_dialog import ProductDialog

    dialog = ProductDialog({})
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitUntil(dialog.isVisible, timeout=2000)
    yield dialog
    dialog.close()


def _type(qtbot, widget: QLineEdit, text: str) -> None:
    """Ввід тексту як користувач. ASCII — подіями клавіатури (keyClicks).

    Не-ASCII — через widget.insert(): QTest.keyClick з не-ASCII падає з
    сегфолтом (PySide6 6.11, Windows), а вставка буфером спрацьовує лише
    раз — після першої paste() Qt на Windows не дає перезаписати буфер
    у цьому процесі (known Qt bug). insert() іде тим самим шляхом
    редагування QLineEdit, що й вставлений текст (textChanged тощо)."""
    widget.setFocus()
    qtbot.waitUntil(widget.hasFocus, timeout=2000)
    if text.isascii():
        qtbot.keyClicks(widget, text)
    else:
        widget.insert(text)


def _save_button(dialog) -> QPushButton:
    box = dialog.findChild(QDialogButtonBox)
    assert box is not None
    return box.button(QDialogButtonBox.StandardButton.Save)


def _calc_button(dialog) -> QPushButton:
    for btn in dialog.findChildren(QPushButton):
        if "Розрахувати" in btn.text():
            return btn
    raise AssertionError("Кнопку «Розрахувати ціну» не знайдено")


class TestFullUserFlow:
    def test_create_product_end_to_end(self, qtbot, dlg):
        """Повний сценарій: назва → матеріал → товщина → розрахунок → збереження."""
        _type(qtbot, dlg.edit_name, "Прямокутний повітропровід 500×300")
        dlg.combo_material.setCurrentText("Оцинкована сталь")
        dlg.combo_thickness.setCurrentText("0.7")
        # Ціна металу підтягнулась з «Ціноутворення»
        assert "580" in dlg.lbl_metal_price.text()

        qtbot.mouseClick(_calc_button(dlg), Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: dlg._calc_result is not None, timeout=2000)

        qtbot.mouseClick(_save_button(dlg), Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: dlg.result() == QDialog.DialogCode.Accepted, timeout=2000)

        data = dlg.get_data()
        assert data["name"] == "Прямокутний повітропровід 500×300"
        assert data["material"] == "Оцинкована сталь"
        assert data["thickness"] == 0.7
        assert data["quantity"] == 1
        assert data["total_price"] > 0
        assert data["cost_price"] > 0
        # Вага й площа металу — у params (серіалізуються в notes як JSON)
        params = json.loads(data["notes"])
        assert params["weight_kg"] > 0
        assert params["metal_area_m2"] > 0

    def test_save_without_name_warns_and_stays_open(self, qtbot, dlg, monkeypatch):
        warnings = []
        monkeypatch.setattr(
            QMessageBox,
            "warning",
            staticmethod(lambda *a, **k: warnings.append(a)),
        )
        qtbot.mouseClick(_save_button(dlg), Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: len(warnings) == 1, timeout=2000)
        assert dlg.result() != QDialog.DialogCode.Accepted

    def test_save_without_calc_asks_and_calculates(self, qtbot, dlg, monkeypatch):
        """Без розрахунку → питання «Розрахувати зараз?» → Yes → розрахунок."""
        _type(qtbot, dlg.edit_name, "Відвод 90°")
        monkeypatch.setattr(
            QMessageBox,
            "question",
            staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
        )
        qtbot.mouseClick(_save_button(dlg), Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: dlg._calc_result is not None, timeout=2000)
        # Діалог лишається відкритим: користувач ще не натиснув «Зберегти» повторно
        assert dlg.result() != QDialog.DialogCode.Accepted

    def test_save_without_calc_no_accepts(self, qtbot, dlg, monkeypatch):
        """Без розрахунку → «Ні» → діалог закривається без розрахунку."""
        _type(qtbot, dlg.edit_name, "Заглушка")
        monkeypatch.setattr(
            QMessageBox,
            "question",
            staticmethod(lambda *a, **k: QMessageBox.StandardButton.No),
        )
        qtbot.mouseClick(_save_button(dlg), Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: dlg.result() == QDialog.DialogCode.Accepted, timeout=2000)
        assert dlg._calc_result is None


class TestUiInteractions:
    def test_cancel_closes_without_save(self, qtbot, dlg):
        box = dlg.findChild(QDialogButtonBox)
        qtbot.mouseClick(
            box.button(QDialogButtonBox.StandardButton.Cancel), Qt.MouseButton.LeftButton
        )
        qtbot.waitUntil(lambda: dlg.result() == QDialog.DialogCode.Rejected, timeout=2000)

    def test_round_pipe_disables_height(self, qtbot, dlg):
        _type(qtbot, dlg.edit_name, "Круглий повітропровід")
        dlg.combo_type.setCurrentText("Повітропровід круглий")
        assert not dlg.spin_height.isEnabled()
        assert dlg.spin_height.value() == 0
        assert dlg.spin_width.prefix() == "Ø "

    def test_flange_checkbox_enables_fields(self, qtbot, dlg):
        assert not dlg.spin_flange_count.isEnabled()
        qtbot.mouseClick(dlg.chk_with_flanges, Qt.MouseButton.LeftButton)
        assert dlg.chk_with_flanges.isChecked()
        assert dlg.spin_flange_count.isEnabled()
        assert dlg.combo_flange_profile.isEnabled()

    def test_edit_existing_product_prefills(self, qtbot):
        """Відкриття виробу на редагування: усі поля відновлені з даних."""
        from ventilation_company.gui_pyside6.product_dialog import ProductDialog

        data = {
            "name": "Перехід 400×300",
            "product_type": "Перехід прямокутний",
            "width": 400,
            "height": 300,
            "length": 500,
            "material": "Нержавіюча сталь",
            "thickness": 1.5,
            "quantity": 3,
            "notes": '{"with_flanges": true, "flange_count": 2}',
        }
        dialog = ProductDialog(data)
        qtbot.addWidget(dialog)
        assert dialog.edit_name.text() == "Перехід 400×300"
        assert dialog.combo_material.currentText() == "Нержавіюча сталь"
        assert dialog.combo_thickness.currentText() == "1.5"
        assert dialog.spin_qty.value() == 3
        assert dialog.chk_with_flanges.isChecked()
        assert dialog.spin_flange_count.value() == 2
        dialog.close()

    def test_material_switch_updates_price_label(self, qtbot, dlg):
        """Зміна матеріалу → ціна металу в лейблі оновлюється (сигнали живі)."""
        _type(qtbot, dlg.edit_name, "Тест")
        dlg.combo_material.setCurrentText("Мідь")
        dlg.combo_thickness.setCurrentText("0.8")
        assert "2,100.00" in dlg.lbl_metal_price.text()
