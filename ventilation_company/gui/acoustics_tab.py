"""Вкладка "Акустика" — розрахунок рівня шуму та підбір шумоглушників."""

import tkinter as tk
from tkinter import messagebox, ttk

from ventilation_company.acoustics import (
    AcousticCalculator,
    AcousticReport,
    DuctPath,
    NoiseSource,
    Room,
    SILENCER_CATALOG,
    NOISE_LIMITS,
    OCTAVE_BANDS,
)


class AcousticsTab:
    """Вкладка акустичного розрахунку."""

    def __init__(self, parent: ttk.Notebook):
        self.frame = ttk.Frame(parent)
        self.current_report: AcousticReport | None = None

        self._build_ui()

    def _build_ui(self):
        # ── Ліва панель: параметри ──
        left = ttk.LabelFrame(self.frame, text="Параметри системи", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Вентилятор
        fan_frame = ttk.LabelFrame(left, text="Вентилятор", padding=5)
        fan_frame.grid(row=0, column=0, sticky=tk.EW, pady=3)

        ttk.Label(fan_frame, text="Тип:").grid(row=0, column=0, sticky=tk.W)
        self.fan_type_var = tk.StringVar(value="радіальний")
        ttk.Combobox(fan_frame, textvariable=self.fan_type_var,
                     values=["осьовий", "радіальний", "канальний", "діагональний"],
                     state="readonly", width=15).grid(row=0, column=1, padx=2)

        ttk.Label(fan_frame, text="Потік (м³/год):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.fan_flow_var = tk.DoubleVar(value=2000)
        ttk.Spinbox(fan_frame, from_=100, to=50000, textvariable=self.fan_flow_var, width=12).grid(row=1, column=1, padx=2)

        ttk.Label(fan_frame, text="Тиск (Па):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.fan_pressure_var = tk.DoubleVar(value=800)
        ttk.Spinbox(fan_frame, from_=10, to=5000, textvariable=self.fan_pressure_var, width=12).grid(row=2, column=1, padx=2)

        ttk.Label(fan_frame, text="Потужність (кВт):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.fan_power_var = tk.DoubleVar(value=0.75)
        ttk.Spinbox(fan_frame, from_=0.04, to=30, increment=0.1, textvariable=self.fan_power_var, width=12).grid(row=3, column=1, padx=2)

        # Повітропровід
        duct_frame = ttk.LabelFrame(left, text="Повітропровід", padding=5)
        duct_frame.grid(row=1, column=0, sticky=tk.EW, pady=5)

        ttk.Label(duct_frame, text="Довжина (м):").grid(row=0, column=0, sticky=tk.W)
        self.duct_length_var = tk.DoubleVar(value=20)
        ttk.Spinbox(duct_frame, from_=1, to=200, textvariable=self.duct_length_var, width=12).grid(row=0, column=1, padx=2)

        ttk.Label(duct_frame, text="Ширина (мм):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.duct_width_var = tk.DoubleVar(value=300)
        ttk.Spinbox(duct_frame, from_=50, to=2000, textvariable=self.duct_width_var, width=12).grid(row=1, column=1, padx=2)

        ttk.Label(duct_frame, text="Висота (мм):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.duct_height_var = tk.DoubleVar(value=200)
        ttk.Spinbox(duct_frame, from_=50, to=2000, textvariable=self.duct_height_var, width=12).grid(row=2, column=1, padx=2)

        ttk.Label(duct_frame, text="Швидкість (м/с):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.velocity_var = tk.DoubleVar(value=9.3)
        ttk.Spinbox(duct_frame, from_=1, to=25, textvariable=self.velocity_var, width=12).grid(row=3, column=1, padx=2)

        ttk.Label(duct_frame, text="Відводів:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.elbows_var = tk.IntVar(value=2)
        ttk.Spinbox(duct_frame, from_=0, to=20, textvariable=self.elbows_var, width=12).grid(row=4, column=1, padx=2)

        ttk.Label(duct_frame, text="Трійників:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.tees_var = tk.IntVar(value=1)
        ttk.Spinbox(duct_frame, from_=0, to=10, textvariable=self.tees_var, width=12).grid(row=5, column=1, padx=2)

        # Приміщення
        room_frame = ttk.LabelFrame(left, text="Приміщення", padding=5)
        room_frame.grid(row=2, column=0, sticky=tk.EW, pady=5)

        ttk.Label(room_frame, text="Тип:").grid(row=0, column=0, sticky=tk.W)
        self.room_type_var = tk.StringVar(value="офіс")
        ttk.Combobox(room_frame, textvariable=self.room_type_var,
                     values=list(NOISE_LIMITS.keys()), state="readonly", width=15).grid(row=0, column=1, padx=2)

        ttk.Label(room_frame, text="Об'єм (м³):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.room_volume_var = tk.DoubleVar(value=120)
        ttk.Spinbox(room_frame, from_=10, to=10000, textvariable=self.room_volume_var, width=12).grid(row=1, column=1, padx=2)

        ttk.Label(room_frame, text="Поглинання (м²):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.absorption_var = tk.DoubleVar(value=15)
        ttk.Spinbox(room_frame, from_=1, to=500, textvariable=self.absorption_var, width=12).grid(row=2, column=1, padx=2)

        # Кнопки
        ttk.Separator(left, orient=tk.HORIZONTAL).grid(row=3, column=0, sticky=tk.EW, pady=10)

        ttk.Button(left, text="📊 Розрахувати шум", command=self._calculate).grid(row=4, column=0, pady=5, sticky=tk.EW)
        ttk.Button(left, text="🔇 Підібрати шумоглушник", command=self._select_silencer).grid(row=5, column=0, pady=3, sticky=tk.EW)
        ttk.Button(left, text="🔄 Очистити", command=self._clear).grid(row=6, column=0, pady=3, sticky=tk.EW)

        # ── Центральна панель: результати ──
        center = ttk.Frame(self.frame)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Результати
        result_frame = ttk.LabelFrame(center, text="Результати розрахунку", padding=10)
        result_frame.pack(fill=tk.X, pady=2)

        self.result_labels = {}
        result_fields = [
            ("fan_noise", "Шум вентилятора Lw:", "дБА"),
            ("flow_noise", "Шум потоку Lw:", "дБА"),
            ("total_lw", "Сумарний Lw:", "дБА"),
            ("path_att", "Зниження на шляху:", "дБ"),
            ("silencer_att", "Шумоглушник:", "дБ"),
            ("result_lp", "Рівень у приміщенні Lp:", "дБА"),
            ("limit", "Допустимий рівень:", "дБА"),
            ("excess", "Перевищення:", "дБА"),
        ]
        for i, (key, text, unit) in enumerate(result_fields):
            ttk.Label(result_frame, text=text, font=("Arial", 10)).grid(row=i, column=0, sticky=tk.W, pady=3)
            lbl = ttk.Label(result_frame, text="—", font=("Arial", 11, "bold"))
            lbl.grid(row=i, column=1, sticky=tk.W, pady=3, padx=5)
            ttk.Label(result_frame, text=unit, font=("Arial", 9), foreground="#666").grid(row=i, column=2, sticky=tk.W, pady=3)
            self.result_labels[key] = lbl

        # Статус
        self.status_var = tk.StringVar(value="Введіть параметри та натисніть «Розрахувати шум»")
        status_lbl = ttk.Label(result_frame, textvariable=self.status_var,
                               font=("Arial", 10, "bold"), foreground="#0066cc")
        status_lbl.grid(row=len(result_fields), column=0, columnspan=3, pady=10, sticky=tk.W)

        # ── Права панель: каталог шумоглушників ──
        right = ttk.LabelFrame(self.frame, text="Каталог шумоглушників", padding=5)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        cols = ("Найменування", "Тип", "Розмір", "Зниження", "Δp", "Ціна")
        self.sil_tree = ttk.Treeview(right, columns=cols, show="headings", height=14)
        for c in cols:
            self.sil_tree.heading(c, text=c)
        self.sil_tree.column("Найменування", width=180)
        self.sil_tree.column("Тип", width=80)
        self.sil_tree.column("Розмір", width=80)
        self.sil_tree.column("Зниження", width=60, anchor=tk.CENTER)
        self.sil_tree.column("Δp", width=50, anchor=tk.CENTER)
        self.sil_tree.column("Ціна", width=60, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.sil_tree.yview)
        self.sil_tree.configure(yscrollcommand=vsb.set)
        self.sil_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._fill_silencer_catalog()

        # ── Підказка ──
        hint = ttk.Label(
            self.frame,
            text="💡 Введіть параметри вентилятора, повітропроводу та приміщення. Програма розрахує сумарний шум і порівняє з нормами. Якщо перевищення — підберіть шумоглушник з каталогу.",
            foreground="#666", font=("Arial", 8)
        )
        hint.pack(anchor=tk.W, padx=5, pady=2)

    def _fill_silencer_catalog(self):
        """Заповнити таблицю каталогу шумоглушників."""
        for sil in SILENCER_CATALOG:
            att = sil.get_total_attenuation()
            self.sil_tree.insert("", tk.END, values=(
                sil.name,
                sil.silencer_type.value,
                f"{int(sil.width_mm)}×{int(sil.height_mm)}",
                f"{att:.0f} дБ",
                f"{sil.pressure_drop_pa:.0f} Па",
                f"{sil.price:.0f} грн",
            ))

    def _calculate(self):
        """Розрахувати рівень шуму."""
        try:
            # Джерела шуму
            fan_noise = AcousticCalculator.calculate_fan_noise(
                fan_type=self.fan_type_var.get(),
                air_flow_m3h=self.fan_flow_var.get(),
                pressure_pa=self.fan_pressure_var.get(),
                fan_power_kw=self.fan_power_var.get(),
            )

            duct_area = (self.duct_width_var.get() / 1000) * (self.duct_height_var.get() / 1000)
            flow_noise = AcousticCalculator.calculate_flow_noise(
                velocity_ms=self.velocity_var.get(),
                duct_area_m2=duct_area,
            )

            grille_noise = AcousticCalculator.calculate_grille_noise(
                velocity_ms=self.velocity_var.get(),
                grille_area_m2=duct_area,
            )

            sources = [fan_noise, flow_noise, grille_noise]
            total_lw = AcousticCalculator.calculate_total_noise(sources)

            # Шлях поширення
            is_circ = self.duct_width_var.get() == self.duct_height_var.get()
            att_per_m = 0.5 if is_circ else 1.5
            duct_path = DuctPath(
                name="Шлях до приміщення",
                length_m=self.duct_length_var.get(),
                diameter_mm=(self.duct_width_var.get() + self.duct_height_var.get()) / 2,
                is_circular=is_circ,
                attenuation_per_meter=att_per_m,
                elbow_count=self.elbows_var.get(),
                tee_count=self.tees_var.get(),
            )

            # Приміщення
            room_type = self.room_type_var.get()
            limit = NOISE_LIMITS.get(room_type, 45)

            room = Room(
                name="Приміщення",
                room_type=room_type,
                volume_m3=self.room_volume_var.get(),
                absorption_m2=self.absorption_var.get(),
            )

            path_att = duct_path.get_path_attenuation()
            silencer_att = 0.0

            lp = room.calculate_lp(total_lw, path_att, silencer_att)
            excess = max(0, lp - limit)

            # Зберегти звіт
            self.current_report = AcousticReport(
                room_name="Приміщення",
                room_type=room_type,
                noise_limit=limit,
                sources=sources,
                duct_path=duct_path,
            )

            # Оновити UI
            self.result_labels["fan_noise"].config(text=f"{fan_noise.get_lw_total():.1f}")
            self.result_labels["flow_noise"].config(text=f"{flow_noise.get_lw_total():.1f}")
            self.result_labels["total_lw"].config(text=f"{total_lw:.1f}")
            self.result_labels["path_att"].config(text=f"{path_att:.1f}")
            self.result_labels["silencer_att"].config(text="0.0")
            self.result_labels["result_lp"].config(text=f"{lp:.1f}")
            self.result_labels["limit"].config(text=f"{limit}")

            if excess > 0:
                self.result_labels["excess"].config(text=f"+{excess:.1f}", foreground="#cc0000")
                self.status_var.set(f"❌ ПЕРЕВИЩЕННЯ НОРМИ на {excess:.1f} дБА! Потрібен шумоглушник.")
                self.status_var.set("❌ ПЕРЕВИЩЕННЯ НОРМИ на " + f"{excess:.1f}" + " дБА! Потрібен шумоглушник.")
            else:
                self.result_labels["excess"].config(text="0.0", foreground="#27ae60")
                self.status_var.set("✅ ВІДПОВІДАЄ НОРМАМ. Додатковий шумоглушник не потрібен.")

        except Exception as e:
            messagebox.showerror("Помилка розрахунку", str(e))

    def _select_silencer(self):
        """Підібрати шумоглушник."""
        if not self.current_report:
            messagebox.showwarning("Увага", "Спочатку розрахуйте шум.")
            return

        excess = self.current_report.excess_db
        if excess <= 0:
            messagebox.showinfo("Інформація", "Шум вже відповідає нормам. Шумоглушник не потрібен.")
            return

        # Підбір з запасом 3 дБ
        required = excess + 3

        silencer = AcousticCalculator.select_silencer(
            required_attenuation=required,
            duct_width=self.duct_width_var.get(),
            duct_height=self.duct_height_var.get(),
            max_pressure_drop=100,
        )

        if silencer:
            self.current_report.silencer = silencer
            att = silencer.get_total_attenuation()

            # Перерахувати з шумоглушником
            room = Room(
                name="Приміщення",
                room_type=self.room_type_var.get(),
                volume_m3=self.room_volume_var.get(),
                absorption_m2=self.absorption_var.get(),
            )
            new_lp = room.calculate_lp(
                self.current_report.source_lw_total,
                self.current_report.path_attenuation,
                att,
            )
            new_excess = max(0, new_lp - self.current_report.noise_limit)

            self.result_labels["silencer_att"].config(text=f"{att:.1f}")
            self.result_labels["result_lp"].config(text=f"{new_lp:.1f}")

            if new_excess > 0:
                self.result_labels["excess"].config(text=f"+{new_excess:.1f}", foreground="#cc0000")
                msg = ("⚠️ Рекомендовано: " + silencer.name +
                       " (зниження " + f"{att:.0f}" + " дБ). "
                       "Але все ще перевищення на " + f"{new_excess:.1f}" + " дБА. "
                       "Спробуйте більший шумоглушник або комбінацію.")
                self.status_var.set(msg)
            else:
                self.result_labels["excess"].config(text="0.0", foreground="#27ae60")
                msg = ("✅ Підібрано: " + silencer.name +
                       " (зниження " + f"{att:.0f}" + " дБ, " +
                       f"{silencer.pressure_drop_pa:.0f}" + " Па). "
                       "Шум у приміщенні: " + f"{new_lp:.1f}" + " дБА — ВІДПОВІДАЄ НОРМАМ!")
                self.status_var.set(msg)
        else:
            messagebox.showwarning(
                "Не знайдено",
                "Не знайдено шумоглушник для заданих розмірів. "
                "Спробуйте змінити розміри повітропроводу."
            )

    def _clear(self):
        """Очистити результати."""
        self.current_report = None
        for key in self.result_labels:
            self.result_labels[key].config(text="—", foreground="black")
        self.status_var.set("Введіть параметри та натисніть «Розрахувати шум»")
