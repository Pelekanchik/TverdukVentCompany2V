"""Вкладка "Націнки по категоріях" для GUI."""

import tkinter as tk
from tkinter import messagebox, ttk


STANDARD_SIZES = {
    50, 100, 150, 200, 250, 300, 350, 400, 450, 500,
    550, 600, 650, 700, 750, 800, 850, 900, 950, 1000,
    1250,
}

MATERIALS = ["цинк", "нержавійка", "алюміній"]
PRODUCT_TYPES = [
    "прямокутні_труби",
    "прямокутні_фасонні",
    "круглі_труби",
    "круглі_фасонні",
]
PRODUCT_TYPE_LABELS = {
    "прямокутні_труби": "Прямокутні труби",
    "прямокутні_фасонні": "Прямокутні фасонні вироби",
    "круглі_труби": "Круглі труби",
    "круглі_фасонні": "Круглі фасонні вироби",
}
THICKNESSES = ["0.5", "0.7", "0.9", "1.0", "1.2", "1.5", "2.0"]


def is_standard_size(width=0, height=0, length=0, diameter=0):
    """Перевірити, чи всі розміри виробу стандартні."""
    dims = [d for d in [width, height, length, diameter] if d and d > 0]
    if not dims:
        return True
    return all(round(d) in STANDARD_SIZES for d in dims)


def classify_product(name="", product_type="", material=""):
    """Визначити матеріал і категорію виробу за назвою/типом/матеріалом."""
    mat_lower = material.lower()
    name_lower = (name + " " + product_type).lower()

    if "нержав" in mat_lower or "stainless" in mat_lower or "нерж" in name_lower:
        material_key = "нержавійка"
    elif "алюм" in mat_lower or "alumin" in mat_lower:
        material_key = "алюміній"
    else:
        material_key = "цинк"

    is_round = "кругл" in name_lower or "round" in name_lower or "спірал" in name_lower
    is_duct = "труб" in name_lower or "duct" in name_lower or "повітропровід" in name_lower

    if is_round:
        category = "круглі_труби" if is_duct else "круглі_фасонні"
    else:
        category = "прямокутні_труби" if is_duct else "прямокутні_фасонні"

    return material_key, category


def build_default_markup_matrix():
    """Побудувати матрицю націнок за замовчуванням."""
    matrix = {}
    for mat in MATERIALS:
        matrix[mat] = {}
        for ptype in PRODUCT_TYPES:
            matrix[mat][ptype] = {}
            for th in THICKNESSES:
                base = {"цинк": 30.0, "нержавійка": 45.0, "алюміній": 35.0}[mat]
                add = 5.0 if "фасонні" in ptype else 0.0
                th_add = float(th) * 2.0
                std = round(base + add + th_add, 1)
                nonstd = round(std + 5.0, 1)
                matrix[mat][ptype][th] = {"standard": std, "nonstandard": nonstd}
    return matrix


class MarkupMatrixTab:
    """Вкладка матриці націнок."""

    def __init__(self, parent, settings):
        self.settings = settings
        self.frame = ttk.Frame(parent)
        self._build_ui()
        self._refresh_tree()

    def _build_ui(self):
        top = ttk.Frame(self.frame, padding=5)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Матриця націнок по категоріях", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(top, text="Зберегти", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(top, text="Скинути за замовчуванням", command=self._reset_defaults).pack(side=tk.RIGHT, padx=5)

        left = ttk.LabelFrame(self.frame, text="Фільтр", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        ttk.Label(left, text="Матеріал:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.mat_var = tk.StringVar(value=MATERIALS[0])
        mat_combo = ttk.Combobox(left, textvariable=self.mat_var, values=MATERIALS, state="readonly", width=15)
        mat_combo.grid(row=0, column=1, padx=5, pady=3)
        mat_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_tree())

        ttk.Label(left, text="Тип виробу:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.type_var = tk.StringVar(value=PRODUCT_TYPE_LABELS[PRODUCT_TYPES[0]])
        self.type_combo = ttk.Combobox(
            left, textvariable=self.type_var,
            values=[PRODUCT_TYPE_LABELS[t] for t in PRODUCT_TYPES],
            state="readonly", width=30
        )
        self.type_combo.grid(row=1, column=1, padx=5, pady=3)
        self.type_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_tree())

        help_text = (
            "Стандартні розміри (мм):\n"
            "  50, 100, 150, 200, 250, 300, 350, 400,\n"
            "  450, 500, 550, 600, 650, 700, 750, 800,\n"
            "  850, 900, 950, 1000\n\n"
            "Все інше - нестандартні розміри.\n\n"
            "Націнка застосовується:\n"
            "  (вартість виробу) x (1 + націнка%/100)"
        )
        ttk.Label(left, text=help_text, foreground="#2E7D32", justify=tk.LEFT,
                  font=("Consolas", 9)).grid(row=2, column=0, columnspan=2, pady=15, sticky=tk.W)

        right = ttk.Frame(self.frame)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(right, text="Товщина металу -> Націнка (%)", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=5)

        columns = ("thickness", "standard", "nonstandard")
        self.tree = ttk.Treeview(right, columns=columns, show="headings", height=12)
        self.tree.heading("thickness", text="Товщина, мм")
        self.tree.heading("standard", text="Стандартні вироби, %")
        self.tree.heading("nonstandard", text="Нестандартні вироби, %")
        self.tree.column("thickness", width=120, anchor=tk.CENTER)
        self.tree.column("standard", width=180, anchor=tk.CENTER)
        self.tree.column("nonstandard", width=180, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", lambda e: self._edit_dialog())

        edit = ttk.LabelFrame(right, text="Редагування", padding=10)
        edit.pack(fill=tk.X, pady=10)

        ttk.Label(edit, text="Товщина:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.edit_th_var = tk.StringVar()
        ttk.Entry(edit, textvariable=self.edit_th_var, width=10, state="readonly").grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(edit, text="Стандартна націнка (%):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.edit_std_var = tk.StringVar(value="30.0")
        ttk.Entry(edit, textvariable=self.edit_std_var, width=10).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(edit, text="Нестандартна націнка (%):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.edit_non_var = tk.StringVar(value="35.0")
        ttk.Entry(edit, textvariable=self.edit_non_var, width=10).grid(row=2, column=1, padx=5, pady=2)

        ttk.Button(edit, text="Застосувати", command=self._apply_edit).grid(row=3, column=0, columnspan=2, pady=10)

    def _get_current_keys(self):
        mat = self.mat_var.get()
        type_label = self.type_var.get()
        type_key = None
        for k, v in PRODUCT_TYPE_LABELS.items():
            if v == type_label:
                type_key = k
                break
        if type_key is None:
            type_key = PRODUCT_TYPES[0]
        return mat, type_key

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        mat, ptype = self._get_current_keys()
        data = self.settings.markup_matrix.get(mat, {}).get(ptype, {})

        for th in THICKNESSES:
            vals = data.get(th, {"standard": 30.0, "nonstandard": 35.0})
            self.tree.insert(
                "", tk.END,
                values=(th, f"{vals['standard']:.1f}", f"{vals['nonstandard']:.1f}")
            )

    def _edit_dialog(self):
        selected = self.tree.selection()
        if not selected:
            return
        idx = self.tree.index(selected[0])
        th = THICKNESSES[idx]
        mat, ptype = self._get_current_keys()
        vals = self.settings.markup_matrix.get(mat, {}).get(ptype, {}).get(th, {"standard": 30.0, "nonstandard": 35.0})

        self.edit_th_var.set(th)
        self.edit_std_var.set(str(vals["standard"]))
        self.edit_non_var.set(str(vals["nonstandard"]))

    def _apply_edit(self):
        th = self.edit_th_var.get()
        if not th:
            messagebox.showwarning("Увага", "Оберіть товщину з таблиці (подвійний клік).")
            return
        try:
            std = float(self.edit_std_var.get())
            non = float(self.edit_non_var.get())
        except ValueError:
            messagebox.showwarning("Увага", "Націнки мають бути числами.")
            return

        mat, ptype = self._get_current_keys()
        if mat not in self.settings.markup_matrix:
            self.settings.markup_matrix[mat] = {}
        if ptype not in self.settings.markup_matrix[mat]:
            self.settings.markup_matrix[mat][ptype] = {}
        self.settings.markup_matrix[mat][ptype][th] = {"standard": std, "nonstandard": non}
        self._refresh_tree()

    def _save(self):
        self.settings.save()
        messagebox.showinfo("Успіх", "Матрицю націнок збережено!")

    def _reset_defaults(self):
        if messagebox.askyesno("Підтвердження", "Скинути матрицю націнок до замовчування?"):
            self.settings.markup_matrix = build_default_markup_matrix()
            self._refresh_tree()
            self.settings.save()
