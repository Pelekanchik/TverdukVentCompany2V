"""Вкладка "Заявка на матеріали" — формування та експорт заявки для постачальника."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

from ventilation_company.material_order import (
    MaterialItem,
    MaterialOrder,
    MaterialCalculator,
    calculate_material_order,
    export_material_order_to_excel,
)


class MaterialOrderTab:
    """Вкладка формування заявки на матеріали."""

    def __init__(self, parent: ttk.Notebook, get_products_callback, get_project_info_callback=None):
        self.frame = ttk.Frame(parent)
        self.get_products = get_products_callback
        self.get_project_info = get_project_info_callback

        self.current_order = None

        self._build_ui()

    def _build_ui(self):
        # ── Верхня панель ──
        top = ttk.Frame(self.frame, padding=5)
        top.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(top, text="📦 ЗАЯВКА НА МАТЕРІАЛИ", font=("Arial", 14, "bold")).pack(side=tk.LEFT)

        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=15)

        ttk.Button(top, text="📊 Розрахувати потребу", command=self._calculate
                   ).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="📥 Експорт Excel", command=self._export_excel
                   ).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="📄 Експорт PDF", command=self._export_pdf
                   ).pack(side=tk.LEFT, padx=2)

        # ── Параметри ──
        params = ttk.LabelFrame(self.frame, text="Параметри заявки", padding=5)
        params.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(params, text="Назва проєкту:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.project_var = tk.StringVar(value="Проєкт")
        ttk.Entry(params, textvariable=self.project_var, width=40).grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(params, text="Примітки:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.notes_var = tk.StringVar(value="")
        ttk.Entry(params, textvariable=self.notes_var, width=60).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        # ── Таблиця матеріалів ──
        table_frame = ttk.LabelFrame(self.frame, text="Перелік матеріалів", padding=5)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Кнопки CRUD над таблицею (grid в table_frame)
        crud_frame = ttk.Frame(table_frame)
        crud_frame.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=(0, 5))
        ttk.Button(crud_frame, text="➕ Додати", command=self._add_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(crud_frame, text="✏️ Редагувати", command=self._edit_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(crud_frame, text="🗑️ Видалити", command=self._delete_item).pack(side=tk.LEFT, padx=2)

        cols = ("№", "Категорія", "Найменування", "Специфікація", "Од. вим.", "Кількість", "Ціна", "Сума", "Примітки")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=18)

        widths = [5, 15, 25, 22, 10, 12, 12, 12, 20]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w * 8, anchor=tk.CENTER if col not in ("Найменування", "Специфікація", "Примітки") else tk.W)

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")
        table_frame.grid_rowconfigure(1, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # ── Підсумок ──
        self.summary_frame = ttk.LabelFrame(self.frame, text="Підсумок", padding=5)
        self.summary_frame.pack(fill=tk.X, padx=5, pady=2)

        self.summary_labels = {}
        summary_fields = [
            ("total_items", "Позицій:"),
            ("total_cost", "Загальна сума:"),
            ("metal", "Листовий метал:"),
            ("gasket", "Ущільнювачі:"),
            ("fasteners", "Кріплення:"),
            ("insulation", "Ізоляція:"),
            ("components", "Комплектуючі:"),
        ]
        for i, (key, text) in enumerate(summary_fields):
            ttk.Label(self.summary_frame, text=text, font=("Arial", 9)).grid(row=0, column=i * 2, padx=5)
            lbl = ttk.Label(self.summary_frame, text="—", font=("Arial", 9, "bold"))
            lbl.grid(row=0, column=i * 2 + 1, padx=5)
            self.summary_labels[key] = lbl

        # ── Підказка ──
        hint = ttk.Label(
            self.frame,
            text="💡 Натисніть «Розрахувати потребу» щоб сформувати заявку на основі виробів проєкту, або додайте матеріали вручну. Потім експортуйте в Excel для постачальника.",
            foreground="#666", font=("Arial", 8)
        )
        hint.pack(anchor=tk.W, padx=5, pady=2)

    # ── CRUD методи ──

    def _add_item(self):
        """Діалог додавання матеріалу."""
        self._item_dialog()

    def _edit_item(self):
        """Діалог редагування матеріалу."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Увага", "Оберіть матеріал для редагування.")
            return
        idx = self.tree.index(sel[0])
        if self.current_order and 0 <= idx < len(self.current_order.items):
            self._item_dialog(self.current_order.items[idx], idx)

    def _delete_item(self):
        """Видалити вибраний матеріал."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Увага", "Оберіть матеріал для видалення.")
            return
        idx = self.tree.index(sel[0])
        if self.current_order and 0 <= idx < len(self.current_order.items):
            if messagebox.askyesno("Підтвердження", f'Видалити "{self.current_order.items[idx].name}"?'):
                self.current_order.items.pop(idx)
                self._update_table()
                self._update_summary()

    def _item_dialog(self, item=None, index=None):
        """Універсальний діалог додавання/редагування матеріалу."""
        title = "Редагувати матеріал" if item else "Додати матеріал"
        dlg = tk.Toplevel(self.frame)
        dlg.title(title)
        dlg.geometry("450x380")
        dlg.transient(self.frame)
        dlg.grab_set()

        frm = ttk.Frame(dlg, padding=15)
        frm.pack(fill=tk.BOTH, expand=True)

        # Поля
        ttk.Label(frm, text="Категорія *").grid(row=0, column=0, sticky=tk.W, pady=5)
        cat_var = tk.StringVar(value=item.category if item else "Листовий метал")
        ttk.Combobox(frm, values=["Листовий метал", "Ущільнювачі", "Кріплення", "Ізоляція", "Комплектуючі", "Розхідні матеріали"],
                     textvariable=cat_var, state="readonly", width=30).grid(row=0, column=1, sticky=tk.W, pady=5)

        ttk.Label(frm, text="Найменування *").grid(row=1, column=0, sticky=tk.W, pady=5)
        name_var = tk.StringVar(value=item.name if item else "")
        ttk.Entry(frm, textvariable=name_var, width=32).grid(row=1, column=1, sticky=tk.W, pady=5)

        ttk.Label(frm, text="Специфікація").grid(row=2, column=0, sticky=tk.W, pady=5)
        spec_var = tk.StringVar(value=item.specification if item else "")
        ttk.Entry(frm, textvariable=spec_var, width=32).grid(row=2, column=1, sticky=tk.W, pady=5)

        ttk.Label(frm, text="Од. вим. *").grid(row=3, column=0, sticky=tk.W, pady=5)
        unit_var = tk.StringVar(value=item.unit if item else "шт")
        ttk.Entry(frm, textvariable=unit_var, width=10).grid(row=3, column=1, sticky=tk.W, pady=5)

        ttk.Label(frm, text="Кількість *").grid(row=4, column=0, sticky=tk.W, pady=5)
        qty_var = tk.StringVar(value=str(item.quantity if item else 1))
        ttk.Entry(frm, textvariable=qty_var, width=10).grid(row=4, column=1, sticky=tk.W, pady=5)

        ttk.Label(frm, text="Ціна за од.").grid(row=5, column=0, sticky=tk.W, pady=5)
        price_var = tk.StringVar(value=str(item.price_per_unit if item else 0))
        ttk.Entry(frm, textvariable=price_var, width=10).grid(row=5, column=1, sticky=tk.W, pady=5)

        ttk.Label(frm, text="Примітки").grid(row=6, column=0, sticky=tk.W, pady=5)
        notes_var = tk.StringVar(value=item.notes if item else "")
        ttk.Entry(frm, textvariable=notes_var, width=32).grid(row=6, column=1, sticky=tk.W, pady=5)

        status = ttk.Label(frm, text="", foreground="#ef4444")
        status.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=5)

        def save():
            try:
                cat = cat_var.get().strip()
                name = name_var.get().strip()
                unit = unit_var.get().strip()
                qty = float(qty_var.get() or 0)
                price = float(price_var.get() or 0)
                if not cat or not name or not unit:
                    status.config(text="⚠️ Заповніть обов'язкові поля", foreground="#f59e0b")
                    return
                new_item = MaterialItem(
                    category=cat,
                    name=name,
                    specification=spec_var.get().strip(),
                    unit=unit,
                    quantity=qty,
                    price_per_unit=price,
                    notes=notes_var.get().strip(),
                )
                if self.current_order is None:
                    self.current_order = MaterialOrder(
                        project_name=self.project_var.get(),
                        items=[new_item],
                    )
                elif item is not None and index is not None:
                    self.current_order.items[index] = new_item
                else:
                    self.current_order.items.append(new_item)
                self._update_table()
                self._update_summary()
                dlg.destroy()
            except ValueError:
                status.config(text="❌ Кількість і ціна мають бути числами", foreground="#ef4444")

        ttk.Button(frm, text="💾 Зберегти", command=save).grid(row=8, column=0, columnspan=2, pady=10)

    def _calculate(self):
        """Розрахувати потребу в матеріалах."""
        products = self.get_products()
        if not products:
            messagebox.showwarning("Увага", "У проєкті немає виробів для розрахунку.")
            return

        project_name = self.project_var.get()
        if self.get_project_info:
            info = self.get_project_info()
            if info and info.get("name"):
                project_name = info["name"]

        try:
            self.current_order = calculate_material_order(products, project_name)
            self.current_order.notes = self.notes_var.get()
            self._update_table()
            self._update_summary()
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Помилка розрахунку", str(e))

    def _update_table(self):
        """Оновити таблицю матеріалів."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.current_order:
            return

        for i, item in enumerate(self.current_order.items, 1):
            self.tree.insert("", tk.END, values=(
                i,
                item.category,
                item.name,
                item.specification,
                item.unit,
                f"{item.quantity:.1f}" if item.quantity != int(item.quantity) else str(int(item.quantity)),
                f"{item.price_per_unit:.2f}" if item.price_per_unit > 0 else "—",
                f"{item.total_price:.2f}" if item.total_price > 0 else "—",
                item.notes,
            ))

    def _update_summary(self):
        """Оновити підсумкові дані."""
        if not self.current_order:
            return

        self.summary_labels["total_items"].config(text=str(self.current_order.total_items))
        self.summary_labels["total_cost"].config(text=f"{self.current_order.total_cost:,.2f} грн")

        cats = {
            "metal": "Листовий метал",
            "gasket": "Ущільнювачі",
            "fasteners": "Кріплення",
            "insulation": "Ізоляція",
            "components": "Комплектуючі",
        }
        for key, cat_name in cats.items():
            items = self.current_order.get_by_category(cat_name)
            total = sum(i.total_price for i in items)
            self.summary_labels[key].config(text=f"{total:,.2f} грн")

    def _export_excel(self):
        """Експортувати заявку в Excel."""
        if not self.current_order:
            messagebox.showwarning("Увага", "Спочатку розрахуйте потребу або додайте матеріали.")
            return

        fpath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel файли", "*.xlsx"), ("Всі файли", "*.*")],
            title="Зберегти заявку на матеріали",
            initialfile=f"Заявка_матеріали_{datetime.now().strftime('%d%m%Y')}.xlsx",
        )
        if not fpath:
            return

        try:
            export_material_order_to_excel(self.current_order, fpath)
            messagebox.showinfo("Готово", f"Заявку збережено:\n{fpath}")
        except Exception as e:
            messagebox.showerror("Помилка експорту", str(e))

    def _export_pdf(self):
        """Експортувати заявку в PDF (через Excel → PDF або fpdf2)."""
        if not self.current_order:
            messagebox.showwarning("Увага", "Спочатку розрахуйте потребу або додайте матеріали.")
            return

        fpath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF файли", "*.pdf"), ("Всі файли", "*.*")],
            title="Зберегти заявку на матеріали (PDF)",
            initialfile=f"Заявка_матеріали_{datetime.now().strftime('%d%m%Y')}.pdf",
        )
        if not fpath:
            return

        try:
            # Спочатку створимо тимчасовий Excel, потім конвертуємо через fpdf2
            from ventilation_company.pdf_generator import PDFGenerator
            pdf = PDFGenerator()
            pdf.add_page()
            pdf.set_font("DejaVu", "B", 16)
            pdf.cell(0, 10, f"ЗАЯВКА НА МАТЕРІАЛИ — {self.current_order.project_name}", ln=True, align="C")
            pdf.set_font("DejaVu", "", 10)
            pdf.cell(0, 8, f"Дата: {self.current_order.order_date.strftime('%d.%m.%Y %H:%M')}", ln=True, align="C")
            pdf.ln(5)

            # Заголовки
            pdf.set_fill_color(44, 62, 80)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("DejaVu", "B", 9)
            headers = ["№", "Категорія", "Найменування", "Специф.", "Од.", "К-ть", "Ціна", "Сума"]
            col_widths = [10, 30, 45, 40, 15, 18, 20, 22]
            for w, h in zip(col_widths, headers):
                pdf.cell(w, 8, h, border=1, fill=True, align="C")
            pdf.ln()

            # Дані
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("DejaVu", "", 8)
            for i, item in enumerate(self.current_order.items, 1):
                pdf.cell(10, 7, str(i), border=1, align="C")
                pdf.cell(30, 7, item.category, border=1)
                pdf.cell(45, 7, item.name, border=1)
                pdf.cell(40, 7, item.specification[:20], border=1)
                pdf.cell(15, 7, item.unit, border=1, align="C")
                qty_str = f"{item.quantity:.1f}" if item.quantity != int(item.quantity) else str(int(item.quantity))
                pdf.cell(18, 7, qty_str, border=1, align="R")
                price_str = f"{item.price_per_unit:.2f}" if item.price_per_unit > 0 else "—"
                pdf.cell(20, 7, price_str, border=1, align="R")
                total_str = f"{item.total_price:.2f}" if item.total_price > 0 else "—"
                pdf.cell(22, 7, total_str, border=1, align="R")
                pdf.ln()

            # Підсумок
            pdf.set_font("DejaVu", "B", 10)
            pdf.cell(178, 10, f"ЗАГАЛЬНА СУМА: {self.current_order.total_cost:,.2f} грн", border=1, align="R")
            pdf.ln()

            pdf.output(fpath)
            messagebox.showinfo("Готово", f"PDF збережено:\n{fpath}")
        except Exception as e:
            messagebox.showerror("Помилка експорту", str(e))
