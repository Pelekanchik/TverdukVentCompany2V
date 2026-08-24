import os
import glob

# Знаходимо ВСІ файли products_tab.py в проєкті
files = glob.glob("**/products_tab.py", recursive=True)
print("Знайдено файли products_tab.py:")
for f in files:
    print(f"  - {os.path.abspath(f)}")

if not files:
    print("Файл products_tab.py не знайдено!")
    exit(1)

# Беремо перший знайдений (має бути ventilation_company/gui/products_tab.py)
target = files[0]
print(f"\nВиправляємо: {target}")

with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# Перевіряємо, чи файл вже виправлений
if '"area_unit"' not in content:
    print("Файл вже виправлений (немає area_unit)")
    exit(0)

print("Знайдено старі колонки — виправляємо...")

# 1. Додаємо MATERIAL_SHORT
old_thick = """    THICKNESSES = {
        "0.5 мм": Thickness.T0_5,
        "0.7 мм": Thickness.T0_7,
        "0.9 мм": Thickness.T0_9,
        "1.0 мм": Thickness.T1_0,
        "1.2 мм": Thickness.T1_2,
        "1.5 мм": Thickness.T1_5,
        "2.0 мм": Thickness.T2_0,
    }"""

new_thick = """    THICKNESSES = {
        "0.5 мм": Thickness.T0_5,
        "0.7 мм": Thickness.T0_7,
        "0.9 мм": Thickness.T0_9,
        "1.0 мм": Thickness.T1_0,
        "1.2 мм": Thickness.T1_2,
        "1.5 мм": Thickness.T1_5,
        "2.0 мм": Thickness.T2_0,
    }

    MATERIAL_SHORT = {
        "оцинкована сталь": "оцинк. сталь",
        "нержавіюча сталь": "нерж. сталь",
        "алюміній": "алюм.",
    }"""

if old_thick in content:
    content = content.replace(old_thick, new_thick)
    print("✓ Додано MATERIAL_SHORT")

# 2. Замінюємо колонки
old_cols = """        columns = ("type", "dimensions", "material", "thickness", "qty",
                   "area_unit", "area_total", "blank_unit", "blank_total",
                   "mat_unit", "mat_total", "price_unit", "price_total")
        self.tree = ttk.Treeview(right_frame, columns=columns, show="headings", height=20)

        self.tree.heading("type", text="Тип")
        self.tree.heading("dimensions", text="Розміри")
        self.tree.heading("material", text="Матеріал")
        self.tree.heading("thickness", text="Товщ.")
        self.tree.heading("qty", text="К-ть")
        self.tree.heading("area_unit", text="Поверхня 1шт")
        self.tree.heading("area_total", text="Поверхня заг.")
        self.tree.heading("blank_unit", text="Заготівля 1шт")
        self.tree.heading("blank_total", text="Заготівля заг.")
        self.tree.heading("mat_unit", text="Матеріал 1шт")
        self.tree.heading("mat_total", text="Матеріал заг.")
        self.tree.heading("price_unit", text="Ціна 1шт")
        self.tree.heading("price_total", text="Ціна заг.")

        self.tree.column("type", width=140)
        self.tree.column("dimensions", width=90)
        self.tree.column("material", width=110)
        self.tree.column("thickness", width=45, anchor=tk.CENTER)
        self.tree.column("qty", width=45, anchor=tk.CENTER)
        self.tree.column("area_unit", width=70, anchor=tk.CENTER)
        self.tree.column("area_total", width=70, anchor=tk.CENTER)
        self.tree.column("blank_unit", width=70, anchor=tk.CENTER)
        self.tree.column("blank_total", width=70, anchor=tk.CENTER)
        self.tree.column("mat_unit", width=70, anchor=tk.CENTER)
        self.tree.column("mat_total", width=70, anchor=tk.CENTER)
        self.tree.column("price_unit", width=80, anchor=tk.CENTER)
        self.tree.column("price_total", width=80, anchor=tk.CENTER)"""

new_cols = """        columns = ("type", "dimensions", "material", "thickness", "qty",
                   "area_total", "blank_total", "mat_total", "price_total")
        self.tree = ttk.Treeview(right_frame, columns=columns, show="headings", height=20)

        self.tree.heading("type", text="Тип")
        self.tree.heading("dimensions", text="Розміри")
        self.tree.heading("material", text="Матеріал")
        self.tree.heading("thickness", text="Товщ.")
        self.tree.heading("qty", text="К-ть")
        self.tree.heading("area_total", text="Поверхня")
        self.tree.heading("blank_total", text="Заготівля")
        self.tree.heading("mat_total", text="Матеріал")
        self.tree.heading("price_total", text="Ціна")

        self.tree.column("type", width=140)
        self.tree.column("dimensions", width=90)
        self.tree.column("material", width=100)
        self.tree.column("thickness", width=45, anchor=tk.CENTER)
        self.tree.column("qty", width=45, anchor=tk.CENTER)
        self.tree.column("area_total", width=75, anchor=tk.CENTER)
        self.tree.column("blank_total", width=75, anchor=tk.CENTER)
        self.tree.column("mat_total", width=75, anchor=tk.CENTER)
        self.tree.column("price_total", width=85, anchor=tk.CENTER)"""

if old_cols in content:
    content = content.replace(old_cols, new_cols)
    print("✓ Колонки замінено")
else:
    print("⚠ Колонки не знайдено — можливо, файл вже змінено або інший формат")

# 3. Замінюємо _refresh_tree
old_refresh = """    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for p in self.library.products:
            mat_str = p._material_str() if hasattr(p, "_material_str") else str(p.material)
            thick_str = p._thickness_float() if hasattr(p, "_thickness_float") else float(p.thickness)
            try:
                unit_price = float(p.unit_price)
            except Exception:
                unit_price = 0.0
            try:
                total_price = float(p.total_price)
            except Exception:
                total_price = 0.0
            self.tree.insert(
                "", tk.END,
                values=(
                    p.product_type,
                    f"{p.width:.0f}×{p.height:.0f}×{p.length:.0f}",
                    mat_str,
                    f"{thick_str:.1f}",
                    p.quantity,
                    f"{p.surface_area:.3f}",
                    f"{p.surface_area * p.quantity:.3f}",
                    f"{p.blank_area:.3f}",
                    f"{p.blank_area * p.quantity:.3f}",
                    f"{p.material_area:.3f}",
                    f"{p.material_area * p.quantity:.3f}",
                    f"{unit_price:.2f}",
                    f"{total_price:.2f}",
                ),
            )"""

new_refresh = """    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for p in self.library.products:
            mat_str = p._material_str() if hasattr(p, "_material_str") else str(p.material)
            # Скорочуємо назву матеріалу
            mat_lower = mat_str.lower()
            for full, short in self.MATERIAL_SHORT.items():
                if full in mat_lower:
                    mat_str = short
                    break
            thick_str = p._thickness_float() if hasattr(p, "_thickness_float") else float(p.thickness)
            try:
                total_price = float(p.total_price)
            except Exception:
                total_price = 0.0
            self.tree.insert(
                "", tk.END,
                values=(
                    p.product_type,
                    f"{p.width:.0f}×{p.height:.0f}×{p.length:.0f}",
                    mat_str,
                    f"{thick_str:.1f}",
                    p.quantity,
                    f"{p.surface_area * p.quantity:.3f}",
                    f"{p.blank_area * p.quantity:.3f}",
                    f"{p.material_area * p.quantity:.3f}",
                    f"{total_price:.2f}",
                ),
            )"""

if old_refresh in content:
    content = content.replace(old_refresh, new_refresh)
    print("✓ _refresh_tree виправлено")
else:
    print("⚠ _refresh_tree не знайдено — можливо, файл вже змінено або інший формат")

with open(target, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\n✅ Файл збережено: {os.path.abspath(target)}")
print("\nТепер обов'язково:")
print("1. Видали папку __pycache__ в ventilation_company/gui/")
print("2. Перезапусти програму")
