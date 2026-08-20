"""Діалог вибору пресету з бібліотеки типових розмірів + 3D прев'ю."""

import copy
import tkinter as tk
from tkinter import messagebox, ttk

from ventilation_company.product_presets_manager import PresetsManager
from ventilation_company.gui.preview_3d import ProductPreview3D
from ventilation_company.standard_products import StandardProduct
from ventilation_company.gui.dialog_utils import setup_dialog


class PresetDialog:
    """Модальний діалог для вибору пресету з 3D прев'ю."""

    def __init__(self, parent: tk.Widget, title: str = "Бібліотека типових розмірів"):
        self.parent = parent
        self.result = None
        self.manager = PresetsManager()

        self.top = tk.Toplevel(parent)
        setup_dialog(self.top, title=title, min_w=900, min_h=600)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(bg="#f5f5f5")

        self._build_ui()
        self._on_cat_changed()
        self.top.wait_window(self.top)

    def _build_ui(self):
        # === ВЕРХНЯ ПАНЕЛЬ ===
        header = ttk.Frame(self.top)
        header.pack(fill=tk.X, padx=10, pady=(10, 5))

        ttk.Label(header, text="📚 Бібліотека типових розмірів", font=("Arial", 14, "bold")).pack(side=tk.LEFT)

        # Категорія
        cat_frame = ttk.Frame(header)
        cat_frame.pack(side=tk.LEFT, padx=(30, 0))
        ttk.Label(cat_frame, text="Категорія:").pack(side=tk.LEFT)
        self.cat_var = tk.StringVar()
        self.cat_combo = ttk.Combobox(
            cat_frame, textvariable=self.cat_var, state="readonly", width=25
        )
        self.cat_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.cat_combo.bind("<<ComboboxSelected>>", self._on_cat_changed)

        # Пошук
        search_frame = ttk.Frame(header)
        search_frame.pack(side=tk.LEFT, padx=(20, 0))
        ttk.Label(search_frame, text="Пошук:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._filter_list())
        ttk.Entry(search_frame, textvariable=self.search_var, width=20).pack(side=tk.LEFT, padx=(5, 0))

        # === ОСНОВНИЙ КОНТЕНТ ===
        content = ttk.Frame(self.top)
        content.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # --- Ліва частина: список ---
        left = ttk.Frame(content)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Кнопки CRUD
        crud_frame = ttk.Frame(left)
        crud_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Button(
            crud_frame, text="➕ Додати", bg="#4CAF50", fg="white",
            font=("Arial", 9, "bold"), command=self._on_add_preset
        ).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(
            crud_frame, text="✏️ Редагувати", bg="#2196F3", fg="white",
            font=("Arial", 9, "bold"), command=self._on_edit_preset
        ).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(
            crud_frame, text="🗑️ Видалити", bg="#F44336", fg="white",
            font=("Arial", 9, "bold"), command=self._on_delete_preset
        ).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(
            crud_frame, text="↺ Скинути", bg="#FF9800", fg="white",
            font=("Arial", 9, "bold"), command=self._on_reset
        ).pack(side=tk.LEFT)

        # Таблиця
        cols = ("name", "size", "length", "material", "thickness")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=18)
        self.tree.heading("name", text="Назва")
        self.tree.heading("size", text="Переріз")
        self.tree.heading("length", text="Довжина")
        self.tree.heading("material", text="Матеріал")
        self.tree.heading("thickness", text="Товщ.")
        self.tree.column("name", width=220)
        self.tree.column("size", width=100)
        self.tree.column("length", width=70, anchor=tk.CENTER)
        self.tree.column("material", width=110)
        self.tree.column("thickness", width=50, anchor=tk.CENTER)

        vbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self._on_ok())

        # --- Права частина: 3D прев'ю + деталі ---
        right = ttk.Frame(content, width=420)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right.pack_propagate(False)

        # 3D прев'ю
        preview_label = ttk.Label(right, text="🔍 3D Перегляд", font=("Arial", 11, "bold"))
        preview_label.pack(pady=(0, 5))

        self.preview = ProductPreview3D(right, width=400, height=320)
        self.preview.pack(fill=tk.X)

        # Інфо про деталь
        self.info_frame = ttk.LabelFrame(right, text="Параметри", padding=5)
        self.info_frame.pack(fill=tk.X, pady=10)
        self.info_text = tk.Text(
            self.info_frame, height=6, width=45, wrap=tk.WORD,
            font=("Consolas", 9), bg="#f5f5f5", relief=tk.FLAT, state=tk.DISABLED
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)

        # === НИЖНЯ ПАНЕЛЬ ===
        bottom = ttk.Frame(self.top)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        # Кількість
        qty_frame = ttk.Frame(bottom)
        qty_frame.pack(side=tk.LEFT)
        ttk.Label(qty_frame, text="Кількість:").pack(side=tk.LEFT)
        self.qty_var = tk.StringVar(value="1")
        ttk.Entry(qty_frame, textvariable=self.qty_var, width=8).pack(side=tk.LEFT, padx=(5, 0))

        # Кнопки дії
        ttk.Button(bottom, text="❌ Скасувати", command=self._on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(bottom, text="➕ Додати", command=self._on_ok).pack(side=tk.RIGHT)

    def _on_cat_changed(self, event=None):
        cats = self.manager.get_by_category()
        cat_names = list(cats.keys())
        self.cat_combo["values"] = cat_names
        if not self.cat_var.get() or self.cat_var.get() not in cat_names:
            self.cat_var.set(cat_names[0] if cat_names else "")
        self._filter_list()

    def _filter_list(self):
        search = self.search_var.get().lower()
        cat = self.cat_var.get()
        cats = self.manager.get_by_category()
        presets = cats.get(cat, [])

        self.tree.delete(*self.tree.get_children())
        self._current_presets = []
        for p in presets:
            text = p.name.lower()
            if search and search not in text:
                continue
            size = f"{p.width:.0f}×{p.height:.0f}" if p.width != p.height else f"Ø{p.width:.0f}"
            mat = p._material_str() if hasattr(p, "_material_str") else str(p.material)
            thick = p._thickness_float() if hasattr(p, "_thickness_float") else float(p.thickness)
            self.tree.insert("", tk.END, values=(
                p.name, size, f"{p.length:.0f}", mat, f"{thick:.1f}"
            ), tags=(len(self._current_presets),))
            self._current_presets.append(p)

        self.preview.clear()
        self.preview.draw()
        self._update_info(None)

    def _on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        tags = item.get("tags", [])
        if not tags:
            return
        idx = int(tags[0])
        if 0 <= idx < len(self._current_presets):
            product = self._current_presets[idx]
            self.preview.show_product(product)
            self._update_info(product)

    def _update_info(self, product: StandardProduct | None):
        self.info_text.configure(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        if product:
            text = (
                f"Назва: {product.name}\n"
                f"Тип: {product.product_type}\n"
                f"Розміри: {product.width:.0f} × {product.height:.0f} × {product.length:.0f} мм\n"
                f"Площа поверхні: {product.surface_area:.4f} м²\n"
                f"Заготовка: {product.blank_area:.4f} м²\n"
                f"Матеріал: {product.material.value}\n"
                f"Товщина: {product.thickness.value} мм"
            )
            self.info_text.insert("1.0", text)
        self.info_text.configure(state=tk.DISABLED)

    def _on_ok(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Увага", "Оберіть виріб зі списку.", parent=self.top)
            return
        item = self.tree.item(sel[0])
        tags = item.get("tags", [])
        if not tags:
            return
        idx = int(tags[0])
        if idx < 0 or idx >= len(self._current_presets):
            return
        preset = self._current_presets[idx]
        try:
            qty = int(self.qty_var.get())
            if qty < 1:
                qty = 1
        except ValueError:
            qty = 1
        self.result = copy.deepcopy(preset)
        self.result.quantity = qty
        self.result.__post_init__()
        self.top.destroy()

    def _on_cancel(self):
        self.top.destroy()

    def _on_add_preset(self):
        """Додати новий пресет (спрощено — копія обраного з редагуванням)."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Увага", "Спочатку оберіть виріб для копіювання.", parent=self.top)
            return
        item = self.tree.item(sel[0])
        tags = item.get("tags", [])
        if not tags:
            return
        idx = int(tags[0])
        base = self._current_presets[idx]

        dlg = _PresetEditorDialog(self.top, base)
        if dlg.result:
            if self.manager.add(dlg.result):
                self._on_cat_changed()
                messagebox.showinfo("Успіх", f"Пресет '{dlg.result.name}' додано.", parent=self.top)
            else:
                messagebox.showwarning("Увага", "Пресет з такою назвою вже існує.", parent=self.top)

    def _on_edit_preset(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Увага", "Оберіть виріб для редагування.", parent=self.top)
            return
        item = self.tree.item(sel[0])
        tags = item.get("tags", [])
        if not tags:
            return
        idx = int(tags[0])
        base = self._current_presets[idx]

        # Знайти глобальний індекс
        all_presets = self.manager.get_all()
        global_idx = None
        for i, p in enumerate(all_presets):
            if p.name == base.name:
                global_idx = i
                break
        if global_idx is None:
            return

        dlg = _PresetEditorDialog(self.top, base)
        if dlg.result:
            self.manager.update(global_idx, dlg.result)
            self._on_cat_changed()
            messagebox.showinfo("Успіх", f"Пресет '{dlg.result.name}' оновлено.", parent=self.top)

    def _on_delete_preset(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Увага", "Оберіть виріб для видалення.", parent=self.top)
            return
        item = self.tree.item(sel[0])
        name = item["values"][0]
        if not messagebox.askyesno("Підтвердження", f"Видалити пресет '{name}'?", parent=self.top):
            return
        all_presets = self.manager.get_all()
        for i, p in enumerate(all_presets):
            if p.name == name:
                self.manager.remove(i)
                break
        self._on_cat_changed()

    def _on_reset(self):
        if messagebox.askyesno("Підтвердження", "Скинути бібліотеку до заводських налаштувань?\nВсі ваші зміни будуть втрачені!", parent=self.top):
            self.manager.reset_to_defaults()
            self._on_cat_changed()


def choose_preset(parent: tk.Widget) -> object | None:
    """Відкрити діалог вибору пресету."""
    dlg = PresetDialog(parent)
    return dlg.result


class _PresetEditorDialog:
    """Внутрішній діалог для редагування/додавання пресету."""

    def __init__(self, parent, base: StandardProduct):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title("Редактор пресету")
        self.top.geometry("350x450")
        top.minsize(400, 300)
        top.resizable(True, True)
        self.top.transient(parent)
        self.top.grab_set()

        ttk.Label(self.top, text="Назва:").pack(pady=(10, 0))
        self.name_var = tk.StringVar(value=base.name)
        ttk.Entry(self.top, textvariable=self.name_var, width=35).pack()

        ttk.Label(self.top, text="Ширина (мм):").pack(pady=(10, 0))
        self.w_var = tk.StringVar(value=str(base.width))
        ttk.Entry(self.top, textvariable=self.w_var, width=15).pack()

        ttk.Label(self.top, text="Висота (мм):").pack(pady=(10, 0))
        self.h_var = tk.StringVar(value=str(base.height))
        ttk.Entry(self.top, textvariable=self.h_var, width=15).pack()

        ttk.Label(self.top, text="Довжина (мм):").pack(pady=(10, 0))
        self.l_var = tk.StringVar(value=str(base.length))
        ttk.Entry(self.top, textvariable=self.l_var, width=15).pack()

        ttk.Label(self.top, text="Тип виробу:").pack(pady=(10, 0))
        self.type_var = tk.StringVar(value=base.product_type)
        ttk.Entry(self.top, textvariable=self.type_var, width=35).pack()

        ttk.Label(self.top, text="Матеріал:").pack(pady=(10, 0))
        self.mat_var = tk.StringVar(value=base._material_str() if hasattr(base, "_material_str") else str(base.material))
        ttk.Combobox(self.top, textvariable=self.mat_var, values=["оцинкована сталь", "нержавіюча сталь", "алюміній"], state="readonly", width=25).pack()

        ttk.Label(self.top, text="Товщина:").pack(pady=(10, 0))
        self.thick_var = tk.StringVar(value=str(base._thickness_float() if hasattr(base, "_thickness_float") else float(base.thickness)))
        ttk.Combobox(self.top, textvariable=self.thick_var, values=["0.5", "0.7", "1.0", "1.2", "1.5", "2.0"], state="readonly", width=10).pack()

        btn_frame = ttk.Frame(self.top)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Зберегти", command=self._on_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Скасувати", command=self.top.destroy).pack(side=tk.LEFT, padx=5)

        self.top.wait_window(self.top)

    def _on_save(self):
        from ventilation_company.standard_products import MaterialType, Thickness
        try:
            w = float(self.w_var.get())
            h = float(self.h_var.get())
            l = float(self.l_var.get())
            qty = 1
            name = self.name_var.get().strip()
            if not name:
                raise ValueError("Назва не може бути порожньою")
            ptype = self.type_var.get()
            mat_str = self.mat_var.get()
            mat = MaterialType.GALVANIZED
            for m in MaterialType:
                if m.value == mat_str:
                    mat = m
                    break
            thick_val = float(self.thick_var.get())
            thick = Thickness.T0_7
            for t in Thickness:
                if abs(t.value - thick_val) < 0.01:
                    thick = t
                    break

            # Створюємо базовий продукт (спрощено — RectDuct, можна розширити)
            from ventilation_company.standard_products import RectDuct, RoundDuct
            if "кругл" in ptype.lower():
                p = RoundDuct(name=name, product_type=ptype, width=w, height=w, length=l, thickness=thick, material=mat, quantity=qty)
            else:
                p = RectDuct(name=name, product_type=ptype, width=w, height=h, length=l, thickness=thick, material=mat, quantity=qty)
            self.result = p
            self.top.destroy()
        except Exception as e:
            messagebox.showerror("Помилка", f"Некоректні дані: {e}", parent=self.top)