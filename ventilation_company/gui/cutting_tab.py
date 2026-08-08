"""
Вкладка "Розкрій металу" для GUI.
Розрахунок оптимального розкрою листів, візуалізація плану.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from ventilation_company.metal_cutting import MetalCutter


class CuttingTab:
    """Вкладка розкрою металу."""

    SHEET_SIZES = {
        "1250 × 2500 мм": (1250, 2500),
        "1000 × 2000 мм": (1000, 2000),
        "1500 × 3000 мм": (1500, 3000),
        "1250 × 3000 мм": (1250, 3000),
    }

    def __init__(self, parent: ttk.Notebook, get_products_callback):
        self.frame = ttk.Frame(parent)

        self.get_products = get_products_callback
        self.current_plan = None

        self._build_ui()

    def _build_ui(self):
        left = ttk.LabelFrame(self.frame, text="Параметри листа", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        ttk.Label(left, text="Розмір листа:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.sheet_var = tk.StringVar(value="1250 × 2500 мм")
        ttk.Combobox(
            left,
            textvariable=self.sheet_var,
            values=list(self.SHEET_SIZES.keys()),
            state="readonly",
            width=18,
        ).grid(row=0, column=1, pady=2)

        ttk.Label(left, text="Товщина (мм):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.thick_var = tk.StringVar(value="0.7")
        ttk.Entry(left, textvariable=self.thick_var, width=12).grid(row=1, column=1, pady=2)

        ttk.Label(left, text="Матеріал:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.material_var = tk.StringVar(value="оцинкована сталь")
        ttk.Combobox(
            left,
            textvariable=self.material_var,
            values=["оцинкована сталь", "нержавіюча сталь", "алюміній"],
            state="readonly",
            width=18,
        ).grid(row=2, column=1, pady=2)

        ttk.Button(left, text="🧮 Розрахувати розкрій", command=self._calculate).grid(
            row=3, column=0, columnspan=2, pady=15, sticky=tk.EW
        )

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
            legend, text="🟦 деталь  |  ⬜ вільне місце  |  масштаб: 1:4", foreground="#666"
        ).pack(side=tk.LEFT)

    def _calculate(self):
        products = self.get_products()
        if not products:
            messagebox.showwarning("Увага", "Додайте вироби у вкладці 'Вироби'.")
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
            messagebox.showerror("Помилка", f"Помилка розрахунку:\n{str(e)}")

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
                text=f"Лист {sheet_idx + 1}  ({sheet.width:.0f}×{sheet.height:.0f} мм)",
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

                self.canvas.create_rectangle(
                    px, py, px + pw, py + ph, outline="white", width=1, fill=color
                )

                if pw > 40 and ph > 20:
                    self.canvas.create_text(
                        px + pw / 2,
                        py + ph / 2,
                        text=placed.detail.name[:15],
                        fill="white",
                        font=("Arial", 7),
                        anchor=tk.CENTER,
                    )

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

    def get_plan(self):
        return self.current_plan
