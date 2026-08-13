"""
Вкладка "Розкрій металу" для GUI.
Розрахунок оптимального розкрою листів, візуалізація плану.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from ventilation_company.metal_cutting import MetalCutter
from ventilation_company.cnc_export import (CNCSettings, export_to_dxf, export_to_gcode, export_summary_text)

class CNCSettingsDialog(tk.Toplevel):
    """Діалог налаштувань ЧПУ верстата перед експортом."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("⚙️ Налаштування ЧПУ верстата")
        self.geometry("420x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result = None

        row = 0
        ttk.Label(self, text="Тип верстата:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=4)
        self.machine_var = tk.StringVar(value="plasma")
        ttk.Combobox(self, textvariable=self.machine_var,
                     values=["plasma", "laser", "gas"], state="readonly", width=18
                     ).grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)

        row += 1
        ttk.Label(self, text="Швидкість різу (мм/хв):").grid(row=row, column=0, sticky=tk.W, padx=10, pady=4)
        self.feed_var = tk.DoubleVar(value=1500)
        ttk.Spinbox(self, from_=100, to=20000, textvariable=self.feed_var, width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)

        row += 1
        ttk.Label(self, text="Висота підпалу (мм):").grid(row=row, column=0, sticky=tk.W, padx=10, pady=4)
        self.pierce_h_var = tk.DoubleVar(value=3.0)
        ttk.Spinbox(self, from_=0.5, to=50, increment=0.5, textvariable=self.pierce_h_var, width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)

        row += 1
        ttk.Label(self, text="Висота різу (мм):").grid(row=row, column=0, sticky=tk.W, padx=10, pady=4)
        self.cut_h_var = tk.DoubleVar(value=1.5)
        ttk.Spinbox(self, from_=0.1, to=20, increment=0.1, textvariable=self.cut_h_var, width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)

        row += 1
        ttk.Label(self, text="Висота підйому (мм):").grid(row=row, column=0, sticky=tk.W, padx=10, pady=4)
        self.retract_h_var = tk.DoubleVar(value=5.0)
        ttk.Spinbox(self, from_=1, to=100, increment=1, textvariable=self.retract_h_var, width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)

        row += 1
        ttk.Label(self, text="Затримка підпалу (с):").grid(row=row, column=0, sticky=tk.W, padx=10, pady=4)
        self.pierce_d_var = tk.DoubleVar(value=0.5)
        ttk.Spinbox(self, from_=0, to=5, increment=0.1, textvariable=self.pierce_d_var, width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)

        row += 1
        ttk.Label(self, text="Lead-in (мм):").grid(row=row, column=0, sticky=tk.W, padx=10, pady=4)
        self.lead_in_var = tk.DoubleVar(value=3.0)
        ttk.Spinbox(self, from_=0, to=50, increment=0.5, textvariable=self.lead_in_var, width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)

        row += 1
        ttk.Label(self, text="Lead-out (мм):").grid(row=row, column=0, sticky=tk.W, padx=10, pady=4)
        self.lead_out_var = tk.DoubleVar(value=3.0)
        ttk.Spinbox(self, from_=0, to=50, increment=0.5, textvariable=self.lead_out_var, width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)

        row += 1
        ttk.Label(self, text="Ширина пропилу (мм):").grid(row=row, column=0, sticky=tk.W, padx=10, pady=4)
        self.kerf_var = tk.DoubleVar(value=1.5)
        ttk.Spinbox(self, from_=0.1, to=10, increment=0.1, textvariable=self.kerf_var, width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)

        row += 1
        self.kerf_comp_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self, text="Компенсація пропилу", variable=self.kerf_comp_var
                        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=10, pady=4)

        row += 1
        ttk.Separator(self, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=10)

        row += 1
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="✅ OK", command=self._on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="⛔ Скасувати", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _on_ok(self):
        self.result = CNCSettings(
            machine_type=self.machine_var.get(),
            feed_rate=self.feed_var.get(),
            pierce_height=self.pierce_h_var.get(),
            cut_height=self.cut_h_var.get(),
            retract_height=self.retract_h_var.get(),
            pierce_delay=self.pierce_d_var.get(),
            lead_in_length=self.lead_in_var.get(),
            lead_out_length=self.lead_out_var.get(),
            kerf_width=self.kerf_var.get(),
            use_kerf_compensation=self.kerf_comp_var.get(),
        )
        self.destroy()

class CuttingTab:
    """Вкладка розкрою металу."""

    SHEET_SIZES = {
        "1250 x 2500 мм": (1250, 2500),
        "1000 x 2000 мм": (1000, 2000),
        "1500 x 3000 мм": (1500, 3000),
        "1250 x 3000 мм": (1250, 3000),
    }

    THICKNESSES = ["0.5", "0.7", "1.0", "1.2", "1.5", "2.0"]

    def __init__(self, parent: ttk.Notebook, get_products_callback):
        self.frame = ttk.Frame(parent)

        self.get_products = get_products_callback
        self.current_plan = None
        self._tooltip_win = None  # Toplevel для tooltip
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

        ttk.Button(left, text="Розрахувати розкрій", command=self._calculate).grid(
            row=3, column=0, columnspan=2, pady=15, sticky=tk.EW
        )

                # ── Експорт ЧПУ ──
        export_frame = ttk.LabelFrame(left, text="Експорт для ЧПУ", padding=5)
        export_frame.grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=10)

        ttk.Button(export_frame, text="📐 DXF (AutoCAD)", command=self._export_dxf
                   ).grid(row=0, column=0, padx=2, pady=2, sticky=tk.EW)
        ttk.Button(export_frame, text="⚙️ G-code", command=self._export_gcode
                   ).grid(row=0, column=1, padx=2, pady=2, sticky=tk.EW)
        ttk.Button(export_frame, text="📝 Зведення TXT", command=self._export_summary
                   ).grid(row=1, column=0, columnspan=2, padx=2, pady=2, sticky=tk.EW)

        self.results_frame = ttk.LabelFrame(left, text="Результати", padding=10)
        self.results_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=5)

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
            legend, text="[кольоровий] деталь  |  [сірий] вільне місце  |  масштаб: 1:4", foreground="#666"
        ).pack(side=tk.LEFT)

    def _calculate(self):
        products = self.get_products()
        self.run_cutting_for_products(products)

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

            self.current_plan = cutter.calculate_from_products(products)
            self._update_results()
            self._draw_sheets()

        except Exception as e:
            import traceback
            err = traceback.format_exc()
            print(err)  # виведе в консоль
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
                text=f"Лист {sheet_idx + 1}  ({sheet.width:.0f}x{sheet.height:.0f} мм)",
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

                # Привязка tooltip через Toplevel (безпечно, не зависає)
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

    # ── Tooltip через Toplevel (виправлення зависання) ──
    def _schedule_tooltip(self, event, placed, sheet_idx):
        """Запланувати показ tooltip через 300 мс — уникаємо миготіння."""
        self._cancel_tooltip()
        self._tooltip_after = self.canvas.after(300, lambda: self._show_tooltip(event, placed, sheet_idx))

    def _show_tooltip(self, event, placed, sheet_idx):
        """Показати tooltip у вигляді плаваючого Toplevel вікна."""
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

        # Створити Toplevel без рамки
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

        # Позиція: поруч з курсором, але трохи зміщено
        x = event.x_root + 12
        y = event.y_root + 12
        self._tooltip_win.geometry(f"+{x}+{y}")

    def _cancel_tooltip(self):
        """Сховати tooltip і скасувати відкладений показ."""
        if self._tooltip_after:
            self.canvas.after_cancel(self._tooltip_after)
            self._tooltip_after = None
        if self._tooltip_win:
            self._tooltip_win.destroy()
            self._tooltip_win = None

        # ── ЧПУ ЕКСПОРТ ──

    def _get_cnc_settings(self) -> CNCSettings:
        """Показати діалог і повернути налаштування ЧПУ."""
        dialog = CNCSettingsDialog(self.frame)
        self.frame.wait_window(dialog)
        return dialog.result or CNCSettings()

    def _export_dxf(self):
        if not self.current_plan:
            messagebox.showwarning("Увага", "Спочатку розрахуйте розкрій.")
            return
        from tkinter import filedialog
        fpath = filedialog.asksaveasfilename(
            defaultextension=".dxf",
            filetypes=[("DXF файли", "*.dxf"), ("Всі файли", "*.*")],
            title="Зберегти DXF",
        )
        if not fpath:
            return
        try:
            settings = self._get_cnc_settings()
            export_to_dxf(self.current_plan, fpath, settings)
            messagebox.showinfo("Готово", f"DXF збережено:\n{fpath}")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))

    def _export_gcode(self):
        if not self.current_plan:
            messagebox.showwarning("Увага", "Спочатку розрахуйте розкрій.")
            return
        from tkinter import filedialog
        directory = filedialog.askdirectory(title="Виберіть папку для G-code")
        if not directory:
            return
        try:
            settings = self._get_cnc_settings()
            paths = export_to_gcode(self.current_plan, directory, settings)
            msg = "\\n".join(os.path.basename(p) for p in paths)
            messagebox.showinfo("Готово", f"G-code збережено ({len(paths)} файлів):\\n{msg}")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))

    def _export_summary(self):
        if not self.current_plan:
            messagebox.showwarning("Увага", "Спочатку розрахуйте розкрій.")
            return
        from tkinter import filedialog
        fpath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Текстові файли", "*.txt"), ("Всі файли", "*.*")],
            title="Зберегти зведення",
        )
        if not fpath:
            return
        try:
            export_summary_text(self.current_plan, fpath)
            messagebox.showinfo("Готово", f"Зведення збережено:\\n{fpath}")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))

    def get_plan(self):
        return self.current_plan