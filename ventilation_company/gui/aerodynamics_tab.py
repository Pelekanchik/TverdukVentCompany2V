"""Вкладка "Аеродинаміка" — розрахунок втрат тиску та підбір вентилятора."""

import tkinter as tk
from tkinter import messagebox, ttk

from ventilation_company.aerodynamics import (
    AIR_DENSITY,
    DuctSection,
    DuctShape,
    Fitting,
    FittingType,
    AerodynamicRoute,
    select_fan,
    get_all_fan_types,
    get_fitting_types,
    FITTING_ZETA,
    GRAVITY,
)


class AerodynamicsTab:
    """Вкладка аеродинамічного розрахунку."""

    def __init__(self, parent: ttk.Notebook):
        self.frame = ttk.Frame(parent)
        self.current_route: AerodynamicRoute | None = None

        self._build_ui()

    def _build_ui(self):
        # ── Ліва панель: параметри траси ──
        left = ttk.LabelFrame(self.frame, text="Параметри траси", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Назва траси
        ttk.Label(left, text="Назва траси:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.route_name_var = tk.StringVar(value="Траса 1")
        ttk.Entry(left, textvariable=self.route_name_var, width=25).grid(row=0, column=1, pady=2)

        # Тип системи
        ttk.Label(left, text="Тип системи:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.system_type_var = tk.StringVar(value="припливна")
        ttk.Combobox(left, textvariable=self.system_type_var,
                     values=["припливна", "витяжна", "димовидалення"],
                     state="readonly", width=22).grid(row=1, column=1, pady=2)

        # Повітряний потік
        ttk.Label(left, text="Повітряний потік (м³/год):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.air_flow_var = tk.DoubleVar(value=2000)
        ttk.Spinbox(left, from_=100, to=50000, textvariable=self.air_flow_var, width=15).grid(row=2, column=1, pady=2)

        # Форма перерізу
        ttk.Label(left, text="Форма перерізу:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.shape_var = tk.StringVar(value="прямокутний")
        ttk.Combobox(left, textvariable=self.shape_var,
                     values=["прямокутний", "круглий"],
                     state="readonly", width=22).grid(row=3, column=1, pady=2)

        # Розміри
        ttk.Label(left, text="Ширина / D (мм):").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.width_var = tk.DoubleVar(value=300)
        ttk.Spinbox(left, from_=50, to=2000, textvariable=self.width_var, width=15).grid(row=4, column=1, pady=2)

        ttk.Label(left, text="Висота (мм):").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.height_var = tk.DoubleVar(value=200)
        ttk.Spinbox(left, from_=50, to=2000, textvariable=self.height_var, width=15).grid(row=5, column=1, pady=2)

        # Довжина
        ttk.Label(left, text="Довжина траси (м):").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.length_var = tk.DoubleVar(value=15)
        ttk.Spinbox(left, from_=1, to=500, textvariable=self.length_var, width=15).grid(row=6, column=1, pady=2)

        ttk.Separator(left, orient=tk.HORIZONTAL).grid(row=7, column=0, columnspan=2, sticky=tk.EW, pady=10)

        # Кнопки
        ttk.Button(left, text="➕ Додати ділянку", command=self._add_section).grid(row=8, column=0, columnspan=2, pady=3, sticky=tk.EW)
        ttk.Button(left, text="📊 Розрахувати", command=self._calculate).grid(row=9, column=0, columnspan=2, pady=5, sticky=tk.EW)
        ttk.Button(left, text="🔄 Очистити", command=self._clear).grid(row=10, column=0, columnspan=2, pady=3, sticky=tk.EW)

        # ── Середня панель: ділянки та фітинги ──
        mid = ttk.Frame(self.frame)
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Таблиця ділянок
        sec_frame = ttk.LabelFrame(mid, text="Ділянки повітропроводу", padding=5)
        sec_frame.pack(fill=tk.X, pady=2)

        sec_cols = ("№", "Назва", "L (м)", "Шир (мм)", "Вис (мм)", "Форма", "Q (м³/год)", "V (м/с)", "Δp (Па)")
        self.sec_tree = ttk.Treeview(sec_frame, columns=sec_cols, show="headings", height=6)
        for c in sec_cols:
            self.sec_tree.heading(c, text=c)
            self.sec_tree.column(c, width=70, anchor=tk.CENTER)
        self.sec_tree.column("Назва", width=100)
        self.sec_tree.pack(fill=tk.X)

        # Додавання фітингів
        fit_frame = ttk.LabelFrame(mid, text="Місцеві опори (фітинги)", padding=5)
        fit_frame.pack(fill=tk.X, pady=5)

        fit_input = ttk.Frame(fit_frame)
        fit_input.pack(fill=tk.X)

        ttk.Label(fit_input, text="Тип:").pack(side=tk.LEFT, padx=2)
        self.fit_type_var = tk.StringVar(value="відвід 90°")
        ttk.Combobox(fit_input, textvariable=self.fit_type_var,
                     values=get_fitting_types(), state="readonly", width=18).pack(side=tk.LEFT, padx=2)

        ttk.Label(fit_input, text="К-ть:").pack(side=tk.LEFT, padx=(10, 2))
        self.fit_qty_var = tk.IntVar(value=1)
        ttk.Spinbox(fit_input, from_=1, to=50, textvariable=self.fit_qty_var, width=6).pack(side=tk.LEFT, padx=2)

        ttk.Label(fit_input, text="Ділянка:").pack(side=tk.LEFT, padx=(10, 2))
        self.fit_section_var = tk.StringVar(value="1")
        self.fit_section_combo = ttk.Combobox(fit_input, textvariable=self.fit_section_var,
                                               values=["1"], state="readonly", width=6)
        self.fit_section_combo.pack(side=tk.LEFT, padx=2)

        ttk.Button(fit_input, text="➕ Додати", command=self._add_fitting).pack(side=tk.LEFT, padx=(10, 2))

        # Таблиця фітингів
        fit_cols = ("№", "Тип", "ζ", "К-ть", "Ділянка", "Δp (Па)")
        self.fit_tree = ttk.Treeview(fit_frame, columns=fit_cols, show="headings", height=6)
        for c in fit_cols:
            self.fit_tree.heading(c, text=c)
            self.fit_tree.column(c, width=80, anchor=tk.CENTER)
        self.fit_tree.column("Тип", width=150)
        self.fit_tree.pack(fill=tk.X)

        # ── Права панель: результати ──
        right = ttk.LabelFrame(self.frame, text="Результати розрахунку", padding=10)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        self.result_labels = {}
        result_fields = [
            ("air_flow", "Потік повітря:", "м³/год"),
            ("velocity", "Швидкість в трубі:", "м/с"),
            ("dyn_pressure", "Динамічний тиск:", "Па"),
            ("friction_loss", "Втрати на тертя:", "Па"),
            ("local_loss", "Місцеві втрати:", "Па"),
            ("total_loss_pa", "ЗАГАЛЬНІ ВТРАТИ:", "Па"),
            ("total_loss_mm", "Втрати тиску:", "мм вод.ст."),
        ]
        for i, (key, text, unit) in enumerate(result_fields):
            ttk.Label(right, text=text, font=("Arial", 9)).grid(row=i, column=0, sticky=tk.W, pady=3)
            lbl = ttk.Label(right, text="—", font=("Arial", 10, "bold"))
            lbl.grid(row=i, column=1, sticky=tk.W, pady=3, padx=5)
            ttk.Label(right, text=unit, font=("Arial", 8), foreground="#666").grid(row=i, column=2, sticky=tk.W, pady=3)
            self.result_labels[key] = lbl

        ttk.Separator(right, orient=tk.HORIZONTAL).grid(row=len(result_fields), column=0, columnspan=3, sticky=tk.EW, pady=10)

        # ── Підбір вентилятора ──
        fan_frame = ttk.LabelFrame(right, text="Підбір вентилятора", padding=5)
        fan_frame.grid(row=len(result_fields)+1, column=0, columnspan=3, sticky=tk.EW, pady=5)

        ttk.Label(fan_frame, text="Тип:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.fan_type_var = tk.StringVar(value="будь-який")
        ttk.Combobox(fan_frame, textvariable=self.fan_type_var,
                     values=["будь-який"] + get_all_fan_types(), state="readonly", width=15).grid(row=0, column=1, padx=2)

        ttk.Button(fan_frame, text="🔍 Підібрати", command=self._select_fan).grid(row=0, column=2, padx=5)

        self.fan_result_var = tk.StringVar(value="Вентилятор не підібрано")
        ttk.Label(fan_frame, textvariable=self.fan_result_var, font=("Arial", 9, "bold"),
                  foreground="#0066cc", wraplength=250).grid(row=1, column=0, columnspan=3, pady=5)

        self.fan_details_var = tk.StringVar(value="")
        ttk.Label(fan_frame, textvariable=self.fan_details_var, font=("Arial", 8),
                  foreground="#666", wraplength=250).grid(row=2, column=0, columnspan=3)

        # ── Підказка ──
        hint = ttk.Label(
            self.frame,
            text="💡 Введіть параметри траси → додайте ділянки → додайте фітинги → натисніть «Розрахувати». "
                 "Потім підберіть вентилятор. ζ — коефіцієнт місцевого опору.",
            foreground="#666", font=("Arial", 8)
        )
        hint.pack(anchor=tk.W, padx=5, pady=2)

        # ── Внутрішні списки ──
        self.sections: list[DuctSection] = []
        self.fittings: list[Fitting] = []

    def _add_section(self):
        """Додати ділянку до траси."""
        name = f"Ділянка {len(self.sections) + 1}"
        shape_str = self.shape_var.get()
        shape = DuctShape.CIRCULAR if shape_str == "круглий" else DuctShape.RECTANGULAR

        section = DuctSection(
            name=name,
            length=self.length_var.get(),
            width=self.width_var.get(),
            height=self.height_var.get() if shape == DuctShape.RECTANGULAR else 0,
            shape=shape,
            air_flow=self.air_flow_var.get(),
        )
        self.sections.append(section)

        # Оновити таблицю
        self.sec_tree.insert("", tk.END, values=(
            len(self.sections),
            name,
            section.length,
            section.width,
            section.height if shape == DuctShape.RECTANGULAR else section.width,
            shape.value,
            section.air_flow,
            f"{section.velocity:.1f}",
            f"{section.friction_loss():.1f}",
        ))

        # Оновити список ділянок для фітингів
        self.fit_section_combo["values"] = [str(i + 1) for i in range(len(self.sections))]
        self.fit_section_combo.set(str(len(self.sections)))

    def _add_fitting(self):
        """Додати фітинг."""
        if not self.sections:
            messagebox.showwarning("Увага", "Спочатку додайте хоча б одну ділянку.")
            return

        fit_type_str = self.fit_type_var.get()
        # Знайти FittingType за значенням
        fit_type = None
        for ft in FittingType:
            if ft.value == fit_type_str:
                fit_type = ft
                break
        if fit_type is None:
            return

        sec_idx = int(self.fit_section_var.get()) - 1
        if sec_idx < 0 or sec_idx >= len(self.sections):
            return

        section = self.sections[sec_idx]
        qty = self.fit_qty_var.get()

        fitting = Fitting(
            name=f"{fit_type.value} #{len(self.fittings) + 1}",
            fitting_type=fit_type,
            section=section,
            quantity=qty,
        )
        self.fittings.append(fitting)

        self.fit_tree.insert("", tk.END, values=(
            len(self.fittings),
            fit_type.value,
            f"{fitting.zeta:.2f}",
            qty,
            section.name,
            f"{fitting.local_loss():.1f}",
        ))

    def _calculate(self):
        """Розрахувати втрати тиску."""
        if not self.sections:
            messagebox.showwarning("Увага", "Додайте хоча б одну ділянку траси.")
            return

        self.current_route = AerodynamicRoute(
            name=self.route_name_var.get(),
            system_type=self.system_type_var.get(),
            sections=self.sections,
            fittings=self.fittings,
        )

        s = self.current_route.get_summary()

        # Оновити результати
        self.result_labels["air_flow"].config(text=f"{s['total_air_flow']:.0f}")
        if self.sections:
            v = self.sections[0].velocity
            dp = self.sections[0].dynamic_pressure
            self.result_labels["velocity"].config(text=f"{v:.1f}")
            self.result_labels["dyn_pressure"].config(text=f"{dp:.1f}")
        self.result_labels["friction_loss"].config(text=f"{s['friction_loss_pa']:.1f}")
        self.result_labels["local_loss"].config(text=f"{s['local_loss_pa']:.1f}")
        self.result_labels["total_loss_pa"].config(text=f"{s['total_loss_pa']:.1f}", foreground="#cc0000")
        self.result_labels["total_loss_mm"].config(text=f"{s['total_loss_mm']:.2f}")

        # Оновити таблицю ділянок з розрахованими втратами
        for item in self.sec_tree.get_children():
            self.sec_tree.delete(item)
        for i, sec in enumerate(self.sections):
            self.sec_tree.insert("", tk.END, values=(
                i + 1,
                sec.name,
                sec.length,
                sec.width,
                sec.height if sec.shape == DuctShape.RECTANGULAR else sec.width,
                sec.shape.value,
                sec.air_flow,
                f"{sec.velocity:.1f}",
                f"{sec.friction_loss():.1f}",
            ))

        # Оновити таблицю фітингів
        for item in self.fit_tree.get_children():
            self.fit_tree.delete(item)
        for i, fit in enumerate(self.fittings):
            self.fit_tree.insert("", tk.END, values=(
                i + 1,
                fit.fitting_type.value,
                f"{fit.zeta:.2f}",
                fit.quantity,
                fit.section.name,
                f"{fit.local_loss():.1f}",
            ))

    def _select_fan(self):
        """Підібрати вентилятор."""
        if not self.current_route:
            messagebox.showwarning("Увага", "Спочатку розрахуйте втрати тиску.")
            return

        flow = self.current_route.total_air_flow
        pressure = self.current_route.total_pressure_loss
        fan_type = self.fan_type_var.get()
        if fan_type == "будь-який":
            fan_type = None

        fan = select_fan(flow, pressure, fan_type)
        if fan:
            self.fan_result_var.set(f"✅ {fan['name']}")
            self.fan_details_var.set(
                f"Тип: {fan['type']} | Потік: {fan['flow_min']}-{fan['flow_max']} м³/год | "
                f"Тиск: {fan['pressure_min']}-{fan['pressure_max']} Па | "
                f"Потужність: {fan['power']} кВт | Шум: {fan['noise']} дБ | Ціна: {fan['price']} грн"
            )
        else:
            self.fan_result_var.set("❌ Вентилятор не знайдено")
            self.fan_details_var.set(
                f"Потрібно: {flow:.0f} м³/год, {pressure:.1f} Па. "
                "Спробуйте змінити тип або зменшити опори."
            )

    def _clear(self):
        """Очистити всі дані."""
        self.sections = []
        self.fittings = []
        self.current_route = None

        for item in self.sec_tree.get_children():
            self.sec_tree.delete(item)
        for item in self.fit_tree.get_children():
            self.fit_tree.delete(item)

        for key in self.result_labels:
            self.result_labels[key].config(text="—", foreground="black")
        self.result_labels["total_loss_pa"].config(foreground="black")

        self.fan_result_var.set("Вентилятор не підібрано")
        self.fan_details_var.set("")
        self.fit_section_combo["values"] = ["1"]
        self.fit_section_combo.set("1")
