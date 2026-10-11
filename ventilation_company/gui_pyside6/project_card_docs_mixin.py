"""Документи, креслення та генерація PDF/Excel для картки проєкту.

ProjectCardDocsMixin — міксин для ProjectCardDialog: усі методи працюють
з атрибутами головного класу (self.project_id, self._data, self.tabs тощо),
тому клас нащадка не потребує змін окрім успадкування.

Механічно винесено з project_card_dialog.py (рефакторинг v2.10) — логіка
не змінювалася.
"""

import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:  # QtPdf існує не в усіх збірках Qt6
    from PySide6.QtPdf import QPdfDocument
except ImportError:  # pragma: no cover
    QPdfDocument = None  # type: ignore[assignment, misc]

from ventilation_company.act_generator import generate_act
from ventilation_company.contract_generator import generate_contract
from ventilation_company.database.repositories.project_document_repo import (
    ProjectDocumentRepository,
)
from ventilation_company.database.repositories.project_drawing_repo import (
    ProjectDrawingRepository,
)
from ventilation_company.gui_pyside6.material_order_dialog import MaterialOrderPreviewDialog
from ventilation_company.gui_pyside6.project_card_dialogs import (
    DRAWING_FILE_FILTER,
    DrawingsTable,
)
from ventilation_company.gui_pyside6.table_utils import setup_table
from ventilation_company.gui_pyside6.telegram_send import send_document_telegram
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.invoice_generator import generate_invoice
from ventilation_company.material_order import (
    calculate_material_order,
    export_material_order_to_excel,
)
from ventilation_company.proposal_generator import export_proposal_to_excel, generate_proposal
from ventilation_company.services.audit_service import log_action
from ventilation_company.services.business_settings import BusinessSettings
from ventilation_company.services.contract_numbering import (
    ensure_contract_number,
    ensure_document_number,
)


class ProjectCardDocsMixin:
    """Документи, креслення та генерація PDF/Excel (див. модуль-докстрінг)."""

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Придатне для файлу ім'я проєкту."""
        forbidden = '<>:"/\\|?*'
        cleaned = "".join("_" if ch in forbidden else ch for ch in name).strip()
        return cleaned[:60] or "проєкт"

    def _register_document(self, doc_type: str, path: str):
        """Додати збережений файл у вкладку «Документи» проєкту."""
        try:
            data = Path(path).read_bytes()
            ProjectDocumentRepository.create(
                self.project_id, doc_type, os.path.basename(path), data
            )
            self._refresh_documents()
        except Exception as exc:  # noqa: BLE001 — файл уже збережено, це лише додатково
            QMessageBox.warning(
                self,
                "Документи",
                f"Файл збережено, але не вдалося додати його у «Документи»:\n{exc}",
            )

    def _offer_after_save(self, path: str, caption: str):
        """Після збереження документа: відкрити файл, надіслати в Telegram чи закрити."""
        box = QMessageBox()
        box.setWindowTitle("Готово")
        box.setText(f"Файл збережено:\n{path}")
        btn_open = box.addButton("📂 Відкрити", QMessageBox.ButtonRole.AcceptRole)
        btn_tg = box.addButton("📨 В Telegram", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Закрити", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked is btn_open:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        elif clicked is btn_tg:
            send_document_telegram(self, path, caption)

    def _on_contract_pdf(self):
        """Згенерувати договір (PDF) з реквізитами сторін."""
        name = self._project_data.get("name") or f"Проєкт #{self.project_id}"
        default = f"Договір_{self._safe_filename(name)}.pdf"
        path, _selected = QFileDialog.getSaveFileName(
            self,
            "Зберегти договір",
            default,
            "PDF (*.pdf)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        discounted = float(self._project_data.get("discounted_price") or 0)
        total = (
            discounted if discounted > 0 else float(self._project_data.get("customer_price") or 0)
        )
        project_data = {
            "name": name,
            "project_number": self._project_data.get("project_number", ""),
            "client": self._project_data.get("client", ""),
            "address": self._project_data.get("address", ""),
            "total_amount": total,
            "contract_number": ensure_contract_number(self.project_id, self._project_data),
            "company": BusinessSettings.get_instance().get_company(),
        }
        try:
            generate_contract(project_data, path)
        except Exception as exc:  # noqa: BLE001 — показуємо будь-яку помилку користувачу
            QMessageBox.critical(self, "Помилка", f"Не вдалося сформувати договір:\n{exc}")
            return
        self._register_document("договір", path)
        log_action(
            "project.contract",
            entity_type="project",
            entity_id=self.project_id,
            details={
                "contract_number": project_data["contract_number"],
                "path": path,
                "total_amount": total,
            },
            message=f"Сформовано договір {project_data['contract_number']}",
        )
        self._offer_after_save(
            path,
            f"📄 Договір {project_data['contract_number']} — {name}",
        )

    def _on_proposal_pdf(self):
        """Згенерувати комерційну пропозицію (PDF) для замовника."""
        if not self._products and not self._works:
            QMessageBox.information(
                self,
                "Комерційна пропозиція",
                "У проєкті немає виробів і робіт — немає що пропонувати.",
            )
            return
        name = self._project_data.get("name") or f"Проєкт #{self.project_id}"
        items = self._collect_document_items()
        default = f"КП_{self._safe_filename(name)}.pdf"
        path, _selected = QFileDialog.getSaveFileName(
            self,
            "Зберегти комерційну пропозицію",
            default,
            "PDF (*.pdf)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        project_data = {
            "name": name,
            "project_number": self._project_data.get("project_number", ""),
            "client": self._project_data.get("client", ""),
            "address": self._project_data.get("address", ""),
            "company": BusinessSettings.get_instance().get_company(),
        }
        try:
            generate_proposal(project_data, items, path)
        except Exception as exc:  # noqa: BLE001 — показуємо будь-яку помилку користувачу
            QMessageBox.critical(self, "Помилка", f"Не вдалося сформувати КП:\n{exc}")
            return
        self._register_document("кп", path)
        self._offer_after_save(path, f"📋 Комерційна пропозиція — {name}")

    def _on_proposal_excel(self):
        """Експорт комерційної пропозиції у Excel."""
        if not self._products and not self._works:
            QMessageBox.information(
                self,
                "Комерційна пропозиція",
                "У проєкті немає виробів і робіт — немає що пропонувати.",
            )
            return
        name = self._project_data.get("name") or f"Проєкт #{self.project_id}"
        items = self._collect_document_items()
        default = f"КП_{self._safe_filename(name)}.xlsx"
        path, _selected = QFileDialog.getSaveFileName(
            self,
            "Зберегти комерційну пропозицію (Excel)",
            default,
            "Excel (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        project_data = {
            "name": name,
            "project_number": self._project_data.get("project_number", ""),
            "client": self._project_data.get("client", ""),
            "address": self._project_data.get("address", ""),
            "company": BusinessSettings.get_instance().get_company(),
        }
        try:
            export_proposal_to_excel(project_data, items, path)
        except Exception as exc:  # noqa: BLE001 — показуємо будь-яку помилку користувачу
            QMessageBox.critical(self, "Помилка", f"Не вдалося сформувати КП:\n{exc}")
            return
        self._register_document("кп", path)
        answer = QMessageBox.question(
            self,
            "Готово",
            f"Комерційну пропозицію (Excel) збережено:\n{path}\n\nВідкрити файл?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _on_act_pdf(self):
        """Згенерувати акт виконаних робіт (PDF) для підписання з замовником."""
        if not self._products and not self._works:
            QMessageBox.information(
                self,
                "Акт виконаних робіт",
                "У проєкті немає виробів і робіт — немає що здавати.",
            )
            return
        name = self._project_data.get("name") or f"Проєкт #{self.project_id}"
        items = self._collect_document_items()
        default = f"Акт_{self._safe_filename(name)}.pdf"
        path, _selected = QFileDialog.getSaveFileName(
            self,
            "Зберегти акт виконаних робіт",
            default,
            "PDF (*.pdf)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        project_data = {
            "name": name,
            "project_number": self._project_data.get("project_number", ""),
            "client": self._project_data.get("client", ""),
            "address": self._project_data.get("address", ""),
            "contract_number": self._project_data.get("contract_number", ""),
            "act_number": ensure_document_number(self.project_id, self._project_data, "act_number"),
            "company": BusinessSettings.get_instance().get_company(),
        }
        try:
            generate_act(project_data, items, path)
        except Exception as exc:  # noqa: BLE001 — показуємо будь-яку помилку користувачу
            QMessageBox.critical(self, "Помилка", f"Не вдалося сформувати акт:\n{exc}")
            return
        self._register_document("акт", path)
        log_action(
            "project.act",
            entity_type="project",
            entity_id=self.project_id,
            details={
                "act_number": project_data["act_number"],
                "path": path,
                "contract_number": project_data["contract_number"],
            },
            message=f"Сформовано акт {project_data['act_number']}",
        )
        self._offer_after_save(path, f"✅ Акт {project_data['act_number']} — {name}")

    def _collect_document_items(self) -> list[dict]:
        """Позиції для КП/акта/рахунка: виробі (зі знижкою, якщо є) + роботи."""
        items = []
        for p in self._products:
            qty = float(p.get("quantity") or 1) or 1
            total = float(p.get("discounted_price") or 0) or float(p.get("total_price") or 0)
            items.append(
                {
                    "name": p.get("name", ""),
                    "description": str(p.get("product_type", "")),
                    "quantity": qty,
                    "unit": "шт",
                    "price": round(total / qty, 2),
                }
            )
        for w in self._works:
            qty = float(w.get("quantity") or 1) or 1
            total = float(w.get("total_price") or 0)
            items.append(
                {
                    "name": w.get("work_name", ""),
                    "description": "Монтажні роботи",
                    "quantity": qty,
                    "unit": w.get("unit", "шт"),
                    "price": round(total / qty, 2),
                }
            )
        return items

    def _on_invoice_pdf(self):
        """Згенерувати рахунок на оплату (PDF) з банківськими реквізитами."""
        if not self._products and not self._works:
            QMessageBox.information(
                self,
                "Рахунок на оплату",
                "У проєкті немає виробів і робіт — немає за що виставляти рахунок.",
            )
            return
        name = self._project_data.get("name") or f"Проєкт #{self.project_id}"
        items = self._collect_document_items()
        default = f"Рахунок_{self._safe_filename(name)}.pdf"
        path, _selected = QFileDialog.getSaveFileName(
            self,
            "Зберегти рахунок на оплату",
            default,
            "PDF (*.pdf)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        project_data = {
            "name": name,
            "project_number": self._project_data.get("project_number", ""),
            "client": self._project_data.get("client", ""),
            "address": self._project_data.get("address", ""),
            "contract_number": self._project_data.get("contract_number", ""),
            "invoice_number": ensure_document_number(
                self.project_id, self._project_data, "invoice_number"
            ),
            "company": BusinessSettings.get_instance().get_company(),
        }
        try:
            generate_invoice(project_data, items, path)
        except Exception as exc:  # noqa: BLE001 — показуємо будь-яку помилку користувачу
            QMessageBox.critical(self, "Помилка", f"Не вдалося сформувати рахунок:\n{exc}")
            return
        self._register_document("рахунок", path)
        log_action(
            "project.invoice",
            entity_type="project",
            entity_id=self.project_id,
            details={
                "invoice_number": project_data["invoice_number"],
                "path": path,
                "contract_number": project_data["contract_number"],
            },
            message=f"Сформовано рахунок {project_data['invoice_number']}",
        )
        self._offer_after_save(path, f"🧾 Рахунок {project_data['invoice_number']} — {name}")

    def _on_material_order(self):
        """Розрахувати заявку на матеріали за виробами проєкту та зберегти в Excel."""
        if not self._products:
            QMessageBox.information(
                self,
                "Замовлення матеріалів",
                "У проєкті ще немає виробів — нічого розраховувати.\n"
                "Спочатку додайте вироби на вкладці «Деталі».",
            )
            return
        name = self._project_data.get("name") or f"Проєкт #{self.project_id}"
        try:
            order = calculate_material_order(self._products, project_name=name)
        except Exception as exc:  # noqa: BLE001 — показуємо будь-яку помилку користувачу
            QMessageBox.critical(self, "Помилка", f"Не вдалося розрахувати заявку:\n{exc}")
            return
        preview = MaterialOrderPreviewDialog(order, parent=self, project_id=self.project_id)
        if preview.exec() != QDialog.DialogCode.Accepted:
            return
        order = preview.get_order()
        default = f"Заявка_матеріали_{self._safe_filename(name)}.xlsx"
        path, _selected = QFileDialog.getSaveFileName(
            self,
            "Зберегти заявку на матеріали",
            default,
            "Excel (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            export_material_order_to_excel(order, path)
        except Exception as exc:  # noqa: BLE001 — показуємо будь-яку помилку користувачу
            QMessageBox.critical(self, "Помилка", f"Не вдалося сформувати заявку:\n{exc}")
            return
        self._register_document("заявка", path)
        answer = QMessageBox.question(
            self,
            "Готово",
            f"Заявку на матеріали збережено:\n{path}\n\n"
            f"Позицій: {order.total_items}, орієнтовна сума: ₴ {order.total_cost:,.2f}\n\n"
            "Відкрити файл?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _build_documents_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        top = QHBoxLayout()
        self._lbl_docs_count = QLabel("📄 Документи проєкту (…)")
        self._lbl_docs_count.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-size: 14px;")
        top.addWidget(self._lbl_docs_count)
        top.addStretch()
        btn_refresh = QPushButton("🔄 Оновити")
        btn_refresh.clicked.connect(self._refresh_documents)
        top.addWidget(btn_refresh)
        layout.addLayout(top)
        self.docs_table = QTableView()
        setup_table(self.docs_table, read_only=True)
        layout.addWidget(self.docs_table)
        self.docs_model = QStandardItemModel()
        self.docs_model.setHorizontalHeaderLabels(["ID", "Тип", "Файл", "Розмір", "Дата", "Дії"])
        self.docs_table.setModel(self.docs_model)
        self.docs_table.clicked.connect(self._on_docs_table_clicked)
        self.docs_table.doubleClicked.connect(lambda _idx: self._open_document())
        self.docs_table.setColumnWidth(0, 40)
        self.docs_table.setColumnWidth(1, 120)
        self.docs_table.setColumnWidth(2, 250)
        self.docs_table.setColumnWidth(3, 80)
        self.docs_table.setColumnWidth(4, 120)
        self.docs_table.setColumnWidth(5, 100)
        self._populate_documents()
        actions = QHBoxLayout()
        btn_add_doc = QPushButton("➕ Додати файл…")
        btn_add_doc.setToolTip(
            "Прикріпити довільний файл до документів проєкту (зберігається у базі)"
        )
        btn_add_doc.clicked.connect(self._on_add_document)
        actions.addWidget(btn_add_doc)
        actions.addStretch()
        btn_export = QPushButton("💾 Експортувати вибраний")
        btn_export.clicked.connect(self._export_document)
        actions.addWidget(btn_export)
        btn_delete = QPushButton("🗑️ Видалити вибраний")
        btn_delete.setStyleSheet(f"color: {Theme.DANGER};")
        btn_delete.clicked.connect(self._delete_document)
        actions.addWidget(btn_delete)
        layout.addLayout(actions)
        return tab

    def _populate_documents(self):
        self._lbl_docs_count.setText(f"📄 Документи проєкту ({len(self._documents)})")
        self.docs_model.removeRows(0, self.docs_model.rowCount())
        type_names = {
            "spec": "Специфікація",
            "calc": "Калькуляція",
            "metal": "Метал",
            "order": "Наряд",
            "заявка": "Заявка на матеріали",
            "кп": "КП (PDF)",
            "договір": "Договір",
            "файл": "Файл",
        }
        for doc in self._documents:
            row = [
                QStandardItem(str(doc["id"])),
                QStandardItem(type_names.get(doc["doc_type"], doc["doc_type"])),
                QStandardItem(doc["filename"]),
                QStandardItem(f"{doc['file_size'] / 1024:.1f} КБ"),
                QStandardItem(str(doc["created_at"])[:16] if doc["created_at"] else "—"),
                QStandardItem("📥 Завантажити"),
            ]
            for cell in row:
                cell.setEditable(False)
            self.docs_model.appendRow(row)

    def _refresh_documents(self):
        self._documents = ProjectDocumentRepository.get_by_project(self.project_id)
        self._populate_documents()

    MAX_DOC_FILE_MB = 25

    def _on_add_document(self):
        """Прикріпити файли з диску до документів проєкту."""
        paths, _selected = QFileDialog.getOpenFileNames(
            self,
            "Додати файли у документи проєкту",
            "",
            "Усі файли (*.*)",
        )
        for path in paths:
            try:
                size = os.path.getsize(path)
            except OSError as exc:
                QMessageBox.warning(self, "Документи", f"Не вдалося прочитати файл:\n{path}\n{exc}")
                continue
            if size > self.MAX_DOC_FILE_MB * 1024 * 1024:
                QMessageBox.warning(
                    self,
                    "Файл завеликий",
                    f"Файл більший за {self.MAX_DOC_FILE_MB} МБ — пропущено:\n{path}",
                )
                continue
            self._register_document("файл", path)

    # ── Креслення проєкту ──

    def _build_drawings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        top = QHBoxLayout()
        self._lbl_drawings_count = QLabel("📐 Креслення (…)")
        self._lbl_drawings_count.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-size: 14px;")
        top.addWidget(self._lbl_drawings_count)
        top.addStretch()
        btn_add = QPushButton("➕ Додати файли…")
        btn_add.clicked.connect(self._on_add_drawings)
        top.addWidget(btn_add)
        layout.addLayout(top)

        hint = QLabel(
            "DWG · DXF · PDF · Revit (RVT/RFA) · SolidWorks (SLDPRT/SLDASM/SLDDRW) · FreeCAD. "
            "Можна перетягнути файли мишкою прямо в таблицю. Подвійний клік — відкрити."
        )
        hint.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(hint)

        self.drawings_table = DrawingsTable()
        self.drawings_table.setColumnCount(5)
        self.drawings_table.setHorizontalHeaderLabels(["Назва", "Тип", "Шлях", "Примітка", "Дата"])
        setup_table(self.drawings_table, select_rows=True, single_selection=True, read_only=True)
        self.drawings_table.itemDoubleClicked.connect(self._on_open_drawing)
        self.drawings_table.itemSelectionChanged.connect(self._update_drawing_preview)
        self.drawings_table.filesDropped.connect(self._add_drawing_paths)

        # Попередній перегляд обраного креслення (PDF / картинки).
        self._drawing_preview = QLabel("Оберіть креслення для перегляду")
        self._drawing_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drawing_preview.setMinimumWidth(300)
        self._drawing_preview.setMinimumHeight(380)
        self._drawing_preview.setWordWrap(True)
        self._drawing_preview.setStyleSheet(
            f"color: {Theme.TEXT_MUTED}; font-size: 12px; border: 1px dashed {Theme.BORDER};"
        )
        # Без parent — self не QObject; посилання зберігаємо у self._pdf_doc
        self._pdf_doc = QPdfDocument() if QPdfDocument is not None else None

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.drawings_table)
        splitter.addWidget(self._drawing_preview)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        actions = QHBoxLayout()
        actions.addStretch()
        btn_open = QPushButton("📂 Відкрити")
        btn_open.clicked.connect(self._on_open_drawing)
        actions.addWidget(btn_open)
        btn_edit = QPushButton("✏️ Змінити")
        btn_edit.clicked.connect(self._on_edit_drawing)
        actions.addWidget(btn_edit)
        btn_del = QPushButton("🗑️ Видалити")
        btn_del.setStyleSheet(f"color: {Theme.DANGER};")
        btn_del.clicked.connect(self._on_delete_drawing)
        actions.addWidget(btn_del)
        layout.addLayout(actions)
        return tab

    def _populate_drawings(self):
        self._lbl_drawings_count.setText(f"📐 Креслення ({len(self._drawings)})")
        self.drawings_table.setRowCount(0)
        for d in self._drawings:
            row = self.drawings_table.rowCount()
            self.drawings_table.insertRow(row)
            values = [
                d["filename"],
                d["drawing_type"],
                d["file_path"],
                d.get("notes") or "",
                str(d.get("created_at") or "")[:16] or "—",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, d["id"])
                self.drawings_table.setItem(row, col, item)
        self.drawings_table.resizeColumnsToContents()
        self.drawings_table.horizontalHeader().setStretchLastSection(True)

    def _on_add_drawings(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Оберіть креслення або моделі", "", DRAWING_FILE_FILTER
        )
        if paths:
            self._add_drawing_paths(paths)

    def _add_drawing_paths(self, paths: list):
        added = 0
        for path in paths:
            try:
                ProjectDrawingRepository.create(
                    project_id=self.project_id,
                    filename=os.path.basename(path),
                    file_path=os.path.abspath(path),
                    drawing_type=self._guess_drawing_type(path),
                )
                added += 1
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося додати {path}:\n{e}")
        if added:
            QMessageBox.information(self, "Успіх", f"Додано креслень: {added}")
            self._reload_all()

    @staticmethod
    def _guess_drawing_type(path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        if ext in (
            ".rvt",
            ".rfa",
            ".rte",
            ".ifc",
            ".fcstd",
            ".step",
            ".stp",
            ".sldprt",
            ".sldasm",
        ):
            return "модель"
        if "детал" in os.path.basename(path).lower():
            return "деталювання"
        return "креслення"

    def _selected_drawing(self) -> dict | None:
        row = self.drawings_table.currentRow()
        if row < 0:
            return None
        item = self.drawings_table.item(row, 0)
        drawing_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        for d in self._drawings:
            if d["id"] == drawing_id:
                return d
        return None

    _PREVIEW_IMAGES = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}

    def _set_preview_message(self, text: str) -> None:
        self._drawing_preview.setPixmap(QPixmap())
        self._drawing_preview.setText(text)

    def _update_drawing_preview(self) -> None:
        """Показати мініатюру обраного креслення (PDF/картинки) у правій панелі."""
        drawing = self._selected_drawing()
        if not drawing:
            self._set_preview_message("Оберіть креслення для перегляду")
            return
        path = drawing.get("file_path") or ""
        if not path or not os.path.exists(path):
            self._set_preview_message(f"Файл не знайдено:\n{path or '—'}")
            return
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf" and self._pdf_doc is not None:
            try:
                self._pdf_doc.load(path)
                image = self._pdf_doc.render(0, QSize(760, 1100))
                if image.isNull():
                    self._set_preview_message("Не вдалося відрендерити сторінку PDF")
                    return
                self._drawing_preview.setPixmap(QPixmap.fromImage(image))
                self._drawing_preview.setText("")
                return
            except Exception as e:  # noqa: BLE001 — попередній перегляд не критичний
                self._set_preview_message(f"Помилка перегляду PDF:\n{e}")
                return
        if ext in self._PREVIEW_IMAGES:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                self._set_preview_message("Не вдалося завантажити зображення")
                return
            self._drawing_preview.setPixmap(
                pixmap.scaled(
                    self._drawing_preview.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self._drawing_preview.setText("")
            return
        if ext == ".pdf":
            self._set_preview_message("Модуль QtPdf недоступний у цій збірці Qt")
            return
        self._set_preview_message(
            f"Попередній перегляд недоступний для {ext.upper()}\n"
            "Відкрийте файл кнопкою «📂 Відкрити»"
        )

    def _on_open_drawing(self, *_args):
        drawing = self._selected_drawing()
        if not drawing:
            QMessageBox.warning(self, "Увага", "Оберіть креслення для відкриття")
            return
        path = drawing["file_path"]
        if not os.path.exists(path):
            QMessageBox.critical(
                self,
                "Файл не знайдено",
                f"Файл не знайдено за шляхом:\n{path}\n\n"
                "Можливо, його переміщено або перейменовано.",
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _on_edit_drawing(self):
        drawing = self._selected_drawing()
        if not drawing:
            QMessageBox.warning(self, "Увага", "Оберіть креслення для редагування")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Змінити — {drawing['filename']}")
        layout = QFormLayout(dialog)
        combo_type = QComboBox()
        combo_type.addItems(["креслення", "модель", "деталювання"])
        combo_type.setCurrentText(drawing["drawing_type"])
        layout.addRow("Тип:", combo_type)
        edit_notes = QLineEdit(drawing.get("notes") or "")
        edit_notes.setPlaceholderText("Примітка (необов'язково)")
        layout.addRow("Примітка:", edit_notes)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            ProjectDrawingRepository.update(
                drawing["id"],
                drawing_type=combo_type.currentText(),
                notes=edit_notes.text().strip(),
            )
            self._reload_all()
            QMessageBox.information(self, "Успіх", "Зміни збережено")
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти зміни: {e}")

    def _on_delete_drawing(self):
        drawing = self._selected_drawing()
        if not drawing:
            QMessageBox.warning(self, "Увага", "Оберіть креслення для видалення")
            return
        reply = QMessageBox.question(
            self,
            "Видалення",
            f"Видалити посилання на «{drawing['filename']}»?\nФайл на диску не чіпатиметься.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                ProjectDrawingRepository.delete(drawing["id"])
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Посилання видалено")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити: {e}")

    def _get_selected_doc_id(self):
        idx = self.docs_table.currentIndex()
        if not idx.isValid():
            return None
        row = idx.row()
        if 0 <= row < len(self._documents):
            return self._documents[row]["id"]
        return None

    def _on_docs_table_clicked(self, index):
        if not index.isValid():
            return
        if index.column() == self.docs_model.columnCount() - 1:
            self._open_document()

    def _open_document(self):
        doc_id = self._get_selected_doc_id()
        if not doc_id:
            QMessageBox.warning(self, "Увага", "Оберіть документ")
            return
        get_doc = getattr(ProjectDocumentRepository, "get_by_id", None) or getattr(
            ProjectDocumentRepository, "get", None
        )
        if get_doc is None:
            QMessageBox.warning(self, "Увага", "Документ недоступний")
            return
        doc = get_doc(doc_id)
        if not doc:
            QMessageBox.warning(self, "Увага", "Документ не знайдено")
            return
        content = doc.get("content") or b""
        if isinstance(content, str):
            content = content.encode("utf-8")
        filename = doc.get("filename") or f"document_{doc_id}.xlsx"
        filename = Path(filename).name
        suffix = Path(filename).suffix or ".xlsx"
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix, prefix="ventcompany_doc_"
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            os.startfile(tmp_path)
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося відкрити документ: {e}")

    def _export_document(self):
        doc_id = self._get_selected_doc_id()
        if not doc_id:
            QMessageBox.warning(self, "Увага", "Виберіть документ для експорту")
            return
        doc = ProjectDocumentRepository.get_by_id(doc_id)
        if not doc:
            QMessageBox.warning(self, "Увага", "Документ не знайдено")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Зберегти документ", doc["filename"], "Excel files (*.xlsx);;All files (*.*)"
        )
        if path:
            try:
                with open(path, "wb") as f:
                    f.write(doc["content"])
                QMessageBox.information(self, "Успіх", f"Документ збережено:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти: {e}")

    def _delete_document(self):
        doc_id = self._get_selected_doc_id()
        if not doc_id:
            QMessageBox.warning(self, "Увага", "Виберіть документ для видалення")
            return
        reply = QMessageBox.question(
            self,
            "Видалення",
            "Видалити документ з бази даних?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                ProjectDocumentRepository.delete(doc_id)
                self._refresh_documents()
                QMessageBox.information(self, "Успіх", "Документ видалено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити: {e}")
