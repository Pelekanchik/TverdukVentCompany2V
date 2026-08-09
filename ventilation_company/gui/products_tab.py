"""Вкладка "Вироби" для GUI."""

import copy
import re
import tkinter as tk
from collections.abc import Callable
from dataclasses import fields
from tkinter import filedialog, messagebox, ttk

from ventilation_company.freecad_models import FREECAD_AVAILABLE, export_products_to_freecad
from ventilation_company.standard_products import (
    FlexibleConnector,
    MaterialType,
    ProductLibrary,
    RectCap,
    RectElbow,
    RectFlange,
    RectTee,
    RectTransition,
    RoundCap,
    RoundElbow,
    RoundFlange,
    RoundTee,
    RoundTransition,
    StandardProduct,
    Thickness,
    make_rect_duct,
    make_round_duct,
)

from ventilation_company.gui.markup_matrix_tab import classify_product, is_standard_size
from ventilation_company.gui.settings_tab import PricingSettings


# ── TOOLTIP КЛАС ────────────────────────────────────────────

class Tooltip:
    """Вспливаюча підказка для віджетів tkinter."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        widget.bind("<ButtonPress>", self._on_leave)

    def _on_enter(self, event=None):
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#ffffe0", relief=tk.SOLID, borderwidth=1,
            font=("tahoma", "9", "normal"), padx=5, pady=3
        )
        label.pack(ipadx=1)

    def _on_leave(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


# ── КОНСТАНТИ ──────────────────────────────────────────────

PYTHON_KEYWORDS = {
    "if", "else", "elif", "and", "or", "not", "in", "is",
    "True", "False", "None", "for", "while", "def", "class",
    "return", "import", "from", "as", "try", "except", "finally",
    "with", "lambda", "pass", "break", "continue", "raise",
    "yield", "global", "nonlocal", "assert", "del"
}

PARAM_FIELDS = {
    "angle": {"label": "Кут згину (°):", "type": "float", "default": "90"},
    "radius": {"label": "Радіус дуги (мм):", "type": "float", "default": "150"},
    "branch_width": {"label": "Відгалуження Ш (мм):", "type": "float", "default": "200"},
    "branch_height":{"label": "Відгалуження В (мм):", "type": "float", "default": "200"},
    "branch_length":{"label": "Довжина відгалуж. (мм):","type": "float", "default": "400"},
    "branch_offset":{"label": "Відстань від краю (мм):","type": "float", "default": "300"},
    "branch_diameter":{"label": "Ø відгалуження (мм):", "type": "float", "default": "200"},
    "end_width": {"label": "Кінцева ширина (мм):", "type": "float", "default": "300"},
    "end_height": {"label": "Кінцева висота (мм):", "type": "float", "default": "150"},
    "end_diameter": {"label": "Кінцевий Ø (мм):", "type": "float", "default": "300"},
    "depth": {"label": "Глибина (мм):", "type": "float", "default": "30"},
    "border": {"label": "Ширина загину (мм):", "type": "float", "default": "25"},
    "segments": {"label": "Кількість сегментів:", "type": "int", "default": "3"},
    "bolt_count": {"label": "Кількість болтів:", "type": "int", "default": "8"},
    "bolt_diameter":{"label": "Ø отвору під болт (мм):","type": "float", "default": "10"},
    "bolt_spacing": {"label": "Крок отворів (мм):", "type": "float", "default": "100"},
}

INTERNAL_VARS = {
    "metal_area", "metal_area_m2", "thickness", "material_price",
    "weight", "weight_kg", "quantity", "length", "width", "height",
    "profile", "__builtins__",
}


class ProductsTab:
    BASE_PRODUCT_TYPES = {
        "Повітропровід прямокутний": "rect_duct",
        "Повітропровід круглий": "round_duct",
        "Фланець прямокутний": "rect_flange",
        "Фланець круглий": "round_flange",
        "Трійник прямокутний": "rect_tee",
        "Трійник круглий": "round_tee",
        "Перехід прямокутний": "rect_transition",
        "Перехід круглий": "round_transition",
        "Відвід прямокутний": "rect_elbow",
        "Відвід круглий": "round_elbow",
        "Заглушка прямокутна": "rect_cap",
        "Заглушка кругла": "round_cap",
        "Гнучка вставка": "flexible",
    }

    MATERIALS = {
        "Оцинкована сталь": MaterialType.GALVANIZED,
        "Нержавіюча сталь": MaterialType.STAINLESS,
        "Алюміній": MaterialType.ALUMINUM,
    }

    THICKNESSES = {
        "0.5 мм": Thickness.T0_5,
        "0.7 мм": Thickness.T0_7,
        "0.9 мм": Thickness.T0_9,
        "1.0 мм": Thickness.T1_0,
        "1.2 мм": Thickness.T1_2,
        "1.5 мм": Thickness.T1_5,
        "2.0 мм": Thickness.T2_0,
    }

    PROFILE_RECT = {"П20": 20.0, "П30": 30.0}
    PROFILE_ROUND = {"30": 30.0, "40": 40.0}

    HELP_TEXTS = {
        "rect_duct": "📐 Прямокутний повітропровід\nШирина × Висота = переріз (мм)\nДовжина = вздовж осі (мм)",
        "round_duct": "🔵 Круглий повітропровід\nØ = діаметр труби (мм)\nДовжина = вздовж осі (мм)",
        "rect_flange": "⬜ Прямокутний фланець\nШирина × Висота = під повітропровід (мм)\nПрофіль = розмір полки (П20/П30)",
        "round_flange": "🔘 Круглий фланець\nØ = під трубу (мм)\nПрофіль = розмір кутника (30/40)",
        "rect_tee": "┬ Прямокутний трійник\nШ×В = основний канал (мм)\nДовжина = основного каналу",
        "round_tee": "┬ Круглий трійник\nØ = основної труби (мм)\nДовжина = основної труби",
        "rect_transition":"◺ Прямокутний перехід\nШ×В = початковий переріз (мм)\nДовжина = розмір переходу",
        "round_transition":"◺ Круглий перехід\nØ = початковий діаметр (мм)\nДовжина = розмір переходу",
        "rect_elbow": "⌒ Прямокутне коліно\nШ×В = переріз (мм)\nКут = кут згину\nРадіус = радіус дуги",
        "round_elbow": "⌒ Кругле коліно\nØ = діаметр труби (мм)\nКут = кут згину\nРадіус = радіус дуги",
        "rect_cap": "⊞ Прямокутна заглушка\nШ×В = під повітропровід (мм)",
        "round_cap": "⊞ Кругла заглушка\nØ = під трубу (мм)\nГлибина = висота заглушки",
        "flexible": "〰 Гнучка вставка\nШ×В = переріз (мм)\nДовжина = довжина вставки",
        "custom": "🔧 Кастомний виріб з каталогу\nВкажіть розміри та площу металу\nПараметри з формули зʼявляться автоматично",
    }

    def __init__(self, parent: ttk.Notebook, on_products_changed: Callable | None = None):
        self.frame = ttk.Frame(parent)
        self.library = ProductLibrary()
        self.on_products_changed = on_products_changed
        self.PRODUCT_TYPES = dict(self.BASE_PRODUCT_TYPES)
        self._dynamic_types = {}
        self._dynamic_vars = {}
        self._extra_vars = {}
        self._trace_callbacks = []
        self._build_ui()
        self._load_dynamic_types()
        self._bind_preview_updates()
        self._update_summary()

    def _load_dynamic_types(self, event=None):
        try:
            from ventilation_company.gui.settings_tab import PricingSettings
            settings = PricingSettings()
            self._dynamic_types = {}
            for p in settings.products:
                name = p.get("name", "").strip()
                if name and name not in self.PRODUCT_TYPES:
                    self._dynamic_types[name] = f"custom_{name}"
            all_types = list(self.PRODUCT_TYPES.keys()) + list(self._dynamic_types.keys())
            self.type_combo["values"] = all_types
        except Exception as e:
            print(f"[DEBUG] _load_dynamic_types error: {e}")

    def _get_custom_formula(self, product_name: str) -> str:
        try:
            from ventilation_company.gui.settings_tab import PricingSettings
            settings = PricingSettings()
            for p in settings.products:
                if p.get("name", "").strip() == product_name.strip():
                    return p.get("formula", "")
        except Exception:
            pass
        return ""

    def _parse_formula_params(self, formula: str) -> list[str]:
        if not formula:
            return []
        identifiers = set(re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', formula))
        params = [name for name in identifiers
                  if name in PARAM_FIELDS and name not in INTERNAL_VARS
                  and name not in PYTHON_KEYWORDS]
        return params

    def _build_ui(self):
        left_frame = ttk.LabelFrame(self.frame, text="Додати виріб", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        type_frame = ttk.Frame(left_frame)
        type_frame.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=2)
        ttk.Label(type_frame, text="Тип:").pack(side=tk.LEFT)
        self.type_var = tk.StringVar(value="Повітропровід прямокутний")
        self.type_combo = ttk.Combobox(
            type_frame, textvariable=self.type_var,
            values=list(self.PRODUCT_TYPES.keys()), state="readonly", width=22
        )
        self.type_combo.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(type_frame, text="🔄", width=3, command=self._load_dynamic_types).pack(
            side=tk.LEFT, padx=(2, 0)
        )
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_changed)
        self.type_combo.bind("<FocusIn>", self._load_dynamic_types)
        self.type_combo.bind("<Button-1>", self._load_dynamic_types)
        self.frame.bind("<Visibility>", self._load_dynamic_types)

        self.width_label = ttk.Label(left_frame, text="Ширина (мм):")
        self.width_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.width_var = tk.StringVar(value="400")
        self.width_entry = ttk.Entry(left_frame, textvariable=self.width_var, width=12)
        self.width_entry.grid(row=1, column=1, pady=2)

        self.height_label = ttk.Label(left_frame, text="Висота (мм):")
        self.height_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        self.height_var = tk.StringVar(value="200")
        self.height_entry = ttk.Entry(left_frame, textvariable=self.height_var, width=12)
        self.height_entry.grid(row=2, column=1, pady=2)

        self.length_label = ttk.Label(left_frame, text="Довжина (мм):")
        self.length_label.grid(row=3, column=0, sticky=tk.W, pady=2)
        self.length_var = tk.StringVar(value="1000")
        self.length_entry = ttk.Entry(left_frame, textvariable=self.length_var, width=12)
        self.length_entry.grid(row=3, column=1, pady=2)

        self.flange_label = ttk.Label(left_frame, text="З фланцями:")
        self.flange_label.grid(row=4, column=0, sticky=tk.W, pady=2)
        self.flange_var = tk.BooleanVar(value=False)
        self.flange_check = ttk.Checkbutton(
            left_frame, variable=self.flange_var, command=self._on_flange_changed
        )
        self.flange_check.grid(row=4, column=1, sticky=tk.W, pady=2)

        self.flange_qty_label = ttk.Label(left_frame, text="Кількість фланців:")
        self.flange_qty_var = tk.StringVar(value="2")
        self.flange_qty_entry = ttk.Entry(left_frame, textvariable=self.flange_qty_var, width=12)
        self._show_flange_widgets(False)

        self.profile_label = ttk.Label(left_frame, text="Профіль:")
        self.profile_var = tk.StringVar(value="П30")
        self.profile_combo = ttk.Combobox(
            left_frame, textvariable=self.profile_var,
            values=list(self.PROFILE_RECT.keys()), state="readonly", width=10
        )
        self._show_profile_widgets(False)

        self.custom_area_label = ttk.Label(left_frame, text="Площа металу (м²):")
        self.custom_area_var = tk.StringVar(value="0")
        self.custom_area_entry = ttk.Entry(left_frame, textvariable=self.custom_area_var, width=12)
        self._show_custom_area(False)

        self.dynamic_frame = ttk.Frame(left_frame)
        self.dynamic_frame.grid(row=8, column=0, columnspan=2, pady=5, sticky=tk.EW)

        self.extra_frame = ttk.Frame(left_frame)
        self.extra_frame.grid(row=9, column=0, columnspan=2, pady=5, sticky=tk.EW)
        self.extra_widgets = []

        ttk.Label(left_frame, text="Матеріал:").grid(row=10, column=0, sticky=tk.W, pady=2)
        self.material_var = tk.StringVar(value="Оцинкована сталь")
        ttk.Combobox(
            left_frame, textvariable=self.material_var,
            values=list(self.MATERIALS.keys()), state="readonly", width=28
        ).grid(row=10, column=1, pady=2)

        ttk.Label(left_frame, text="Товщина:").grid(row=11, column=0, sticky=tk.W, pady=2)
        self.thickness_var = tk.StringVar(value="0.7 мм")
        ttk.Combobox(
            left_frame, textvariable=self.thickness_var,
            values=list(self.THICKNESSES.keys()), state="readonly", width=28
        ).grid(row=11, column=1, pady=2)

        ttk.Label(left_frame, text="Кількість:").grid(row=12, column=0, sticky=tk.W, pady=2)
        self.qty_var = tk.StringVar(value="1")
        ttk.Entry(left_frame, textvariable=self.qty_var, width=12).grid(row=12, column=1, pady=2)



        ttk.Button(left_frame, text="➕ Додати виріб", command=self._add_product).grid(
            row=13, column=0, columnspan=2, pady=10, sticky=tk.EW
        )

        self.help_label = ttk.Label(
            left_frame, text=self.HELP_TEXTS["rect_duct"],
            foreground="#2E7D32", wraplength=300, justify=tk.LEFT, font=("Consolas", 9)
        )
        self.help_label.grid(row=14, column=0, columnspan=2, pady=5, sticky=tk.W)

        self.preview_frame = ttk.LabelFrame(left_frame, text="🔍 Попередній перегляд розрахунку", padding=8)
        self.preview_frame.grid(row=15, column=0, columnspan=2, pady=8, sticky=tk.EW)

        self.preview_text = tk.Text(
            self.preview_frame, height=14, width=38, wrap=tk.WORD,
            font=("Consolas", 9), bg="#f5f5f5", fg="#333",
            relief=tk.FLAT, state=tk.DISABLED
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)

        right_frame = ttk.Frame(self.frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        toolbar = ttk.Frame(right_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        # ── ІКОНКИ З ПІДКАЗКАМИ ──────────────────────────────
        btn_cfg = [
            ("🗑️", "Видалити обраний виріб", self._remove_selected),
            ("📋", "Дублювати обраний виріб", self._duplicate_selected),
            ("🧹", "Очистити всі вироби", self._clear_all),
            ("🔄", "Перерахувати ціни всіх виробів", self._recalculate_all_prices),
        ]
        if FREECAD_AVAILABLE:
            btn_cfg.append(("🏗️", "Експорт у FreeCAD", self._export_selected_freecad))

        for icon, tooltip, cmd in btn_cfg:
            btn = tk.Button(
                toolbar, text=icon, font=("Segoe UI Emoji", 14),
                width=3, height=1, relief=tk.FLAT, bg="#f0f0f0",
                cursor="hand2", command=cmd
            )
            btn.pack(side=tk.LEFT, padx=2)
            Tooltip(btn, tooltip)
            # Ефект при наведенні
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#e0e0e0"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg="#f0f0f0"))

        # --- Інфо про категорію націнки (поруч з іконками) ---
        info_frame = ttk.LabelFrame(right_frame, text="Категорія націнки", padding=5)
        info_frame.pack(fill=tk.X, pady=(5, 5))

        info_inner = ttk.Frame(info_frame)
        info_inner.pack(fill=tk.X)

        ttk.Label(info_inner, text="Матеріал / Тип / Розмір:", font=("Arial", 9)).pack(side=tk.LEFT, padx=(0, 5))
        self.category_label = ttk.Label(info_inner, text="—", foreground="#1565C0", font=("Consolas", 10, "bold"))
        self.category_label.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(info_inner, text="Націнка:", font=("Arial", 9)).pack(side=tk.LEFT, padx=(0, 5))
        self.markup_label = ttk.Label(info_inner, text="—", foreground="#C62828", font=("Consolas", 12, "bold"))
        self.markup_label.pack(side=tk.LEFT)

        self.summary_label = ttk.Label(
            right_frame,
            text="Всього: 0 виробів | 0.000 м² | 0.00 грн",
            font=("Arial", 10, "bold")
        )
        self.summary_label.pack(fill=tk.X, pady=(0, 5))

        columns = ("type", "dimensions", "material", "thickness", "qty",
                   "area_unit", "area_total", "price_unit", "price_total")
        self.tree = ttk.Treeview(right_frame, columns=columns, show="headings", height=20)

        self.tree.heading("type", text="Тип")
        self.tree.heading("dimensions", text="Розміри")
        self.tree.heading("material", text="Матеріал")
        self.tree.heading("thickness", text="Товщ.")
        self.tree.heading("qty", text="К-ть")
        self.tree.heading("area_unit", text="Площа 1шт, м²")
        self.tree.heading("area_total", text="Площа заг., м²")
        self.tree.heading("price_unit", text="Ціна 1шт, грн")
        self.tree.heading("price_total", text="Ціна заг., грн")

        self.tree.column("type", width=140)
        self.tree.column("dimensions", width=90)
        self.tree.column("material", width=110)
        self.tree.column("thickness", width=45, anchor=tk.CENTER)
        self.tree.column("qty", width=45, anchor=tk.CENTER)
        self.tree.column("area_unit", width=85, anchor=tk.CENTER)
        self.tree.column("area_total", width=85, anchor=tk.CENTER)
        self.tree.column("price_unit", width=90, anchor=tk.CENTER)
        self.tree.column("price_total", width=90, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Button-3>", self._on_tree_right_click)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

    def _show_flange_widgets(self, show: bool):
        if show:
            self.flange_label.grid(row=4, column=0, sticky=tk.W, pady=2)
            self.flange_check.grid(row=4, column=1, sticky=tk.W, pady=2)
        else:
            self.flange_label.grid_remove()
            self.flange_check.grid_remove()
            self.flange_var.set(False)
            self._show_flange_qty(False)

    def _show_flange_qty(self, show: bool):
        if show:
            self.flange_qty_label.grid(row=5, column=0, sticky=tk.W, pady=2)
            self.flange_qty_entry.grid(row=5, column=1, pady=2)
        else:
            self.flange_qty_label.grid_remove()
            self.flange_qty_entry.grid_remove()

    def _show_profile_widgets(self, show: bool, is_round: bool = False):
        if show:
            self.profile_label.grid(row=6, column=0, sticky=tk.W, pady=2)
            self.profile_combo.grid(row=6, column=1, sticky=tk.W, pady=2)
            values = list(self.PROFILE_ROUND.keys()) if is_round else list(self.PROFILE_RECT.keys())
            self.profile_combo["values"] = values
            self.profile_var.set(values[0])
        else:
            self.profile_label.grid_remove()
            self.profile_combo.grid_remove()

    def _show_custom_area(self, show: bool):
        if show:
            self.custom_area_label.grid(row=7, column=0, sticky=tk.W, pady=2)
            self.custom_area_entry.grid(row=7, column=1, pady=2)
        else:
            self.custom_area_label.grid_remove()
            self.custom_area_entry.grid_remove()
            self.custom_area_var.set("0")

    def _show_height_field(self, show: bool):
        if show:
            self.height_label.grid(row=2, column=0, sticky=tk.W, pady=2)
            self.height_entry.grid(row=2, column=1, pady=2)
        else:
            self.height_label.grid_remove()
            self.height_entry.grid_remove()

    def _show_length_field(self, show: bool):
        if show:
            self.length_label.grid(row=3, column=0, sticky=tk.W, pady=2)
            self.length_entry.grid(row=3, column=1, pady=2)
        else:
            self.length_label.grid_remove()
            self.length_entry.grid_remove()

    def _clear_dynamic_fields(self):
        for var, cb_id in self._trace_callbacks:
            try:
                var.trace_remove("write", cb_id)
            except Exception:
                pass
        self._trace_callbacks.clear()
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()
        self._dynamic_vars.clear()
        if not self.dynamic_frame.winfo_children():
            self.dynamic_frame.grid_remove()
        else:
            self.dynamic_frame.grid()

    def _clear_extra_frame(self):
        for widget in self.extra_frame.winfo_children():
            widget.destroy()
        self.extra_widgets.clear()
        self._extra_vars.clear()

    def _on_flange_changed(self):
        self._show_flange_qty(self.flange_var.get())

    def _on_type_changed(self, event=None):
        self._clear_extra_frame()
        self._clear_dynamic_fields()

        selected_name = self.type_var.get()
        ptype = self.PRODUCT_TYPES.get(selected_name, "")
        if not ptype:
            ptype = self._dynamic_types.get(selected_name, "")

        is_custom = ptype.startswith("custom_")
        is_round = "round" in ptype or "кругл" in selected_name.lower()
        is_flange = "flange" in ptype or "фланець" in selected_name.lower()
        is_duct = "duct" in ptype or "повітропровід" in selected_name.lower()

        if is_round:
            self.width_label.config(text="Діаметр (мм):")
            self._show_height_field(False)
            self.height_var.set(self.width_var.get())
        else:
            self.width_label.config(text="Ширина (мм):")
            self._show_height_field(True)

        if is_flange:
            self._show_length_field(False)
            self._show_profile_widgets(True, is_round)
        else:
            self._show_length_field(True)
            self._show_profile_widgets(False)

        if is_duct:
            self._show_flange_widgets(True)
        else:
            self._show_flange_widgets(False)

        if is_custom:
            help_text = self.HELP_TEXTS["custom"]
            self._show_custom_area(True)
            formula = self._get_custom_formula(selected_name)
            params = self._parse_formula_params(formula)
            self._build_dynamic_fields(params)
            if formula:
                help_text += f"\n\n📝 Формула:\n{formula}"
            if params:
                help_text += "\n\n📥 Параметри:\n" + ", ".join(params)
        else:
            help_text = self.HELP_TEXTS.get(ptype, "")
            self._show_custom_area(False)

        self.help_label.config(text=help_text)

        if "tee" in ptype:
            self._build_tee_fields(ptype)
        elif "transition" in ptype:
            self._build_transition_fields(ptype)
        elif "elbow" in ptype:
            self._build_elbow_fields()
        elif "cap" in ptype:
            self._build_cap_fields(ptype)
        elif ptype == "flexible":
            self._build_flexible_fields()

    def _build_tee_fields(self, ptype):
        self._extra_vars["branch_offset"] = tk.StringVar(value="300")
        ttk.Label(self.extra_frame, text="Відстань від краю (мм):").pack(anchor=tk.W)
        ttk.Entry(self.extra_frame, textvariable=self._extra_vars["branch_offset"], width=12).pack(anchor=tk.W)
        if "rect" in ptype:
            self._extra_vars["branch_width"] = tk.StringVar(value="200")
            self._extra_vars["branch_height"] = tk.StringVar(value="200")
            ttk.Label(self.extra_frame, text="Відгалуження Ш×В (мм):").pack(anchor=tk.W)
            f = ttk.Frame(self.extra_frame)
            f.pack(fill=tk.X)
            ttk.Entry(f, textvariable=self._extra_vars["branch_width"], width=8).pack(side=tk.LEFT)
            ttk.Label(f, text="×").pack(side=tk.LEFT)
            ttk.Entry(f, textvariable=self._extra_vars["branch_height"], width=8).pack(side=tk.LEFT)
            self.extra_widgets.append(f)
        else:
            self._extra_vars["branch_diameter"] = tk.StringVar(value="200")
            ttk.Label(self.extra_frame, text="Ø відгалуження (мм):").pack(anchor=tk.W)
            ttk.Entry(self.extra_frame, textvariable=self._extra_vars["branch_diameter"], width=12).pack(anchor=tk.W)
        self._extra_vars["branch_length"] = tk.StringVar(value="400")
        ttk.Label(self.extra_frame, text="Довжина відгалуження (мм):").pack(anchor=tk.W)
        ttk.Entry(self.extra_frame, textvariable=self._extra_vars["branch_length"], width=12).pack(anchor=tk.W)

    def _build_transition_fields(self, ptype):
        if "rect" in ptype:
            self._extra_vars["end_width"] = tk.StringVar(value="300")
            self._extra_vars["end_height"] = tk.StringVar(value="150")
            ttk.Label(self.extra_frame, text="Кінцеві розміри Ш×В (мм):").pack(anchor=tk.W)
            f = ttk.Frame(self.extra_frame)
            f.pack(fill=tk.X)
            ttk.Entry(f, textvariable=self._extra_vars["end_width"], width=8).pack(side=tk.LEFT)
            ttk.Label(f, text="×").pack(side=tk.LEFT)
            ttk.Entry(f, textvariable=self._extra_vars["end_height"], width=8).pack(side=tk.LEFT)
            self.extra_widgets.append(f)
        else:
            self._extra_vars["end_diameter"] = tk.StringVar(value="300")
            ttk.Label(self.extra_frame, text="Кінцевий Ø (мм):").pack(anchor=tk.W)
            ttk.Entry(self.extra_frame, textvariable=self._extra_vars["end_diameter"], width=12).pack(anchor=tk.W)

    def _build_elbow_fields(self):
        self._extra_vars["angle"] = tk.StringVar(value="90")
        self._extra_vars["radius"] = tk.StringVar(value="150")
        ttk.Label(self.extra_frame, text="Кут згину (°):").pack(anchor=tk.W)
        ttk.Entry(self.extra_frame, textvariable=self._extra_vars["angle"], width=12).pack(anchor=tk.W)
        ttk.Label(self.extra_frame, text="Радіус дуги (мм):").pack(anchor=tk.W)
        ttk.Entry(self.extra_frame, textvariable=self._extra_vars["radius"], width=12).pack(anchor=tk.W)

    def _build_cap_fields(self, ptype):
        if "rect" in ptype:
            self._extra_vars["border"] = tk.StringVar(value="25")
            ttk.Label(self.extra_frame, text="Ширина загину (мм):").pack(anchor=tk.W)
            ttk.Entry(self.extra_frame, textvariable=self._extra_vars["border"], width=12).pack(anchor=tk.W)
        else:
            self._extra_vars["depth"] = tk.StringVar(value="30")
            ttk.Label(self.extra_frame, text="Глибина заглушки (мм):").pack(anchor=tk.W)
            ttk.Entry(self.extra_frame, textvariable=self._extra_vars["depth"], width=12).pack(anchor=tk.W)

    def _build_flexible_fields(self):
        self._extra_vars["fabric_type"] = tk.StringVar(value="поліестер")
        ttk.Label(self.extra_frame, text="Тип тканини:").pack(anchor=tk.W)
        ttk.Combobox(
            self.extra_frame, textvariable=self._extra_vars["fabric_type"],
            values=["поліестер", "склотканина", "ПВХ"],
            state="readonly", width=20
        ).pack(anchor=tk.W)

    def _build_dynamic_fields(self, params: list[str]):
        self._clear_dynamic_fields()
        if not params:
            return
        ttk.Separator(self.dynamic_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        ttk.Label(self.dynamic_frame, text="📐 Параметри формули:", font=("Arial", 9, "bold")).pack(
            anchor=tk.W, pady=2
        )
        for param_name in params:
            info = PARAM_FIELDS.get(param_name, {"label": f"{param_name}:", "type": "float", "default": "0"})
            row = ttk.Frame(self.dynamic_frame)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=info["label"], width=24, anchor=tk.W).pack(side=tk.LEFT)
            var = tk.StringVar(value=info["default"])
            ttk.Entry(row, textvariable=var, width=12).pack(side=tk.LEFT)
            self._dynamic_vars[param_name] = var
            cb_id = var.trace_add("write", lambda *args: self._update_formula_preview())
            self._trace_callbacks.append((var, cb_id))

    def _bind_preview_updates(self):
        vars_to_trace = [
            self.width_var, self.height_var, self.length_var,
            self.qty_var, self.material_var, self.thickness_var,
            self.flange_qty_var, self.profile_var, self.custom_area_var,
        ]
        for var in vars_to_trace:
            var.trace_add("write", lambda *args: self._update_formula_preview())
        self.type_var.trace_add("write", lambda *args: self._update_formula_preview())

    def _update_formula_preview(self):
        # --- Спочатку оновлюємо категорію (завжди, навіть якщо розрахунок ще не готовий) ---
        try:
            selected_name = self.type_var.get()
            ptype = self.PRODUCT_TYPES.get(selected_name, "")
            if not ptype:
                ptype = self._dynamic_types.get(selected_name, "")

            w = self._safe_float(self.width_var.get(), 0)
            h = self._safe_float(self.height_var.get(), w) if self.height_entry.winfo_ismapped() else w
            length = self._safe_float(self.length_var.get(), 0) if self.length_entry.winfo_ismapped() else 0
            material = self.MATERIALS.get(self.material_var.get(), MaterialType.GALVANIZED)
            thickness = self.THICKNESSES.get(self.thickness_var.get(), Thickness.T0_7)

            product_data = {
                "name": selected_name,
                "type": ptype if not ptype.startswith("custom_") else selected_name,
                "material": material.value if hasattr(material, 'value') else str(material),
                "thickness": thickness.value if hasattr(thickness, 'value') else float(thickness),
                "width": w, "height": h, "length": length,
            }

            mat_key, cat_key = classify_product(selected_name, ptype, material.value if hasattr(material, 'value') else str(material))
            is_round_prod = "кругл" in selected_name.lower() or "round" in selected_name.lower() or "спірал" in selected_name.lower()
            is_std = is_standard_size(w, h, length, w if is_round_prod else 0)
            size_label = "стандарт" if is_std else "нестандарт"

            pricing = PricingSettings()
            markup_pct = pricing.get_markup_percent(product_data)

            self.category_label.config(text=f"{mat_key} / {cat_key} / {size_label}")
            self.markup_label.config(text=f"{markup_pct:.1f}%")
        except Exception:
            self.category_label.config(text="—")
            self.markup_label.config(text="—")

        # --- Тепер розрахунок ціни ---
        try:
            pricing = PricingSettings()

            selected_name = self.type_var.get()
            ptype = self.PRODUCT_TYPES.get(selected_name, "")
            if not ptype:
                ptype = self._dynamic_types.get(selected_name, "")

            w = self._safe_float(self.width_var.get(), 0)
            h = self._safe_float(self.height_var.get(), w) if self.height_entry.winfo_ismapped() else w
            length = self._safe_float(self.length_var.get(), 0) if self.length_entry.winfo_ismapped() else 0
            qty = max(1, int(self._safe_float(self.qty_var.get(), 1)))
            material = self.MATERIALS.get(self.material_var.get(), MaterialType.GALVANIZED)
            thickness = self.THICKNESSES.get(self.thickness_var.get(), Thickness.T0_7)

            profile = 30.0
            if self.profile_combo.winfo_ismapped():
                pk = self.profile_var.get()
                if "rect" in ptype or "прямокутн" in selected_name.lower():
                    profile = self.PROFILE_RECT.get(pk, 30.0)
                else:
                    profile = self.PROFILE_ROUND.get(pk, 30.0)

            metal_area = self._calc_preview_area(ptype, selected_name, w, h, length, profile)

            density = 7850
            weight = metal_area * (thickness.value / 1000) * density

            dynamic_values = {}
            for param_name, var in self._dynamic_vars.items():
                info = PARAM_FIELDS.get(param_name, {})
                try:
                    dynamic_values[param_name] = int(var.get()) if info.get("type") == "int" else float(var.get())
                except ValueError:
                    dynamic_values[param_name] = 0

            extra_values = {}
            for key, var in self._extra_vars.items():
                try:
                    extra_values[key] = float(var.get())
                except ValueError:
                    extra_values[key] = 0

            product_data = {
                "name": selected_name,
                "type": ptype if not ptype.startswith("custom_") else selected_name,
                "material": material.value,
                "thickness": thickness.value,
                "metal_area_m2": metal_area,
                "weight_kg": weight,
                "quantity": qty,
                "width": w, "height": h, "length": length,
                "profile": profile,
            }
            product_data.update(dynamic_values)
            product_data.update(extra_values)

            mat_key, cat_key = classify_product(selected_name, ptype, material.value if hasattr(material, 'value') else str(material))
            is_round_prod = "кругл" in selected_name.lower() or "round" in selected_name.lower() or "спірал" in selected_name.lower()
            is_std = is_standard_size(w, h, length, w if is_round_prod else 0)
            size_label = "стандарт" if is_std else "нестандарт"

            result = pricing.calculate_product_price_detailed(product_data)

            lines = []
            lines.append(f"📂 Категорія: {mat_key} / {cat_key} / {size_label}")
            lines.append(f"📝 Формула: {result['formula']}")
            lines.append("")
            lines.append("─" * 36)
            for step in result["steps"]:
                lines.append(f"{step['name']}:")
                lines.append(f"  {step['calc']}")
                lines.append(f" = {step['value']:.2f} грн")
                lines.append("")
            lines.append("─" * 36)
            lines.append(f"💰 ВСЬОГО за 1 шт: {result['total']:.2f} грн")
            lines.append(f"💰 Загальна ({qty} шт): {result['total'] * qty:.2f} грн")

            text = chr(10).join(lines)

            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.insert(tk.END, text)
            self.preview_text.config(state=tk.DISABLED)

        except Exception as e:
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.insert(tk.END, "🔍 Попередній перегляд\n\nЗаповніть поля,\nщоб побачити розрахунок.\n\n[" + str(e)[:80] + "]")
            self.preview_text.config(state=tk.DISABLED)

    def _calc_preview_area(self, ptype, selected_name, w, h, length, profile):
        try:
            if ptype.startswith("custom_"):
                return self._safe_float(self.custom_area_var.get(), 0)
            elif ptype == "rect_duct":
                return make_rect_duct(w, h, length, 0.7).metal_area
            elif ptype == "round_duct":
                return make_round_duct(w, length, 0.7).metal_area
            elif ptype == "rect_flange":
                return RectFlange(name="", width=w, height=h, length=0, thickness=Thickness.T0_7,
                                  material=MaterialType.GALVANIZED, quantity=1, profile=profile).metal_area
            elif ptype == "round_flange":
                return RoundFlange(name="", width=w, height=w, length=0, thickness=Thickness.T0_7,
                                   material=MaterialType.GALVANIZED, quantity=1, profile=profile).metal_area
            elif ptype == "rect_tee":
                bw = self._get_extra("branch_width", 200)
                bh = self._get_extra("branch_height", 200)
                bl = self._get_extra("branch_length", 400)
                offset = self._get_extra("branch_offset", 300)
                return RectTee(name="", width=w, height=h, length=length, thickness=Thickness.T0_7,
                               material=MaterialType.GALVANIZED, quantity=1,
                               branch_width=bw, branch_height=bh, branch_length=bl, branch_offset=offset).metal_area
            elif ptype == "round_tee":
                bd = self._get_extra("branch_diameter", 200)
                bl = self._get_extra("branch_length", 400)
                offset = self._get_extra("branch_offset", 300)
                return RoundTee(name="", width=w, height=w, length=length, thickness=Thickness.T0_7,
                                material=MaterialType.GALVANIZED, quantity=1,
                                branch_diameter=bd, branch_length=bl, branch_offset=offset).metal_area
            elif ptype == "rect_transition":
                ew = self._get_extra("end_width", 300)
                eh = self._get_extra("end_height", 150)
                return RectTransition(name="", width=w, height=h, length=length, thickness=Thickness.T0_7,
                                      material=MaterialType.GALVANIZED, quantity=1,
                                      end_width=ew, end_height=eh).metal_area
            elif ptype == "round_transition":
                ed = self._get_extra("end_diameter", 300)
                return RoundTransition(name="", width=w, height=w, length=length, thickness=Thickness.T0_7,
                                     material=MaterialType.GALVANIZED, quantity=1,
                                     end_diameter=ed).metal_area
            elif ptype == "rect_elbow":
                angle = self._get_extra("angle", 90)
                radius = self._get_extra("radius", 150)
                return RectElbow(name="", width=w, height=h, length=length, thickness=Thickness.T0_7,
                                 material=MaterialType.GALVANIZED, quantity=1,
                                 angle=angle, radius=radius).metal_area
            elif ptype == "round_elbow":
                angle = self._get_extra("angle", 90)
                radius = self._get_extra("radius", 150)
                return RoundElbow(name="", width=w, height=w, length=length, thickness=Thickness.T0_7,
                                  material=MaterialType.GALVANIZED, quantity=1,
                                  angle=angle, radius=radius).metal_area
            elif ptype == "rect_cap":
                border = self._get_extra("border", 25)
                return RectCap(name="", width=w, height=h, length=0, thickness=Thickness.T0_7,
                               material=MaterialType.GALVANIZED, quantity=1, profile=border).metal_area
            elif ptype == "round_cap":
                depth = self._get_extra("depth", 30)
                return RoundCap(name="", width=w, height=w, length=0, thickness=Thickness.T0_7,
                                material=MaterialType.GALVANIZED, quantity=1, depth=depth).metal_area
            elif ptype == "flexible":
                return FlexibleConnector(name="", width=w, height=h, length=length, thickness=Thickness.T0_7,
                                         material=MaterialType.GALVANIZED, quantity=1).metal_area
            else:
                return 0
        except Exception:
            return 0

    def _get_extra(self, key: str, default: float = 0) -> float:
        var = self._extra_vars.get(key)
        if var is None:
            return default
        try:
            return float(var.get())
        except ValueError:
            return default

    def _safe_float(self, value, default=0):
        try:
            return float(str(value).replace(',', '.'))
        except (ValueError, TypeError):
            return default

    def _calc_price(self, product: StandardProduct) -> float:
        try:
            from ventilation_company.gui.settings_tab import PricingSettings
            pricing = PricingSettings()
            data = product.to_dict()
            return pricing.calculate_product_price(data)
        except Exception as e:
            print(f"[DEBUG] _calc_price error: {e}")
            return product.calculate_price()

    def _validate_input(self):
        errors = []

        def get_float(var, name):
            try:
                v = float(str(var.get()).replace(',', '.'))
                if v < 0:
                    errors.append(f"'{name}' не може бути від'ємним")
                return v
            except ValueError:
                errors.append(f"'{name}' має бути числом")
                return 0

        def get_int(var, name):
            try:
                v = int(float(str(var.get()).replace(',', '.')))
                if v < 0:
                    errors.append(f"'{name}' не може бути від'ємним")
                return v
            except ValueError:
                errors.append(f"'{name}' має бути цілим числом")
                return 0

        w = get_float(self.width_var, "Ширина/Діаметр")
        h = get_float(self.height_var, "Висота") if self.height_entry.winfo_ismapped() else w
        length = get_float(self.length_var, "Довжина") if self.length_entry.winfo_ismapped() else 0
        qty = get_int(self.qty_var, "Кількість")
        if qty == 0:
            errors.append("Кількість має бути більше 0")

        if errors:
            raise ValueError("\n".join(errors))

        return {"w": w, "h": h, "length": length, "qty": qty}

    def _add_product(self):
        try:
            validated = self._validate_input()
            w, h, length, qty = validated["w"], validated["h"], validated["length"], validated["qty"]
        except ValueError as e:
            messagebox.showerror("Помилка валідації", str(e))
            return

        selected_name = self.type_var.get()
        ptype = self.PRODUCT_TYPES.get(selected_name, "")
        if not ptype:
            ptype = self._dynamic_types.get(selected_name, "")

        material = self.MATERIALS[self.material_var.get()]
        thickness = self.THICKNESSES[self.thickness_var.get()]

        profile = 30.0
        if self.profile_combo.winfo_ismapped():
            profile_key = self.profile_var.get()
            if "rect" in ptype or "прямокутн" in selected_name.lower():
                profile = self.PROFILE_RECT.get(profile_key, 30.0)
            else:
                profile = self.PROFILE_ROUND.get(profile_key, 30.0)

        product = None
        flanges = []

        if ptype.startswith("custom_"):
            custom_area = self._safe_float(self.custom_area_var.get(), 0)
            dynamic_values = {}
            for param_name, var in self._dynamic_vars.items():
                info = PARAM_FIELDS.get(param_name, {})
                try:
                    dynamic_values[param_name] = int(var.get()) if info.get("type") == "int" else float(var.get())
                except ValueError:
                    dynamic_values[param_name] = 0

            class CustomProduct(StandardProduct):
                def __post_init__(self):
                    self.product_type = selected_name
                    super().__post_init__()
                def calculate_metal_area(self):
                    return custom_area

            product = CustomProduct(
                name=selected_name, product_type=selected_name,
                width=w, height=h, length=length,
                thickness=thickness, material=material, quantity=qty,
            )
            product._dynamic_params = dynamic_values

        elif ptype == "rect_duct":
            product = make_rect_duct(w, h, length, thickness.value, material, qty)
        elif ptype == "round_duct":
            product = make_round_duct(w, length, thickness.value, material, qty)
        elif ptype == "rect_flange":
            product = RectFlange(
                name=f"Фланець {w:.0f}×{h:.0f}",
                width=w, height=h, length=0,
                thickness=thickness, material=material, quantity=qty,
                profile=profile,
            )
        elif ptype == "round_flange":
            product = RoundFlange(
                name=f"Фланець Ø{w:.0f}",
                width=w, height=w, length=0,
                thickness=thickness, material=material, quantity=qty,
                profile=profile,
            )
        elif ptype == "rect_tee":
            bw = self._get_extra("branch_width", 200)
            bh = self._get_extra("branch_height", 200)
            bl = self._get_extra("branch_length", 400)
            offset = self._get_extra("branch_offset", 300)
            product = RectTee(
                name=f"Трійник {w:.0f}×{h:.0f}/{bw:.0f}×{bh:.0f}",
                width=w, height=h, length=length,
                thickness=thickness, material=material, quantity=qty,
                branch_width=bw, branch_height=bh, branch_length=bl, branch_offset=offset,
            )
        elif ptype == "round_tee":
            bd = self._get_extra("branch_diameter", 200)
            bl = self._get_extra("branch_length", 400)
            offset = self._get_extra("branch_offset", 300)
            product = RoundTee(
                name=f"Трійник Ø{w:.0f}/Ø{bd:.0f}",
                width=w, height=w, length=length,
                thickness=thickness, material=material, quantity=qty,
                branch_diameter=bd, branch_length=bl, branch_offset=offset,
            )
        elif ptype == "rect_transition":
            ew = self._get_extra("end_width", 300)
            eh = self._get_extra("end_height", 150)
            product = RectTransition(
                name=f"Перехід {w:.0f}×{h:.0f}→{ew:.0f}×{eh:.0f}",
                width=w, height=h, length=length,
                thickness=thickness, material=material, quantity=qty,
                end_width=ew, end_height=eh,
            )
        elif ptype == "round_transition":
            ed = self._get_extra("end_diameter", 300)
            product = RoundTransition(
                name=f"Перехід Ø{w:.0f}→Ø{ed:.0f}",
                width=w, height=w, length=length,
                thickness=thickness, material=material, quantity=qty,
                end_diameter=ed,
            )
        elif ptype == "rect_elbow":
            angle = self._get_extra("angle", 90)
            radius = self._get_extra("radius", 150)
            product = RectElbow(
                name=f"Відвід {w:.0f}×{h:.0f} {angle:.0f}°",
                width=w, height=h, length=length,
                thickness=thickness, material=material, quantity=qty,
                angle=angle, radius=radius,
            )
        elif ptype == "round_elbow":
            angle = self._get_extra("angle", 90)
            radius = self._get_extra("radius", 150)
            product = RoundElbow(
                name=f"Відвід Ø{w:.0f} {angle:.0f}°",
                width=w, height=w, length=length,
                thickness=thickness, material=material, quantity=qty,
                angle=angle, radius=radius,
            )
        elif ptype == "rect_cap":
            border = self._get_extra("border", 25)
            product = RectCap(
                name=f"Заглушка {w:.0f}×{h:.0f}",
                width=w, height=h, length=0,
                thickness=thickness, material=material, quantity=qty,
                profile=border,
            )
        elif ptype == "round_cap":
            depth = self._get_extra("depth", 30)
            product = RoundCap(
                name=f"Заглушка Ø{w:.0f}",
                width=w, height=w, length=0,
                thickness=thickness, material=material, quantity=qty,
                depth=depth,
            )
        elif ptype == "flexible":
            fabric = self._extra_vars.get("fabric_type", tk.StringVar(value="поліестер")).get()
            product = FlexibleConnector(
                name=f"Гнучка вставка {w:.0f}×{h:.0f}",
                width=w, height=h, length=length,
                thickness=thickness, material=material, quantity=qty,
                fabric_type=fabric,
            )

        if product:
            product.unit_price = self._calc_price(product)
            product.total_price = product.unit_price * qty

            if self.flange_var.get() and ptype in ("rect_duct", "round_duct"):
                try:
                    flange_qty = int(self._safe_float(self.flange_qty_var.get(), 2))
                    if flange_qty > 0:
                        if ptype == "rect_duct":
                            flange = RectFlange(
                                name=f"Фланець {w:.0f}×{h:.0f}",
                                width=w, height=h, length=0,
                                thickness=thickness, material=material,
                                quantity=flange_qty * qty, profile=profile,
                            )
                        else:
                            flange = RoundFlange(
                                name=f"Фланець Ø{w:.0f}",
                                width=w, height=w, length=0,
                                thickness=thickness, material=material,
                                quantity=flange_qty * qty, profile=profile,
                            )
                        flange.unit_price = self._calc_price(flange)
                        flange.total_price = flange.unit_price * flange.quantity
                        product.has_flanges = True
                        product.flange_count = flange_qty
                        product.flange_price = flange.unit_price
                        flanges.append(flange)
                except ValueError:
                    messagebox.showwarning("Увага", "Кількість фланців має бути числом.")

            self.library.add(product)
            for f in flanges:
                self.library.add(f)

            self._refresh_tree()
            self._update_summary()
            if self.on_products_changed:
                self.on_products_changed()
        else:
            messagebox.showerror("Помилка", f"Тип виробу '{ptype}' ще не реалізовано.")

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for p in self.library.products:
            self.tree.insert(
                "", tk.END,
                values=(
                    p.product_type,
                    f"{p.width:.0f}×{p.height:.0f}×{p.length:.0f}",
                    p.material.value,
                    p.thickness.value,
                    p.quantity,
                    f"{p.metal_area:.3f}",
                    f"{p.metal_area * p.quantity:.3f}",
                    f"{p.unit_price:.2f}",
                    f"{p.total_price:.2f}",
                ),
            )

    def _update_summary(self):
        total = len(self.library)
        area = self.library.get_total_metal_area()
        price = self.library.get_total_price()
        self.summary_label.config(
            text=f"Всього: {total} виробів | {area:.3f} м² | {price:.2f} грн"
        )

    def _get_selected_index(self) -> int:
        selected = self.tree.selection()
        if not selected:
            return -1
        return self.tree.index(selected[0])

    def _remove_selected(self):
        idx = self._get_selected_index()
        if 0 <= idx < len(self.library.products):
            del self.library.products[idx]
            self._refresh_tree()
            self._update_summary()
            if self.on_products_changed:
                self.on_products_changed()

    def _duplicate_selected(self):
        idx = self._get_selected_index()
        if 0 <= idx < len(self.library.products):
            original = self.library.products[idx]
            kwargs = {f.name: getattr(original, f.name) for f in fields(original)}
            duplicate = original.__class__(**kwargs)
            duplicate.quantity = original.quantity
            duplicate.total_price = duplicate.unit_price * duplicate.quantity
            self.library.add(duplicate)
            self._refresh_tree()
            self._update_summary()
            if self.on_products_changed:
                self.on_products_changed()

    def _on_tree_double_click(self, event):
        idx = self._get_selected_index()
        if 0 <= idx < len(self.library.products):
            self._edit_product_dialog(idx)

    def _edit_product_dialog(self, idx: int):
        product = self.library.products[idx]
        dialog = tk.Toplevel(self.frame)
        dialog.title(f"Редагування: {product.name}")
        dialog.geometry("400x350")
        dialog.transient(self.frame)
        dialog.grab_set()

        ttk.Label(dialog, text="Кількість:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        qty_var = tk.StringVar(value=str(product.quantity))
        ttk.Entry(dialog, textvariable=qty_var, width=12).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Ціна за шт (грн):").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        price_var = tk.StringVar(value=f"{product.unit_price:.2f}")
        ttk.Entry(dialog, textvariable=price_var, width=12).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Примітки:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        notes_var = tk.StringVar(value=product.notes)
        ttk.Entry(dialog, textvariable=notes_var, width=30).grid(row=2, column=1, padx=5, pady=5)

        def save():
            try:
                product.quantity = int(qty_var.get())
                product.unit_price = float(price_var.get())
                product.total_price = product.unit_price * product.quantity
                product.notes = notes_var.get()
                self._refresh_tree()
                self._update_summary()
                if self.on_products_changed:
                    self.on_products_changed()
                dialog.destroy()
            except ValueError:
                messagebox.showwarning("Увага", "Кількість та ціна мають бути числами.")

        ttk.Button(dialog, text="✅ Застосувати", command=save).grid(row=3, column=0, columnspan=2, pady=15)

    def _recalculate_all_prices(self):
        if not self.library.products:
            return
        for p in self.library.products:
            p.unit_price = self._calc_price(p)
            p.total_price = p.unit_price * p.quantity
        self._refresh_tree()
        self._update_summary()
        messagebox.showinfo("Успіх", "Ціни всіх виробів перераховано!")

    def _clear_all(self):
        if messagebox.askyesno("Підтвердження", "Видалити всі вироби?"):
            self.library.clear()
            self._refresh_tree()
            self._update_summary()
            if self.on_products_changed:
                self.on_products_changed()

    def _on_tree_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            menu = tk.Menu(self.frame, tearoff=0)
            menu.add_command(label="Редагувати", command=lambda: self._edit_product_dialog(self._get_selected_index()))
            menu.add_command(label="Видалити", command=self._remove_selected)
            menu.add_command(label="Дублювати", command=self._duplicate_selected)
            if FREECAD_AVAILABLE:
                menu.add_separator()
                menu.add_command(label="🏗️ Експорт .FCStd", command=self._export_selected_freecad)
                menu.add_command(label="📐 Експорт .STEP", command=self._export_selected_step)
            menu.post(event.x_root, event.y_root)

    def _export_selected_freecad(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Увага", "Оберіть виріб для експорту.")
            return
        idx = self.tree.index(selected[0])
        if idx < 0 or idx >= len(self.library.products):
            return
        product = self.library.products[idx]
        filepath = filedialog.asksaveasfilename(
            defaultextension=".FCStd", filetypes=[("FreeCAD", "*.FCStd")],
            initialfile=f"{product.name}.FCStd",
        )
        if not filepath:
            return
        try:
            export_products_to_freecad([product], filepath, "fcstd")
            messagebox.showinfo("Успіх", f"Збережено:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))

    def _export_selected_step(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Увага", "Оберіть виріб для експорту.")
            return
        idx = self.tree.index(selected[0])
        if idx < 0 or idx >= len(self.library.products):
            return
        product = self.library.products[idx]
        filepath = filedialog.asksaveasfilename(
            defaultextension=".step", filetypes=[("STEP", "*.step"), ("STP", "*.stp")],
            initialfile=f"{product.name}.step",
        )
        if not filepath:
            return
        try:
            export_products_to_freecad([product], filepath, "step")
            messagebox.showinfo("Успіх", f"Збережено:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))

    def get_library(self):
        return self.library

    def get_products_dict(self):
        return self.library.to_dict()

    def load_products_from_dict(self, products: list[dict]):
        """Завантажити вироби зі списку dict (з БД)."""
        self.library.clear()
        for p in products:
            ptype = p.get("product_type", p.get("type", ""))
            material_str = p.get("material", "оцинкована сталь")
            material = MaterialType.GALVANIZED
            for m in MaterialType:
                if m.value == material_str:
                    material = m
                    break
            thickness_val = p.get("thickness", 0.7)
            thickness = Thickness.T0_7
            for t in Thickness:
                if abs(t.value - thickness_val) < 0.01:
                    thickness = t
                    break
            qty = int(p.get("quantity", 1))
            w = p.get("width", 0)
            h = p.get("height", 0)
            length = p.get("length", 0)
            name = p.get("name", "Виріб")

            kwargs = {
                "name": name, "width": w, "height": h, "length": length,
                "thickness": thickness, "material": material, "quantity": qty,
            }
            for key in ["branch_width", "branch_height", "branch_length", "branch_diameter",
                        "branch_offset", "end_width", "end_height", "end_diameter",
                        "angle", "radius", "segments", "depth", "border", "profile",
                        "bolt_count", "bolt_diameter", "bolt_spacing", "fabric_type",
                        "has_flanges", "flange_count", "flange_price", "unit_price", "notes"]:
                if key in p:
                    kwargs[key] = p[key]

            product = None
            if "повітропровід прямокутний" in ptype:
                product = make_rect_duct(w, h, length, thickness.value, material, qty)
            elif "повітропровід круглий" in ptype:
                product = make_round_duct(w, length, thickness.value, material, qty)
            elif "фланець прямокутний" in ptype:
                product = RectFlange(**kwargs)
            elif "фланець круглий" in ptype:
                product = RoundFlange(**kwargs)
            elif "трійник прямокутний" in ptype:
                product = RectTee(**kwargs)
            elif "трійник круглий" in ptype:
                product = RoundTee(**kwargs)
            elif "перехід прямокутний" in ptype:
                product = RectTransition(**kwargs)
            elif "перехід круглий" in ptype:
                product = RoundTransition(**kwargs)
            elif "відвід прямокутний" in ptype:
                product = RectElbow(**kwargs)
            elif "відвід круглий" in ptype:
                product = RoundElbow(**kwargs)
            elif "заглушка прямокутна" in ptype:
                product = RectCap(**kwargs)
            elif "заглушка кругла" in ptype:
                product = RoundCap(**kwargs)
            elif "гнучка вставка" in ptype:
                product = FlexibleConnector(**kwargs)
            else:
                product = StandardProduct(**kwargs)

            if product:
                product.unit_price = p.get("unit_price", 0)
                product.total_price = p.get("total_price", product.unit_price * qty)
                self.library.add(product)

        self._refresh_tree()
        self._update_summary()
        if self.on_products_changed:
            self.on_products_changed()
