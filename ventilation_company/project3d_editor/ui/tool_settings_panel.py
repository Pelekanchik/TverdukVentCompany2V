"""Панель налаштувань поточного інструменту (під тулбаром)."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Optional

from ventilation_company.project3d_editor.tools.base_tool import BaseTool
from ventilation_company.project3d_editor.tools.duct_tool import DuctTool
from ventilation_company.project3d_editor.tools.fitting_tool import FittingTool
from ventilation_company.project3d_editor.tools.wall_tool import WallTool
from ventilation_company.project3d_editor.tools.equipment_tool import EquipmentTool


class ToolSettingsPanel(ttk.LabelFrame):
    """Панель налаштувань активного інструменту."""

    def __init__(self, parent: tk.Widget):
        super().__init__(parent, text="Налаштування інструменту", padding=3)
        self._current_tool: Optional[BaseTool] = None
        self._fields: dict = {}

    def update_for_tool(self, tool: Optional[BaseTool]) -> None:
        """Оновити панель відповідно до активного інструменту."""
        # Очистити
        for w in self.winfo_children():
            w.destroy()
        self._fields.clear()
        self._current_tool = tool

        if tool is None:
            return

        if isinstance(tool, DuctTool):
            self._build_duct_settings(tool)
        elif isinstance(tool, FittingTool):
            self._build_fitting_settings(tool)
        elif isinstance(tool, WallTool):
            self._build_wall_settings(tool)
        elif isinstance(tool, EquipmentTool):
            self._build_equipment_settings(tool)
        else:
            ttk.Label(self, text="Немає налаштувань", foreground="gray").pack(pady=5)

    def _add_combo(self, parent, label: str, values: list, current: str, callback) -> ttk.Combobox:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=1)
        ttk.Label(frame, text=label, width=12).pack(side=tk.LEFT)
        var = tk.StringVar(value=current)
        combo = ttk.Combobox(frame, textvariable=var, values=values, width=15, state="readonly")
        combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        combo.bind("<<ComboboxSelected>>", lambda e: callback(var.get()))
        return combo

    def _add_entry(self, parent, label: str, value, callback, width=8) -> ttk.Entry:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=1)
        ttk.Label(frame, text=label, width=12).pack(side=tk.LEFT)
        var = tk.StringVar(value=str(value))
        entry = ttk.Entry(frame, textvariable=var, width=width)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind("<FocusOut>", lambda e: self._try_apply(callback, var))
        entry.bind("<Return>", lambda e: self._try_apply(callback, var))
        return entry

    def _add_check(self, parent, label: str, value: bool, callback) -> ttk.Checkbutton:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=1)
        var = tk.BooleanVar(value=value)
        chk = ttk.Checkbutton(frame, text=label, variable=var,
                              command=lambda: callback(var.get()))
        chk.pack(side=tk.LEFT)
        return chk

    def _try_apply(self, callback, var):
        try:
            val = var.get()
            callback(val)
        except Exception:
            pass

    # ── DuctTool ──
    def _build_duct_settings(self, tool: DuctTool) -> None:
        ttk.Label(self, text="🌬️ Повітропровід", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 3))

        # Тип системи
        self._add_combo(self, "Система:",
                        ["приплив", "витяжка", "димовидалення"],
                        tool.duct_type,
                        lambda v: self._set_duct_type(tool, v))

        # Розміри
        self._add_entry(self, "Ширина:", tool.width,
                        lambda v: setattr(tool, "width", float(v)))
        self._add_entry(self, "Висота:", tool.height,
                        lambda v: setattr(tool, "height", float(v)))

        # Круглий
        self._add_check(self, "Круглий", tool.is_round,
                        lambda v: setattr(tool, "is_round", v))

    def _set_duct_type(self, tool: DuctTool, value: str) -> None:
        tool.duct_type = value
        # Оновити preview якщо є
        if tool.renderer._last_mouse_pos and tool._start_point is not None:
            tool.on_mouse_move(tool.renderer._last_mouse_pos)

    # ── FittingTool ──
    def _build_fitting_settings(self, tool: FittingTool) -> None:
        ttk.Label(self, text="🔀 Фасонний виріб", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 3))

        # Тип виробу
        self._add_combo(self, "Тип виробу:",
                        ["відвід", "трійник", "перехід", "заглушка", "фланець", "клапан"],
                        tool.fitting_type,
                        lambda v: setattr(tool, "fitting_type", v))

        # Тип системи
        self._add_combo(self, "Система:",
                        ["приплив", "витяжка", "димовидалення"],
                        tool.duct_type,
                        lambda v: self._set_fitting_type(tool, v))

        # Розміри
        self._add_entry(self, "Вх. ширина:", tool.width_in,
                        lambda v: setattr(tool, "width_in", float(v)))
        self._add_entry(self, "Вх. висота:", tool.height_in,
                        lambda v: setattr(tool, "height_in", float(v)))
        self._add_entry(self, "Вих. ширина:", tool.width_out,
                        lambda v: setattr(tool, "width_out", float(v)))
        self._add_entry(self, "Вих. висота:", tool.height_out,
                        lambda v: setattr(tool, "height_out", float(v)))
        self._add_entry(self, "Кут (°):", tool.angle,
                        lambda v: setattr(tool, "angle", float(v)))

    def _set_fitting_type(self, tool: FittingTool, value: str) -> None:
        tool.duct_type = value
        if tool.renderer._last_mouse_pos:
            tool.on_mouse_move(tool.renderer._last_mouse_pos)

    # ── WallTool ──
    def _build_wall_settings(self, tool: WallTool) -> None:
        ttk.Label(self, text="🧱 Стіна", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 3))
        self._add_entry(self, "Товщина:", tool.thickness,
                        lambda v: setattr(tool, "thickness", float(v)))
        self._add_entry(self, "Висота:", tool.height,
                        lambda v: setattr(tool, "height", float(v)))
        self._add_check(self, "Несуча", tool.is_load_bearing,
                        lambda v: setattr(tool, "is_load_bearing", v))

    # ── EquipmentTool ──
    def _build_equipment_settings(self, tool: EquipmentTool) -> None:
        ttk.Label(self, text="⚙️ Обладнання", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 3))
        self._add_combo(self, "Тип:",
                        ["вентилятор", "рекуператор", "калорифер", "фільтр", "глушник", "ПВУ"],
                        tool.equipment_type,
                        lambda v: setattr(tool, "equipment_type", v))
        self._add_entry(self, "Ширина:", tool.width,
                        lambda v: setattr(tool, "width", float(v)))
        self._add_entry(self, "Висота:", tool.height,
                        lambda v: setattr(tool, "height", float(v)))
