"""Діалоги редагування та додавання елементів проєкту 3D.

Універсальні форми для всіх типів об'єктів.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Any

from ventilation_company.project3d.vent_system import (
    Point3D, DuctSegment, DuctShape, DuctType, Fitting, Equipment,
    VentilationTrunk, VentilationSystem,
)
from ventilation_company.project3d.arch_context import Wall, Opening, Floor


# ═══════════════════════════════════════════════════════════════
# Базовий діалог
# ═══════════════════════════════════════════════════════════════

class BaseDialog(tk.Toplevel):
    """Базовий діалог з кнопками OK/Cancel."""

    def __init__(self, parent, title: str, width: int = 450, height: int = 500):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.transient(parent)
        self.grab_set()
        self.result = None

        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="✅ Зберегти", command=self._on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="❌ Скасувати", command=self._on_cancel).pack(side=tk.RIGHT, padx=5)

        self._fields = {}
        self._build_form()

    def _build_form(self):
        pass

    def _add_field(self, label: str, row: int, default: str = "",
                   var_type: str = "entry", width: int = 25, options: list = None):
        ttk.Label(self.scrollable_frame, text=label + ":").grid(row=row, column=0, sticky=tk.W, padx=5, pady=3)

        if var_type == "entry":
            var = tk.StringVar(value=str(default))
            widget = ttk.Entry(self.scrollable_frame, textvariable=var, width=width)
        elif var_type == "spin":
            var = tk.DoubleVar(value=float(default) if default else 0)
            widget = ttk.Spinbox(self.scrollable_frame, from_=0, to=99999, increment=1,
                                 textvariable=var, width=width)
        elif var_type == "combo":
            var = tk.StringVar(value=str(default))
            widget = ttk.Combobox(self.scrollable_frame, textvariable=var, values=options or [],
                                  state="readonly", width=width)
        elif var_type == "text":
            widget = tk.Text(self.scrollable_frame, width=width, height=4, wrap=tk.WORD)
            widget.insert("1.0", str(default))
            var = widget
        else:
            var = tk.StringVar(value=str(default))
            widget = ttk.Entry(self.scrollable_frame, textvariable=var, width=width)

        widget.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=3)
        self._fields[label] = var
        return var

    def _get_value(self, label: str):
        val = self._fields.get(label)
        if isinstance(val, tk.Text):
            return val.get("1.0", tk.END).strip()
        return val.get() if val else ""

    def _on_ok(self):
        self.result = self._collect_data()
        if self.result is not None:
            self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()

    def _collect_data(self):
        return {}

    def show(self):
        self.wait_window()
        return self.result


# ═══════════════════════════════════════════════════════════════
# DuctSegment Dialog
# ═══════════════════════════════════════════════════════════════

class EditSegmentDialog(BaseDialog):
    """Діалог редагування сегмента повітропроводу."""

    def __init__(self, parent, segment: DuctSegment):
        self.segment = segment
        super().__init__(parent, f"Редагування сегмента {segment.id}", 450, 550)

    def _build_form(self):
        ttk.Label(self.scrollable_frame, text="Сегмент повітропроводу",
                  font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        self._add_field("ID", 1, self.segment.id)
        self._add_field("Назва", 2, getattr(self.segment, "name", ""))
        self._add_field("Початок X", 3, self.segment.start.x, "spin")
        self._add_field("Початок Y", 4, self.segment.start.y, "spin")
        self._add_field("Початок Z", 5, self.segment.start.z, "spin")
        self._add_field("Кінець X", 6, self.segment.end.x, "spin")
        self._add_field("Кінець Y", 7, self.segment.end.y, "spin")
        self._add_field("Кінець Z", 8, self.segment.end.z, "spin")
        self._add_field("Ширина", 9, self.segment.width, "spin")
        self._add_field("Висота", 10, self.segment.height, "spin")
        self._add_field("Довжина", 11, self.segment.length, "spin")
        self._add_field("Форма", 12, self.segment.shape.value, "combo",
                        ["прямокутний", "круглий"])
        self._add_field("Тип повітря", 13, self.segment.duct_type.value, "combo",
                        ["приплив", "витяжка", "рециркуляція", "димовидалення"])
        self._add_field("Матеріал", 14, self.segment.material)
        self._add_field("Товщина", 15, self.segment.thickness, "spin")
        self._add_field("Ізоляція", 16, "Так" if self.segment.insulation else "Ні", "combo",
                        ["Так", "Ні"])
        self._add_field("Примітки", 17, self.segment.notes, "text")

    def _collect_data(self):
        try:
            return {
                "id": self._get_value("ID"),
                "start": Point3D(
                    float(self._get_value("Початок X")),
                    float(self._get_value("Початок Y")),
                    float(self._get_value("Початок Z")),
                ),
                "end": Point3D(
                    float(self._get_value("Кінець X")),
                    float(self._get_value("Кінець Y")),
                    float(self._get_value("Кінець Z")),
                ),
                "width": float(self._get_value("Ширина")),
                "height": float(self._get_value("Висота")),
                "length": float(self._get_value("Довжина")),
                "shape": DuctShape(self._get_value("Форма")),
                "duct_type": DuctType(self._get_value("Тип повітря")),
                "material": self._get_value("Матеріал"),
                "thickness": float(self._get_value("Товщина")),
                "insulation": self._get_value("Ізоляція") == "Так",
                "notes": self._get_value("Примітки"),
            }
        except ValueError as e:
            messagebox.showerror("Помилка", f"Некоректне числове значення: {e}")
            return None


class AddSegmentDialog(EditSegmentDialog):
    """Діалог додавання нового сегмента."""

    def __init__(self, parent, default_start: Point3D = None):
        seg = DuctSegment(
            start=default_start or Point3D(0, 0, 2500),
            end=Point3D(1000, 0, 2500),
        )
        super().__init__(parent, seg)
        self.title("Додавання сегмента повітропроводу")


# ═══════════════════════════════════════════════════════════════
# Equipment Dialog
# ═══════════════════════════════════════════════════════════════

class EditEquipmentDialog(BaseDialog):
    """Діалог редагування обладнання."""

    def __init__(self, parent, equipment: Equipment):
        self.equipment = equipment
        super().__init__(parent, f"Редагування обладнання {equipment.name}", 450, 520)

    def _build_form(self):
        ttk.Label(self.scrollable_frame, text="Обладнання",
                  font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        self._add_field("ID", 1, self.equipment.id)
        self._add_field("Назва", 2, self.equipment.name)
        self._add_field("Позиція X", 3, self.equipment.position.x, "spin")
        self._add_field("Позиція Y", 4, self.equipment.position.y, "spin")
        self._add_field("Позиція Z", 5, self.equipment.position.z, "spin")
        self._add_field("Ширина", 6, self.equipment.width, "spin")
        self._add_field("Висота", 7, self.equipment.height, "spin")
        self._add_field("Довжина", 8, self.equipment.length, "spin")
        self._add_field("Витрата повітря", 9, self.equipment.air_flow, "spin")
        self._add_field("Тиск", 10, self.equipment.pressure, "spin")
        self._add_field("Потужність", 11, self.equipment.power, "spin")
        self._add_field("Примітки", 12, self.equipment.notes, "text")

    def _collect_data(self):
        try:
            return {
                "id": self._get_value("ID"),
                "name": self._get_value("Назва"),
                "position": Point3D(
                    float(self._get_value("Позиція X")),
                    float(self._get_value("Позиція Y")),
                    float(self._get_value("Позиція Z")),
                ),
                "width": float(self._get_value("Ширина")),
                "height": float(self._get_value("Висота")),
                "length": float(self._get_value("Довжина")),
                "air_flow": float(self._get_value("Витрата повітря")),
                "pressure": float(self._get_value("Тиск")),
                "power": float(self._get_value("Потужність")),
                "notes": self._get_value("Примітки"),
            }
        except ValueError as e:
            messagebox.showerror("Помилка", f"Некоректне числове значення: {e}")
            return None


class AddEquipmentDialog(EditEquipmentDialog):
    """Діалог додавання нового обладнання."""

    def __init__(self, parent, default_position: Point3D = None):
        eq = Equipment(name="Нове обладнання", position=default_position or Point3D(0, 0, 2500))
        super().__init__(parent, eq)
        self.title("Додавання обладнання")


# ═══════════════════════════════════════════════════════════════
# Wall Dialog
# ═══════════════════════════════════════════════════════════════

class EditWallDialog(BaseDialog):
    """Діалог редагування стіни."""

    def __init__(self, parent, wall: Wall):
        self.wall = wall
        super().__init__(parent, f"Редагування стіни {wall.name}", 450, 480)

    def _build_form(self):
        ttk.Label(self.scrollable_frame, text="Стіна",
                  font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        self._add_field("ID", 1, self.wall.id)
        self._add_field("Назва", 2, self.wall.name)
        self._add_field("Початок X", 3, self.wall.start.x, "spin")
        self._add_field("Початок Y", 4, self.wall.start.y, "spin")
        self._add_field("Початок Z", 5, self.wall.start.z, "spin")
        self._add_field("Кінець X", 6, self.wall.end.x, "spin")
        self._add_field("Кінець Y", 7, self.wall.end.y, "spin")
        self._add_field("Кінець Z", 8, self.wall.end.z, "spin")
        self._add_field("Висота", 9, self.wall.height, "spin")
        self._add_field("Товщина", 10, self.wall.thickness, "spin")
        self._add_field("Матеріал", 11, self.wall.material.value, "combo",
                        ["цегла", "бетон", "гіпсокартон", "метал", "невідомо"])
        self._add_field("Несуча", 12, "Так" if self.wall.is_load_bearing else "Ні", "combo",
                        ["Так", "Ні"])
        self._add_field("Примітки", 13, self.wall.notes, "text")

    def _collect_data(self):
        try:
            from ventilation_company.project3d.arch_context import WallMaterial
            return {
                "id": self._get_value("ID"),
                "name": self._get_value("Назва"),
                "start": Point3D(
                    float(self._get_value("Початок X")),
                    float(self._get_value("Початок Y")),
                    float(self._get_value("Початок Z")),
                ),
                "end": Point3D(
                    float(self._get_value("Кінець X")),
                    float(self._get_value("Кінець Y")),
                    float(self._get_value("Кінець Z")),
                ),
                "height": float(self._get_value("Висота")),
                "thickness": float(self._get_value("Товщина")),
                "material": WallMaterial(self._get_value("Матеріал")),
                "is_load_bearing": self._get_value("Несуча") == "Так",
                "notes": self._get_value("Примітки"),
            }
        except ValueError as e:
            messagebox.showerror("Помилка", f"Некоректне числове значення: {e}")
            return None


class AddWallDialog(EditWallDialog):
    """Діалог додавання нової стіни."""

    def __init__(self, parent):
        wall = Wall(name="Нова стіна")
        super().__init__(parent, wall)
        self.title("Додавання стіни")


# ═══════════════════════════════════════════════════════════════
# Fitting Dialog
# ═══════════════════════════════════════════════════════════════

class EditFittingDialog(BaseDialog):
    """Діалог редагування фасонного виробу."""

    def __init__(self, parent, fitting: Fitting):
        self.fitting = fitting
        super().__init__(parent, f"Редагування: {fitting.fitting_type}", 450, 520)

    def _build_form(self):
        ttk.Label(self.scrollable_frame, text="Фасонний виріб",
                  font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        self._add_field("ID", 1, self.fitting.id)
        self._add_field("Тип", 2, self.fitting.fitting_type, "combo",
                        ["відвід", "трійник", "перехід", "фланець", "заглушка", "гнучка вставка"])
        self._add_field("Позиція X", 3, self.fitting.position.x, "spin")
        self._add_field("Позиція Y", 4, self.fitting.position.y, "spin")
        self._add_field("Позиція Z", 5, self.fitting.position.z, "spin")
        self._add_field("Ширина входу", 6, self.fitting.width_in, "spin")
        self._add_field("Висота входу", 7, self.fitting.height_in, "spin")
        self._add_field("Ширина виходу", 8, self.fitting.width_out, "spin")
        self._add_field("Висота виходу", 9, self.fitting.height_out, "spin")
        self._add_field("Кут", 10, self.fitting.angle, "spin")
        self._add_field("Радіус", 11, self.fitting.radius, "spin")
        self._add_field("Матеріал", 12, self.fitting.material)
        self._add_field("Товщина", 13, self.fitting.thickness, "spin")
        self._add_field("Примітки", 14, self.fitting.notes, "text")

    def _collect_data(self):
        try:
            return {
                "id": self._get_value("ID"),
                "fitting_type": self._get_value("Тип"),
                "position": Point3D(
                    float(self._get_value("Позиція X")),
                    float(self._get_value("Позиція Y")),
                    float(self._get_value("Позиція Z")),
                ),
                "width_in": float(self._get_value("Ширина входу")),
                "height_in": float(self._get_value("Висота входу")),
                "width_out": float(self._get_value("Ширина виходу")),
                "height_out": float(self._get_value("Висота виходу")),
                "angle": float(self._get_value("Кут")),
                "radius": float(self._get_value("Радіус")),
                "material": self._get_value("Матеріал"),
                "thickness": float(self._get_value("Товщина")),
                "notes": self._get_value("Примітки"),
            }
        except ValueError as e:
            messagebox.showerror("Помилка", f"Некоректне числове значення: {e}")
            return None


class AddFittingDialog(EditFittingDialog):
    """Діалог додавання нового фасонного виробу."""

    def __init__(self, parent, default_position: Point3D = None):
        fitting = Fitting(fitting_type="відвід", position=default_position or Point3D(0, 0, 2500))
        super().__init__(parent, fitting)
        self.title("Додавання фасонного виробу")


# ═══════════════════════════════════════════════════════════════
# VentilationSystem Dialog
# ═══════════════════════════════════════════════════════════════

class EditSystemDialog(BaseDialog):
    """Діалог редагування вентиляційної системи."""

    def __init__(self, parent, system: VentilationSystem):
        self.system = system
        super().__init__(parent, f"Редагування системи {system.name}", 450, 350)

    def _build_form(self):
        ttk.Label(self.scrollable_frame, text="Вентиляційна система",
                  font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        self._add_field("ID", 1, self.system.id)
        self._add_field("Назва", 2, self.system.name)
        self._add_field("Тип системи", 3, self.system.system_type, "combo",
                        ["припливна", "витяжна", "припливно-витяжна", "димовидалення", "кондиціонування"])
        self._add_field("Витрата повітря", 4, self.system.total_air_flow, "spin")
        self._add_field("Тиск", 5, self.system.total_pressure, "spin")
        self._add_field("Примітки", 6, self.system.notes, "text")

    def _collect_data(self):
        try:
            return {
                "id": self._get_value("ID"),
                "name": self._get_value("Назва"),
                "system_type": self._get_value("Тип системи"),
                "total_air_flow": float(self._get_value("Витрата повітря")),
                "total_pressure": float(self._get_value("Тиск")),
                "notes": self._get_value("Примітки"),
            }
        except ValueError as e:
            messagebox.showerror("Помилка", f"Некоректне числове значення: {e}")
            return None


class AddSystemDialog(EditSystemDialog):
    """Діалог додавання нової системи."""

    def __init__(self, parent):
        system = VentilationSystem(name="Нова система")
        super().__init__(parent, system)
        self.title("Додавання вентиляційної системи")


# ═══════════════════════════════════════════════════════════════
# VentilationTrunk Dialog
# ═══════════════════════════════════════════════════════════════

class EditTrunkDialog(BaseDialog):
    """Діалог редагування трасси."""

    def __init__(self, parent, trunk: VentilationTrunk):
        self.trunk = trunk
        super().__init__(parent, f"Редагування трасси {trunk.name}", 450, 350)

    def _build_form(self):
        ttk.Label(self.scrollable_frame, text="Трасса (магістраль)",
                  font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        self._add_field("ID", 1, self.trunk.id)
        self._add_field("Назва", 2, self.trunk.name)
        self._add_field("Поверх", 3, str(self.trunk.floor))
        self._add_field("Тип повітря", 4, self.trunk.duct_type.value, "combo",
                        ["приплив", "витяжка", "рециркуляція", "димовидалення"])
        self._add_field("Витрата", 5, self.trunk.air_flow, "spin")
        self._add_field("Примітки", 6, self.trunk.notes, "text")

    def _collect_data(self):
        try:
            return {
                "id": self._get_value("ID"),
                "name": self._get_value("Назва"),
                "floor": self._get_value("Поверх"),
                "duct_type": DuctType(self._get_value("Тип повітря")),
                "air_flow": float(self._get_value("Витрата")),
                "notes": self._get_value("Примітки"),
            }
        except ValueError as e:
            messagebox.showerror("Помилка", f"Некоректне числове значення: {e}")
            return None


class AddTrunkDialog(EditTrunkDialog):
    """Діалог додавання нової трасси."""

    def __init__(self, parent):
        trunk = VentilationTrunk(name="Нова трасса")
        super().__init__(parent, trunk)
        self.title("Додавання трасси")
