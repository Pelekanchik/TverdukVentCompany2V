"""Окреме вікно редактора креслень на весь екран.

Функціонал:
 • Креслення: сегмент, полілінія, стіна, обладнання, отвір
 • Snap: до об'єктів + до сітки
 • Grid: редагуюча сітка з кроком
 • Erase: стирання елементів ЛКМ
 • Кольори систем: приплив/витяжка/димова
 • Масштаб колесиком + друк PDF
"""

import os
import tempfile
import math
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional, Callable

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, Polygon
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe
import numpy as np

from ventilation_company.project3d.project_model import VentProject
from ventilation_company.project3d.vent_system import Point3D, DuctShape, DuctType, DuctSegment
from ventilation_company.project3d.arch_context import Wall, WallMaterial, Opening, Floor
from ventilation_company.project3d.dialogs import AddSegmentDialog, AddWallDialog, AddEquipmentDialog


class DrawingEditorWindow(tk.Toplevel):
    """Окреме вікно редактора креслень на весь екран."""

    COLORS = {
        "wall": "#555555",
        "wall_partition": "#888888",
        "opening": "#ff4444",
        "duct_supply": "#0066cc",
        "duct_exhaust": "#009900",
        "duct_smoke": "#cc6600",
        "fitting": "#990099",
        "equipment": "#cc9900",
        "grid": "#e0e0e0",
        "grid_bold": "#c0c0c0",
        "text": "#333333",
        "bg": "#fafafa",
        "draw_preview": "#ff6600",
        "draw_snap": "#00aa00",
        "snap_marker": "#00cc00",
        "erase_highlight": "#ff0000",
    }

    SNAP_RADIUS_MM = 400
    ERASE_RADIUS_MM = 300

    EQUIPMENT_TYPES = {
        "Вентилятор": {"w": 600, "h": 600, "l": 800, "color": "#cc4400"},
        "Клапан": {"w": 400, "h": 200, "l": 300, "color": "#8844cc"},
        "Фільтр": {"w": 500, "h": 500, "l": 400, "color": "#44aa44"},
        "Шумопоглинач": {"w": 500, "h": 500, "l": 1000, "color": "#aa8844"},
        "Решітка": {"w": 300, "h": 300, "l": 50, "color": "#4488aa"},
        "Дифузор": {"w": 200, "h": 200, "l": 100, "color": "#aa4488"},
        "Калорифер": {"w": 700, "h": 600, "l": 500, "color": "#cc6666"},
        "Рекуператор": {"w": 800, "h": 800, "l": 600, "color": "#66aaaa"},
    }

    OPENING_TYPES = ["Двері", "Вікно", "Отвір для повітропроводу", "Отвір загальний"]

    def __init__(self, parent, project: VentProject, on_close_callback: Optional[Callable] = None):
        super().__init__(parent)
        self.title("✏️ Редактор креслень — VentCompany")
        self.geometry("1600x1000")
        try:
            self.state("zoomed")
        except tk.TclError:
            self.attributes("-fullscreen", True)

        self.project = project
        self.on_close_callback = on_close_callback
        self.current_floor: Optional[str] = None
        self._zoom_level = 1.0
        self._modified = False

        # Режим креслення
        self._draw_mode: Optional[str] = None
        self._draw_start: Optional[Point3D] = None
        self._draw_temp_line = None
        self._draw_color = self.COLORS["draw_preview"]
        self._pending_trunk_id: Optional[str] = None

        # Полілінія
        self._polyline_points = []
        self._polyline_lines = []

        # Snap
        self._snap_marker = None
        self._snap_point: Optional[Point3D] = None
        self._snap_active = False

        # Grid
        self._grid_enabled = True
        self._grid_snap_enabled = True
        self._grid_step = 500  # мм
        self._grid_lines = []

        # Erase highlight
        self._erase_highlight = None

        self._build_ui()
        self._connect_mouse_events()
        self._connect_scroll_event()
        self._connect_keyboard_events()
        self._set_floor_options()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ═══════════════════════════════════════════════════════════════════
    # UI
    # ═══════════════════════════════════════════════════════════════════

    def _build_ui(self):
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True)

        # Toolbar
        toolbar = ttk.Frame(main, padding=5)
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="✏️ Редактор креслень", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Label(toolbar, text="Поверх:").pack(side=tk.LEFT)
        self.floor_var = tk.StringVar()
        self.floor_combo = ttk.Combobox(toolbar, textvariable=self.floor_var, state="readonly", width=16)
        self.floor_combo.pack(side=tk.LEFT, padx=2)
        self.floor_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Видимість
        self.wall_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Стіни", variable=self.wall_var, command=self.refresh).pack(side=tk.LEFT, padx=2)
        self.duct_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Повітропроводи", variable=self.duct_var, command=self.refresh).pack(side=tk.LEFT, padx=2)
        self.eq_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Обладнання", variable=self.eq_var, command=self.refresh).pack(side=tk.LEFT, padx=2)
        self.dim_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Розміри", variable=self.dim_var, command=self.refresh).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Креслення
        ttk.Button(toolbar, text="➡️ Сегмент", command=self._start_draw_segment).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📐 Полілінія", command=self._start_draw_polyline).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🧱 Стіна", command=self._start_draw_wall).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="⚙️ Обладнання", command=self._start_draw_equipment).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🚪 Отвір", command=self._start_draw_opening).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑️ Стирати", command=self._start_erase).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="✅ Завершити", command=self._finish_polyline).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="⛔ Скасувати", command=self._cancel_draw).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Grid
        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="⊞ Сітка", variable=self.grid_var, command=self.refresh).pack(side=tk.LEFT, padx=2)
        self.grid_snap_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="⊞ Прив'язка", variable=self.grid_snap_var, command=self.refresh).pack(side=tk.LEFT, padx=2)
        ttk.Label(toolbar, text="Крок:").pack(side=tk.LEFT)
        self.grid_step_var = tk.IntVar(value=500)
        step_combo = ttk.Combobox(toolbar, textvariable=self.grid_step_var, values=[100, 500, 1000, 2000], width=6, state="readonly")
        step_combo.pack(side=tk.LEFT, padx=2)
        step_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Навігація + друк
        ttk.Button(toolbar, text="🔍 +", command=self._zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔍 -", command=self._zoom_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄 Центрувати", command=self._center_view).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🏛️ +Поверх", command=self._add_floor_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🖨️ Друк", command=self._print).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(toolbar, text="💾 Закрити редактор", command=self._on_close).pack(side=tk.RIGHT, padx=5)

        # Status
        self.status_label = ttk.Label(main, text="Готово", foreground="#0066cc", font=("Arial", 10, "bold"))
        self.status_label.pack(fill=tk.X, padx=5, pady=2)

        # Canvas
        self.figure = Figure(figsize=(16, 10), dpi=100, facecolor=self.COLORS["bg"])
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor(self.COLORS["bg"])

        self.canvas = FigureCanvasTkAgg(self.figure, master=main)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.toolbar = NavigationToolbar2Tk(self.canvas, main)
        self.toolbar.update()

        hint = ttk.Label(main,
                         text="💡 Колесо — масштаб | ЛКМ — креслення/стирання | Прив'язка — автоматична (об'єкти + сітка) | Enter — завершити полілінію | Esc — скасувати",
                         foreground="#666", font=("Arial", 8))
        hint.pack(anchor=tk.W, padx=5)

    def _set_floor_options(self):
        floors = []
        if self.project and self.project.arch_context:
            for f in self.project.arch_context.floors:
                floors.append(f.name)
        if not floors:
            floors = ["Поверх 1"]
        self.floor_combo["values"] = floors
        self.floor_var.set(floors[0])
        self.refresh()

    # ═══════════════════════════════════════════════════════════════════
    # EVENTS
    # ═══════════════════════════════════════════════════════════════════

    def _connect_mouse_events(self):
        self.canvas.mpl_connect("button_press_event", self._on_mpl_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_mpl_move)
        self.canvas.mpl_connect("button_release_event", self._on_mpl_release)

    def _connect_scroll_event(self):
        self.canvas.mpl_connect("scroll_event", self._on_scroll)

    def _connect_keyboard_events(self):
        self.canvas.get_tk_widget().bind("<KeyPress-Return>", lambda e: self._finish_polyline())
        self.canvas.get_tk_widget().bind("<KeyPress-Escape>", lambda e: self._cancel_draw())
        self.canvas.get_tk_widget().bind("<KeyPress-KP_Enter>", lambda e: self._finish_polyline())
        self.canvas.get_tk_widget().focus_set()

    def _on_scroll(self, event):
        if event.inaxes != self.ax:
            return
        scale = 0.85 if event.button == "up" else 1.15
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        xdata, ydata = event.xdata, event.ydata
        if xdata is None or ydata is None:
            return
        new_xlim = (xdata - (xdata - xlim[0]) * scale, xdata + (xlim[1] - xdata) * scale)
        new_ylim = (ydata - (ydata - ylim[0]) * scale, ydata + (ylim[1] - ydata) * scale)
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.canvas.draw_idle()

    # ═══════════════════════════════════════════════════════════════════
    # GRID & SNAP
    # ═══════════════════════════════════════════════════════════════════

    def _snap_to_grid(self, x: float, y: float) -> tuple[float, float]:
        """Прив'язати точку до сітки."""
        if not self._grid_snap_enabled or not self.grid_snap_var.get():
            return x, y
        step = self.grid_step_var.get()
        return round(x / step) * step, round(y / step) * step

    def _draw_grid(self):
        """Намалювати сітку на плані."""
        if not self.grid_var.get():
            return
        step = self.grid_step_var.get()
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        x_min = math.floor(xlim[0] / step) * step
        x_max = math.ceil(xlim[1] / step) * step
        y_min = math.floor(ylim[0] / step) * step
        y_max = math.ceil(ylim[1] / step) * step

        # Основні лінії (кожна 5-а жирніша)
        for x in np.arange(x_min, x_max + step, step):
            is_bold = abs(x % (step * 5)) < 0.1
            self.ax.axvline(x, color=self.COLORS["grid_bold"] if is_bold else self.COLORS["grid"],
                            linewidth=0.8 if is_bold else 0.3, linestyle="-", alpha=0.6)
        for y in np.arange(y_min, y_max + step, step):
            is_bold = abs(y % (step * 5)) < 0.1
            self.ax.axhline(y, color=self.COLORS["grid_bold"] if is_bold else self.COLORS["grid"],
                            linewidth=0.8 if is_bold else 0.3, linestyle="-", alpha=0.6)

    # ═══════════════════════════════════════════════════════════════════
    # OBJECT SNAP
    # ═══════════════════════════════════════════════════════════════════

    def _get_all_snap_points(self):
        points = []
        floor_name = self.floor_var.get()
        for system in self.project.ventilation_systems:
            for trunk in system.trunks:
                for seg in trunk.segments:
                    points.append((seg.start.x, seg.start.y))
                    points.append((seg.end.x, seg.end.y))
        for floor in self.project.arch_context.floors:
            if floor.name != floor_name:
                continue
            for wall in floor.walls:
                points.append((wall.start.x, wall.start.y))
                points.append((wall.end.x, wall.end.y))
            for opening in floor.openings:
                points.append((opening.position.x, opening.position.y))
        for system in self.project.ventilation_systems:
            for trunk in system.trunks:
                for eq in trunk.equipment:
                    points.append((eq.position.x, eq.position.y))
                for fit in trunk.fittings:
                    points.append((fit.position.x, fit.position.y))
        return points

    def _find_snap_point(self, x, y):
        snap_points = self._get_all_snap_points()
        if not snap_points:
            return None
        best_dist = float("inf")
        best_point = None
        for sx, sy in snap_points:
            dist = ((sx - x) ** 2 + (sy - y) ** 2) ** 0.5
            if dist < best_dist and dist < self.SNAP_RADIUS_MM:
                best_dist = dist
                best_point = (sx, sy)
        if best_point:
            return Point3D(best_point[0], best_point[1], self._get_floor_z())
        return None

    def _update_snap_visual(self, x, y):
        if self._snap_marker:
            try:
                self._snap_marker.remove()
            except Exception:
                pass
            self._snap_marker = None
        snap = self._find_snap_point(x, y)
        self._snap_point = snap
        self._snap_active = snap is not None
        if snap:
            self._snap_marker = Circle(
                (snap.x, snap.y), 120,
                facecolor=self.COLORS["snap_marker"],
                edgecolor="white", linewidth=2, alpha=0.6, zorder=1000,
            )
            self.ax.add_patch(self._snap_marker)
            self.canvas.draw_idle()

    def _get_cursor_point(self, event):
        if event.xdata is None or event.ydata is None:
            return None
        x, y = event.xdata, event.ydata
        z = self._get_floor_z()
        # Спочатку snap до об'єктів
        snap = self._find_snap_point(x, y)
        if snap:
            return snap
        # Потім snap до сітки
        gx, gy = self._snap_to_grid(x, y)
        return Point3D(gx, gy, z)

    # ═══════════════════════════════════════════════════════════════════
    # MOUSE HANDLERS
    # ═══════════════════════════════════════════════════════════════════

    def _on_mpl_press(self, event):
        if not self._draw_mode:
            return
        if event.inaxes != self.ax:
            return
        if event.button != 1:
            return
        point = self._get_cursor_point(event)
        if point is None:
            return

        if self._draw_mode == "erase":
            self._do_erase(point.x, point.y)
            return
        if self._draw_mode == "opening":
            self._do_opening_click(point.x, point.y)
            return
        if self._draw_mode == "equipment":
            self._do_equipment_click(point)
            return
        if self._draw_mode == "polyline":
            self._handle_polyline_click(point)
        elif self._draw_mode in ("segment", "wall"):
            self._draw_start = point
            if self._draw_temp_line:
                try:
                    self._draw_temp_line.remove()
                except Exception:
                    pass
            self._draw_temp_line, = self.ax.plot(
                [point.x, point.x], [point.y, point.y],
                color=self._draw_color, linewidth=2.5, linestyle="--",
                marker="o", markersize=6, markerfacecolor=self.COLORS["draw_snap"], zorder=999,
            )
            self.canvas.draw_idle()

    def _on_mpl_move(self, event):
        if event.inaxes != self.ax:
            return
        if event.xdata is None or event.ydata is None:
            return
        x, y = event.xdata, event.ydata

        if self._draw_mode == "erase":
            self._update_erase_highlight(x, y)
            return

        if self._draw_mode:
            self._update_snap_visual(x, y)

        if self._draw_mode in ("segmen