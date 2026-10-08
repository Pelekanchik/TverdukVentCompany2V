"""Діалог "Картка проєкту" — v2.4 зі знижкою на виробах.

Логіка:
  Собівартість = сума cost_price × quantity
  Ціна замовнику = сума discounted_price (якщо > 0) інакше total_price
  Роботи = сума з project_works
  Витрати = сума з project_expenses
  Прибуток = ціна (зі знижкою) − собівартість − роботи − витрати

Рефакторинг v2.10: допоміжні діалоги — у project_card_dialogs.py, документи/
креслення/PDF — у міксині project_card_docs_mixin.py. Цей файл — ядро
(життєвий цикл + вкладки інфо/вироби/роботи/витрати/оплати).
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ventilation_company.database.repositories.payment_repo import PaymentRepository
from ventilation_company.database.repositories.product_repo import ProductRepository
from ventilation_company.database.repositories.project_document_repo import (
    ProjectDocumentRepository,
)
from ventilation_company.database.repositories.project_drawing_repo import (
    ProjectDrawingRepository,
)
from ventilation_company.database.repositories.project_expense_repo import ProjectExpenseRepository
from ventilation_company.database.repositories.project_repo import ProjectRepository
from ventilation_company.database.repositories.project_work_repo import ProjectWorkRepository
from ventilation_company.gui_pyside6.material_order_dialog import (  # noqa: F401  (реекспорт: тести патчать за цим шляхом)
    MaterialOrderPreviewDialog,
)
from ventilation_company.gui_pyside6.project_card_dialogs import (  # noqa: F401
    DRAWING_FILE_FILTER,
    ComponentPickerDialog,
    DrawingsTable,
    ExpenseEditDialog,
    PaymentEditDialog,
    WorkEditDialog,
)
from ventilation_company.gui_pyside6.project_card_docs_mixin import ProjectCardDocsMixin
from ventilation_company.gui_pyside6.table_utils import setup_table
from ventilation_company.gui_pyside6.theme import Theme
from ventilation_company.gui_pyside6.workers import FunctionWorker
from ventilation_company.services.receivables import payment_summary


class ProjectCardDialog(ProjectCardDocsMixin, QDialog):
    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle(f"📁 Картка проєкту #{project_id}")
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        self.resize(1000, 700)
        self._project_data: dict = {}
        self._products: list[dict] = []
        self._documents: list[dict] = []
        self._works: list[dict] = []
        self._expenses: list[dict] = []
        self._payments: list[dict] = []
        self._drawings: list[dict] = []
        self._worker: FunctionWorker | None = None
        self._build_ui()
        self._start_load()

    # ── Асинхронне завантаження даних ──

    def _fetch_data(self) -> dict:
        """Зібрати всі дані картки проєкту (виконується у фоновому потоці).

        Не чіпає GUI-стану; у разі помилки виняток передається через worker.error.
        """
        p = ProjectRepository.get(self.project_id)
        if not p:
            return {"project": None}

        products = ProductRepository.get_all(project_id=self.project_id)
        works = ProjectWorkRepository.get_all(self.project_id)
        expenses = ProjectExpenseRepository.get_all(self.project_id)
        documents = ProjectDocumentRepository.get_by_project(self.project_id)
        drawings = ProjectDrawingRepository.get_by_project(self.project_id)
        payments = PaymentRepository.list_by_project(self.project_id)
        paid_total = sum(
            float(p.get("amount") or 0)
            for p in payments
            if (p.get("type") or "вхідний") == "вхідний"
        )

        cost = sum(
            float(item.get("cost_price") or 0) * float(item.get("quantity") or 1)
            for item in products
        )
        base_price = sum(
            (
                float(item.get("discounted_price") or 0)
                if float(item.get("discounted_price") or 0) > 0
                else float(item.get("total_price") or 0)
            )
            for item in products
        )
        works_total = sum(float(item.get("total_price") or 0) for item in works)
        plus_expenses_total = sum(
            float(item.get("total_price") or 0)
            for item in expenses
            if (item.get("direction") or "minus") == "plus"
        )
        minus_expenses_total = sum(
            float(item.get("total_price") or 0)
            for item in expenses
            if (item.get("direction") or "minus") != "plus"
        )

        project_data = dict(p)
        project_data["cost_price"] = cost
        project_data["customer_price"] = base_price
        project_data["works_total"] = works_total
        project_data["plus_expenses_total"] = plus_expenses_total
        project_data["minus_expenses_total"] = minus_expenses_total
        project_data["expenses_total"] = minus_expenses_total
        project_data["paid_total"] = paid_total
        return {
            "project": project_data,
            "products": products,
            "documents": documents,
            "drawings": drawings,
            "works": works,
            "expenses": expenses,
            "payments": payments,
        }

    def _start_load(self):
        """Запустити фонове завантаження даних картки."""
        self._set_busy(True)
        worker = FunctionWorker(self._fetch_data)
        worker.result.connect(self._on_data_loaded)
        worker.error.connect(self._on_load_error)
        # Життєвий цикл worker'а прив'язано до finished потоку (а не до result):
        # посилання знімається лише після того, як run() справді завершився,
        # інакше можливий крах "QThread: Destroyed while thread is still running".
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(self._on_worker_finished)
        self._worker = worker  # захист від збирання сміття
        worker.start()

    def _on_worker_finished(self):
        """Потік завершився — знімаємо посилання (лише якщо це поточний worker)."""
        if self._worker is self.sender():
            self._worker = None

    def _on_data_loaded(self, result: dict):
        project = result.get("project")
        if project is None:
            self._set_busy(False)
            QMessageBox.warning(self, "Увага", f"Проєкт #{self.project_id} не знайдено")
            return
        self._project_data = project
        self._products = result["products"]
        self._documents = result["documents"]
        self._drawings = result["drawings"]
        self._works = result["works"]
        self._expenses = result["expenses"]
        self._payments = result["payments"]
        # Новіші оплати — зверху (відповідність порядку рядків таблиці).
        self._payments.sort(key=lambda p: str(p.get("date") or ""), reverse=True)

        name = self._project_data.get("name", "Проєкт")
        self.setWindowTitle(f"📁 {name} (#{self.project_id})")
        if hasattr(self, "lbl_title"):
            self.lbl_title.setText(f"📁 {name}")
        self._populate_all()
        self._set_busy(False)

    def _on_load_error(self, message: str):
        self._set_busy(False)
        QMessageBox.critical(self, "Помилка", f"Не вдалося завантажити проєкт:\n{message}")

    def _set_busy(self, busy: bool):
        if busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            if hasattr(self, "lbl_title"):
                self.lbl_title.setText("⏳ Завантаження…")
        else:
            QApplication.restoreOverrideCursor()

    def _populate_all(self):
        """Оновити всі вкладки після завантаження/перезавантаження даних."""
        self._populate_info_tab()
        self._populate_products()
        self._populate_documents()
        self._populate_drawings()
        self._populate_works()
        self._populate_expenses()
        self._populate_payments()

    def _load_data(self):
        """Сумісність: синхронне завантаження (використовується лише у тестах)."""
        result = self._fetch_data()
        self._on_data_loaded(result)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        self.lbl_title = QLabel("⏳ Завантаження…")
        self.lbl_title.setObjectName("title")
        layout.addWidget(self.lbl_title)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_info_tab(), "ℹ️ Інформація")
        self.tabs.addTab(self._build_products_tab(), "🔧 Деталі")
        self.tabs.addTab(self._build_documents_tab(), "📄 Документи")
        self.tabs.addTab(self._build_drawings_tab(), "📐 Креслення")
        self.tabs.addTab(self._build_works_tab(), "🔨 Роботи")
        self.tabs.addTab(self._build_expenses_tab(), "💸 Витрати")
        self.tabs.addTab(self._build_payments_tab(), "💳 Оплати")
        layout.addWidget(self.tabs)
        btn_close = QPushButton("✅ Закрити")
        btn_close.setMinimumHeight(36)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _build_info_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        layout.setSpacing(12)
        self._info_labels: dict[str, QLabel] = {}

        def add_row(key: str, caption: str) -> QLabel:
            lbl = QLabel("—")
            layout.addRow(caption, lbl)
            self._info_labels[key] = lbl
            return lbl

        add_row("project_number", "Номер:")
        add_row("name", "Назва:")
        add_row("client", "Клієнт:")
        add_row("status", "Статус:")
        add_row("created_at", "Дата створення:")
        layout.addRow(QLabel(""))
        add_row("cost_price", "🔧 Собівартість (вироби):")
        add_row("works_total", "🔨 Додаткові роботи:")
        add_row("expenses_total", "💸 Витрати:")
        add_row("plus_expenses_total", "➕ Надходження:")
        layout.addRow(QLabel(""))
        add_row("customer_price", "💰 Ціна замовнику (з виробів):")
        add_row("discounted_price", "🏷️ Ціна зі знижкою (проєкт):")
        layout.addRow(QLabel(""))
        add_row("products_total", "Сума виробів:")
        add_row("products_count", "Кількість виробів:")
        add_row("paid_total", "💳 Оплачено:")
        add_row("balance", "💳 Залишок:")
        add_row("profit", "📊 Прибуток (комплексний):")
        self._lbl_discount_note = QLabel("")
        self._lbl_discount_note.setStyleSheet(f"color: {Theme.WARNING}; font-size: 12px;")
        layout.addRow("", self._lbl_discount_note)
        self._info_tab = tab
        self._populate_info_tab()
        return tab

    def _populate_info_tab(self):
        d = self._project_data
        if not d:
            return
        cost = d.get("cost_price", 0)
        base_price = d.get("customer_price", 0)
        discounted = d.get("discounted_price", 0)
        works_total = d.get("works_total", 0)
        plus_expenses_total = d.get("plus_expenses_total", 0)
        minus_expenses_total = d.get("minus_expenses_total", 0)
        effective = discounted if discounted > 0 else base_price
        total_customer = effective + works_total + plus_expenses_total
        display_profit = total_customer - cost - minus_expenses_total
        paid_total = float(d.get("paid_total") or 0)
        balance = total_customer - paid_total

        def set_text(key: str, text: str, style: str | None = None):
            lbl = self._info_labels.get(key)
            if lbl is None:
                return
            lbl.setText(text)
            if style:
                lbl.setStyleSheet(style)

        set_text("project_number", str(d.get("project_number", "—")))
        set_text("name", str(d.get("name", "—")))
        set_text("client", str(d.get("client", "—")))
        set_text("status", str(d.get("status", "—")))
        set_text("created_at", str(d.get("created_at") or "—"))
        set_text("cost_price", f"₴ {cost:,.2f}", f"color: {Theme.SUCCESS}; font-weight: bold;")
        set_text(
            "works_total", f"₴ {works_total:,.2f}", f"color: {Theme.ACCENT}; font-weight: bold;"
        )
        set_text(
            "expenses_total",
            f"₴ {minus_expenses_total:,.2f}",
            f"color: {Theme.WARNING}; font-weight: bold;",
        )
        set_text(
            "plus_expenses_total",
            f"₴ {plus_expenses_total:,.2f}",
            f"color: {Theme.SUCCESS}; font-weight: bold;",
        )
        set_text(
            "customer_price", f"₴ {base_price:,.2f}", f"color: {Theme.ACCENT}; font-weight: bold;"
        )
        if discounted > 0:
            set_text(
                "discounted_price",
                f"₴ {discounted:,.2f}",
                f"color: {Theme.WARNING}; font-weight: bold; font-size: 15px;",
            )
        else:
            set_text("discounted_price", "— (не вказано)", f"color: {Theme.TEXT_MUTED};")
        set_text("products_total", f"₴ {base_price:,.2f}")
        set_text("products_count", str(len(self._products)))
        set_text("paid_total", f"₴ {paid_total:,.2f}")
        set_text("balance", f"₴ {balance:,.2f}")
        if display_profit >= 0:
            margin = display_profit / total_customer * 100 if total_customer > 0 else 0.0
            set_text(
                "profit",
                f"₴ {display_profit:,.2f}  ·  маржа {margin:.1f} %  ✅",
                f"color: {Theme.SUCCESS}; font-weight: bold; font-size: 16px; "
                f"padding: 8px 16px; background: #1a3a1a; border-radius: 8px;",
            )
        else:
            set_text(
                "profit",
                f"₴ {display_profit:,.2f}  ⚠️ ЗБИТОК",
                f"color: {Theme.DANGER}; font-weight: bold; font-size: 16px; "
                f"padding: 8px 16px; background: #3a1a1a; border-radius: 8px;",
            )

        if discounted > 0 and abs(discounted - base_price) > 0.01 and base_price > 0:
            diff = discounted - base_price
            diff_pct = diff / base_price * 100
            self._lbl_discount_note.setText(f"Знижка: ₴ {diff:,.2f} ({diff_pct:.1f}% від базової)")
        else:
            self._lbl_discount_note.setText("")

    def _build_products_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.products_table = QTableView()
        setup_table(self.products_table, read_only=True)
        layout.addWidget(self.products_table)
        self.products_model = QStandardItemModel()
        # ← v2.4: додано колонку "Зі знижкою"
        self.products_model.setHorizontalHeaderLabels(
            [
                "№",
                "Назва",
                "Тип",
                "Розміри",
                "Матеріал",
                "К-ть",
                "Собіварт.",
                "Ціна",
                "Зі знижкою",
                "Сума",
            ]
        )
        self.products_table.setModel(self.products_model)
        self._populate_products()
        actions = QHBoxLayout()
        actions.addStretch()
        btn_contract = QPushButton("📑 Договір (PDF)…")
        btn_contract.setToolTip(
            "Згенерувати типовий договір на виготовлення та монтаж "
            "з реквізитами сторін і сумою проєкту"
        )
        btn_contract.clicked.connect(self._on_contract_pdf)
        actions.addWidget(btn_contract)
        btn_proposal = QPushButton("📄 КП (PDF)…")
        btn_proposal.setToolTip(
            "Згенерувати комерційну пропозицію для замовника: вироби, роботи, "
            "підсумки з ПДВ, терміни та гарантія"
        )
        btn_proposal.clicked.connect(self._on_proposal_pdf)
        actions.addWidget(btn_proposal)
        btn_proposal_xls = QPushButton("📗 КП (Excel)…")
        btn_proposal_xls.setToolTip(
            "Експорт комерційної пропозиції у Excel (зручно для редагування)"
        )
        btn_proposal_xls.clicked.connect(self._on_proposal_excel)
        actions.addWidget(btn_proposal_xls)
        btn_act = QPushButton("✅ Акт (PDF)…")
        btn_act.setToolTip(
            "Згенерувати акт виконаних робіт для підписання: перелік робіт та "
            "виробів, сума прописом, реквізити та підписи сторін"
        )
        btn_act.clicked.connect(self._on_act_pdf)
        actions.addWidget(btn_act)
        btn_invoice = QPushButton("🧾 Рахунок (PDF)…")
        btn_invoice.setToolTip(
            "Згенерувати рахунок на оплату з банківськими реквізитами " "та призначенням платежу"
        )
        btn_invoice.clicked.connect(self._on_invoice_pdf)
        actions.addWidget(btn_invoice)
        btn_materials = QPushButton("📦 Замовлення матеріалів…")
        btn_materials.setToolTip(
            "Розрахувати потребу в матеріалах за виробами проєкту "
            "(метал, ущільнювачі, кріплення, ізоляція) та зберегти заявку в Excel"
        )
        btn_materials.clicked.connect(self._on_material_order)
        actions.addWidget(btn_materials)
        layout.addLayout(actions)
        return tab

    def _populate_products(self):
        self.products_model.removeRows(0, self.products_model.rowCount())
        for i, item in enumerate(self._products, 1):
            w = item.get("width", 0) or 0
            h = item.get("height", 0) or 0
            l = item.get("length", 0) or 0
            dims = f"Ø{w:.0f} x {l:.0f}" if h == 0 else f"{w:.0f}x{h:.0f}x{l:.0f}"
            cost = item.get("cost_price", 0)
            unit = item.get("unit_price", 0)
            disc = item.get("discounted_price", 0)
            total = item.get("total_price", 0)
            qty = item.get("quantity", 1)
            # Якщо є знижка — показуємо її, інакше базову ціну
            effective_price = disc if disc > 0 else total
            row = [
                QStandardItem(str(i)),
                QStandardItem(item.get("name", "—")),
                QStandardItem(item.get("product_type", "—")),
                QStandardItem(dims),
                QStandardItem(item.get("material", "—")),
                QStandardItem(str(qty)),
                QStandardItem(f"₴ {cost:,.2f}"),
                QStandardItem(f"₴ {unit:,.2f}"),
                QStandardItem(f"₴ {disc:,.2f}" if disc > 0 else "—"),
                QStandardItem(f"₴ {effective_price:,.2f}"),
            ]
            for cell in row:
                cell.setEditable(False)
            # Числові колонки (к-ть, ціни, сума) — вирівнювання праворуч
            for cell in (row[5], row[6], row[7], row[8], row[9]):
                cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            # Зафарбовуємо знижку жовтим, якщо вона є
            if disc > 0:
                row[8].setForeground(QBrush(QColor(Theme.WARNING)))
            self.products_model.appendRow(row)

    def _build_works_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        top = QHBoxLayout()
        self._lbl_works_count = QLabel("🔨 Додаткові роботи (…)")
        self._lbl_works_count.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-size: 14px;")
        top.addWidget(self._lbl_works_count)
        top.addStretch()
        btn_add = QPushButton("➕ Додати роботу")
        btn_add.clicked.connect(self._on_add_work)
        top.addWidget(btn_add)
        layout.addLayout(top)
        self.works_table = QTableView()
        setup_table(self.works_table, read_only=True)
        layout.addWidget(self.works_table)
        self.works_model = QStandardItemModel()
        self.works_model.setHorizontalHeaderLabels(
            ["ID", "Назва", "К-ть", "Од.", "Ціна за од.", "Сума", "Дата", "Бригада", ""]
        )
        self.works_table.setModel(self.works_model)
        self.works_table.setColumnWidth(0, 40)
        self.works_table.setColumnWidth(1, 200)
        self.works_table.setColumnWidth(2, 60)
        self.works_table.setColumnWidth(3, 60)
        self.works_table.setColumnWidth(4, 100)
        self.works_table.setColumnWidth(5, 100)
        self.works_table.setColumnWidth(6, 90)
        self.works_table.setColumnWidth(7, 120)
        self.works_table.setColumnWidth(8, 40)
        self._populate_works()
        actions = QHBoxLayout()
        actions.addStretch()
        btn_edit = QPushButton("✏️ Редагувати")
        btn_edit.clicked.connect(self._on_edit_work)
        actions.addWidget(btn_edit)
        btn_del = QPushButton("🗑️ Видалити")
        btn_del.setStyleSheet(f"color: {Theme.DANGER};")
        btn_del.clicked.connect(self._on_delete_work)
        actions.addWidget(btn_del)
        layout.addLayout(actions)
        return tab

    def _populate_works(self):
        self._lbl_works_count.setText(f"🔨 Додаткові роботи ({len(self._works)})")
        self.works_model.removeRows(0, self.works_model.rowCount())
        for w in self._works:
            row = [
                QStandardItem(str(w["id"])),
                QStandardItem(w["work_name"]),
                QStandardItem(f"{w['quantity']:,.2f}"),
                QStandardItem(w["unit"]),
                QStandardItem(f"₴ {w['unit_price']:,.2f}"),
                QStandardItem(f"₴ {w['total_price']:,.2f}"),
                QStandardItem(str(w.get("work_date") or "")),
                QStandardItem(str(w.get("crew") or "")),
                QStandardItem(""),
            ]
            for cell in row:
                cell.setEditable(False)
            # К-ть, ціна, сума — праворуч
            for cell in (row[2], row[4], row[5]):
                cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.works_model.appendRow(row)

    def _on_add_work(self):
        dlg = WorkEditDialog(self.project_id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data["work_name"]:
                QMessageBox.warning(self, "Помилка", "Введіть назву роботи")
                return
            try:
                ProjectWorkRepository.create(data)
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Роботу додано!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося додати: {e}")

    def _on_edit_work(self):
        idx = self.works_table.currentIndex()
        if not idx.isValid():
            QMessageBox.warning(self, "Увага", "Виберіть роботу для редагування")
            return
        row = idx.row()
        if row < 0 or row >= len(self._works):
            return
        dlg = WorkEditDialog(self.project_id, self._works[row], parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                ProjectWorkRepository.update(self._works[row]["id"], data)
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Роботу оновлено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося оновити: {e}")

    def _on_delete_work(self):
        idx = self.works_table.currentIndex()
        if not idx.isValid():
            QMessageBox.warning(self, "Увага", "Виберіть роботу для видалення")
            return
        row = idx.row()
        if row < 0 or row >= len(self._works):
            return
        reply = QMessageBox.question(
            self,
            "Видалення",
            "Видалити роботу?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                ProjectWorkRepository.delete(self._works[row]["id"])
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Роботу видалено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити: {e}")

    def _build_expenses_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        top = QHBoxLayout()
        self._lbl_expenses_count = QLabel("💸 Витрати / надходження (…)")
        self._lbl_expenses_count.setStyleSheet(f"color: {Theme.TEXT_BRIGHT}; font-size: 14px;")
        top.addWidget(self._lbl_expenses_count)
        top.addStretch()
        btn_add = QPushButton("➕ Додати витрату")
        btn_add.clicked.connect(self._on_add_expense)
        top.addWidget(btn_add)
        btn_components = QPushButton("🔩 Комплектуючі…")
        btn_components.setToolTip(
            "Додати комплектуючу з бізнес-налаштувань (вентилятор, фільтр, клапан…)"
        )
        btn_components.clicked.connect(self._on_add_component)
        top.addWidget(btn_components)
        layout.addLayout(top)
        self.expenses_table = QTableView()
        setup_table(self.expenses_table, read_only=True)
        layout.addWidget(self.expenses_table)
        self.expenses_model = QStandardItemModel()
        self.expenses_model.setHorizontalHeaderLabels(
            ["ID", "Тип", "Назва", "К-ть", "Од.", "Ціна за од.", "Сума", ""]
        )
        self.expenses_table.setModel(self.expenses_model)
        self.expenses_table.setColumnWidth(0, 40)
        self.expenses_table.setColumnWidth(1, 200)
        self.expenses_table.setColumnWidth(2, 60)
        self.expenses_table.setColumnWidth(3, 60)
        self.expenses_table.setColumnWidth(4, 100)
        self.expenses_table.setColumnWidth(5, 100)
        self.expenses_table.setColumnWidth(6, 80)
        self._populate_expenses()
        actions = QHBoxLayout()
        actions.addStretch()
        btn_edit = QPushButton("✏️ Редагувати")
        btn_edit.clicked.connect(self._on_edit_expense)
        actions.addWidget(btn_edit)
        btn_del = QPushButton("🗑️ Видалити")
        btn_del.setStyleSheet(f"color: {Theme.DANGER};")
        btn_del.clicked.connect(self._on_delete_expense)
        actions.addWidget(btn_del)
        layout.addLayout(actions)
        return tab

    def _populate_expenses(self):
        self._lbl_expenses_count.setText(f"💸 Витрати / надходження ({len(self._expenses)})")
        self.expenses_model.removeRows(0, self.expenses_model.rowCount())
        for e in self._expenses:
            direction = e.get("direction") or "minus"
            direction_label = "➕ Плюс" if direction == "plus" else "➖ Витрата"
            row = [
                QStandardItem(str(e["id"])),
                QStandardItem(direction_label),
                QStandardItem(e["expense_name"]),
                QStandardItem(f"{e['quantity']:,.2f}"),
                QStandardItem(e["unit"]),
                QStandardItem(f"₴ {e['unit_price']:,.2f}"),
                QStandardItem(f"₴ {e['total_price']:,.2f}"),
                QStandardItem(""),
            ]
            for cell in row:
                cell.setEditable(False)
            # К-ть, ціна, сума — праворуч
            for cell in (row[3], row[5], row[6]):
                cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.expenses_model.appendRow(row)

    def _on_add_expense(self):
        dlg = ExpenseEditDialog(self.project_id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data["expense_name"]:
                QMessageBox.warning(self, "Помилка", "Введіть назву витрати")
                return
            try:
                ProjectExpenseRepository.create(data)
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Витрату додано!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося додати: {e}")

    def _on_add_component(self):
        dlg = ComponentPickerDialog(self.project_id, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data:
            QMessageBox.warning(self, "Увага", "Оберіть комплектуючу зі списку")
            return
        try:
            ProjectExpenseRepository.create(data)
            self._reload_all()
            QMessageBox.information(
                self, "Успіх", f"Додано: {data['expense_name']} × {data['quantity']:g}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося додати: {e}")

    def _on_edit_expense(self):
        idx = self.expenses_table.currentIndex()
        if not idx.isValid():
            QMessageBox.warning(self, "Увага", "Виберіть витрату для редагування")
            return
        row = idx.row()
        if row < 0 or row >= len(self._expenses):
            return
        dlg = ExpenseEditDialog(self.project_id, self._expenses[row], parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                ProjectExpenseRepository.update(self._expenses[row]["id"], data)
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Витрату оновлено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося оновити: {e}")

    def _on_delete_expense(self):
        idx = self.expenses_table.currentIndex()
        if not idx.isValid():
            QMessageBox.warning(self, "Увага", "Виберіть витрату для видалення")
            return
        row = idx.row()
        if row < 0 or row >= len(self._expenses):
            return
        reply = QMessageBox.question(
            self,
            "Видалення",
            "Видалити витрату?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                ProjectExpenseRepository.delete(self._expenses[row]["id"])
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Витрату видалено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити: {e}")

    def _build_payments_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # ── Підсумок по оплатах ──
        summary = QGroupBox("Підсумок по оплатах")
        sgrid = QGridLayout(summary)
        sgrid.addWidget(QLabel("Вартість проєкту:"), 0, 0)
        self.lbl_pay_price = QLabel("—")
        self.lbl_pay_price.setStyleSheet("font-weight: bold;")
        sgrid.addWidget(self.lbl_pay_price, 0, 1)
        sgrid.addWidget(QLabel("Сплачено:"), 0, 2)
        self.lbl_pay_paid = QLabel("—")
        self.lbl_pay_paid.setStyleSheet("font-weight: bold;")
        sgrid.addWidget(self.lbl_pay_paid, 0, 3)
        sgrid.addWidget(QLabel("Залишок:"), 1, 0)
        self.lbl_pay_left = QLabel("—")
        self.lbl_pay_left.setStyleSheet("font-weight: bold;")
        sgrid.addWidget(self.lbl_pay_left, 1, 1)
        sgrid.addWidget(QLabel("Оплачено:"), 1, 2)
        self.lbl_pay_percent = QLabel("—")
        self.lbl_pay_percent.setStyleSheet("font-weight: bold;")
        sgrid.addWidget(self.lbl_pay_percent, 1, 3)
        self.progress_pay = QProgressBar()
        self.progress_pay.setRange(0, 100)
        sgrid.addWidget(self.progress_pay, 2, 0, 1, 4)
        layout.addWidget(summary)

        top = QHBoxLayout()
        btn_add = QPushButton("➕ Додати оплату")
        btn_add.clicked.connect(self._on_add_payment)
        top.addWidget(btn_add)
        top.addStretch()
        layout.addLayout(top)
        self.payments_table = QTableWidget()
        self.payments_table.setColumnCount(5)
        self.payments_table.setHorizontalHeaderLabels(
            ["Дата", "Тип", "Сума", "Призначення", "Нотатки"]
        )
        setup_table(self.payments_table, select_rows=True, read_only=True)
        layout.addWidget(self.payments_table)
        self._populate_payments()
        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_edit = QPushButton("✏️ Редагувати")
        btn_edit.clicked.connect(self._on_edit_payment)
        bottom.addWidget(btn_edit)
        btn_delete = QPushButton("🗑 Видалити")
        btn_delete.setStyleSheet(f"color: {Theme.DANGER};")
        btn_delete.clicked.connect(self._on_delete_payment)
        bottom.addWidget(btn_delete)
        layout.addLayout(bottom)
        return tab

    def _update_payments_summary(self):
        """Оновити панель підсумку оплат (вартість/сплачено/залишок/%)."""
        if not hasattr(self, "lbl_pay_price"):
            return
        d = self._project_data or {}
        base = float(d.get("customer_price") or 0)
        discounted = float(d.get("discounted_price") or 0)
        effective = discounted if discounted > 0 else base
        total_customer = (
            effective + float(d.get("works_total") or 0) + float(d.get("plus_expenses_total") or 0)
        )
        s = payment_summary(getattr(self, "_payments", []), total_customer)

        self.lbl_pay_price.setText(f"₴ {total_customer:,.2f}")
        self.lbl_pay_paid.setText(f"₴ {s['paid']:,.2f}")
        if s["overpaid"]:
            self.lbl_pay_left.setText(f"Переплата ₴ {-s['balance']:,.2f}")
            self.lbl_pay_left.setStyleSheet(f"color: {Theme.ACCENT}; font-weight: bold;")
        else:
            self.lbl_pay_left.setText(f"₴ {s['balance']:,.2f}")
            self.lbl_pay_left.setStyleSheet(
                f"color: {Theme.SUCCESS if s['balance'] <= 0 else Theme.DANGER}; font-weight: bold;"
            )
        self.lbl_pay_percent.setText(f"{s['percent']:.0f} %")
        self.progress_pay.setValue(int(s["percent"]))
        if s["overpaid"] or (s["balance"] <= 0 and total_customer > 0):
            color, label = Theme.SUCCESS, "Оплачено повністю"
        elif s["paid"] > 0:
            color, label = Theme.WARNING, "Частково оплачено"
        else:
            color, label = Theme.DANGER, "Не оплачено"
        self.progress_pay.setStyleSheet(
            f"QProgressBar::chunk {{ background-color: {color}; }}"
            "QProgressBar { text-align: center; }"
        )
        self.progress_pay.setFormat(label + " — %p%")

    def _populate_payments(self):
        self.payments_table.setRowCount(0)
        # self._payments відсортовано за датою (новіші — зверху) при завантаженні.
        for p in getattr(self, "_payments", []):
            row = self.payments_table.rowCount()
            self.payments_table.insertRow(row)
            values = [
                str(p.get("date"))[:10] if p.get("date") else "",
                p.get("type") or "",
                f"₴ {float(p.get('amount') or 0):,.2f}",
                p.get("purpose") or "",
                p.get("notes") or "",
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if col == 2:  # сума — праворуч
                    cell.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.payments_table.setItem(row, col, cell)
        self._update_payments_summary()

    def _get_selected_payment(self):
        row = self.payments_table.currentRow()
        if row < 0 or row >= len(getattr(self, "_payments", [])):
            QMessageBox.warning(self, "Увага", "Оберіть оплату")
            return None
        return self._payments[row]

    def _on_add_payment(self):
        dlg = PaymentEditDialog(self.project_id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                PaymentRepository.create(dlg.get_data())
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Оплату додано")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося додати оплату: {e}")

    def _on_edit_payment(self):
        payment = self._get_selected_payment()
        if not payment:
            return
        dlg = PaymentEditDialog(self.project_id, payment, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                PaymentRepository.update(payment["id"], dlg.get_data())
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Оплату оновлено")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося оновити оплату: {e}")

    def _on_delete_payment(self):
        payment = self._get_selected_payment()
        if not payment:
            return
        reply = QMessageBox.question(
            self,
            "Видалення",
            "Видалити обрану оплату?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                PaymentRepository.delete(payment["id"])
                self._reload_all()
                QMessageBox.information(self, "Успіх", "Оплату видалено")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити оплату: {e}")

    def _reload_all(self):
        """Перезавантажити дані картки у фоновому потоці та оновити вкладки."""
        self._start_load()
