"""🔧 Вкладка "Ціни на метал" — управління цінами на листовий метал.

Працює з тим самим файлом data/pricing_settings.json, що й PricingSettings.
"""

from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

from ventilation_company.gui.theme_manager import get_theme_manager

PRICING_SETTINGS_FILE = "data/pricing_settings.json"

DENSITIES = {
    "оцинкована сталь": 7850,
    "нержавіюча сталь": 7900,
    "алюміній": 2700,
    "пластик ПВХ": 1400,
    "ізоляція (базальтова вата)": 100,
}

DEFAULT_PRICES = {
    "оцинкована сталь": {0.5: 45.0, 0.7: 42.0, 1.0: 40.0, 1.2: 38.0, 1.5: 36.0, 2.0: 34.0},
    "нержавіюча сталь": {0.5: 120.0, 0.7: 115.0, 1.0: 110.0, 1.2: 108.0, 1.5: 105.0, 2.0: 100.0},
    "алюміній": {0.5: 180.0, 0.7: 175.0, 1.0: 170.0, 1.2: 168.0, 1.5: 165.0, 2.0: 160.0},
    "пластик ПВХ": {2.0: 35.0, 3.0: 32.0, 4.0: 30.0},
    "ізоляція (базальтова вата)": {50: 25.0, 100: 22.0},
}


class MetalPricesManager:
    def __init__(self, filepath: str = PRICING_SETTINGS_FILE):
        self.filepath = filepath
        self.prices: dict[str, dict[float, float]] = {}
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, encoding="utf-8") as f:
                    data = json.load(f)
                raw = data.get("material_prices", {})
                self.prices = {}
                for material, thicknesses in raw.items():
                    self.prices[material] = {}
                    for t_str, price in thicknesses.items():
                        self.prices[material][float(t_str)] = float(price)
            except Exception as e:
                print(f"[MetalPrices] Помилка завантаження: {e}")
                self.prices = DEFAULT_PRICES.copy()
        else:
            self.prices = DEFAULT_PRICES.copy()
            self.save()

    def save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        data = {}
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, encoding="utf-8") as f:
                    data = json.load(f)
            except (ValueError, TypeError):
                pass
        material_prices = {}
        for material, thicknesses in self.prices.items():
            material_prices[material] = {}
            for t, price in thicknesses.items():
                material_prices[material][str(t)] = price
        data["material_prices"] = material_prices
        data["_metal_prices_updated"] = datetime.now().isoformat()
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_price_per_kg(self, material: str, thickness: float) -> float | None:
        return self.prices.get(material, {}).get(thickness)

    def get_price_per_m2(self, material: str, thickness: float) -> float | None:
        price_kg = self.get_price_per_kg(material, thickness)
        if price_kg is None:
            return None
        density = DENSITIES.get(material, 7850)
        weight_per_m2 = (thickness / 1000) * density
        return price_kg * weight_per_m2

    def set_price(self, material: str, thickness: float, price_per_kg: float):
        if material not in self.prices:
            self.prices[material] = {}
        self.prices[material][thickness] = price_per_kg
        self.save()

    def delete_price(self, material: str, thickness: float) -> bool:
        if material in self.prices and thickness in self.prices[material]:
            del self.prices[material][thickness]
            if not self.prices[material]:
                del self.prices[material]
            self.save()
            return True
        return False

    def get_materials(self) -> list[str]:
        return sorted(self.prices.keys())

    def get_thicknesses(self, material: str) -> list[float]:
        return sorted(self.prices.get(material, {}).keys())

    def get_all_entries(self) -> list[dict]:
        entries = []
        for material, thicknesses in self.prices.items():
            for thickness, price_kg in thicknesses.items():
                price_m2 = self.get_price_per_m2(material, thickness)
                density = DENSITIES.get(material, 7850)
                entries.append({
                    "material": material,
                    "thickness": thickness,
                    "price_per_kg": price_kg,
                    "price_per_m2": price_m2,
                    "density": density,
                })
        return sorted(entries, key=lambda x: (x["material"], x["thickness"]))

    def get_manager(self) -> MetalPricesManager:
        return self


class MetalPricesTab:
    """Вкладка цін на метал."""

    def __init__(self, parent: ttk.Notebook):
        self.frame = ttk.Frame(parent)
        self.manager = MetalPricesManager()
        self.theme = get_theme_manager()
        self._build_ui()
        self._refresh_tree()

    def _fg(self, key="fg"):
        return self.theme.color(key)

    def _build_ui(self):
        top = ttk.Frame(self.frame, padding=5)
        top.pack(fill=tk.X)

        ttk.Label(top, text="🔧 Ціни на метал", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        ttk.Label(top, text="(єдине джерело для всієї програми)", font=("Arial", 9),
                  foreground=self._fg("fg_muted")).pack(side=tk.LEFT, padx=10)

        btn_frame = ttk.Frame(top)
        btn_frame.pack(side=tk.LEFT, padx=(20, 0))
        ttk.Button(btn_frame, text="➕ Додати", command=self._add_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="✏️ Редагувати", command=self._edit_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑️ Видалити", command=self._delete_selected).pack(side=tk.LEFT, padx=2)

        filter_frame = ttk.Frame(self.frame, padding=5)
        filter_frame.pack(fill=tk.X, padx=5)

        ttk.Label(filter_frame, text="Матеріал:").pack(side=tk.LEFT)
        self.filter_material_var = tk.StringVar(value="всі")
        self.material_combo = ttk.Combobox(
            filter_frame, textvariable=self.filter_material_var,
            values=["всі"] + self.manager.get_materials(), state="readonly", width=25
        )
        self.material_combo.pack(side=tk.LEFT, padx=5)
        self.filter_material_var.trace_add("write", lambda *args: self._refresh_tree())

        table_frame = ttk.Frame(self.frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("material", "thickness", "price_kg", "price_m2", "density")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)

        self.tree.heading("material", text="Матеріал")
        self.tree.heading("thickness", text="Товщина (мм)")
        self.tree.heading("price_kg", text="Ціна за кг (грн)")
        self.tree.heading("price_m2", text="Ціна за м² (грн)")
        self.tree.heading("density", text="Щільність (кг/м³)")

        self.tree.column("material", width=200, anchor=tk.W)
        self.tree.column("thickness", width=100, anchor=tk.CENTER)
        self.tree.column("price_kg", width=120, anchor=tk.CENTER)
        self.tree.column("price_m2", width=120, anchor=tk.CENTER)
        self.tree.column("density", width=120, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", lambda e: self._edit_dialog())

        self.summary_label = ttk.Label(
            self.frame, text="", font=("Consolas", 10), padding=5
        )
        self.summary_label.pack(fill=tk.X, padx=5)

        note = ttk.Label(
            self.frame,
            text="💡 Ці ціни використовуються автоматично в калькуляторі вкладки 'Ціноутворення'. "
                 "Ціна за м² обчислюється автоматично: ціна_за_кг × (товщина/1000) × щільність",
            font=("Arial", 9), foreground=self._fg("blue"), wraplength=800, justify=tk.LEFT
        )
        note.pack(fill=tk.X, padx=5, pady=(0, 5))

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        material_filter = self.filter_material_var.get()
        entries = self.manager.get_all_entries()
        if material_filter != "всі":
            entries = [e for e in entries if e["material"] == material_filter]
        for entry in entries:
            self.tree.insert("", tk.END, values=(
                entry["material"],
                entry["thickness"],
                f"{entry['price_per_kg']:.2f}",
                f"{entry['price_per_m2']:.2f}",
                entry["density"],
            ), tags=(f"{entry['material']}|{entry['thickness']}",))

        self.summary_label.config(
            text=f"Матеріалів: {len(self.manager.get_materials())} | Записів: {len(entries)} | "
                 f"Файл: data/pricing_settings.json"
        )
        current = list(self.material_combo["values"] or [])
        new_values = ["всі"] + self.manager.get_materials()
        if current != new_values:
            self.material_combo["values"] = new_values

    def _get_selected(self) -> tuple[str, float] | None:
        selected = self.tree.selection()
        if not selected:
            return None
        values = self.tree.item(selected[0], "values")
        if values:
            return values[0], float(values[1])
        return None

    def _add_dialog(self):
        self._open_dialog()

    def _edit_dialog(self):
        selected = self._get_selected()
        if not selected:
            messagebox.showwarning("Увага", "Оберіть запис для редагування")
            return
        material, thickness = selected
        price_kg = self.manager.get_price_per_kg(material, thickness)
        if price_kg is not None:
            self._open_dialog(material, thickness, price_kg)

    def _open_dialog(self, material: str = "", thickness: float = 0.0, price_kg: float = 0.0):
        dialog = tk.Toplevel(self.frame)
        dialog.title("Редагувати ціну" if material else "Додати ціну на метал")
        dialog.geometry("420x300")
        dialog.minsize(400, 260)
        dialog.transient(self.frame)
        dialog.grab_set()

        is_edit = bool(material)
        mat_var = tk.StringVar(value=material)
        thick_var = tk.StringVar(value=str(thickness) if thickness else "")
        kg_var = tk.StringVar(value=str(price_kg) if price_kg else "")

        row = 0
        ttk.Label(dialog, text="Матеріал:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        if is_edit:
            ttk.Label(dialog, text=material, font=("Arial", 10, "bold")).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        else:
            existing = self.manager.get_materials()
            if existing:
                ttk.Combobox(dialog, textvariable=mat_var, values=existing, width=25).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
            else:
                ttk.Entry(dialog, textvariable=mat_var, width=25).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        ttk.Label(dialog, text="Товщина (мм):").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        if is_edit:
            ttk.Label(dialog, text=str(thickness), font=("Arial", 10, "bold")).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        else:
            ttk.Entry(dialog, textvariable=thick_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        ttk.Label(dialog, text="Ціна за кг (грн):").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        ttk.Entry(dialog, textvariable=kg_var, width=12).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        if not is_edit:
            ttk.Label(dialog, text="Ціна за м² буде обчислена автоматично", foreground=self._fg("fg_muted")).grid(row=row, column=0, columnspan=2, padx=10, pady=2)
            row += 1

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=15)

        def save():
            try:
                mat = mat_var.get().strip()
                thick = float(thick_var.get())
                kg = float(kg_var.get())
                if not mat or thick <= 0 or kg < 0:
                    messagebox.showwarning("Увага", "Перевірте введені дані")
                    return
                self.manager.set_price(mat, thick, kg)
                self._refresh_tree()
                dialog.destroy()
            except ValueError:
                messagebox.showwarning("Увага", "Некоректні числові дані")

        ttk.Button(btn_frame, text="✅ Зберегти", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="❌ Скасувати", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _delete_selected(self):
        selected = self._get_selected()
        if not selected:
            messagebox.showwarning("Увага", "Оберіть запис для видалення")
            return
        material, thickness = selected
        if messagebox.askyesno("Підтвердження", f'Видалити "{material} {thickness}мм"?'):
            self.manager.delete_price(material, thickness)
            self._refresh_tree()

    def get_manager(self) -> MetalPricesManager:
        return self.manager
