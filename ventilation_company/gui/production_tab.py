"""Вкладка "Виробництво" — планування з Gantt-діаграмою."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime, timedelta

from ventilation_company.production_models import (
    DEFAULT_EQUIPMENT,
    Equipment,
    OperationStatus,
    ProductionPlan,
)
from ventilation_company.production_scheduler import ProductionScheduler
from ventilation_company.production_gantt import GanttChart, EquipmentLoadChart


class ProductionTab:
    """Вкладка планування виробництва."""

    def __init__(self, parent: ttk.Notebook, get_products_callback, get_project_info_callback=None):
        self.frame = ttk.Frame(parent)
        self.get_products = get_products_callback
        self.get_project_info = get_project_info_callback

        self.current_plan: ProductionPlan | None = None
        self.gantt_canvas = None
        self.load_canvas = None

        self._build_ui()

    def _build_ui(self):
        # ── Верхня панель керування ──
        top = ttk.Frame(self.frame, padding=5)
        top.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(top, text="📅 Початок:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=2)
        self.start_var = tk.StringVar(value=datetime.now().strftime("%d.%m.%Y 08:00"))
        ttk.Entry(top, textvariable=self.start_var, width=18).pack(side=tk.LEFT, padx=2)

        ttk.Label(top, text="⏰ Дедлайн:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(15, 2))
        self.deadline_var = tk.StringVar(value=(datetime.now() + timedelta(days=7)).strftime("%d.%m.%Y 17:00"))
        ttk.Entry(top, textvariable=self.deadline_var, width=18).pack(side=tk.LEFT, padx=2)

        ttk.Button(top, text="📊 Запланувати виробництво", command=self._schedule
                   ).pack(side=tk.LEFT, padx=(20, 2))
        ttk.Button(top, text="💾 Експорт PNG", command=self._export_png
                   ).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="📄 Експорт PDF", command=self._export_pdf
                   ).pack(side=tk.LEFT, padx=2)

        # ── Статусна панель ──
        self.status_frame = ttk.LabelFrame(self.frame, text="Статус проєкту", padding=5)
        self.status_frame.pack(fill=tk.X, padx=5, pady=2)

        self.status_labels = {}
        status_fields = [
            ("project", "Проєкт:"),
            ("operations", "Операцій:"),
            ("duration", "Тривалість:"),
            ("completion", "Виконано:"),
            ("deadline_status", "Дедлайн:"),
        ]
        for i, (key, text) in enumerate(status_fields):
            ttk.Label(self.status_frame, text=text, font=("Arial", 9)).grid(row=0, column=i*2, padx=5)
            lbl = ttk.Label(self.status_frame, text="—", font=("Arial", 9, "bold"))
            lbl.grid(row=0, column=i*2+1, padx=5)
            self.status_labels[key] = lbl

        # ── Notebook з діаграмами ──
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Вкладка 1: Gantt
        self.gantt_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.gantt_tab, text="📊 Gantt-діаграма")
        self.gantt_container = ttk.Frame(self.gantt_tab)
        self.gantt_container.pack(fill=tk.BOTH, expand=True)

        # Вкладка 2: Завантаження обладнання
        self.load_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.load_tab, text="⚙️ Завантаження обладнання")
        self.load_container = ttk.Frame(self.load_tab)
        self.load_container.pack(fill=tk.BOTH, expand=True)

        # Вкладка 3: Таблиця операцій
        self.table_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.table_tab, text="📋 Таблиця операцій")
        self._build_table_tab()

        # ── Підказка ──
        hint = ttk.Label(
            self.frame,
            text="💡 Підказка: введіть дату початку та дедлайн, натисніть «Запланувати виробництво». Кольори = тип операції, штрихування = статус.",
            foreground="#666", font=("Arial", 8)
        )
        hint.pack(anchor=tk.W, padx=5, pady=2)

    def _build_table_tab(self):
        """Побудувати таблицю операцій."""
        cols = ("Виріб", "Операція", "Обладнання", "Початок", "Кінець", "Тривалість", "Статус")
        self.tree = ttk.Treeview(self.table_tab, columns=cols, show="headings", height=20)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120, anchor=tk.CENTER)
        self.tree.column("Виріб", width=180, anchor=tk.W)
        self.tree.column("Операція", width=100, anchor=tk.W)

        vsb = ttk.Scrollbar(self.table_tab, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(self.table_tab, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.table_tab.grid_rowconfigure(0, weight=1)
        self.table_tab.grid_columnconfigure(0, weight=1)

    def _parse_datetime(self, text: str) -> datetime | None:
        """Розпарсити дату з рядка."""
        formats = ["%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%d %H:%M", "%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(text.strip(), fmt)
            except ValueError:
                continue
        return None

    def _schedule(self):
        """Запустити планування виробництва."""
        products = self.get_products()
        if not products:
            messagebox.showwarning("Увага", "У проєкті немає виробів для планування.")
            return

        start = self._parse_datetime(self.start_var.get())
        deadline = self._parse_datetime(self.deadline_var.get())

        if start is None:
            messagebox.showerror("Помилка", "Невірний формат дати початку. Використовуйте ДД.ММ.РРРР ГГ:ХХ")
            return

        project_name = "Проєкт"
        if self.get_project_info:
            info = self.get_project_info()
            if info and info.get("name"):
                project_name = info["name"]

        try:
            scheduler = ProductionScheduler()
            self.current_plan = scheduler.schedule_project(
                project_name=project_name,
                products=products,
                start_date=start,
                deadline=deadline,
            )
            self._update_ui()
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Помилка планування", str(e))

    def _update_ui(self):
        """Оновити всі елементи інтерфейсу."""
        if not self.current_plan:
            return

        plan = self.current_plan

        # Статус
        duration = plan.estimated_end - plan.start_date if plan.estimated_end else timedelta(0)
        dl_text = "✅ Встигаємо" if plan.is_on_time else "❌ Затримка!"
        dl_color = "#27ae60" if plan.is_on_time else "#cc0000"

        self.status_labels["project"].config(text=plan.project_name)
        self.status_labels["operations"].config(text=str(plan.total_operations))
        self.status_labels["duration"].config(text=f"{duration.days} дн {duration.seconds//3600} год")
        self.status_labels["completion"].config(text=f"{plan.completion_percent:.0f}%")
        self.status_labels["deadline_status"].config(text=dl_text, foreground=dl_color)

        # Gantt
        self._draw_gantt()

        # Завантаження обладнання
        self._draw_load()

        # Таблиця
        self._update_table()

    def _draw_gantt(self):
        """Намалювати Gantt-діаграму."""
        for widget in self.gantt_container.winfo_children():
            widget.destroy()

        chart = GanttChart(self.current_plan, figsize=(14, max(6, len(self.current_plan.operations) * 0.4)))
        chart.draw(show_equipment=True)

        self.gantt_canvas = chart.get_canvas(self.gantt_container)
        self.gantt_canvas.draw()
        self.gantt_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _draw_load(self):
        """Намалювати діаграму завантаження."""
        for widget in self.load_container.winfo_children():
            widget.destroy()

        chart = EquipmentLoadChart(self.current_plan, figsize=(10, 5))
        chart.draw()

        self.load_canvas = chart.get_canvas(self.load_container)
        self.load_canvas.draw()
        self.load_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _update_table(self):
        """Оновити таблицю операцій."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for op in self.current_plan.operations:
            self.tree.insert("", tk.END, values=(
                op.product_name,
                op.operation_type.value,
                op.equipment.name,
                op.start_time.strftime("%d.%m %H:%M"),
                op.end_time.strftime("%d.%m %H:%M"),
                f"{op.duration_minutes:.0f} хв",
                op.status.value,
            ))

    def _export_png(self):
        """Експортувати діаграми в PNG."""
        if not self.current_plan:
            messagebox.showwarning("Увага", "Спочатку заплануйте виробництво.")
            return
        directory = filedialog.askdirectory(title="Виберіть папку для збереження")
        if not directory:
            return
        try:
            gantt = GanttChart(self.current_plan)
            gantt.draw()
            gantt.save(os.path.join(directory, "gantt_chart.png"))

            load = EquipmentLoadChart(self.current_plan)
            load.draw()
            load.save(os.path.join(directory, "equipment_load.png"))

            messagebox.showinfo("Готово", f"Діаграми збережено в:\n{directory}")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))

    def _export_pdf(self):
        """Експортувати діаграми в PDF."""
        if not self.current_plan:
            messagebox.showwarning("Увага", "Спочатку заплануйте виробництво.")
            return
        directory = filedialog.askdirectory(title="Виберіть папку для збереження")
        if not directory:
            return
        try:
            gantt = GanttChart(self.current_plan)
            gantt.draw()
            gantt.save(os.path.join(directory, "gantt_chart.pdf"))

            load = EquipmentLoadChart(self.current_plan)
            load.draw()
            load.save(os.path.join(directory, "equipment_load.pdf"))

            messagebox.showinfo("Готово", f"PDF збережено в:\n{directory}")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))
