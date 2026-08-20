"""🏷️ Вкладка "Прайс-лист" — повноцінний модуль ціноутворення.

Можливості:
  • CRUD для позицій прайсу (власні вироби + перепродаж + послуги)
  • Два прайси: внутрішній (повний) та замовника (публічний)
  • Експорт у PDF, Excel, CSV, HTML
  • Автосинхронізація з вкладкою "Вироби" та "Архів проєктів"
  • Категорії: власне виробництво, перепродаж, монтаж, послуга
"""

from __future__ import annotations

import csv
import io
import json
import os
import tkinter as tk
import zipfile
from collections.abc import Callable
from dataclasses import asdict, dataclass, field

from ventilation_company.gui.price_list_tab.models import PriceItem, PriceListManager
from ventilation_company.gui.price_list_tab.exporter import PriceListExporter

from datetime import datetime
from tkinter import filedialog, messagebox, ttk

# Спробуємо імпортувати openpyxl для Excel
HAVE_OPENPYXL = False
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    HAVE_OPENPYXL = True
except ImportError:
    pass

# Спробуємо імпортувати reportlab для PDF
HAVE_REPORTLAB = False
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    HAVE_REPORTLAB = True
except ImportError:
    pass


PRICE_LIST_FILE = "data/price_list.json"
ARCHIVE_DIR = "data/archive"


class PriceListTab:
    """Вкладка прайс-листа."""

    CATEGORIES = ["власне виробництво", "перепродаж", "монтаж", "послуга"]
    UNITS = ["шт", "м", "м²", "м³", "кг", "комплект"]

    def __init__(self, parent: ttk.Notebook, get_products_callback: Callable | None = None):
        self.frame = ttk.Frame(parent)
        self.manager = PriceListManager()
        self.get_products_callback = get_products_callback
        self._current_view = "internal"
        self._selected_item_id: str | None = None
        self._build_ui()
        self._refresh_tree()

    def _build_ui(self):
        top = ttk.Frame(self.frame, padding=5)
        top.pack(fill=tk.X)

        ttk.Label(top, text="🏷️ Прайс-лист", font=("Arial", 14, "bold")).pack(side=tk.LEFT)

        btn_frame = ttk.Frame(top)
        btn_frame.pack(side=tk.LEFT, padx=(20, 0))

        ttk.Button(btn_frame, text="➕ Додати", command=self._add_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="✏️ Редагувати", command=self._edit_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑️ Видалити", command=self._delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📋 Дублювати", command=self._duplicate_selected).pack(side=tk.LEFT, padx=2)

        # Синхронізація
        sync_frame = ttk.LabelFrame(top, text="Синхронізація", padding=3)
        sync_frame.pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(sync_frame, text="🔄 З виробів", command=self._sync_from_products).pack(side=tk.LEFT, padx=2)
        ttk.Button(sync_frame, text="📦 З архіву", command=self._sync_from_archive).pack(side=tk.LEFT, padx=2)
        ttk.Button(sync_frame, text="♻️ Оновити прайс", command=self._refresh_current_project).pack(side=tk.LEFT, padx=2)

        # Експорт
        export_frame = ttk.LabelFrame(top, text="Експорт", padding=3)
        export_frame.pack(side=tk.RIGHT, padx=5)
        ttk.Button(export_frame, text="📄 PDF", command=lambda: self._export("pdf")).pack(side=tk.LEFT, padx=2)
        ttk.Button(export_frame, text="📊 Excel", command=lambda: self._export("excel")).pack(side=tk.LEFT, padx=2)
        ttk.Button(export_frame, text="🌐 HTML", command=lambda: self._export("html")).pack(side=tk.LEFT, padx=2)
        ttk.Button(export_frame, text="📋 CSV", command=lambda: self._export("csv")).pack(side=tk.LEFT, padx=2)
        ttk.Button(export_frame, text="🖨️ Друк", command=self._print_dialog).pack(side=tk.LEFT, padx=2)

        view_frame = ttk.LabelFrame(self.frame, text="Режим перегляду", padding=5)
        view_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        self.view_var = tk.StringVar(value="internal")
        ttk.Radiobutton(
            view_frame, text="🔐 Внутрішній прайс (повна інформація)",
            variable=self.view_var, value="internal", command=self._on_view_changed
        ).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(
            view_frame, text="📋 Прайс замовника (публічний)",
            variable=self.view_var, value="customer", command=self._on_view_changed
        ).pack(side=tk.LEFT, padx=10)

        filter_frame = ttk.Frame(self.frame, padding=5)
        filter_frame.pack(fill=tk.X, padx=5)

        ttk.Label(filter_frame, text="Фільтр категорії:").pack(side=tk.LEFT)
        self.filter_cat_var = tk.StringVar(value="всі")
        ttk.Combobox(
            filter_frame, textvariable=self.filter_cat_var,
            values=["всі"] + self.CATEGORIES, state="readonly", width=20
        ).pack(side=tk.LEFT, padx=5)
        self.filter_cat_var.trace_add("write", lambda *args: self._refresh_tree())

        ttk.Label(filter_frame, text="Пошук:").pack(side=tk.LEFT, padx=(15, 0))
        self.search_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.search_var, width=25).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="🔍", width=3, command=self._refresh_tree).pack(side=tk.LEFT)
        self.search_var.trace_add("write", lambda *args: self._refresh_tree())

        table_frame = ttk.Frame(self.frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.internal_columns = (
            "num", "name", "category", "type", "dimensions", "material", "thickness",
            "unit", "qty", "cost", "labor", "overhead", "markup",
            "unit_price", "total", "profit", "supplier", "notes"
        )
        self.internal_headings = {
            "num": "№", "name": "Назва", "category": "Категорія", "type": "Тип",
            "dimensions": "Розміри", "material": "Матеріал", "thickness": "Товщ.",
            "unit": "Од.", "qty": "К-ть", "cost": "Собіварт.", "labor": "Роботи",
            "overhead": "Накладні", "markup": "Націнка%", "unit_price": "Ціна од.",
            "total": "Сума", "profit": "Прибуток", "supplier": "Постач.", "notes": "Примітки"
        }
        self.internal_widths = {
            "num": 30, "name": 150, "category": 90, "type": 100, "dimensions": 90,
            "material": 90, "thickness": 45, "unit": 40, "qty": 45, "cost": 70,
            "labor": 60, "overhead": 60, "markup": 55, "unit_price": 70,
            "total": 80, "profit": 70, "supplier": 90, "notes": 100
        }

        self.customer_columns = (
            "num", "name", "type", "dimensions", "material", "thickness",
            "unit", "qty", "unit_price", "total", "notes"
        )
        self.customer_headings = {
            "num": "№", "name": "Назва", "type": "Тип", "dimensions": "Розміри",
            "material": "Матеріал", "thickness": "Товщ.", "unit": "Од.",
            "qty": "К-ть", "unit_price": "Ціна за од.", "total": "Загальна", "notes": "Примітки"
        }
        self.customer_widths = {
            "num": 35, "name": 200, "type": 120, "dimensions": 120,
            "material": 100, "thickness": 50, "unit": 45, "qty": 50,
            "unit_price": 90, "total": 90, "notes": 150
        }

        self.tree = ttk.Treeview(table_frame, show="headings", height=20)
        self._setup_tree_columns()

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", lambda e: self._edit_dialog())
        self.tree.bind("<Button-3>", self._on_right_click)

        self.summary_frame = ttk.LabelFrame(self.frame, text="Зведення", padding=5)
        self.summary_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.summary_label = ttk.Label(self.summary_frame, text="", font=("Consolas", 10))
        self.summary_label.pack(anchor=tk.W)

    def _setup_tree_columns(self):
        for col in self.tree["columns"]:
            self.tree.heading(col, text="")
        self.tree.delete(*self.tree.get_children())

        if self._current_view == "internal":
            cols = self.internal_columns
            headings = self.internal_headings
            widths = self.internal_widths
        else:
            cols = self.customer_columns
            headings = self.customer_headings
            widths = self.customer_widths

        self.tree["columns"] = cols
        for col in cols:
            self.tree.heading(col, text=headings.get(col, col))
            self.tree.column(col, width=widths.get(col, 80), anchor=tk.CENTER if col != "name" else tk.W)

    def _on_view_changed(self):
        self._current_view = self.view_var.get()
        self._setup_tree_columns()
        self._refresh_tree()

    def _get_filtered_items(self) -> list[PriceItem]:
        if self._current_view == "internal":
            items = self.manager.get_internal_view()
        else:
            items = self.manager.get_customer_view()

        cat = self.filter_cat_var.get()
        if cat != "всі":
            items = [i for i in items if i.category == cat]

        search = self.search_var.get().lower().strip()
        if search:
            items = [
                i for i in items
                if search in i.name.lower()
                or search in i.product_type.lower()
                or search in i.dimensions.lower()
                or search in i.material.lower()
                or search in i.supplier.lower()
            ]
        return items

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        items = self._get_filtered_items()

        for i, item in enumerate(items, 1):
            if self._current_view == "internal":
                values = (
                    i, item.name, item.category, item.product_type, item.dimensions,
                    item.material, item.thickness, item.unit, item.quantity,
                    f"{item.cost_price:.2f}", f"{item.labor_cost:.2f}",
                    f"{item.overhead_cost:.2f}", f"{item.markup_percent:.1f}",
                    f"{item.unit_price:.2f}", f"{item.total_price:.2f}",
                    f"{item.profit:.2f}", item.supplier, item.notes_internal,
                )
            else:
                values = (
                    i, item.name, item.product_type, item.dimensions,
                    item.material, item.thickness, item.unit, item.quantity,
                    f"{item.unit_price:.2f}", f"{item.total_price:.2f}",
                    item.notes_public,
                )
            self.tree.insert("", tk.END, values=values, tags=(item.id,))

        self._update_summary(items)

    def _update_summary(self, items: list[PriceItem]):
        total_qty = sum(i.quantity for i in items)
        total_price = sum(i.total_price for i in items)

        if self._current_view == "internal":
            total_cost = sum(i.cost_price * i.quantity for i in items)
            total_labor = sum(i.labor_cost * i.quantity for i in items)
            total_overhead = sum(i.overhead_cost * i.quantity for i in items)
            total_profit = sum(i.profit for i in items)
            text = (
                f"Позицій: {len(items)}  |  К-ть: {total_qty}  |  "
                f"Собівартість: {total_cost:,.2f} грн  |  Роботи: {total_labor:,.2f} грн  |  "
                f"Накладні: {total_overhead:,.2f} грн  |  Загальна: {total_price:,.2f} грн  |  "
                f"Прибуток: {total_profit:,.2f} грн"
            )
        else:
            text = f"Позицій: {len(items)}  |  К-ть: {total_qty}  |  Загальна: {total_price:,.2f} грн"

        self.summary_label.config(text=text)

    def _get_selected_item(self) -> PriceItem | None:
        selected = self.tree.selection()
        if not selected:
            return None
        idx = self.tree.index(selected[0])
        items = self._get_filtered_items()
        if 0 <= idx < len(items):
            return items[idx]
        return None

    def _add_dialog(self):
        self._open_item_dialog()

    def _edit_dialog(self):
        item = self._get_selected_item()
        if not item:
            messagebox.showwarning("Увага", "Оберіть позицію для редагування")
            return
        self._open_item_dialog(item)

    def _open_item_dialog(self, item: PriceItem | None = None):
        dialog = tk.Toplevel(self.frame)
        dialog.title("Редагувати позицію" if item else "Додати позицію в прайс")
        dialog.geometry("500x650")
        dialog.minsize(400, 300)
        dialog.resizable(True, True)
        dialog.transient(self.frame)
        dialog.grab_set()

        is_edit = item is not None

        vars_dict = {
            "name": tk.StringVar(value=item.name if is_edit else ""),
            "category": tk.StringVar(value=item.category if is_edit else "власне виробництво"),
            "product_type": tk.StringVar(value=item.product_type if is_edit else ""),
            "dimensions": tk.StringVar(value=item.dimensions if is_edit else ""),
            "material": tk.StringVar(value=item.material if is_edit else ""),
            "thickness": tk.StringVar(value=str(item.thickness) if is_edit else "0.7"),
            "unit": tk.StringVar(value=item.unit if is_edit else "шт"),
            "quantity": tk.StringVar(value=str(item.quantity) if is_edit else "1"),
            "cost_price": tk.StringVar(value=str(item.cost_price) if is_edit else "0"),
            "labor_cost": tk.StringVar(value=str(item.labor_cost) if is_edit else "0"),
            "overhead_cost": tk.StringVar(value=str(item.overhead_cost) if is_edit else "0"),
            "markup_percent": tk.StringVar(value=str(item.markup_percent) if is_edit else "30"),
            "supplier": tk.StringVar(value=item.supplier if is_edit else ""),
            "supplier_price": tk.StringVar(value=str(item.supplier_price) if is_edit else "0"),
            "notes_internal": tk.StringVar(value=item.notes_internal if is_edit else ""),
            "notes_public": tk.StringVar(value=item.notes_public if is_edit else ""),
        }

        row = 0
        def add_row(label_text, var, entry_width=15):
            nonlocal row
            ttk.Label(dialog, text=label_text).grid(row=row, column=0, sticky=tk.W, padx=10, pady=2)
            ttk.Entry(dialog, textvariable=var, width=entry_width).grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
            row += 1

        add_row("Назва *:", vars_dict["name"], 35)

        ttk.Label(dialog, text="Категорія:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=2)
        ttk.Combobox(dialog, textvariable=vars_dict["category"], values=self.CATEGORIES, state="readonly", width=20).grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        row += 1

        add_row("Тип виробу:", vars_dict["product_type"], 25)
        add_row("Розміри:", vars_dict["dimensions"], 25)
        add_row("Матеріал:", vars_dict["material"], 20)
        add_row("Товщина (мм):", vars_dict["thickness"])

        ttk.Label(dialog, text="Од. виміру:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=2)
        ttk.Combobox(dialog, textvariable=vars_dict["unit"], values=self.UNITS, state="readonly", width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        row += 1

        add_row("Кількість:", vars_dict["quantity"])

        ttk.Separator(dialog, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1
        ttk.Label(dialog, text="💰 Фінанси (внутрішні)", font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=10, pady=5)
        row += 1

        add_row("Собівартість за од.:", vars_dict["cost_price"])
        add_row("Вартість робіт за од.:", vars_dict["labor_cost"])
        add_row("Накладні витрати за од.:", vars_dict["overhead_cost"])
        add_row("Націнка (%):", vars_dict["markup_percent"])

        ttk.Separator(dialog, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1
        ttk.Label(dialog, text="🔄 Перепродаж", font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=10, pady=5)
        row += 1

        add_row("Постачальник:", vars_dict["supplier"], 25)
        add_row("Закупівельна ціна:", vars_dict["supplier_price"])

        ttk.Separator(dialog, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1
        ttk.Label(dialog, text="📝 Примітки", font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=10, pady=5)
        row += 1

        add_row("Внутрішні:", vars_dict["notes_internal"], 35)
        add_row("Публічні:", vars_dict["notes_public"], 35)

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=15)

        def save():
            try:
                name = vars_dict["name"].get().strip()
                if not name:
                    messagebox.showwarning("Увага", "Вкажіть назву позиції")
                    return

                qty = max(1, int(float(vars_dict["quantity"].get() or 1)))
                thickness = float(vars_dict["thickness"].get() or 0)
                cost = float(vars_dict["cost_price"].get() or 0)
                labor = float(vars_dict["labor_cost"].get() or 0)
                overhead = float(vars_dict["overhead_cost"].get() or 0)
                markup = float(vars_dict["markup_percent"].get() or 30)
                supplier_price = float(vars_dict["supplier_price"].get() or 0)

                if is_edit:
                    self.manager.update(
                        item.id,
                        name=name,
                        category=vars_dict["category"].get(),
                        product_type=vars_dict["product_type"].get(),
                        dimensions=vars_dict["dimensions"].get(),
                        material=vars_dict["material"].get(),
                        thickness=thickness,
                        unit=vars_dict["unit"].get(),
                        quantity=qty,
                        cost_price=cost,
                        labor_cost=labor,
                        overhead_cost=overhead,
                        markup_percent=markup,
                        supplier=vars_dict["supplier"].get(),
                        supplier_price=supplier_price,
                        notes_internal=vars_dict["notes_internal"].get(),
                        notes_public=vars_dict["notes_public"].get(),
                    )
                else:
                    new_item = PriceItem(
                        name=name,
                        category=vars_dict["category"].get(),
                        product_type=vars_dict["product_type"].get(),
                        dimensions=vars_dict["dimensions"].get(),
                        material=vars_dict["material"].get(),
                        thickness=thickness,
                        unit=vars_dict["unit"].get(),
                        quantity=qty,
                        cost_price=cost,
                        labor_cost=labor,
                        overhead_cost=overhead,
                        markup_percent=markup,
                        supplier=vars_dict["supplier"].get(),
                        supplier_price=supplier_price,
                        notes_internal=vars_dict["notes_internal"].get(),
                        notes_public=vars_dict["notes_public"].get(),
                    )
                    self.manager.add(new_item)

                self._refresh_tree()
                dialog.destroy()
            except ValueError as e:
                messagebox.showwarning("Увага", f"Помилка в даних: {e}")

        ttk.Button(btn_frame, text="✅ Зберегти", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="❌ Скасувати", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _delete_selected(self):
        item = self._get_selected_item()
        if not item:
            messagebox.showwarning("Увага", "Оберіть позицію для видалення")
            return
        if messagebox.askyesno("Підтвердження", f'Видалити "{item.name}"?'):
            self.manager.delete(item.id)
            self._refresh_tree()

    def _duplicate_selected(self):
        item = self._get_selected_item()
        if not item:
            messagebox.showwarning("Увага", "Оберіть позицію для дублювання")
            return
        new_item = PriceItem(
            name=f"{item.name} (копія)",
            category=item.category,
            product_type=item.product_type,
            dimensions=item.dimensions,
            material=item.material,
            thickness=item.thickness,
            unit=item.unit,
            quantity=item.quantity,
            cost_price=item.cost_price,
            labor_cost=item.labor_cost,
            overhead_cost=item.overhead_cost,
            markup_percent=item.markup_percent,
            supplier=item.supplier,
            supplier_price=item.supplier_price,
            notes_internal=item.notes_internal,
            notes_public=item.notes_public,
        )
        self.manager.add(new_item)
        self._refresh_tree()

    def _sync_from_products(self):
        """Синхронізувати вироби з вкладки 'Вироби' для поточного проєкту."""
        project_id = getattr(self, '_current_project_id', '') or 'current'
        if self.get_products_callback:
            products = self.get_products_callback()
            if products:
                count = self.manager.import_from_products(products, project_id=project_id)
                self._refresh_tree()
                if count > 0:
                    messagebox.showinfo("Синхронізація", f"Імпортовано {count} нових позицій з виробів")
                else:
                    messagebox.showinfo("Синхронізація", "Усі вироби вже в прайсі")
            else:
                messagebox.showinfo("Синхронізація", "Немає виробів для імпорту")
        else:
            messagebox.showwarning("Увага", "Функція синхронізації з виробами недоступна")

    def _sync_from_archive(self):
        """Синхронізувати з конкретного проєкту в архіві."""
        project_id = getattr(self, '_current_project_id', None)
        if not project_id:
            try:
                from ventilation_company.db_integration import ProjectDatabase
                db = ProjectDatabase("data/company.db")
                projects = db.list_projects()
                if not projects:
                    messagebox.showinfo("Архів", "Архів проєктів порожній")
                    return
                dialog = tk.Toplevel(self.frame)
                dialog.title("Виберіть проєкт")
                dialog.geometry("400x300")
                dialog.minsize(400, 300)
                dialog.resizable(True, True)
                dialog.transient(self.frame)
                dialog.grab_set()
                listbox = tk.Listbox(dialog, font=("Arial", 11))
                listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                project_map = {}
                for p in projects:
                    display = f"{p.get('name', 'Без назви')} (ID: {p.get('id', '?')})"
                    project_map[display] = p.get('id')
                    listbox.insert(tk.END, display)
                def on_select():
                    sel = listbox.curselection()
                    if not sel:
                        return
                    selected_id = project_map[listbox.get(sel[0])]
                    dialog.destroy()
                    self._do_archive_sync(selected_id)
                ttk.Button(dialog, text="Імпортувати", command=on_select).pack(pady=5)
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося відкрити архів: {e}")
        else:
            self._do_archive_sync(project_id)

    def _do_archive_sync(self, project_id: str):
        """Виконати імпорт з архіву для конкретного проєкту."""
        count = self.manager.import_from_archive(project_id=project_id)
        self._refresh_tree()
        if count > 0:
            messagebox.showinfo("Синхронізація", f"Імпортовано {count} нових позицій з архіву")
        else:
            messagebox.showinfo("Синхронізація", "Усі позиції вже синхронізовані або проєкт порожній")

    def _refresh_current_project(self):
        """Оновити прайс-лист для поточного проєкту (перезавантажити дані)."""
        project_id = getattr(self, '_current_project_id', None)
        if not project_id:
            messagebox.showwarning("Увага", "Спочатку відкрийте або створіть проєкт")
            return
        old_count = len(self.manager.items)
        self.manager.items = [
            i for i in self.manager.items
            if not (i.source in ("products", "archive") and i.project_id == str(project_id))
        ]
        removed = old_count - len(self.manager.items)
        self.manager.save()
        self._sync_from_products()
        self._do_archive_sync(project_id)
        self._refresh_tree()
        messagebox.showinfo("Оновлення", f"Прайс оновлено. Видалено старих: {removed}")

    def _export(self, fmt: str):
        items = self._get_filtered_items()
        if not items:
            messagebox.showwarning("Увага", "Немає даних для експорту")
            return

        internal = self._current_view == "internal"

        try:
            if fmt == "csv":
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                    initialfile=f"price_list_{datetime.now().strftime('%Y%m%d')}.csv"
                )
                if filepath:
                    content = PriceListExporter.to_csv(items, internal)
                    with open(filepath, "w", encoding="utf-8-sig") as f:
                        f.write(content)
                    messagebox.showinfo("Успіх", f"Збережено: {filepath}")

            elif fmt == "excel":
                if not HAVE_OPENPYXL:
                    messagebox.showwarning("Увага", "Встановіть openpyxl: pip install openpyxl")
                    return
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                    initialfile=f"price_list_{datetime.now().strftime('%Y%m%d')}.xlsx"
                )
                if filepath:
                    PriceListExporter.to_excel(items, filepath, internal)
                    messagebox.showinfo("Успіх", f"Збережено: {filepath}")

            elif fmt == "pdf":
                if not HAVE_REPORTLAB:
                    messagebox.showwarning("Увага", "Встановіть reportlab: pip install reportlab")
                    return
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                    initialfile=f"price_list_{datetime.now().strftime('%Y%m%d')}.pdf"
                )
                if filepath:
                    title = "Прайс-лист (внутрішній)" if internal else "Прайс-лист для замовника"
                    PriceListExporter.to_pdf(items, filepath, internal, title)
                    messagebox.showinfo("Успіх", f"Збережено: {filepath}")

            elif fmt == "html":
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".html", filetypes=[("HTML", "*.html")],
                    initialfile=f"price_list_{datetime.now().strftime('%Y%m%d')}.html"
                )
                if filepath:
                    title = "Прайс-лист (внутрішній)" if internal else "Прайс-лист для замовника"
                    content = PriceListExporter.to_html(items, internal, title)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    messagebox.showinfo("Успіх", f"Збережено: {filepath}")

        except Exception as e:
            messagebox.showerror("Помилка", str(e))

    def _print_dialog(self):
        items = self._get_filtered_items()
        if not items:
            messagebox.showwarning("Увага", "Немає даних для друку")
            return

        internal = self._current_view == "internal"
        title = "Прайс-лист (внутрішній)" if internal else "Прайс-лист для замовника"
        content = PriceListExporter.to_html(items, internal, title)

        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(content)
            temp_path = f.name

        import webbrowser
        webbrowser.open(f"file:///{temp_path}")

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            menu = tk.Menu(self.frame, tearoff=0)
            menu.add_command(label="✏️ Редагувати", command=self._edit_dialog)
            menu.add_command(label="📋 Дублювати", command=self._duplicate_selected)
            menu.add_separator()
            menu.add_command(label="🗑️ Видалити", command=self._delete_selected)
            menu.post(event.x_root, event.y_root)

    def get_manager(self) -> PriceListManager:
        return self.manager

    def get_items(self) -> list[PriceItem]:
        return self.manager.items