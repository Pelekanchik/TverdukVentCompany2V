"""Вкладка "Документи" — генерація бухгалтерських документів."""

import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from ventilation_company.documents import (
    Invoice,
    DeliveryNote,
    WorkAct,
    CompanyInfo,
    DEFAULT_COMPANY,
)
from ventilation_company.gui.price_list_tab.models import PriceListManager
from ventilation_company.utils.logging_config import get_logger

_logger = get_logger("documents_tab")


class DocumentsTab:
    """Вкладка для генерації документів."""

    DOC_TYPES = {
        "Рахунок-фактура": "invoice",
        "Товарна накладна": "delivery_note",
        "Акт виконаних робіт": "act",
    }

    def __init__(self, parent: ttk.Notebook):
        self.frame = ttk.Frame(parent)
        self.company = DEFAULT_COMPANY
        self._build_ui()

    def _build_ui(self):
        # ── Заголовок ──────────────────────────────────────────
        header = ttk.Frame(self.frame, padding=10)
        header.pack(fill=tk.X)
        ttk.Label(header, text="📄 Документи", font=("Arial", 14, "bold")).pack(side=tk.LEFT)

        # ── Тип документа ─────────────────────────────────────
        type_frame = ttk.LabelFrame(self.frame, text="Тип документа", padding=10)
        type_frame.pack(fill=tk.X, padx=10, pady=5)

        self.doc_type_var = tk.StringVar(value="Рахунок-фактура")
        for name in self.DOC_TYPES:
            ttk.Radiobutton(
                type_frame, text=name, variable=self.doc_type_var, value=name
            ).pack(side=tk.LEFT, padx=10)

        # ── Реквізити клієнта ──────────────────────────────────
        client_frame = ttk.LabelFrame(self.frame, text="Реквізити замовника", padding=10)
        client_frame.pack(fill=tk.X, padx=10, pady=5)

        self.client_vars = {}
        fields = [
            ("name", "Назва *", 40),
            ("edrpou", "ЄДРПОУ *", 15),
            ("address", "Адреса", 40),
            ("phone", "Телефон", 20),
            ("director", "ПІБ директора", 30),
            ("bank_account", "Р/р", 40),
        ]
        for i, (key, label, width) in enumerate(fields):
            row = i // 2
            col = (i % 2) * 2
            ttk.Label(client_frame, text=f"{label}:").grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
            var = tk.StringVar()
            self.client_vars[key] = var
            ttk.Entry(client_frame, textvariable=var, width=width).grid(row=row, column=col + 1, sticky=tk.W, padx=5, pady=2)

        # ── Товари / послуги ───────────────────────────────────
        items_frame = ttk.LabelFrame(self.frame, text="Позиції", padding=10)
        items_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Кнопки
        btn_frame = ttk.Frame(items_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(btn_frame, text="➕ Додати позицію", command=self._add_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑️ Видалити", command=self._remove_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📥 З прайсу", command=self._load_from_price_list).pack(side=tk.LEFT, padx=2)

        # Таблиця
        self.tree = ttk.Treeview(
            items_frame,
            columns=("name", "unit", "qty", "price", "total"),
            show="headings",
            height=8,
        )
        self.tree.heading("name", text="Найменування")
        self.tree.heading("unit", text="Од.")
        self.tree.heading("qty", text="К-ть")
        self.tree.heading("price", text="Ціна")
        self.tree.heading("total", text="Сума")
        self.tree.column("name", width=250)
        self.tree.column("unit", width=50)
        self.tree.column("qty", width=60)
        self.tree.column("price", width=80)
        self.tree.column("total", width=80)

        vsb = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # ── Кнопка генерації ───────────────────────────────────
        gen_frame = ttk.Frame(self.frame, padding=10)
        gen_frame.pack(fill=tk.X)
        ttk.Button(
            gen_frame,
            text="📄 Згенерувати PDF",
            command=self._generate_document,
        ).pack(side=tk.RIGHT, padx=5)

    def _add_item(self):
        """Додати позицію вручну."""
        dialog = tk.Toplevel(self.frame)
        dialog.title("Додати позицію")
        dialog.geometry("350x200")
        dialog.transient(self.frame)
        dialog.grab_set()

        vars_dict = {
            "name": tk.StringVar(),
            "unit": tk.StringVar(value="шт"),
            "qty": tk.StringVar(value="1"),
            "price": tk.StringVar(value="0"),
        }

        ttk.Label(dialog, text="Назва:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(dialog, textvariable=vars_dict["name"], width=30).grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(dialog, text="Од.:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(dialog, textvariable=vars_dict["unit"], width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(dialog, text="К-ть:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(dialog, textvariable=vars_dict["qty"], width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(dialog, text="Ціна:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(dialog, textvariable=vars_dict["price"], width=10).grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)

        def save():
            try:
                name = vars_dict["name"].get().strip()
                qty = float(vars_dict["qty"].get() or 1)
                price = float(vars_dict["price"].get() or 0)
                if not name:
                    return
                total = qty * price
                self.tree.insert("", tk.END, values=(name, vars_dict["unit"].get(), qty, f"{price:.2f}", f"{total:.2f}"))
                dialog.destroy()
            except ValueError:
                pass

        ttk.Button(dialog, text="Зберегти", command=save).grid(row=4, column=0, columnspan=2, pady=10)

    def _remove_item(self):
        """Видалити вибрану позицію."""
        selected = self.tree.selection()
        if selected:
            self.tree.delete(selected[0])

    def _load_from_price_list(self):
        """Завантажити позиції з прайс-листа."""
        try:
            manager = PriceListManager()
            for item in manager.get_customer_view():
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        item.name,
                        item.unit,
                        item.quantity,
                        f"{float(item.unit_price):.2f}",
                        f"{float(item.total_price):.2f}",
                    ),
                )
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося завантажити прайс: {e}")

    def _generate_document(self):
        """Згенерувати PDF-документ."""
        # Валідація клієнта
        client_data = {k: v.get().strip() for k, v in self.client_vars.items()}
        client = CompanyInfo(**client_data)
        errors = client.validate()
        if errors:
            messagebox.showwarning("Увага", f"Заповніть обов'язкові поля:\n" + "\n".join(f"  • {e}" for e in errors))
            return

        # Зібрати позиції
        items = []
        for child in self.tree.get_children():
            vals = self.tree.item(child)["values"]
            items.append({
                "name": vals[0],
                "unit": vals[1],
                "qty": float(vals[2]),
                "price": float(vals[3]),
                "total": float(vals[4]),
            })

        if not items:
            messagebox.showwarning("Увага", "Додайте хоча б одну позицію")
            return

        # Вибір шляху
        doc_type = self.DOC_TYPES.get(self.doc_type_var.get(), "invoice")
        default_name = f"{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=default_name,
        )
        if not filepath:
            return

        try:
            if doc_type == "invoice":
                doc = Invoice(self.company, client)
            elif doc_type == "delivery_note":
                doc = DeliveryNote(self.company, client)
            else:
                doc = WorkAct(self.company, client)

            doc.build(items, filepath)
            _logger.info("Документ згенеровано: %s", filepath)
            messagebox.showinfo("Успіх", f"Документ збережено:\n{filepath}")

            # Відкрити в браузері / переглядачі
            import platform
            if platform.system() == "Windows":
                os.startfile(filepath)
            else:
                import subprocess
                subprocess.run(["xdg-open", filepath])

        except Exception as e:
            _logger.error("Помилка генерації документа: %s", e)
            messagebox.showerror("Помилка", str(e))
