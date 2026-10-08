"""E2E-тести картки проєкту через pytest-qt (qtbot).

Перевіряють інтеракцію найскладнішого діалогу програми після розбиття на
модулі: вкладки, креслення, документи, заявка на матеріали. Дані БД
підмінено стабом _fetch_data — тестуємо GUI, а не репозиторії.
"""

import os

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QPushButton

CARD_DATA = {
    "project": {
        "id": 1,
        "name": "Тестовий проєкт",
        "project_number": "PRJ-1",
        "client": "ТОВ «Клієнт»",
        "status": "в роботі",
        "created_at": "2026-09-27 10:00",
        "cost_price": 5000.0,
        "customer_price": 8000.0,
        "discounted_price": 0,
        "works_total": 1000.0,
        "plus_expenses_total": 0.0,
        "minus_expenses_total": 0.0,
        "paid_total": 0.0,
    },
    "products": [
        {
            "id": 1,
            "name": "Труба Ø250",
            "product_type": "Повітропровід круглий",
            "quantity": 2,
            "cost_price": 1000.0,
            "unit_price": 1500.0,
            "discounted_price": 0,
            "total_price": 3000.0,
        }
    ],
    "documents": [
        {
            "id": 5,
            "doc_type": "кп",
            "filename": "kp.pdf",
            "file_path": "C:\\docs\\kp.pdf",
            "file_size": 204800,
            "created_at": "2026-09-27 11:00",
        }
    ],
    "drawings": [
        {
            "id": 10,
            "filename": "план_вент.dwg",
            "drawing_type": "креслення",
            "file_path": "C:\\drawings\\план_вент.dwg",
            "notes": "",
            "created_at": "2026-09-27 09:00",
        },
        {
            "id": 11,
            "filename": "model.rvt",
            "drawing_type": "модель",
            "file_path": "C:\\drawings\\model.rvt",
            "notes": "Revit",
            "created_at": "2026-09-27 09:30",
        },
    ],
    "works": [
        {
            "id": 1,
            "work_name": "Монтаж",
            "quantity": 1.0,
            "unit": "шт",
            "unit_price": 1000.0,
            "total_price": 1000.0,
        }
    ],
    "expenses": [],
    "payments": [],
}


@pytest.fixture(autouse=True)
def _no_modal_boxes(monkeypatch):
    """Блокуємо модальні вікна; question за замовчуванням — No."""
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No),
    )


@pytest.fixture
def card(qtbot, monkeypatch):
    """Картка проєкту зі стабованими даними, дочекана завантаження."""
    from ventilation_company.gui_pyside6.project_card_dialog import ProjectCardDialog

    monkeypatch.setattr(ProjectCardDialog, "_fetch_data", lambda self: CARD_DATA)
    dlg = ProjectCardDialog(1)
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitUntil(lambda: dlg._worker is None, timeout=5000)
    yield dlg
    dlg.close()


def _button(widget, text_part: str) -> QPushButton:
    for btn in widget.findChildren(QPushButton):
        if text_part in btn.text():
            return btn
    raise AssertionError(f"Кнопку «{text_part}» не знайдено")


def _tab(widget, label_part: str):
    """Вкладка картки за фрагментом назви (для пошуку кнопок у її межах)."""
    for i in range(widget.tabs.count()):
        if label_part in widget.tabs.tabText(i):
            return widget.tabs.widget(i)
    raise AssertionError(f"Вкладку «{label_part}» не знайдено")


class TestTabs:
    def test_all_seven_tabs_present(self, card):
        labels = [card.tabs.tabText(i) for i in range(card.tabs.count())]
        assert len(labels) == 7
        for expected in ("Інформація", "Деталі", "Документи", "Креслення", "Роботи"):
            assert any(expected in label for label in labels), expected

    def test_switch_through_all_tabs(self, qtbot, card):
        """Перемикання всіх вкладок не падає (regression для _build_*_tab)."""
        for i in range(card.tabs.count()):
            card.tabs.setCurrentIndex(i)
            qtbot.waitUntil(
                lambda i=i: card.tabs.currentIndex() == i, timeout=2000
            )


class TestDrawingsTab:
    def test_drawings_populated(self, card):
        assert card.drawings_table.rowCount() == 2
        assert "📐 Креслення (2)" in card._lbl_drawings_count.text()
        assert card.drawings_table.item(0, 0).text() == "план_вент.dwg"
        assert card.drawings_table.item(1, 1).text() == "модель"

    def test_add_drawings_via_file_dialog(self, qtbot, card, monkeypatch):
        """Клік «➕ Додати файли…» → файл з діалогу потрапляє у репозиторій."""
        created = []
        monkeypatch.setattr(
            "ventilation_company.gui_pyside6.project_card_docs_mixin."
            "ProjectDrawingRepository.create",
            staticmethod(lambda **kw: created.append(kw)),
        )
        fake_path = os.path.abspath("C:\\drawings\\новий_план.dxf")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getOpenFileNames",
            staticmethod(lambda *a, **k: ([fake_path], "")),
        )
        qtbot.mouseClick(
            _button(_tab(card, "Креслення"), "Додати файли"), Qt.MouseButton.LeftButton
        )
        assert len(created) == 1
        assert created[0]["project_id"] == 1
        assert created[0]["filename"] == "новий_план.dxf"
        assert created[0]["drawing_type"] == "креслення"

    def test_add_model_type_guessed_from_extension(self, qtbot, card, monkeypatch):
        created = []
        monkeypatch.setattr(
            "ventilation_company.gui_pyside6.project_card_docs_mixin."
            "ProjectDrawingRepository.create",
            staticmethod(lambda **kw: created.append(kw)),
        )
        fake_path = "C:\\models\\будівля.rvt"
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getOpenFileNames",
            staticmethod(lambda *a, **k: ([fake_path], "")),
        )
        qtbot.mouseClick(
            _button(_tab(card, "Креслення"), "Додати файли"), Qt.MouseButton.LeftButton
        )
        assert created[0]["drawing_type"] == "модель"

    def test_open_without_selection_warns(self, qtbot, card, monkeypatch):
        warnings = []
        monkeypatch.setattr(
            QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a))
        )
        card.drawings_table.clearSelection()
        qtbot.mouseClick(_button(_tab(card, "Креслення"), "Відкрити"), Qt.MouseButton.LeftButton)
        assert len(warnings) == 1

    def test_delete_drawing_declined_keeps_rows(self, qtbot, card, monkeypatch):
        """Підтвердження «Ні» → рядки на місці, delete не викликано."""
        deleted = []
        monkeypatch.setattr(
            "ventilation_company.gui_pyside6.project_card_docs_mixin."
            "ProjectDrawingRepository.delete",
            staticmethod(lambda _id: deleted.append(_id)),
        )
        card.drawings_table.selectRow(0)
        qtbot.mouseClick(_button(_tab(card, "Креслення"), "Видалити"), Qt.MouseButton.LeftButton)
        assert deleted == []
        assert card.drawings_table.rowCount() == 2

    def test_delete_drawing_confirmed_calls_repo(self, qtbot, card, monkeypatch):
        """Підтвердження «Так» → delete(id) і перезавантаження."""
        deleted = []
        monkeypatch.setattr(
            "ventilation_company.gui_pyside6.project_card_docs_mixin."
            "ProjectDrawingRepository.delete",
            staticmethod(lambda _id: deleted.append(_id)),
        )
        monkeypatch.setattr(
            QMessageBox,
            "question",
            staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
        )
        card.drawings_table.selectRow(0)
        qtbot.mouseClick(_button(_tab(card, "Креслення"), "Видалити"), Qt.MouseButton.LeftButton)
        assert deleted == [10]


class TestDocumentsTab:
    def test_documents_populated(self, card):
        assert card.docs_model.rowCount() == 1
        assert "📄 Документи проєкту (1)" in card._lbl_docs_count.text()

    def test_open_document_without_selection_warns(self, qtbot, card, monkeypatch):
        warnings = []
        monkeypatch.setattr(
            QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a))
        )
        card.docs_table.clearSelection()
        qtbot.mouseClick(
            _button(_tab(card, "Документи"), "Експортувати"), Qt.MouseButton.LeftButton
        )
        assert len(warnings) == 1


class TestMaterialOrder:
    def test_button_saves_order_and_registers_doc(self, qtbot, card, monkeypatch, tmp_path):
        """Повний клік шляхом: кнопка → діалог-прев'ю → Excel + реєстрація."""
        from PySide6.QtWidgets import QDialog

        monkeypatch.setattr(
            "ventilation_company.gui_pyside6.project_card_dialog."
            "MaterialOrderPreviewDialog.exec",
            lambda self: QDialog.DialogCode.Accepted,
        )
        out = tmp_path / "заявка.xlsx"
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            staticmethod(lambda *a, **k: (str(out), "")),
        )
        registered = []
        monkeypatch.setattr(
            card,
            "_register_document",
            lambda doc_type, path: registered.append((doc_type, path)),
        )
        qtbot.mouseClick(_button(card, "Замовлення матеріалів"), Qt.MouseButton.LeftButton)
        assert out.exists()
        assert ("заявка", str(out)) in registered
