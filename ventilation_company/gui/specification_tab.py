"""Вкладка "Специфікація" для GUI.
Внутрішній Notebook:
  • 📋 Специфікація — формування та експорт специфікації
  • 📁 Архів проєктів — збережені проєкти з фінансовою аналітикою
"""

import os
import sqlite3
import tempfile
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ventilation_company.auto_specification import SpecBuilder
from ventilation_company.db_integration import ProjectDatabase
from ventilation_company.pdf_generator import generate_project_pdf

class ArchiveProjectDialog(tk.Toplevel):
    """Діалог додавання/редагування проєкту в архіві."""

    def __init__(
        self,
        parent,
        db: ProjectDatabase,
        project: dict | None = None,
        auto_finance: dict | None = None,
    ):
        super().__init__(parent)
        self.db = db
        self.project = project
        self.auto_finance = auto_finance
        self.result = False
        self.title("📁 Новий проєкт" if project is None else "✏️ Редагувати проєкт")
        self.geometry("480x480")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Значення за замовчуванням
        default_name = ""
        default_client = ""
        default_drawing = ""
        default_cost = "0"
        default_salary = "0"
        default_markup = "30"
        default_price = "0"

        if project:
            default_name = project.get("name", "")
            default_client = project.get("client", "")
            default_drawing = project.get("drawing_path", "")
            default_cost = str(project.get("cost_price", 0))
            default_salary = str(project.get("salary_total", 0))
            default_markup = "30"
            default_price = str(project.get("customer_price", 0))
        elif auto_finance:
            default_cost = str(auto_finance.get("cost_price", 0))
            default_salary = str(auto_finance.get("salary_total", 0))
            default_markup = str(auto_finance.get("markup", 30))
            default_price = str(auto_finance.get("customer_price", 0))

        row = 0
        ttk.Label(self, text="Назва проєкту *:").grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5
        )
        self.name_var = tk.StringVar(value=default_name)
        ttk.Entry(self, textvariable=self.name_var, width=35).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )

        row += 1
        ttk.Label(self, text="Клієнт:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.client_var = tk.StringVar(value=default_client)
        ttk.Entry(self, textvariable=self.client_var, width=35).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )

        row += 1
        ttk.Label(self, text="Креслення / FreeCAD:").grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5
        )
        self.drawing_var = tk.StringVar(value=default_drawing)
        ttk.Entry(self, textvariable=self.drawing_var, width=28).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        ttk.Button(self, text="📂", width=3, command=self._browse_drawing).grid(
            row=row, column=1, sticky=tk.E, padx=5
        )

        row += 1
        ttk.Separator(self, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=10
        )

        row += 1
        ttk.Label(self, text="Собівартість:").grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5
        )
        self.cost_var = tk.StringVar(value=default_cost)
        ttk.Entry(self, textvariable=self.cost_var, width=15).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )

        row += 1
        ttk.Label(self, text="Зарплата робітників:").grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5
        )
        self.salary_var = tk.StringVar(value=default_salary)
        ttk.Entry(self, textvariable=self.salary_var, width=15).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )

        row += 1
        ttk.Label(self, text="Націнка (%):").grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5
        )
        self.markup_var = tk.StringVar(value=default_markup)
        ttk.Entry(self, textvariable=self.markup_var, width=15).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )

        row += 1
        ttk.Label(self, text="Ціна для замовника:").grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5
        )
        self.price_var = tk.StringVar(value=default_price)
        self.price_entry = ttk.Entry(
            self, textvariable=self.price_var, width=15, state="readonly"
        )
        self.price_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        row += 1
        ttk.Label(self, text="Прибуток:").grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5
        )
        self.profit_label = ttk.Label(
            self, text="0.00 грн", font=("Arial", 10, "bold"), foreground="#2E7D32"
        )
        self.profit_label.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        # Автоперерахунок
        for var in (self.cost_var, self.salary_var, self.markup_var):
            var.trace_add("write", self._calc_auto)

        row += 1
        btn_frm = ttk.Frame(self)
        btn_frm.grid(row=row, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frm, text="💾 Зберегти", command=self._save).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frm, text="Скасувати", command=self.destroy).pack(
            side=tk.LEFT, padx=5
        )

        self._calc_auto()
        self.wait_window(self)

    def _browse_drawing(self):
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[
                ("FreeCAD", "*.FCStd"),
                ("STEP", "*.step;*.stp"),
                ("Всі файли", "*.*"),
            ],
        )
        if path:
            self.drawing_var.set(path)

    def _calc_auto(self, *args):
        try:
            cost = float(self.cost_var.get() or 0)
            salary = float(self.salary_var.get() or 0)
            markup = float(self.markup_var.get() or 0)
            # Собівартість вже включає зарплату, тому не додаємо її знову
            customer = cost * (1 + markup / 100)
            profit = customer - cost
            color = "#2E7D32" if profit >= 0 else "#C62828"
            self.price_var.set(f"{customer:.2f}")
            self.profit_label.config(text=f"{profit:,.2f} грн", foreground=color)
        except ValueError:
            self.price_var.set("0.00")
            self.profit_label.config(text="—")

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Увага", "Назва проєкту обов'язкова!", parent=self)
            return
        try:
            cost = float(self.cost_var.get() or 0)
            salary = float(self.salary_var.get() or 0)
            customer = float(self.price_var.get() or 0)
        except ValueError:
            messagebox.showwarning(
                "Увага", "Фінансові поля мають бути числами!", parent=self
            )
            return

        data = {
            "name": name,
            "client": self.client_var.get().strip(),
            "drawing_path": self.drawing_var.get().strip(),
            "customer_price": customer,
            "cost_price": cost,
            "salary_total": salary,
            "profit": customer - cost,
        }

        if self.project:
            self.db.update_project(self.project["id"], **data)
        else:
            self.db.create_project(**data)

        self.result = True
        self.destroy()


class SpecificationTab:
    """Вкладка Специфікації з внутрішнім Notebook (Специфікація + Архів)."""

    EXPORT_FORMATS = {
        "JSON (.json)": "json",
        "CSV (.csv)": "csv",
        "Текст (.txt)": "txt",
        "HTML (.html)": "html",
    }

    def __init__(self, parent: ttk.Notebook, get_products_callback):
        self.frame = ttk.Frame(parent)

        self.get_products = get_products_callback
        self.current_spec = None
        self.current_project_id = None
        self.db = ProjectDatabase("data/company.db")

        self._build_ui()
        self._load_archive()

    def _build_ui(self):
        self.inner_notebook = ttk.Notebook(self.frame)
        self.inner_notebook.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.spec_tab = ttk.Frame(self.inner_notebook)
        self.inner_notebook.add(self.spec_tab, text="📋 Специфікація")
        self._build_spec_tab()

        self.archive_tab = ttk.Frame(self.inner_notebook)
        self.inner_notebook.add(self.archive_tab, text="📁 Архів проєктів")
        self._build_archive_tab()

    # ═══════════════════════════════════════════════════════
    # ПІД-ВКЛАДКА 1: СПЕЦИФІКАЦІЯ
    # ═══════════════════════════════════════════════════════

    def _build_spec_tab(self):
        ctrl_frame = ttk.Frame(self.spec_tab)
        ctrl_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(ctrl_frame, text="Назва проєкту:").pack(side=tk.LEFT, padx=2)
        self.project_name_var = tk.StringVar(value="Новий проєкт")
        ttk.Entry(ctrl_frame, textvariable=self.project_name_var, width=30).pack(
            side=tk.LEFT, padx=2
        )

        ttk.Button(ctrl_frame, text="🔄 Сформувати", command=self._generate).pack(
            side=tk.LEFT, padx=10
        )

        ttk.Label(ctrl_frame, text="Експорт:").pack(side=tk.LEFT, padx=(20, 2))
        self.export_var = tk.StringVar(value="JSON (.json)")
        ttk.Combobox(
            ctrl_frame,
            textvariable=self.export_var,
            values=list(self.EXPORT_FORMATS.keys()),
            state="readonly",
            width=15,
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl_frame, text="💾 Зберегти", command=self._export).pack(
            side=tk.LEFT, padx=2
        )

        self.summary_frame = ttk.LabelFrame(self.spec_tab, text="📊 Підсумки", padding=5)
        self.summary_frame.pack(fill=tk.X, padx=5, pady=2)

        self.summary_labels = {}
        summary_items = [
            ("total_items", "Позицій:"),
            ("total_qty", "Кількість:"),
            ("total_weight", "Вага, кг:"),
            ("total_area", "Площа, м²:"),
            ("total_price", "Вартість, грн:"),
        ]

        for i, (key, text) in enumerate(summary_items):
            ttk.Label(self.summary_frame, text=text, font=("Arial", 9)).grid(
                row=0, column=i * 2, padx=(10 if i > 0 else 5), pady=2
            )
            lbl = ttk.Label(self.summary_frame, text="0", font=("Arial", 10, "bold"))
            lbl.grid(row=0, column=i * 2 + 1, padx=2, pady=2)
            self.summary_labels[key] = lbl

        table_frame = ttk.Frame(self.spec_tab)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = (
            "pos",
            "name",
            "type",
            "dims",
            "material",
            "thick",
            "qty",
            "w_unit",
            "w_total",
            "a_unit",
            "a_total",
            "price",
        )
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=18
        )

        headers = {
            "pos": "№",
            "name": "Найменування",
            "type": "Тип",
            "dims": "Розміри",
            "material": "Матеріал",
            "thick": "Товщ.",
            "qty": "К-ть",
            "w_unit": "Вага 1 шт",
            "w_total": "Вага заг.",
            "a_unit": "Площа 1 шт",
            "a_total": "Площа заг.",
            "price": "Ціна, грн",
        }
        widths = {
            "pos": 30,
            "name": 180,
            "type": 140,
            "dims": 100,
            "material": 100,
            "thick": 50,
            "qty": 40,
            "w_unit": 70,
            "w_total": 70,
            "a_unit": 70,
            "a_total": 70,
            "price": 80,
        }

        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(
                col, width=widths[col], anchor=tk.CENTER if col != "name" else tk.W
            )

        scrollbar = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # ═══════════════════════════════════════════════════════
    # ПІД-ВКЛАДКА 2: АРХІВ ПРОЄКТІВ
    # ═══════════════════════════════════════════════════════

    def _build_archive_tab(self):
        arch_toolbar = ttk.Frame(self.archive_tab)
        arch_toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            arch_toolbar, text="➕ Додати", command=self._add_archive_project
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            arch_toolbar, text="✏️ Редагувати", command=self._edit_archive_project
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            arch_toolbar, text="🗑️ Видалити", command=self._delete_archive_project
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            arch_toolbar, text="📂 Креслення", command=self._open_drawing
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            arch_toolbar, text="🖨️ Друк звіту", command=self._print_archive_project
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            arch_toolbar, text="🔄 Оновити", command=self._load_archive
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            arch_toolbar, text="📄 PDF-звіт", command=self._open_pdf_report
        ).pack(side=tk.LEFT, padx=2)

        table_frame = ttk.Frame(self.archive_tab)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        a_cols = (
            "id",
            "name",
            "client",
            "drawing",
            "customer_price",
            "cost_price",
            "salary",
            "profit",
            "date",
        )
        self.archive_tree = ttk.Treeview(
            table_frame, columns=a_cols, show="headings", height=18
        )

        a_headers = {
            "id": "ID",
            "name": "Назва проєкту",
            "client": "Клієнт",
            "drawing": "Креслення / FreeCAD",
            "customer_price": "Ціна зам., грн",
            "cost_price": "Собівартість, грн",
            "salary": "Зарплата, грн",
            "profit": "Прибуток, грн",
            "date": "Дата",
        }
        a_widths = {
            "id": 40,
            "name": 180,
            "client": 120,
            "drawing": 140,
            "customer_price": 100,
            "cost_price": 100,
            "salary": 100,
            "profit": 100,
            "date": 90,
        }

        for col in a_cols:
            self.archive_tree.heading(col, text=a_headers[col])
            self.archive_tree.column(
                col, width=a_widths[col], anchor=tk.CENTER if col != "name" else tk.W
            )

        a_scroll = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.archive_tree.yview
        )
        self.archive_tree.configure(yscrollcommand=a_scroll.set)

        self.archive_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        a_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.archive_tree.bind("<Double-1>", lambda e: self._open_pdf_report())
        self.archive_tree.bind("<Button-3>", self._archive_context_menu)

        self.arch_ctx = tk.Menu(self.frame, tearoff=0)
        self.arch_ctx.add_command(
            label="✏️ Редагувати", command=self._edit_archive_project
        )
        self.arch_ctx.add_command(
            label="📂 Відкрити креслення", command=self._open_drawing
        )
        self.arch_ctx.add_command(
            label="🖨️ Друк звіту", command=self._print_archive_project
        )
        self.arch_ctx.add_command(
            label="📄 Відкрити PDF-звіт", command=self._open_pdf_report   # ← НОВИЙ ПУНКТ
        )
        self.arch_ctx.add_separator()
        self.arch_ctx.add_command(
            label="🗑️ Видалити", command=self._delete_archive_project
        )

    # ═══════════════════════════════════════════════════════
    # РОЗРАХУНОК ФІНАНСІВ ПРОЄКТУ
    # ═══════════════════════════════════════════════════════

    def _calc_project_finance(self, products: list[dict]) -> dict:
        """Розрахувати фінансові показники проєкту по всім виробам."""
        try:
            from ventilation_company.gui.settings_tab import PricingSettings
            pricing = PricingSettings()
            markup = pricing.markup_percent / 100.0

            total_material = 0.0
            total_labor = 0.0
            total_depreciation = 0.0
            total_electricity = 0.0

            for p in products:
                qty = p.get("quantity", 1)
                data = {
                    "type": p.get("product_type", ""),
                    "material": p.get("material", "оцинкована сталь"),
                    "thickness": p.get("thickness", 0.7),
                    "metal_area_m2": p.get("metal_area_m2", 0),
                    "weight_kg": p.get("weight_kg", 0),
                    "quantity": qty,
                    "width": p.get("width", 0),
                    "height": p.get("height", 0),
                    "length": p.get("length", 0),
                    "profile": p.get("profile", 30.0),
                }

                result = pricing.calculate_product_price_detailed(data)
                steps = result["steps"]

                if len(steps) >= 6:
                    after_waste = steps[1]["value"]
                    labor = steps[2]["value"]
                    after_labor = steps[3]["value"]
                    after_depr = steps[4]["value"]
                    elec = steps[5]["value"]

                    total_material += after_waste * qty
                    total_labor += labor * qty
                    total_depreciation += (after_depr - after_labor) * qty
                    total_electricity += elec * qty

            cost_price = (
                total_material + total_labor + total_depreciation + total_electricity
            )
            customer_price = cost_price * (1 + markup)
            profit = customer_price - cost_price

            return {
                "customer_price": round(customer_price, 2),
                "cost_price": round(cost_price, 2),
                "salary_total": round(total_labor, 2),
                "profit": round(profit, 2),
                "markup": pricing.markup_percent,
            }
        except Exception as e:
            print(f"[DEBUG] _calc_project_finance error: {e}")
            return {
                "customer_price": 0,
                "cost_price": 0,
                "salary_total": 0,
                "profit": 0,
                "markup": pricing.markup_percent if 'pricing' in dir() else 30,
            }

    def _auto_save_to_archive(self, products: list[dict]):
        """Автоматично зберегти/оновити проєкт в архіві після формування специфікації."""
        if not self.current_spec:
            return

        project_name = self.project_name_var.get().strip() or "Новий проєкт"
        finance = self._calc_project_finance(products)

        # Шукаємо існуючий проєкт по ID або по імені
        project_id = self.current_project_id
        if project_id is None:
            for p in self.db.get_all_projects():
                if p["name"] == project_name:
                    project_id = p["id"]
                    break

        project_data = {
            "name": project_name,
            "client": "",
            "status": "active",
            "customer_price": finance["customer_price"],
            "cost_price": finance["cost_price"],
            "salary_total": finance["salary_total"],
            "profit": finance["profit"],
        }

        if project_id:
            # Оновлюємо існуючий — очищаємо вироби і додаємо нові
            self.db.update_project(project_id, **project_data)
            self._clear_project_products(project_id)
        else:
            project_id = self.db.create_project(**project_data)

        # Зберігаємо вироби
        for p in products:
            self.db.add_product_to_project(project_id, p)

        self.current_project_id = project_id
        self._load_archive()

    def _clear_project_products(self, project_id: int):
        """Видалити всі вироби проєкту (для оновлення)."""
        try:
            conn = sqlite3.connect(self.db.db_path)
            conn.execute(
                "DELETE FROM project_products WHERE project_id = ?", (project_id,)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DEBUG] _clear_project_products error: {e}")

    # ═══════════════════════════════════════════════════════
    # ЛОГІКА СПЕЦИФІКАЦІЇ
    # ═══════════════════════════════════════════════════════

    def _generate(self):
        products = self.get_products()
        if not products:
            messagebox.showwarning(
                "Увага",
                "Список виробів порожній. Додайте вироби у вкладці 'Вироби'.",
            )
            return

        builder = SpecBuilder(project_name=self.project_name_var.get())
        builder.set_material_price("оцинкована сталь", 55.0)
        builder.set_material_price("нержавіюча сталь", 180.0)
        builder.set_material_price("алюміній", 120.0)

        for p in products:
            builder.add_product(p)

        self.current_spec = builder.build()
        self._refresh_tree()
        self._update_summary()

        # ═══ АВТОЗБЕРЕЖЕННЯ В АРХІВ ═══
        self._auto_save_to_archive(products)

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.current_spec:
            return

        for item in self.current_spec.items:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    item.position,
                    item.name,
                    item.product_type,
                    item.dimensions,
                    item.material,
                    item.thickness,
                    item.quantity,
                    f"{item.weight_per_unit:.3f}",
                    f"{item.weight_total:.3f}",
                    f"{item.area_per_unit:.4f}",
                    f"{item.area_total:.4f}",
                    f"{item.price_total:.2f}",
                ),
            )

    def _update_summary(self):
        if not self.current_spec:
            return

        self.summary_labels["total_items"].config(
            text=str(self.current_spec.total_items)
        )
        self.summary_labels["total_qty"].config(
            text=str(self.current_spec.total_quantity)
        )
        self.summary_labels["total_weight"].config(
            text=f"{self.current_spec.total_weight:.3f}"
        )
        self.summary_labels["total_area"].config(
            text=f"{self.current_spec.total_area:.4f}"
        )
        self.summary_labels["total_price"].config(
            text=f"{self.current_spec.total_price:.2f}"
        )

    def _export(self):
        if not self.current_spec:
            messagebox.showwarning("Увага", "Спочатку сформуйте специфікацію.")
            return

        fmt_name = self.export_var.get()
        fmt = self.EXPORT_FORMATS.get(fmt_name, "json")
        ext = fmt

        filepath = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            filetypes=[(fmt_name, f"*.{ext}")],
            initialfile=f"spec_{self.project_name_var.get().replace(' ', '_')}",
        )

        if filepath:
            try:
                content = self.current_spec.to_dict()
                if fmt == "json":
                    import json

                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(content, f, ensure_ascii=False, indent=2)
                elif fmt == "csv":
                    with open(filepath, "w", encoding="utf-8-sig") as f:
                        f.write(self.current_spec.to_csv())
                elif fmt == "txt":
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(self.current_spec.to_txt())
                elif fmt == "html":
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(self.current_spec.to_html())

                messagebox.showinfo("Успіх", f"Специфікація збережена:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося зберегти:\n{str(e)}")

    def get_specification(self):
        return self.current_spec

    # ═══════════════════════════════════════════════════════
    # ЛОГІКА АРХІВУ ПРОЄКТІВ
    # ═══════════════════════════════════════════════════════

    def _load_archive(self):
        for item in self.archive_tree.get_children():
            self.archive_tree.delete(item)

        projects = self.db.get_all_projects()
        for p in projects:
            draw_path = p.get("drawing_path", "")
            has_draw = os.path.basename(draw_path) if draw_path else "—"
            profit = p.get("profit", 0)
            profit_color = "#2E7D32" if profit >= 0 else "#C62828"

            self.archive_tree.insert(
                "",
                tk.END,
                iid=str(p["id"]),
                values=(
                    p["id"],
                    p["name"],
                    p.get("client", ""),
                    has_draw,
                    f"{p.get('customer_price', 0):,.2f}",
                    f"{p.get('cost_price', 0):,.2f}",
                    f"{p.get('salary_total', 0):,.2f}",
                    f"{profit:,.2f}",
                    str(p.get("created_at", ""))[:10],
                ),
                tags=("profit_good" if profit >= 0 else "profit_bad",),
            )

        # Розфарбовуємо прибуток
        self.archive_tree.tag_configure("profit_good", foreground="#2E7D32")
        self.archive_tree.tag_configure("profit_bad", foreground="#C62828")

    def _add_archive_project(self):
        dlg = ArchiveProjectDialog(self.frame, self.db)
        if dlg.result:
            self._load_archive()

    def _edit_archive_project(self):
        sel = self.archive_tree.selection()
        if not sel:
            messagebox.showwarning("Увага", "Оберіть проєкт для редагування.")
            return
        pid = int(sel[0])
        project = self.db.get_project(pid)
        if not project:
            return
        dlg = ArchiveProjectDialog(self.frame, self.db, project)
        if dlg.result:
            self._load_archive()

    def _delete_archive_project(self):
        sel = self.archive_tree.selection()
        if not sel:
            messagebox.showwarning("Увага", "Оберіть проєкт для видалення.")
            return
        pid = int(sel[0])
        if messagebox.askyesno("Підтвердження", "Видалити проєкт з архіву?"):
            self.db.delete_project(pid)
            if self.current_project_id == pid:
                self.current_project_id = None
            self._load_archive()

    def _open_drawing(self):
        sel = self.archive_tree.selection()
        if not sel:
            messagebox.showwarning("Увага", "Оберіть проєкт.")
            return
        pid = int(sel[0])
        project = self.db.get_project(pid)
        path = project.get("drawing_path", "")
        if path and os.path.exists(path):
            import platform

            if platform.system() == "Windows":
                os.startfile(path)
            else:
                import subprocess

                subprocess.call(["xdg-open", path])
        elif path:
            messagebox.showerror("Помилка", f"Файл не знайдено:\n{path}")
        else:
            messagebox.showinfo("Інфо", "Креслення не додано.")
    def _open_pdf_report(self):
        """Згенерувати та відкрити PDF-звіт по обраному проєкту."""
        sel = self.archive_tree.selection()
        if not sel:
            messagebox.showwarning("Увага", "Оберіть проєкт для формування PDF.")
            return
        pid = int(sel[0])
        project = self.db.get_project(pid)
        products = self.db.get_project_products(pid)

        try:
            import tempfile
            import platform
            import subprocess

            fd, pdf_path = tempfile.mkstemp(suffix=".pdf", prefix=f"project_{pid}_")
            os.close(fd)

            generate_project_pdf(project, products, pdf_path)

            # Відкрити PDF у стандартному переглядачі
            if platform.system() == "Windows":
                os.startfile(pdf_path)
            elif platform.system() == "Darwin":
                subprocess.call(["open", pdf_path])
            else:
                subprocess.call(["xdg-open", pdf_path])

        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося створити PDF:\n{str(e)}")
            
    def _print_archive_project(self):
        sel = self.archive_tree.selection()
        if not sel:
            messagebox.showwarning("Увага", "Оберіть проєкт для друку.")
            return
        pid = int(sel[0])
        project = self.db.get_project(pid)
        products = self.db.get_project_products(pid)

        html = self._generate_project_html(project, products)
        fd, path = tempfile.mkstemp(suffix=".html", prefix="project_report_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open(f"file:///{path.replace(chr(92), '/')}")

    def _archive_context_menu(self, event):
        item = self.archive_tree.identify_row(event.y)
        if item:
            self.archive_tree.selection_set(item)
            self.arch_ctx.post(event.x_root, event.y_root)

    def _generate_project_html(self, project, products) -> str:
        rows = ""
        for p in products:
            rows += (
                f"<tr>"
                f"<td>{p.get('name', '')}</td>"
                f"<td>{p.get('product_type', '')}</td>"
                f"<td style='text-align:center'>{p.get('quantity', 0)}</td>"
                f"<td style='text-align:right'>{p.get('weight_kg', 0):.2f}</td>"
                f"<td style='text-align:right'>{p.get('metal_area_m2', 0):.3f}</td>"
                f"</tr>"
            )
        if not rows:
            rows = "<tr><td colspan='5' style='text-align:center'>Немає виробів</td></tr>"

        profit = project.get("profit", 0)
        profit_class = "profit" if profit >= 0 else "loss"

        drawing = project.get("drawing_path", "")
        drawing_text = (
            f"<a href='file:///{drawing.replace(chr(92), '/')}'>{drawing}</a>"
            if drawing
            else "—"
        )

        return f"""<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8">
  <title>Звіт: {project['name']}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
    h1 {{ color: #1565c0; margin-bottom: 5px; }}
    .subtitle {{ color: #666; font-size: 13px; margin-bottom: 20px; }}
    .summary {{ background: #f5f5f5; padding: 18px; border-radius: 8px; margin: 20px 0; }}
    .summary div {{ margin: 6px 0; font-size: 14px; }}
    .summary b {{ display: inline-block; width: 220px; }}
    .profit {{ color: #2E7D32; font-weight: bold; font-size: 20px; }}
    .loss {{ color: #C62828; font-weight: bold; font-size: 20px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 20px; font-size: 13px; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
    th {{ background: #e3f2fd; }}
    .footer {{ margin-top: 30px; color: #999; font-size: 12px; }}
    @media print {{ .no-print {{ display: none; }} }}
  </style>
</head>
<body>
  <div class="no-print" style="text-align:center; margin-bottom:20px;">
    <button onclick="window.print()" style="padding:10px 24px; font-size:15px; cursor:pointer;">🖨️ Друкувати</button>
  </div>

  <h1>🏭 Звіт по проєкту: {project['name']}</h1>
  <div class="subtitle">
    Клієнт: <b>{project.get('client', '—')}</b> &nbsp;|&nbsp;
    Дата: {str(project.get('created_at', ''))[:10]} &nbsp;|&nbsp;
    ID: {project['id']}
  </div>

  <div class="summary">
    <div><b>📐 Креслення / FreeCAD:</b> {drawing_text}</div>
    <div><b>💰 Ціна для замовника:</b> {project.get('customer_price', 0):,.2f} грн</div>
    <div><b>🔧 Собівартість:</b> {project.get('cost_price', 0):,.2f} грн</div>
    <div><b>👷 Зарплата робітників:</b> {project.get('salary_total', 0):,.2f} грн</div>
    <div class="{profit_class}">
      <b>📈 Прибуток фірми:</b> {profit:,.2f} грн
    </div>
  </div>

  <h2>📋 Вироби проєкту</h2>
  <table>
    <tr>
      <th>Назва</th>
      <th>Тип</th>
      <th style="text-align:center">К-ть</th>
      <th style="text-align:right">Вага, кг</th>
      <th style="text-align:right">Площа, м²</th>
    </tr>
    {rows}
  </table>

  <p class="footer">Сформовано системою VentCompany</p>
</body>
</html>"""