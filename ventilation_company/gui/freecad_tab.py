"""Вкладка FreeCAD — 3D-моделі, попередній перегляд та експорт."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ventilation_company.freecad_models import (
    FREECAD_AVAILABLE,
    FREECAD_VERSION,
    get_freecad_info,
    export_products_to_freecad,
    export_batch,
    show_preview,
)

# Preview module
try:
    from ventilation_company.freecad_preview import FreeCADPreview
    PREVIEW_AVAILABLE = True
except ImportError:
    PREVIEW_AVAILABLE = False


class FreeCADTab:
    """Вкладка для роботи з 3D-моделями FreeCAD з попереднім переглядом."""

    EXPORT_FORMATS = {
        "fcstd": ("FreeCAD Document", ".FCStd"),
        "step":  ("STEP", ".step"),
        "stl":   ("STL (3D друк)", ".stl"),
        "obj":   ("Wavefront OBJ", ".obj"),
        "iges":  ("IGES", ".igs"),
    }

    def __init__(self, parent, get_products_callback):
        self.parent = parent
        self.get_products_callback = get_products_callback
        self.frame = ttk.Frame(parent)
        self._progress_var = tk.DoubleVar(value=0)
        self._build_ui()

    def _build_ui(self):
        # ── Top status bar ──
        top = ttk.Frame(self.frame, padding=5)
        top.pack(fill=tk.X)

        ttk.Label(top, text="🏗️ FreeCAD 3D Моделі", font=("Arial", 14, "bold")).pack(side=tk.LEFT)

        info = get_freecad_info()
        if info["available"]:
            ver_text = f"✅ FreeCAD {info['version'] or 'доступний'}"
            ver_color = "green"
        else:
            ver_text = "❌ FreeCAD не знайдено"
            ver_color = "red"
        self.status_label = ttk.Label(top, text=ver_text, foreground=ver_color)
        self.status_label.pack(side=tk.RIGHT)

        # ── Main area: left (controls + list) | right (preview) ──
        paned = ttk.PanedWindow(self.frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left = ttk.Frame(paned)
        paned.add(left, weight=1)

        right = ttk.Frame(paned)
        paned.add(right, weight=2)

        # ── Left: Controls ──
        ctrl = ttk.LabelFrame(left, text="Експорт", padding=10)
        ctrl.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(ctrl, text="Формат:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.fmt_var = tk.StringVar(value="step")
        fmt_combo = ttk.Combobox(ctrl, textvariable=self.fmt_var,
                                  values=list(self.EXPORT_FORMATS.keys()),
                                  state="readonly", width=18)
        fmt_combo.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        fmt_combo.bind("<<ComboboxSelected>>", self._on_format_change)

        ttk.Label(ctrl, text="Відстань між виробами (мм):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.spacing_var = tk.DoubleVar(value=50)
        ttk.Spinbox(ctrl, from_=0, to=500, increment=10,
                    textvariable=self.spacing_var, width=8).grid(row=1, column=1, sticky=tk.W, pady=2, padx=5)

        btn_frame = ttk.Frame(ctrl)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="📦 Експорт усіх", command=self._export_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📁 Пакетний експорт", command=self._export_batch).pack(side=tk.LEFT, padx=2)

        if PREVIEW_AVAILABLE:
            ttk.Button(btn_frame, text="🔍 Попередній перегляд", command=self._show_preview).pack(side=tk.LEFT, padx=2)

        # Progress bar
        self.progress = ttk.Progressbar(ctrl, variable=self._progress_var, maximum=100)
        self.progress.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=5)

        # ── Left: Product list ──
        list_frame = ttk.LabelFrame(left, text="Вироби для експорту", padding=5)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("sel", "name", "type", "dimensions", "actions")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        self.tree.heading("sel", text="✓")
        self.tree.heading("name", text="Назва")
        self.tree.heading("type", text="Тип")
        self.tree.heading("dimensions", text="Розміри (мм)")
        self.tree.heading("actions", text="Дії")
        self.tree.column("sel", width=30, anchor=tk.CENTER)
        self.tree.column("name", width=180)
        self.tree.column("type", width=120)
        self.tree.column("dimensions", width=120)
        self.tree.column("actions", width=100)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)

        # Selection tracking
        self._selected = set()

        # ── Right: Preview panel ──
        if PREVIEW_AVAILABLE:
            preview_frame = ttk.LabelFrame(right, text="Попередній перегляд 3D", padding=5)
            preview_frame.pack(fill=tk.BOTH, expand=True)
            self.preview = FreeCADPreview(preview_frame)
        else:
            info_frame = ttk.LabelFrame(right, text="Попередній перегляд", padding=20)
            info_frame.pack(fill=tk.BOTH, expand=True)
            ttk.Label(info_frame, text="🔍 Для попереднього перегляду встановіть matplotlib:",
                      foreground="#666").pack(pady=5)
            ttk.Label(info_frame, text="pip install matplotlib", foreground="blue",
                      font=("Consolas", 10)).pack()
            self.preview = None

        self._refresh_list()

    def _get_products(self):
        products = self.get_products_callback()
        if isinstance(products, dict):
            return list(products.values())
        return products if products else []

    def _product_to_dict(self, p):
        if hasattr(p, "to_dict"):
            return p.to_dict()
        elif isinstance(p, dict):
            return p
        return dict(p)

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._selected.clear()

        products = self._get_products()
        for i, p in enumerate(products):
            name = getattr(p, "name", p.get("name", "—"))
            
            # FIX: правильно отримуємо тип для об'єкта і dict
            if isinstance(p, dict):
                ptype = p.get("product_type", p.get("type", "—"))
                w = p.get("width", 0)
                h = p.get("height", 0)
                length = p.get("length", 0)
                angle = p.get("angle", 0)
                radius = p.get("radius", 0)
                bw = p.get("branch_width", p.get("branch_diameter", 0))
                bl = p.get("branch_length", 0)
                ew = p.get("end_width", p.get("end_diameter", 0))
                eh = p.get("end_height", 0)
            else:
                ptype = getattr(p, "product_type", getattr(p, "type", "—"))
                w = getattr(p, "width", 0)
                h = getattr(p, "height", 0)
                length = getattr(p, "length", 0)
                angle = getattr(p, "angle", 0)
                radius = getattr(p, "radius", 0)
                bw = getattr(p, "branch_width", getattr(p, "branch_diameter", 0))
                bl = getattr(p, "branch_length", 0)
                ew = getattr(p, "end_width", getattr(p, "end_diameter", 0))
                eh = getattr(p, "end_height", 0)
            
            # FIX: адаптивні розміри залежно від типу виробу
            ptype_lower = str(ptype).lower()
            if "elbow" in ptype_lower:
                dims = f"{w:.0f}×{h:.0f} ∠{angle:.0f}° R{radius:.0f}"
            elif "tee" in ptype_lower:
                dims = f"{w:.0f}×{h:.0f}→{bw:.0f}×{bl:.0f}"
            elif "transition" in ptype_lower:
                dims = f"{w:.0f}×{h:.0f}→{ew:.0f}×{eh:.0f}"
            else:
                dims = f"{w:.0f}×{h:.0f}×{length:.0f}"
            
            self.tree.insert("", tk.END, iid=str(i), values=("☐", name, ptype, dims, "▶ Експорт"))

    def _on_tree_click(self, event):
        """Handle checkbox click."""
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            col = self.tree.identify_column(event.x)
            if col == "#1":  # Checkbox column
                item = self.tree.identify_row(event.y)
                if item:
                    if item in self._selected:
                        self._selected.remove(item)
                        self.tree.set(item, "sel", "☐")
                    else:
                        self._selected.add(item)
                        self.tree.set(item, "sel", "☑")
                return "break"

    def _on_double_click(self, event):
        item = self.tree.selection()
        if item:
            idx = int(item[0])
            self._export_single(idx, self.fmt_var.get())

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            menu = tk.Menu(self.frame, tearoff=0)
            for fmt_key, (fmt_name, _) in self.EXPORT_FORMATS.items():
                menu.add_command(
                    label=f"Експорт {fmt_name}",
                    command=lambda f=fmt_key, idx=int(item): self._export_single(idx, f)
                )
            menu.add_separator()
            menu.add_command(label="Попередній перегляд", command=lambda: self._preview_single(int(item)))
            menu.post(event.x_root, event.y_root)

    def _on_format_change(self, event=None):
        pass

    def _get_selected_products(self):
        products = self._get_products()
        if self._selected:
            return [products[int(i)] for i in sorted(self._selected, key=int)]
        return products

    def _export_single(self, idx, fmt):
        products = self._get_products()
        if idx >= len(products):
            return
        product = products[idx]
        name = getattr(product, "name", "product")
        ext = self.EXPORT_FORMATS[fmt][1]
        filepath = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(self.EXPORT_FORMATS[fmt][0], f"*{ext}")],
            initialfile=f"{name}{ext}",
        )
        if not filepath:
            return
        self._run_export([product], filepath, fmt)

    def _export_all(self):
        products = self._get_selected_products()
        if not products:
            messagebox.showwarning("Увага", "Додайте хоча б один виріб або виберіть зі списку.")
            return
        fmt = self.fmt_var.get()
        ext = self.EXPORT_FORMATS[fmt][1]
        filepath = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(self.EXPORT_FORMATS[fmt][0], f"*{ext}")],
            initialfile=f"VentProject{ext}",
        )
        if not filepath:
            return
        self._run_export(products, filepath, fmt)

    def _export_batch(self):
        products = self._get_selected_products()
        if not products:
            messagebox.showwarning("Увага", "Додайте хоча б один виріб.")
            return
        output_dir = filedialog.askdirectory(title="Виберіть папку для пакетного експорту")
        if not output_dir:
            return
        fmt = self.fmt_var.get()
        try:
            self._progress_var.set(0)
            self.frame.update_idletasks()

            def progress(current, total):
                self._progress_var.set((current / total) * 100)
                self.frame.update_idletasks()

            exported = export_batch(products, output_dir, fmt, progress_callback=progress)
            messagebox.showinfo("Успіх", f"Експортовано {len(exported)} файлів у:\n{output_dir}")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))
        finally:
            self._progress_var.set(0)

    def _run_export(self, products, filepath, fmt):
        try:
            self._progress_var.set(10)
            self.frame.update_idletasks()

            def progress(current, total):
                self._progress_var.set(10 + (current / total) * 80)
                self.frame.update_idletasks()

            export_products_to_freecad(products, filepath, fmt, progress_callback=progress)
            self._progress_var.set(100)
            messagebox.showinfo("Успіх", f"Збережено:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))
        finally:
            self._progress_var.set(0)

    def _show_preview(self):
        products = self._get_products()
        if not products:
            messagebox.showwarning("Увага", "Додайте хоча б один виріб.")
            return
        if self.preview:
            self.preview.set_products(products)
        else:
            try:
                show_preview(self.frame.winfo_toplevel(), products)
            except Exception as e:
                messagebox.showerror("Помилка", str(e))

    def _preview_single(self, idx):
        products = self._get_products()
        if idx < len(products):
            try:
                show_preview(self.frame.winfo_toplevel(), [products[idx]])
            except Exception as e:
                messagebox.showerror("Помилка", str(e))
