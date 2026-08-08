"""Вкладка FreeCAD — 3D-моделі та експорт."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ventilation_company.freecad_models import FREECAD_AVAILABLE, export_products_to_freecad


class FreeCADTab:
    """Вкладка для роботи з 3D-моделями FreeCAD."""

    def __init__(self, parent, get_products_callback):
        self.parent = parent
        self.get_products_callback = get_products_callback
        self.frame = ttk.Frame(parent)
        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self.frame, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="🏗️ FreeCAD 3D Моделі", font=("Arial", 14, "bold")).pack(side=tk.LEFT)

        status_text = "✅ FreeCAD доступний" if FREECAD_AVAILABLE else "❌ FreeCAD не знайдено"
        status_color = "green" if FREECAD_AVAILABLE else "red"
        self.status_label = ttk.Label(top, text=status_text, foreground=status_color)
        self.status_label.pack(side=tk.RIGHT)

        if not FREECAD_AVAILABLE:
            info = ttk.Frame(self.frame, padding=20)
            info.pack(pady=20)
            ttk.Label(
                info,
                text="⚠️ FreeCAD не знайдено.",
                foreground="red",
                font=("Arial", 12, "bold"),
            ).pack()
            ttk.Label(
                info,
                text="Встановіть FreeCAD та перезапустіть програму.",
                foreground="#666",
            ).pack(pady=5)
            ttk.Label(
                info,
                text="Windows: https://www.freecad.org/downloads.php\n"
                "Linux: sudo apt install freecad\n"
                "macOS: brew install --cask freecad",
                foreground="#666",
                justify=tk.LEFT,
            ).pack()
            return

        ctrl = ttk.LabelFrame(self.frame, text="Експорт", padding=10)
        ctrl.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(ctrl, text="📦 Експорт усіх (.FCStd)", command=self._export_fcstd).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(ctrl, text="📐 Експорт усіх (.STEP)", command=self._export_step).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(ctrl, text="🖨️ Експорт усіх (.STL)", command=self._export_stl).pack(
            side=tk.LEFT, padx=5
        )

        list_frame = ttk.LabelFrame(self.frame, text="Вироби для експорту", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("name", "type", "dimensions", "actions")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        self.tree.heading("name", text="Назва")
        self.tree.heading("type", text="Тип")
        self.tree.heading("dimensions", text="Розміри (мм)")
        self.tree.heading("actions", text="Дії")
        self.tree.column("name", width=250)
        self.tree.column("type", width=200)
        self.tree.column("dimensions", width=150)
        self.tree.column("actions", width=200)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)

        self._refresh_list()

    def _get_products(self):
        products = self.get_products_callback()
        if isinstance(products, dict):
            return list(products.values())
        return products if products else []

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        products = self._get_products()
        for i, p in enumerate(products):
            name = getattr(p, "name", p.get("name", "—"))
            ptype = getattr(p, "product_type", p.get("type", "—"))
            w = getattr(p, "width", p.get("width", 0))
            h = getattr(p, "height", p.get("height", 0))
            length = getattr(p, "length", p.get("length", 0))
            dims = f"{w}×{h}×{length}"
            self.tree.insert("", tk.END, iid=str(i), values=(name, ptype, dims, "▶ Експорт"))

    def _on_double_click(self, event):
        item = self.tree.selection()
        if item:
            idx = int(item[0])
            self._export_single(idx, "fcstd")

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            menu = tk.Menu(self.frame, tearoff=0)
            menu.add_command(
                label="Експорт .FCStd", command=lambda: self._export_single(int(item), "fcstd")
            )
            menu.add_command(
                label="Експорт .STEP", command=lambda: self._export_single(int(item), "step")
            )
            menu.add_command(
                label="Експорт .STL", command=lambda: self._export_single(int(item), "stl")
            )
            menu.post(event.x_root, event.y_root)

    def _export_single(self, idx, fmt):
        products = self._get_products()
        if idx >= len(products):
            return
        product = products[idx]
        name = getattr(product, "name", "product")
        ext = {"fcstd": ".FCStd", "step": ".step", "stl": ".stl"}[fmt]
        filepath = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(fmt.upper(), f"*{ext}")],
            initialfile=f"{name}{ext}",
        )
        if not filepath:
            return
        try:
            export_products_to_freecad([product], filepath, fmt)
            messagebox.showinfo("Успіх", f"Збережено:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))

    def _export_fcstd(self):
        self._export_all("fcstd")

    def _export_step(self):
        self._export_all("step")

    def _export_stl(self):
        self._export_all("stl")

    def _export_all(self, fmt):
        products = self._get_products()
        if not products:
            messagebox.showwarning("Увага", "Додайте хоча б один виріб.")
            return
        ext = {"fcstd": ".FCStd", "step": ".step", "stl": ".stl"}[fmt]
        filepath = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(fmt.upper(), f"*{ext}")],
            initialfile=f"VentProject{ext}",
        )
        if not filepath:
            return
        try:
            export_products_to_freecad(products, filepath, fmt)
            messagebox.showinfo("Успіх", f"Збережено:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))
