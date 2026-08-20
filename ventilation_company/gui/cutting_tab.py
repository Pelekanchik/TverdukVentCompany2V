"""Вкладка "Розкрій металу" для GUI.
Розрахунок оптимального розкрою листів, візуалізація плану.

ПАТЧ:
    • Додано кнопки експорту G-код (плазма) та DXF (гільйотина)
    • Додано метод get_plan() для сумісності
    • Виправлено дублікат у __init__
    • Додано debug-логування в _calculate

ВСТАНОВЛЕННЯ:
    Замініть ventilation_company/gui/cutting_tab.py
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ventilation_company.metal_cutting import MetalCutter


class CuttingTab:
    """Вкладка розкрою металу."""

    SHEET_SIZES = {
        "1250 x 2500 мм": (1250, 2500),
        "1000 x 2000 мм": (1000, 2000),
        "1500 x 3000 мм": (1500, 3000),
        "1250 x 3000 мм": (1250, 3000),
    }

    THICKNESSES = ["0.5", "0.7", "1.0", "1.2", "1.5", "2.0"]

    def __init__(self, parent: ttk.Notebook, get_products_callback, get_standard_products_callback=None):
        self.frame = ttk.Frame(parent)

        self.get_products = get_products_callback
        self.get_standard_products = get_standard_products_callback
        self.current_plan = None
        self._tooltip_win = None
        self._tooltip_after = None

        self._build_ui()

    def _build_ui(self):
        left = ttk.LabelFrame(self.frame, text="Параметри листа", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        ttk.Label(left, text="Розмір листа:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.sheet_var = tk.StringVar(value="1250 x 2500 мм")
        ttk.Combobox(
            left,
            textvariable=self.sheet_var,
            values=list(self.SHEET_SIZES.keys()),
            state="readonly",
            width=18,
        ).grid(row=0, column=1, pady=2)

        ttk.Label(left, text="Товщина (мм):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.thick_var = tk.StringVar(value="0.7")
        ttk.Combobox(
            left,
            textvariable=self.thick_var,
            values=self.THICKNESSES,
            state="readonly",
            width=12,
        ).grid(row=1, column=1, pady=2)

        ttk.Label(left, text="Матеріал:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.material_var = tk.StringVar(value="оцинкована сталь")
        ttk.Combobox(
            left,
            textvariable=self.material_var,
            values=["оцинкована сталь", "нержавіюча сталь", "алюміній"],
            state="readonly",
            width=18,
        ).grid(row=2, column=1, pady=2)

        self.no_rotation_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            left,
            text="Заборонити поворот 90°",
            variable=self.no_rotation_var,
        ).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2)

        ttk.Button(left, text="Розрахувати розкрій", command=self._calculate).grid(
            row=4, column=0, columnspan=2, pady=15, sticky=tk.EW
        )

        # === НОВЕ: Кнопки експорту ===
        export_frame = ttk.LabelFrame(left, text="Експорт для ЧПУ", padding=5)
        export_frame.grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=5)
        ttk.Button(export_frame, text="🔥 G-код (плазма)", command=self._export_gcode).pack(fill=tk.X, pady=2)
        ttk.Button(export_frame, text="📐 DXF (гільйотина)", command=self._export_dxf).pack(fill=tk.X, pady=2)
        # =============================

        self.results_frame = ttk.LabelFrame(left, text="Результати", padding=10)
        self.results_frame.grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=5)

        self.result_labels = {}
        result_fields = [
            ("sheets", "Листів потрібно:"),
            ("total_area", "Загальна площа, м²:"),
            ("used_area", "Використано, м²:"),
            ("waste", "Відходи, м²:"),
            ("utilization", "Використання, %:"),
        ]
        for i, (key, text) in enumerate(result_fields):
            ttk.Label(self.results_frame, text=text).grid(row=i, column=0, sticky=tk.W, pady=1)
            lbl = ttk.Label(self.results_frame, text="—", font=("Arial", 10, "bold"))
            lbl.grid(row=i, column=1, sticky=tk.W, pady=1, padx=5)
            self.result_labels[key] = lbl

        right = ttk.LabelFrame(self.frame, text="Візуалізація листів", padding=5)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas_frame = ttk.Frame(right)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, bg="white", scrollregion=(0, 0, 2000, 5000))
        hbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        vbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        legend = ttk.Frame(right)
        legend.pack(fill=tk.X, pady=5)
        ttk.Label(
            legend, text="[кольоровий] деталь | [сірий] вільне місце | масштаб: 1:4", foreground="#666"
        ).pack(side=tk.LEFT)

    def _calculate(self):
        try:
            products = self.get_products()
            print(f"[DEBUG] Отримано {len(products) if products else 0} виробів для розкрою")
            if hasattr(self, "get_standard_products") and self.get_standard_products:
                sp = self.get_standard_products()
                print(f"[DEBUG] StandardProducts: {len(sp) if sp else 0}")
            self.run_cutting_for_products(products)
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            print(f"[DEBUG] ПОМИЛКА в _calculate: {err}")
            messagebox.showerror("Помилка", f"Помилка отримання виробів:\n{str(e)}\n\nДеталі в консолі.")

    def run_cutting_for_products(self, products):
        """Запустити розкрій для конкретного списку виробів (напр. з архіву)."""
        if not products:
            messagebox.showwarning("Увага", "У цьому проєкті немає виробів для розкрою.")
            return
        try:
            sheet_size = self.SHEET_SIZES[self.sheet_var.get()]
            thickness = float(self.thick_var.get())

            cutter = MetalCutter(
                sheet_width=sheet_size[0],
                sheet_height=sheet_size[1],
                thickness=thickness,
                material=self.material_var.get(),
            )

            # Етап 4: використовуємо точні розміри заготовки з StandardProduct
            allow_rotation = not self.no_rotation_var.get()
            if self.get_standard_products:
                standard_products = self.get_standard_products()
                if standard_products:
                    self.current_plan = cutter.calculate_from_standard_products(standard_products, allow_rotation=allow_rotation)
                else:
                    self.current_plan = cutter.calculate_from_products(products, allow_rotation=allow_rotation)
            else:
                self.current_plan = cutter.calculate_from_products(products, allow_rotation=allow_rotation)
            if self.get_standard_products:
                standard_products = self.get_standard_products()
                if standard_products:
                    self.current_plan = cutter.calculate_from_standard_products(standard_products)
                else:
                    self.current_plan = cutter.calculate_from_products(products)
            else:
                self.current_plan = cutter.calculate_from_products(products)
            self._update_results()
            self._draw_sheets()

        except Exception as e:
            import traceback
            err = traceback.format_exc()
            print(err)
            messagebox.showerror("Помилка", "Помилка розрахунку:\n" + str(e) + "\n\nДеталі в консолі.")

    def _update_results(self):
        if not self.current_plan:
            return

        s = self.current_plan.get_summary()
        self.result_labels["sheets"].config(text=str(s["total_sheets"]))
        self.result_labels["total_area"].config(text=f"{s['total_area_m2']:.3f}")
        self.result_labels["used_area"].config(text=f"{s['used_area_m2']:.3f}")
        self.result_labels["waste"].config(text=f"{s['waste_area_m2']:.3f}")
        self.result_labels["utilization"].config(text=f"{s['utilization_percent']:.1f}")

    def _draw_sheets(self):
        self.canvas.delete("all")

        if not self.current_plan:
            return

        scale = 0.25
        margin_x = 30
        margin_y = 30
        sheet_gap = 40

        x_offset = margin_x
        y_offset = margin_y

        for sheet_idx, sheet in enumerate(self.current_plan.sheets):
            sw = sheet.width * scale
            sh = sheet.height * scale

            self.canvas.create_rectangle(
                x_offset,
                y_offset,
                x_offset + sw,
                y_offset + sh,
                outline="#333",
                width=2,
                fill="#f5f5f5",
            )

            self.canvas.create_text(
                x_offset + 5,
                y_offset - 15,
                text=f"Лист {sheet_idx + 1} ({sheet.width:.0f}x{sheet.height:.0f} мм)",
                anchor=tk.W,
                font=("Arial", 9, "bold"),
            )

            colors = ["#3498db", "#2ecc71", "#e74c3c", "#9b59b6", "#f39c12", "#1abc9c", "#e67e22"]
            for i, placed in enumerate(sheet.placed_details):
                px = x_offset + placed.x * scale
                py = y_offset + placed.y * scale
                pw = placed.width * scale
                ph = placed.height * scale
                color = colors[i % len(colors)]

                rect_id = self.canvas.create_rectangle(
                    px, py, px + pw, py + ph, outline="white", width=1, fill=color
                )

                self.canvas.tag_bind(
                    rect_id, "<Enter>",
                    lambda e, p=placed, s=sheet_idx: self._schedule_tooltip(e, p, s)
                )
                self.canvas.tag_bind(rect_id, "<Leave>", lambda e: self._cancel_tooltip())

                if pw > 40 and ph > 20:
                    text_id = self.canvas.create_text(
                        px + pw / 2,
                        py + ph / 2,
                        text=placed.detail.name[:15],
                        fill="white",
                        font=("Arial", 7),
                        anchor=tk.CENTER,
                    )
                    self.canvas.tag_bind(
                        text_id, "<Enter>",
                        lambda e, p=placed, s=sheet_idx: self._schedule_tooltip(e, p, s)
                    )
                    self.canvas.tag_bind(text_id, "<Leave>", lambda e: self._cancel_tooltip())

            util = sheet.utilization * 100
            self.canvas.create_text(
                x_offset + sw / 2,
                y_offset + sh + 15,
                text=f"Використання: {util:.1f}%",
                anchor=tk.CENTER,
                font=("Arial", 8),
                fill="#666",
            )

            y_offset += sh + sheet_gap

        self.canvas.configure(scrollregion=(0, 0, 1500, y_offset + 50))

    # ── Tooltip ──
    def _schedule_tooltip(self, event, placed, sheet_idx):
        self._cancel_tooltip()
        self._tooltip_after = self.canvas.after(300, lambda: self._show_tooltip(event, placed, sheet_idx))

    def _show_tooltip(self, event, placed, sheet_idx):
        self._cancel_tooltip()

        detail = placed.detail
        w = placed.width
        h = placed.height
        area = w * h / 1_000_000

        text = (
            detail.name + "\n" +
            f"Розмір: {w:.1f} x {h:.1f} мм\n" +
            f"Площа: {area:.4f} м²\n" +
            "Повернуто: " + ("Так" if placed.rotated else "Ні") + "\n" +
            f"Лист: {sheet_idx + 1}"
        )

        self._tooltip_win = tk.Toplevel(self.canvas)
        self._tooltip_win.overrideredirect(True)
        self._tooltip_win.attributes("-topmost", True)
        self._tooltip_win.configure(bg="#fff9c4")

        lbl = tk.Label(
            self._tooltip_win,
            text=text,
            bg="#fff9c4",
            fg="#333",
            font=("Arial", 9),
            justify=tk.LEFT,
            padx=8,
            pady=5,
            relief=tk.SOLID,
            borderwidth=1,
        )
        lbl.pack()

        x = event.x_root + 12
        y = event.y_root + 12
        self._tooltip_win.geometry(f"+{x}+{y}")
        _tooltip_win.minsize(400, 300)
        _tooltip_win.resizable(True, True)

    def _cancel_tooltip(self):
        if self._tooltip_after:
            self.canvas.after_cancel(self._tooltip_after)
            self._tooltip_after = None
        if self._tooltip_win:
            self._tooltip_win.destroy()
            self._tooltip_win = None

    # ═════════════════════════════════════════════════════════════════
    #  НОВІ МЕТОДИ: Експорт G-код та DXF
    # ═════════════════════════════════════════════════════════════════

    def _export_gcode(self):
        """Експорт плану розкрою у G-код для плазменного різака."""
        if not self.current_plan or not self.current_plan.sheets:
            messagebox.showwarning("Увага", "Спочатку розрахуйте розкрій.")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".nc",
            filetypes=[("G-код (*.nc, *.tap)", "*.nc *.tap"), ("Всі файли", "*.*")],
            title="Експорт G-коду для плазми",
            initialfile=f"plasma_{self.material_var.get()}_{self.thick_var.get()}mm.nc",
        )
        if not filepath:
            return
        try:
            from ventilation_company.gcode_exporter import GCodeExporter, PlasmaSettings
            settings = PlasmaSettings(
                feed_rate=1500,
                rapid_feed=8000,
                pierce_delay=0.5,
                pierce_height=3.0,
                cut_height=1.5,
                safe_height=15.0,
                kerf_width=1.5,
            )
            exporter = GCodeExporter(settings)
            exporter.export_cutting_plan(self.current_plan, filepath)
            messagebox.showinfo("Успіх", f"G-код збережено:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося експортувати G-код:\n{e}")

    def _export_dxf(self):
        """Експорт плану розкрою у DXF для гільйотини/лазера."""
        if not self.current_plan or not self.current_plan.sheets:
            messagebox.showwarning("Увага", "Спочатку розрахуйте розкрій.")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".dxf",
            filetypes=[("DXF файл", "*.dxf"), ("Всі файли", "*.*")],
            title="Експорт DXF для гільйотини",
            initialfile=f"cutting_{self.material_var.get()}_{self.thick_var.get()}mm.dxf",
        )
        if not filepath:
            return
        try:
            from ventilation_company.dxf_exporter import DXFExporter, DXFSettings
            settings = DXFSettings(
                layer_details="DETAILS",
                layer_text="TEXT",
                layer_sheet="SHEET",
                text_height=8.0,
            )
            exporter = DXFExporter(settings)
            exporter.export_cutting_plan(self.current_plan, filepath)
            messagebox.showinfo("Успіх", f"DXF збережено:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося експортувати DXF:\n{e}")

    def get_plan(self):
        return self.current_plan