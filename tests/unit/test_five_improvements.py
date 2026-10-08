"""Тести п'яти покращень: КП PDF, дублювання виробу, документи, Excel-експорт."""

import time

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QMessageBox


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _no_modal_boxes(monkeypatch):
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(
        "PySide6.QtWidgets.QMessageBox.critical", staticmethod(lambda *a, **k: None)
    )
    monkeypatch.setattr(
        "PySide6.QtWidgets.QMessageBox.information", staticmethod(lambda *a, **k: None)
    )
    monkeypatch.setattr(
        "PySide6.QtWidgets.QMessageBox.question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No),
    )


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
            "name": "Труба",
            "product_type": "Повітропровід круглий",
            "quantity": 2,
            "cost_price": 1000.0,
            "unit_price": 1500.0,
            "discounted_price": 0,
            "total_price": 3000.0,
        }
    ],
    "documents": [],
    "drawings": [],
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


def _wait_worker(qapp, dlg, iterations=500):
    for _ in range(iterations):
        qapp.processEvents()
        if dlg._worker is None:
            return True
        time.sleep(0.001)
    return False


def _make_card(qapp, monkeypatch, tmp_path, out_name="out"):
    from ventilation_company.gui_pyside6.project_card_dialog import ProjectCardDialog

    monkeypatch.setattr(ProjectCardDialog, "_fetch_data", lambda self: CARD_DATA)
    out = tmp_path / out_name
    monkeypatch.setattr(
        "PySide6.QtWidgets.QFileDialog.getSaveFileName",
        staticmethod(lambda *a, **k: (str(out), "")),
    )
    registered = []
    monkeypatch.setattr(
        ProjectCardDialog,
        "_register_document",
        lambda self, doc_type, path: registered.append((doc_type, path)),
    )
    dlg = ProjectCardDialog(1)
    assert _wait_worker(qapp, dlg), "worker завис"
    return dlg, out, registered


class TestProposalPdf:
    def test_proposal_button_saves_pdf_and_registers_doc(self, qapp, monkeypatch, tmp_path):
        from ventilation_company.gui_pyside6 import project_card_docs_mixin as mod

        def _fake_proposal(data, items, path):
            with open(path, "wb") as f:
                f.write(b"%PDF-1.4 fake")

        monkeypatch.setattr(mod, "generate_proposal", staticmethod(_fake_proposal))
        dlg, out, registered = _make_card(qapp, monkeypatch, tmp_path, "КП.pdf")
        dlg._on_proposal_pdf()
        assert out.exists()
        assert ("кп", str(out)) in registered
        dlg.close()

    def test_proposal_empty_project_shows_info(self, qapp, monkeypatch, tmp_path):
        from ventilation_company.gui_pyside6.project_card_dialog import ProjectCardDialog

        data = dict(CARD_DATA)
        data["products"] = []
        data["works"] = []
        monkeypatch.setattr(ProjectCardDialog, "_fetch_data", lambda self: data)
        called = {"info": False}
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.information",
            staticmethod(lambda *a, **k: called.__setitem__("info", True)),
        )
        dlg = ProjectCardDialog(1)
        assert _wait_worker(qapp, dlg)
        dlg._on_proposal_pdf()
        assert called["info"]
        dlg.close()


class TestMaterialOrderRegistersDoc:
    def test_saved_order_registered_in_documents(self, qapp, monkeypatch, tmp_path):
        from PySide6.QtWidgets import QDialog

        monkeypatch.setattr(
            "ventilation_company.gui_pyside6.project_card_dialog.MaterialOrderPreviewDialog.exec",
            lambda self: QDialog.DialogCode.Accepted,
        )
        dlg, out, registered = _make_card(qapp, monkeypatch, tmp_path, "заявка.xlsx")
        dlg._on_material_order()
        assert out.exists()
        assert ("заявка", str(out)) in registered
        dlg.close()


class TestDuplicateProduct:
    def test_duplicate_creates_copy_without_id(self, qapp, monkeypatch):
        from ventilation_company.gui_pyside6.products_tab import ProductsTab

        monkeypatch.setattr(ProductsTab, "_load_data", lambda self: None)
        monkeypatch.setattr(ProductsTab, "_reload_projects", lambda self: None)
        tab = ProductsTab()

        original = {
            "id": 7,
            "name": "Труба Ø400",
            "product_type": "Повітропровід круглий",
            "quantity": 2,
            "total_price": 3000.0,
            "project_id": 1,
        }
        created = {}

        monkeypatch.setattr(tab, "_get_selected_id", lambda: 7)

        from ventilation_company.database.repositories import product_repo

        monkeypatch.setattr(
            product_repo.ProductRepository, "get_by_id", staticmethod(lambda i: dict(original))
        )

        def _create(data):
            created.update(data)
            return {"id": 8, **data}

        monkeypatch.setattr(product_repo.ProductRepository, "create", staticmethod(_create))
        tab._on_duplicate()
        assert created.get("name") == "Труба Ø400 (копія)"
        assert "id" not in created
        assert created.get("quantity") == 2
        tab.close() if hasattr(tab, "close") else None


class TestProjectsExcelExport:
    def test_export_excel_writes_rows(self, qapp, monkeypatch, tmp_path):
        from openpyxl import load_workbook

        from ventilation_company.gui_pyside6.projects_tab import ProjectsTab

        monkeypatch.setattr(ProjectsTab, "_load_data", lambda self: None)
        tab = ProjectsTab()
        tab._projects = [
            {
                "id": 1,
                "project_number": "PRJ-1",
                "name": "Проєкт А",
                "client": "ТОВ «А»",
                "status": "В роботі",
                "contract_number": "ДГ-20261008-001",
                "created_at": "2026-09-27",
                "cost_price": 5000.0,
                "customer_price": 8000.0,
                "discounted_price": 0.0,
                "profit": 3000.0,
            }
        ]
        out = tmp_path / "projects.xlsx"
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            staticmethod(lambda *a, **k: (str(out), "")),
        )
        tab._export_excel()
        assert out.exists()
        ws = load_workbook(out).active
        assert ws.cell(row=2, column=3).value == "Проєкт А"
        assert ws.cell(row=2, column=6).value == "ДГ-20261008-001"
        assert ws.cell(row=2, column=11).value == 3000.0
