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
from tkinter import ttk, messagebox, simpledialog, filedialog
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

        # Підкладка (DXF/DWG background)
        self._bg_lines_cache: List[tuple] = []  # (x1, y1, x2, y2, color, linewidth)
        self._bg_has_dxf = False

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

        # Toolbar — 2 рядки для адаптації під маленькі екрани
        toolbar_wrap = ttk.Frame(main, padding=5)
        toolbar_wrap.pack(fill=tk.X)

        # ── Рядок 1: назва, поверх, видимість, закрити ──
        tbar1 = ttk.Frame(toolbar_wrap)
        tbar1.pack(fill=tk.X)

        ttk.Label(tbar1, text="✏️ Редактор креслень", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        ttk.Separator(tbar1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Label(tbar1, text="Поверх:").pack(side=tk.LEFT)
        self.floor_var = tk.StringVar()
        self.floor_combo = ttk.Combobox(tbar1, textvariable=self.floor_var, state="readonly", width=14)
        self.floor_combo.pack(side=tk.LEFT, padx=2)
        self.floor_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Separator(tbar1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # Видимість
        self.wall_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tbar1, text="Стіни", variable=self.wall_var, command=self.refresh).pack(side=tk.LEFT, padx=2)
        self.duct_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tbar1, text="Повітропроводи", variable=self.duct_var, command=self.refresh).pack(side=tk.LEFT, padx=2)
        self.eq_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tbar1, text="Обладнання", variable=self.eq_var, command=self.refresh).pack(side=tk.LEFT, padx=2)
        self.dim_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tbar1, text="Розміри", variable=self.dim_var, command=self.refresh).pack(side=tk.LEFT, padx=2)

        ttk.Button(tbar1, text="💾 Закрити редактор", command=self._on_close).pack(side=tk.RIGHT, padx=5)

        # ── Рядок 2: креслення, grid, навігація, підкладка, друк ──
        tbar2 = ttk.Frame(toolbar_wrap)
        tbar2.pack(fill=tk.X, pady=(3, 0))

        # Меню "Креслення" — економить місце
        draw_menu_btn = ttk.Menubutton(tbar2, text="✏️ Креслення", direction="below")
        draw_menu_btn.pack(side=tk.LEFT, padx=2)
        draw_menu = tk.Menu(draw_menu_btn, tearoff=0)
        draw_menu.add_command(label="➡️ Сегмент", command=self._start_draw_segment)
        draw_menu.add_command(label="📐 Полілінія", command=self._start_draw_polyline)
        draw_menu.add_command(label="🧱 Стіна", command=self._start_draw_wall)
        draw_menu.add_command(label="⚙️ Обладнання", command=self._start_draw_equipment)
        draw_menu.add_command(label="🚪 Отвір", command=self._start_draw_opening)
        draw_menu.add_separator()
        draw_menu.add_command(label="🗑️ Стирати", command=self._start_erase)
        draw_menu.add_separator()
        draw_menu.add_command(label="✅ Завершити полілінію", command=self._finish_polyline)
        draw_menu.add_command(label="⛔ Скасувати", command=self._cancel_draw)
        draw_menu_btn["menu"] = draw_menu

        ttk.Separator(tbar2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # Grid
        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tbar2, text="⊞ Сітка", variable=self.grid_var, command=self.refresh).pack(side=tk.LEFT, padx=2)
        self.grid_snap_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tbar2, text="⊞ Прив'язка", variable=self.grid_snap_var, command=self.refresh).pack(side=tk.LEFT, padx=2)
        ttk.Label(tbar2, text="Крок:").pack(side=tk.LEFT)
        self.grid_step_var = tk.IntVar(value=500)
        step_combo = ttk.Combobox(tbar2, textvariable=self.grid_step_var, values=[100, 500, 1000, 2000], width=5, state="readonly")
        step_combo.pack(side=tk.LEFT, padx=2)
        step_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Separator(tbar2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # Навігація
        ttk.Button(tbar2, text="🔍 +", command=self._zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Button(tbar2, text="🔍 -", command=self._zoom_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(tbar2, text="🔄 Центр", command=self._center_view).pack(side=tk.LEFT, padx=2)
        ttk.Button(tbar2, text="🏛️ +Поверх", command=self._add_floor_dialog).pack(side=tk.LEFT, padx=2)

        ttk.Separator(tbar2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # Підкладка
        bg_menu_btn = ttk.Menubutton(tbar2, text="📥 Підкладка", direction="below")
        bg_menu_btn.pack(side=tk.LEFT, padx=2)
        bg_menu = tk.Menu(bg_menu_btn, tearoff=0)
        bg_menu.add_command(label="📥 Завантажити DXF", command=self._load_background_dxf)
        bg_menu.add_command(label="⚙️ Налаштувати", command=self._adjust_background_dialog)
        bg_menu.add_command(label="🗑️ Видалити", command=self._remove_background)
        bg_menu_btn["menu"] = bg_menu

        ttk.Separator(tbar2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Button(tbar2, text="🖨️ Друк", command=self._print).pack(side=tk.LEFT, padx=2)

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

        if self._draw_mode in ("segment", "wall") and self._draw_start is not None:
            point = self._get_cursor_point(event)
            if point and self._draw_temp_line:
                self._draw_temp_line.set_data(
                    [self._draw_start.x, point.x], [self._draw_start.y, point.y],
                )
                dx = point.x - self._draw_start.x
                dy = point.y - self._draw_start.y
                length = (dx ** 2 + dy ** 2) ** 0.5
                snap_text = " [SNAP]" if self._snap_active else ""
                self.status_label.config(
                    text=f"✏️ {self._draw_mode.upper()}: L={length:.0f} мм{snap_text} | Відпустіть ЛКМ",
                    foreground="#0066cc",
                )
                self.canvas.draw_idle()
        elif self._draw_mode == "polyline" and self._polyline_points:
            point = self._get_cursor_point(event)
            if point and self._draw_temp_line:
                last = self._polyline_points[-1]
                self._draw_temp_line.set_data(
                    [last.x, point.x], [last.y, point.y],
                )
                dx = point.x - last.x
                dy = point.y - last.y
                length = (dx ** 2 + dy ** 2) ** 0.5
                snap_text = " [SNAP]" if self._snap_active else ""
                self.status_label.config(
                    text=f"📐 ПОЛІЛІНІЯ: точок={len(self._polyline_points)} | L={length:.0f} мм{snap_text} | ЛКМ — додати, Enter — завершити",
                    foreground="#0066cc",
                )
                self.canvas.draw_idle()
        elif self._draw_mode == "opening":
            wall = self._find_nearest_wall(x, y)
            if wall:
                self.status_label.config(
                    text=f"🚪 ОТВІР: найближча стіна — {wall.name} | ЛКМ — розмістити",
                    foreground="#0066cc",
                )
            else:
                self.status_label.config(
                    text="🚪 ОТВІР: клікніть ближче до стіни",
                    foreground="#cc6600",
                )

    def _on_mpl_release(self, event):
        if not self._draw_mode:
            return
        if event.inaxes != self.ax:
            self._cancel_draw()
            return
        if event.button != 1:
            return
        if self._draw_mode in ("erase", "opening", "equipment"):
            return  # Оброблено в press

        point = self._get_cursor_point(event)
        if point is None:
            self._cancel_draw()
            return
        end = point
        start = self._draw_start
        if self._draw_temp_line:
            try:
                self._draw_temp_line.remove()
            except Exception:
                pass
            self._draw_temp_line = None
        mode = self._draw_mode
        if mode == "segment":
            self._draw_start = None
            self._on_draw_segment_done(start, end)
        elif mode == "wall":
            self._draw_start = None
            self._on_draw_wall_done(start, end)

    # ═══════════════════════════════════════════════════════════════════
    # ERASE
    # ═══════════════════════════════════════════════════════════════════

    def _start_erase(self):
        self._cancel_draw()
        self._draw_mode = "erase"
        self.status_label.config(
            text="🗑️ РЕЖИМ: Стирати → наведіть на елемент і клікніть ЛКМ",
            foreground="#cc0000",
        )
        self.canvas.get_tk_widget().config(cursor="X_cursor")
        self.canvas.get_tk_widget().focus_set()

    def _update_erase_highlight(self, x, y):
        """Підсвітити елемент, який буде видалено."""
        if self._erase_highlight:
            try:
                self._erase_highlight.remove()
            except Exception:
                pass
            self._erase_highlight = None

        elem = self._find_nearest_element(x, y)
        if elem:
            ex, ey, er = elem["x"], elem["y"], 200
            self._erase_highlight = Circle(
                (ex, ey), er,
                facecolor="none", edgecolor=self.COLORS["erase_highlight"],
                linewidth=3, linestyle="--", zorder=1001,
            )
            self.ax.add_patch(self._erase_highlight)
            self.canvas.draw_idle()

    def _find_nearest_element(self, x, y):
        """Знайти найближчий елемент для стирання."""
        floor_name = self.floor_var.get()
        floor = None
        for f in self.project.arch_context.floors:
            if f.name == floor_name:
                floor = f
                break
        best = None
        best_dist = float("inf")

        # Сегменти
        for system in self.project.ventilation_systems:
            for trunk in system.trunks:
                for seg in trunk.segments:
                    cx = (seg.start.x + seg.end.x) / 2
                    cy = (seg.start.y + seg.end.y) / 2
                    dist = ((cx - x) ** 2 + (cy - y) ** 2) ** 0.5
                    if dist < best_dist and dist < self.ERASE_RADIUS_MM:
                        best_dist = dist
                        best = {"type": "segment", "id": seg.id, "x": cx, "y": cy, "parent": trunk}

        # Стіни
        if floor:
            for wall in floor.walls:
                cx = (wall.start.x + wall.end.x) / 2
                cy = (wall.start.y + wall.end.y) / 2
                dist = ((cx - x) ** 2 + (cy - y) ** 2) ** 0.5
                if dist < best_dist and dist < self.ERASE_RADIUS_MM:
                    best_dist = dist
                    best = {"type": "wall", "id": wall.id, "x": cx, "y": cy, "parent": floor}

            # Отвори
            for op in floor.openings:
                dist = ((op.position.x - x) ** 2 + (op.position.y - y) ** 2) ** 0.5
                if dist < best_dist and dist < self.ERASE_RADIUS_MM:
                    best_dist = dist
                    best = {"type": "opening", "id": op.id, "x": op.position.x, "y": op.position.y, "parent": floor}

        # Обладнання
        for system in self.project.ventilation_systems:
            for trunk in system.trunks:
                for eq in trunk.equipment:
                    dist = ((eq.position.x - x) ** 2 + (eq.position.y - y) ** 2) ** 0.5
                    if dist < best_dist and dist < self.ERASE_RADIUS_MM:
                        best_dist = dist
                        best = {"type": "equipment", "id": eq.id, "x": eq.position.x, "y": eq.position.y, "parent": trunk}

                # Фітінги
                for fit in trunk.fittings:
                    dist = ((fit.position.x - x) ** 2 + (fit.position.y - y) ** 2) ** 0.5
                    if dist < best_dist and dist < self.ERASE_RADIUS_MM:
                        best_dist = dist
                        best = {"type": "fitting", "id": fit.id, "x": fit.position.x, "y": fit.position.y, "parent": trunk}

        return best

    def _do_erase(self, x, y):
        elem = self._find_nearest_element(x, y)
        if not elem:
            self.status_label.config(text="🗑️ Немає елемента поблизу для видалення", foreground="#cc0000")
            return

        etype = elem["type"]
        eid = elem["id"]

        if etype == "segment":
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    for i, seg in enumerate(t.segments):
                        if seg.id == eid:
                            t.segments.pop(i)
                            break
        elif etype == "wall":
            for fl in self.project.arch_context.floors:
                for i, w in enumerate(fl.walls):
                    if w.id == eid:
                        fl.walls.pop(i)
                        break
        elif etype == "opening":
            for fl in self.project.arch_context.floors:
                for i, o in enumerate(fl.openings):
                    if o.id == eid:
                        fl.openings.pop(i)
                        break
        elif etype == "equipment":
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    for i, eq in enumerate(t.equipment):
                        if eq.id == eid:
                            t.equipment.pop(i)
                            break
        elif etype == "fitting":
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    for i, fit in enumerate(t.fittings):
                        if fit.id == eid:
                            t.fittings.pop(i)
                            break

        self._modified = True
        self.status_label.config(text=f"🗑️ Видалено: {etype} {eid}", foreground="#cc0000")
        self.refresh()

    # ═══════════════════════════════════════════════════════════════════
    # POLYLINE
    # ═══════════════════════════════════════════════════════════════════

    def _handle_polyline_click(self, point):
        if not self._polyline_points:
            self._polyline_points.append(point)
            self.status_label.config(
                text="📐 ПОЛІЛІНІЯ: перша точка. ЛКМ — наступна, Enter — завершити",
                foreground="#0066cc",
            )
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
        else:
            last = self._polyline_points[-1]
            line, = self.ax.plot(
                [last.x, point.x], [last.y, point.y],
                color=self._draw_color, linewidth=2.5, solid_capstyle="round", zorder=998,
            )
            self._polyline_lines.append(line)
            self._polyline_points.append(point)
            self.status_label.config(
                text=f"📐 ПОЛІЛІНІЯ: точок={len(self._polyline_points)} | ЛКМ — додати, Enter — завершити",
                foreground="#0066cc",
            )
            self.canvas.draw_idle()

    def _finish_polyline(self):
        if self._draw_mode != "polyline" or len(self._polyline_points) < 2:
            if self._draw_mode == "polyline" and len(self._polyline_points) < 2:
                messagebox.showinfo("Полілінія", "Потрібно мінімум 2 точки.")
                self._cancel_draw()
            return
        pid = getattr(self, "_pending_trunk_id", None)
        if not pid:
            self._cancel_draw()
            return
        p1 = self._polyline_points[0]
        p2 = self._polyline_points[1]
        data = AddSegmentDialog(self, default_start=p1, default_end=p2).show()
        if data:
            for i in range(len(self._polyline_points) - 1):
                start = self._polyline_points[i]
                end = self._polyline_points[i + 1]
                length = ((end.x - start.x) ** 2 + (end.y - start.y) ** 2) ** 0.5
                seg = DuctSegment(
                    id=f"{data['id']}_seg{i+1}" if i > 0 else data["id"],
                    start=start, end=end,
                    width=data["width"], height=data["height"], length=length,
                    shape=data["shape"], duct_type=data["duct_type"],
                    material=data["material"], thickness=data["thickness"],
                    insulation=data["insulation"],
                    notes=f"{data.get('notes', '')} (полілінія)" if data.get("notes") else "Полілінія",
                )
                for s in self.project.ventilation_systems:
                    for t in s.trunks:
                        if t.id == pid:
                            t.segments.append(seg)
                            break
            self._modified = True
            self.status_label.config(
                text=f"✅ Полілінія: {len(self._polyline_points)} точок, {len(self._polyline_points)-1} сегментів",
                foreground="green",
            )
        self._cancel_draw()
        self.refresh()

    # ═══════════════════════════════════════════════════════════════════
    # DRAW MODE STARTERS
    # ═══════════════════════════════════════════════════════════════════

    def _start_draw_segment(self):
        self._start_draw_mode("segment", "Сегмент")

    def _start_draw_polyline(self):
        self._start_draw_mode("polyline", "Полілінія")

    def _start_draw_mode(self, mode, label):
        trunks = []
        for s in self.project.ventilation_systems:
            for t in s.trunks:
                trunks.append((t, s))
        if not trunks:
            messagebox.showwarning("Увага", "Спочатку додайте трасу.")
            return
        dialog = tk.Toplevel(self)
        dialog.title(f"Виберіть трасу для {label}")
        dialog.geometry("400x180")
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog, text="Трасса:").pack(pady=5)
        var = tk.StringVar()
        combo = ttk.Combobox(dialog, textvariable=var, state="readonly", width=45)
        display_list = []
        id_map = {}
        color_map = {}
        for t, system in trunks:
            d = f"{t.name} [{t.id}] — {system.name}"
            display_list.append(d)
            id_map[d] = t.id
            sys_type = system.system_type.lower()
            if "витяж" in sys_type or "exhaust" in sys_type:
                color_map[d] = self.COLORS["duct_exhaust"]
            elif "дим" in sys_type or "smoke" in sys_type:
                color_map[d] = self.COLORS["duct_smoke"]
            else:
                color_map[d] = self.COLORS["duct_supply"]
        combo["values"] = display_list
        if display_list:
            combo.set(display_list[0])
        combo.pack(padx=10, pady=5)
        result = [None]
        def on_ok():
            result[0] = id_map.get(combo.get())
            self._draw_color = color_map.get(combo.get(), self.COLORS["draw_preview"])
            dialog.destroy()
        def on_cancel():
            dialog.destroy()
        ttk.Button(dialog, text="OK", command=on_ok).pack(pady=5)
        ttk.Button(dialog, text="Скасувати", command=on_cancel).pack()
        self.wait_window(dialog)
        if result[0]:
            self._pending_trunk_id = result[0]
            self._draw_mode = mode
            self._draw_start = None
            self._polyline_points = []
            self._polyline_lines = []
            hint = "перша точка" if mode == "polyline" else "тягніть, відпустіть"
            self.status_label.config(
                text=f"✏️ РЕЖИМ: {label} → ЛКМ ({hint})",
                foreground="#0066cc",
            )
            self.canvas.get_tk_widget().config(cursor="crosshair")
            self.canvas.get_tk_widget().focus_set()

    def _start_draw_wall(self):
        self._draw_mode = "wall"
        self._draw_start = None
        self._draw_color = self.COLORS["wall"]
        self._polyline_points = []
        self._polyline_lines = []
        self.status_label.config(
            text="✏️ РЕЖИМ: Креслення стіни → ЛКМ, тягніть, відпустіть",
            foreground="#0066cc",
        )
        self.canvas.get_tk_widget().config(cursor="crosshair")
        self.canvas.get_tk_widget().focus_set()

    # ═══════════════════════════════════════════════════════════════════
    # EQUIPMENT DRAWING
    # ═══════════════════════════════════════════════════════════════════

    def _start_draw_equipment(self):
        """Вибрати тип обладнання і перейти в режим розміщення."""
        dialog = tk.Toplevel(self)
        dialog.title("Виберіть тип обладнання")
        dialog.geometry("350x250")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="Тип обладнання:").pack(pady=5)
        var = tk.StringVar()
        combo = ttk.Combobox(dialog, textvariable=var, state="readonly", width=30)
        combo["values"] = list(self.EQUIPMENT_TYPES.keys())
        combo.set("Вентилятор")
        combo.pack(padx=10, pady=5)

        ttk.Label(dialog, text="Трасса (система):").pack(pady=5)
        trunk_var = tk.StringVar()
        trunk_combo = ttk.Combobox(dialog, textvariable=trunk_var, state="readonly", width=30)
        trunks = []
        trunk_map = {}
        for s in self.project.ventilation_systems:
            for t in s.trunks:
                d = f"{t.name} [{t.id}]"
                trunks.append(d)
                trunk_map[d] = t.id
        trunk_combo["values"] = trunks
        if trunks:
            trunk_combo.set(trunks[0])
        trunk_combo.pack(padx=10, pady=5)

        result = [None, None]
        def on_ok():
            result[0] = combo.get()
            result[1] = trunk_map.get(trunk_combo.get())
            dialog.destroy()
        def on_cancel():
            dialog.destroy()
        ttk.Button(dialog, text="OK", command=on_ok).pack(pady=5)
        ttk.Button(dialog, text="Скасувати", command=on_cancel).pack()

        self.wait_window(dialog)
        if result[0] and result[1]:
            self._pending_equipment_type = result[0]
            self._pending_trunk_id = result[1]
            self._draw_mode = "equipment"
            self.status_label.config(
                text=f"⚙️ РЕЖИМ: Розміщення {result[0]} → ЛКМ на плані",
                foreground="#0066cc",
            )
            self.canvas.get_tk_widget().config(cursor="crosshair")
            self.canvas.get_tk_widget().focus_set()

    def _do_equipment_click(self, point: Point3D):
        eq_type = getattr(self, "_pending_equipment_type", "Вентилятор")
        pid = getattr(self, "_pending_trunk_id", None)
        if not pid:
            return
        info = self.EQUIPMENT_TYPES.get(eq_type, self.EQUIPMENT_TYPES["Вентилятор"])
        eq = Equipment(
            id=f"EQ_{eq_type[:3].upper()}_{os.urandom(2).hex()}",
            name=eq_type,
            position=point,
            width=info["w"],
            height=info["h"],
            length=info["l"],
            air_flow=1000,
            pressure=100,
            power=0.5,
            notes=eq_type,
        )
        for s in self.project.ventilation_systems:
            for t in s.trunks:
                if t.id == pid:
                    t.equipment.append(eq)
                    self._modified = True
                    self.refresh()
                    self.status_label.config(
                        text=f"✅ Додано обладнання: {eq.name} на ({point.x:.0f}, {point.y:.0f})",
                        foreground="green",
                    )
                    return

    # ═══════════════════════════════════════════════════════════════════
    # OPENING (DOORS / WINDOWS)
    # ═══════════════════════════════════════════════════════════════════

    def _start_draw_opening(self):
        self._cancel_draw()
        self._draw_mode = "opening"
        self.status_label.config(
            text="🚪 РЕЖИМ: Отвір → клікніть на стіну",
            foreground="#0066cc",
        )
        self.canvas.get_tk_widget().config(cursor="crosshair")
        self.canvas.get_tk_widget().focus_set()

    def _find_nearest_wall(self, x, y):
        """Знайти найближчу стіну до точки (x, y)."""
        floor_name = self.floor_var.get()
        floor = None
        for f in self.project.arch_context.floors:
            if f.name == floor_name:
                floor = f
                break
        if not floor:
            return None
        best = None
        best_dist = float("inf")
        for wall in floor.walls:
            # Відстань від точки до відрізка стіни
            dist = self._point_to_segment_distance(x, y, wall.start.x, wall.start.y, wall.end.x, wall.end.y)
            if dist < best_dist and dist < 600:  # 600 мм допуск
                best_dist = dist
                best = wall
        return best

    def _point_to_segment_distance(self, px, py, x1, y1, x2, y2):
        """Відстань від точки до відрізка."""
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5

    def _do_opening_click(self, x, y):
        wall = self._find_nearest_wall(x, y)
        if not wall:
            messagebox.showwarning("Увага", "Клікніть ближче до стіни.")
            return

        # Розрахувати позицію на стіні (проекція точки на стіну)
        dx = wall.end.x - wall.start.x
        dy = wall.end.y - wall.start.y
        length = (dx ** 2 + dy ** 2) ** 0.5
        if length == 0:
            return
        t = max(0, min(1, ((x - wall.start.x) * dx + (y - wall.start.y) * dy) / (length ** 2)))
        proj_x = wall.start.x + t * dx
        proj_y = wall.start.y + t * dy
        offset = t * length

        # Діалог параметрів
        dialog = tk.Toplevel(self)
        dialog.title("Параметри отвору")
        dialog.geometry("350x320")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text=f"Стіна: {wall.name}").pack(pady=2)
        ttk.Label(dialog, text=f"Відступ від початку: {offset:.0f} мм").pack(pady=2)

        ttk.Label(dialog, text="Тип:").pack(pady=2)
        type_var = tk.StringVar(value="Отвір загальний")
        ttk.Combobox(dialog, textvariable=type_var, values=self.OPENING_TYPES, state="readonly", width=25).pack()

        ttk.Label(dialog, text="Ширина (мм):").pack(pady=2)
        w_var = tk.DoubleVar(value=800)
        ttk.Spinbox(dialog, from_=100, to=5000, textvariable=w_var, width=15).pack()

        ttk.Label(dialog, text="Висота (мм):").pack(pady=2)
        h_var = tk.DoubleVar(value=2000)
        ttk.Spinbox(dialog, from_=100, to=5000, textvariable=h_var, width=15).pack()

        ttk.Label(dialog, text="Відступ від початку стіни (мм):").pack(pady=2)
        off_var = tk.DoubleVar(value=offset)
        ttk.Spinbox(dialog, from_=0, to=length, textvariable=off_var, width=15).pack()

        result = [None]
        def on_ok():
            result[0] = {
                "type": type_var.get(),
                "width": w_var.get(),
                "height": h_var.get(),
                "offset": off_var.get(),
            }
            dialog.destroy()
        def on_cancel():
            dialog.destroy()
        ttk.Button(dialog, text="OK", command=on_ok).pack(pady=5)
        ttk.Button(dialog, text="Скасувати", command=on_cancel).pack()

        self.wait_window(dialog)
        if result[0]:
            data = result[0]
            t = max(0, min(1, data["offset"] / length))
            pos_x = wall.start.x + t * dx
            pos_y = wall.start.y + t * dy
            pos_z = wall.start.z + data["height"] / 2

            opening = Opening(
                id=f"OP_{os.urandom(2).hex()}",
                name=data["type"],
                wall_id=wall.id,
                position=Point3D(pos_x, pos_y, pos_z),
                width=data["width"],
                height=data["height"],
                shape="прямокутний",
                notes=f"{data['type']}, відступ {data['offset']:.0f} мм",
            )
            for fl in self.project.arch_context.floors:
                if fl.name == self.floor_var.get():
                    fl.openings.append(opening)
                    wall.has_opening = True
                    self._modified = True
                    self.refresh()
                    self.status_label.config(
                        text=f"✅ Додано {data['type']}: {data['width']:.0f}×{data['height']:.0f} мм",
                        foreground="green",
                    )
                    break
        self._cancel_draw()

    # ═══════════════════════════════════════════════════════════════════
    # ADD FLOOR
    # ═══════════════════════════════════════════════════════════════════

    def _add_floor_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Додати поверх")
        dialog.geometry("300x200")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="Назва:").pack(pady=2)
        name_var = tk.StringVar(value=f"Поверх {len(self.project.arch_context.floors) + 1}")
        ttk.Entry(dialog, textvariable=name_var, width=25).pack()

        ttk.Label(dialog, text="Рівень (мм):").pack(pady=2)
        level = 0
        if self.project.arch_context.floors:
            level = max(f.level for f in self.project.arch_context.floors) + 3000
        level_var = tk.DoubleVar(value=level)
        ttk.Spinbox(dialog, from_=0, to=99999, textvariable=level_var, width=15).pack()

        ttk.Label(dialog, text="Висота (мм):").pack(pady=2)
        height_var = tk.DoubleVar(value=3000)
        ttk.Spinbox(dialog, from_=1000, to=10000, textvariable=height_var, width=15).pack()

        result = [None]
        def on_ok():
            result[0] = {
                "name": name_var.get(),
                "level": level_var.get(),
                "height": height_var.get(),
            }
            dialog.destroy()
        def on_cancel():
            dialog.destroy()
        ttk.Button(dialog, text="OK", command=on_ok).pack(pady=5)
        ttk.Button(dialog, text="Скасувати", command=on_cancel).pack()

        self.wait_window(dialog)
        if result[0]:
            data = result[0]
            floor = Floor(name=data["name"], level=data["level"], height=data["height"])
            self.project.arch_context.floors.append(floor)
            self._modified = True
            self._set_floor_options()
            self.status_label.config(
                text=f"✅ Додано поверх: {floor.name}",
                foreground="green",
            )

    # ═══════════════════════════════════════════════════════════════════
    # DONE CALLBACKS (segment, wall)
    # ═══════════════════════════════════════════════════════════════════

    def _on_draw_segment_done(self, start, end):
        pid = getattr(self, "_pending_trunk_id", None)
        if not pid:
            return
        data = AddSegmentDialog(self, default_start=start, default_end=end).show()
        if data:
            seg = DuctSegment(
                id=data["id"], start=data["start"], end=data["end"],
                width=data["width"], height=data["height"], length=data["length"],
                shape=data["shape"], duct_type=data["duct_type"],
                material=data["material"], thickness=data["thickness"],
                insulation=data["insulation"], notes=data["notes"],
            )
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    if t.id == pid:
                        t.segments.append(seg)
                        self._modified = True
                        self.refresh()
                        self.status_label.config(
                            text=f"✅ Додано сегмент: {seg.id} L={seg.length:.0f} мм",
                            foreground="green",
                        )
                        return

    def _on_draw_wall_done(self, start, end):
        floor = None
        floor_name = self.floor_var.get()
        for fl in self.project.arch_context.floors:
            if fl.name == floor_name:
                floor = fl
                break
        if not floor and self.project.arch_context.floors:
            floor = self.project.arch_context.floors[0]
        if not floor:
            messagebox.showwarning("Увага", "Не знайдено поверх для стіни.")
            return
        data = AddWallDialog(self, default_start=start, default_end=end).show()
        if data:
            wall = Wall(
                id=data["id"], name=data["name"],
                start=data["start"], end=data["end"],
                height=data["height"], thickness=data["thickness"],
                material=data["material"], is_load_bearing=data["is_load_bearing"],
                notes=data["notes"],
            )
            floor.walls.append(wall)
            self._modified = True
            self.refresh()
            self.status_label.config(
                text=f"✅ Додано стіну: {wall.name} L={wall.length:.0f} мм",
                foreground="green",
            )

    def _get_floor_z(self):
        floor_name = self.floor_var.get()
        if self.project and self.project.arch_context:
            for f in self.project.arch_context.floors:
                if f.name == floor_name:
                    return f.level
        return 2500.0

    def _cancel_draw(self):
        self._draw_mode = None
        self._draw_start = None
        self._pending_trunk_id = None
        self._draw_color = self.COLORS["draw_preview"]
        if self._draw_temp_line:
            try:
                self._draw_temp_line.remove()
            except Exception:
                pass
            self._draw_temp_line = None
        for line in self._polyline_lines:
            try:
                line.remove()
            except Exception:
                pass
        self._polyline_lines = []
        self._polyline_points = []
        if self._snap_marker:
            try:
                self._snap_marker.remove()
            except Exception:
                pass
            self._snap_marker = None
        if self._erase_highlight:
            try:
                self._erase_highlight.remove()
            except Exception:
                pass
            self._erase_highlight = None
        self._snap_point = None
        self._snap_active = False
        self.status_label.config(text="Готово", foreground="#0066cc")
        self.canvas.get_tk_widget().config(cursor="")
        self.canvas.draw_idle()

    def _zoom_in(self):
        self._zoom_level *= 1.2
        self.refresh()

    def _zoom_out(self):
        self._zoom_level /= 1.2
        self.refresh()

    def _center_view(self):
        self._zoom_level = 1.0
        self.refresh()

    def _print(self):
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_path = tmp.name
            self.figure.savefig(tmp_path, dpi=300, bbox_inches="tight", facecolor=self.figure.get_facecolor())
            if os.name == "nt":
                os.startfile(tmp_path)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", tmp_path])
            messagebox.showinfo("Друк", "PDF підготовлено.\nФайл відкрито у переглядачі. Натисніть Ctrl+P для друку.")
        except Exception as e:
            messagebox.showerror("Помилка друку", str(e))

    def refresh(self):
        self.ax.clear()
        self.ax.set_facecolor(self.COLORS["bg"])
        if not self.project:
            self.ax.text(0.5, 0.5, "Немає проєкту", transform=self.ax.transAxes, fontsize=14, ha="center", color="#999")
            self.ax.set_xlim(0, 1)
            self.ax.set_ylim(0, 1)
            self.ax.set_aspect("equal")
            self.canvas.draw()
            return
        floor_name = self.floor_var.get()
        floor = None
        for f in self.project.arch_context.floors:
            if f.name == floor_name:
                floor = f
                break
        if not floor:
            self.ax.text(0.5, 0.5, f"Поверх '{floor_name}' не знайдено", transform=self.ax.transAxes, fontsize=14, ha="center", color="#999")
            self.ax.set_xlim(0, 1)
            self.ax.set_ylim(0, 1)
            self.canvas.draw()
            return

        all_x, all_y = [], []

        # Підкладка DXF/DWG (малюємо першою, під сіткою)
        self._draw_background()

        # Сітка (малюємо першою, щоб була на фоні)
        self._draw_grid()
        self.ax.grid(True, color=self.COLORS["grid"], linestyle="-", linewidth=0.5, alpha=0.5)
        self.ax.set_axisbelow(True)

        if self.wall_var.get():
            for wall in floor.walls:
                self._draw_wall_2d(wall)
                all_x.extend([wall.start.x, wall.end.x])
                all_y.extend([wall.start.y, wall.end.y])

        if self.duct_var.get():
            for system in self.project.ventilation_systems:
                sys_type = system.system_type.lower()
                if "витяж" in sys_type or "exhaust" in sys_type:
                    color = self.COLORS["duct_exhaust"]
                elif "дим" in sys_type or "smoke" in sys_type:
                    color = self.COLORS["duct_smoke"]
                else:
                    color = self.COLORS["duct_supply"]
                for trunk in system.trunks:
                    trunk_floor = str(trunk.floor) if hasattr(trunk, "floor") else ""
                    if trunk_floor not in floor_name and trunk.name != floor_name:
                        z_min = min(s.start.z for s in trunk.segments) if trunk.segments else 0
                        z_max = max(s.end.z for s in trunk.segments) if trunk.segments else 0
                        floor_z = floor.floor_z
                        level = floor.level
                        if not (floor_z <= z_min <= level or floor_z <= z_max <= level):
                            continue
                    for seg in trunk.segments:
                        self._draw_duct_segment_2d(seg, color, self.dim_var.get())
                        all_x.extend([seg.start.x, seg.end.x])
                        all_y.extend([seg.start.y, seg.end.y])
                    for fitting in trunk.fittings:
                        self._draw_fitting_2d(fitting)
                        all_x.append(fitting.position.x)
                        all_y.append(fitting.position.y)

        if self.eq_var.get():
            for system in self.project.ventilation_systems:
                for trunk in system.trunks:
                    for eq in trunk.equipment:
                        self._draw_equipment_2d(eq)
                        all_x.extend([eq.position.x - eq.width/2, eq.position.x + eq.width/2])
                        all_y.extend([eq.position.y - eq.height/2, eq.position.y + eq.height/2])

        # Отвори
        if floor:
            for op in floor.openings:
                self._draw_opening_2d(op)
                all_x.extend([op.position.x - op.width/2, op.position.x + op.width/2])
                all_y.extend([op.position.y - op.height/2, op.position.y + op.height/2])

        if all_x and all_y:
            margin = max(max(all_x) - min(all_x), max(all_y) - min(all_y)) * 0.1 + 500
            margin = margin / self._zoom_level
            xlim = (min(all_x) - margin, max(all_x) + margin)
            ylim = (min(all_y) - margin, max(all_y) + margin)
        else:
            xlim, ylim = (-5000, 15000), (-5000, 15000)
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.ax.set_aspect("equal")
        self.ax.set_xlabel("X, мм")
        self.ax.set_ylabel("Y, мм")
        self.ax.set_title(f"{self.project.name} — План: {floor_name}", fontsize=12)

        legend_elements = [
            Line2D([0], [0], color=self.COLORS["wall"], lw=4, label="Стіна"),
            Line2D([0], [0], color=self.COLORS["duct_supply"], lw=3, label="Приплив"),
            Line2D([0], [0], color=self.COLORS["duct_exhaust"], lw=3, label="Витяжка"),
            Line2D([0], [0], marker="s", color="w", markerfacecolor=self.COLORS["equipment"], markersize=10, label="Обладнання"),
            Line2D([0], [0], marker="s", color="w", markerfacecolor=self.COLORS["opening"], markersize=8, label="Отвір"),
        ]
        self.ax.legend(handles=legend_elements, loc="upper right", fontsize=8, framealpha=0.9)

        # Відновити snap marker
        if self._snap_active and self._snap_point:
            self._snap_marker = Circle(
                (self._snap_point.x, self._snap_point.y), 120,
                facecolor=self.COLORS["snap_marker"], edgecolor="white", linewidth=2, alpha=0.6, zorder=1000,
            )
            self.ax.add_patch(self._snap_marker)

        self.canvas.draw()

    def _draw_wall_2d(self, wall):
        dx = wall.end.x - wall.start.x
        dy = wall.end.y - wall.start.y
        length = math.sqrt(dx**2 + dy**2)
        if length == 0:
            return
        nx, ny = dx / length, dy / length
        perp_x, perp_y = -ny, nx
        hw = wall.thickness / 2
        x1 = wall.start.x + perp_x * hw
        y1 = wall.start.y + perp_y * hw
        x2 = wall.start.x - perp_x * hw
        y2 = wall.start.y - perp_y * hw
        x3 = wall.end.x - perp_x * hw
        y3 = wall.end.y - perp_y * hw
        x4 = wall.end.x + perp_x * hw
        y4 = wall.end.y + perp_y * hw
        color = self.COLORS["wall"] if wall.is_load_bearing else self.COLORS["wall_partition"]
        polygon = Polygon([(x1, y1), (x2, y2), (x3, y3), (x4, y4)],
                          closed=True, facecolor=color, edgecolor="black", linewidth=0.5, alpha=0.9)
        self.ax.add_patch(polygon)

    def _draw_duct_segment_2d(self, seg, color, show_dims):
        x1, y1 = seg.start.x, seg.start.y
        x2, y2 = seg.end.x, seg.end.y
        self.ax.plot([x1, x2], [y1, y2], color=color, linewidth=3, solid_capstyle="round")
        if seg.shape == DuctShape.RECT:
            w, h = seg.width, seg.height
            self._draw_rect_profile(x1, y1, w, h, color)
            self._draw_rect_profile(x2, y2, w, h, color)
        else:
            d = seg.width
            self._draw_circle_profile(x1, y1, d, color)
            self._draw_circle_profile(x2, y2, d, color)
        if show_dims and seg.length > 1000:
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            offset = max(seg.width, seg.height) / 2 + 150
            perp_angle = np.radians(angle + 90)
            ox = offset * np.cos(perp_angle)
            oy = offset * np.sin(perp_angle)
            label = f"{seg.width:.0f}×{seg.height:.0f} L={seg.length:.0f}"
            self.ax.annotate(label, xy=(cx, cy), xytext=(cx + ox, cy + oy), fontsize=7, color=color, fontweight="bold",
                             ha="center", va="center", bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8, edgecolor="none"),
                             arrowprops=dict(arrowstyle="->", color=color, lw=0.8))

    def _draw_rect_profile(self, x, y, w, h, color):
        rect = Rectangle((x - w/2, y - h/2), w, h, facecolor=color, edgecolor="black", linewidth=0.5, alpha=0.4)
        self.ax.add_patch(rect)

    def _draw_circle_profile(self, x, y, d, color):
        circle = Circle((x, y), d/2, facecolor=color, edgecolor="black", linewidth=0.5, alpha=0.4)
        self.ax.add_patch(circle)

    def _draw_fitting_2d(self, fitting):
        cx, cy = fitting.position.x, fitting.position.y
        size = max(fitting.width_in, fitting.height_in, 100) / 2
        diamond = Polygon([(cx, cy + size), (cx + size, cy), (cx, cy - size), (cx - size, cy)],
                          closed=True, facecolor=self.COLORS["fitting"], edgecolor="#660066", linewidth=1.5, alpha=0.7)
        self.ax.add_patch(diamond)
        self.ax.text(cx, cy, fitting.fitting_type[:3], fontsize=6, color="white", ha="center", va="center", fontweight="bold")

    def _draw_equipment_2d(self, eq):
        cx, cy = eq.position.x, eq.position.y
        w, h = eq.width, eq.height
        rect = FancyBboxPatch((cx - w/2, cy - h/2), w, h, boxstyle="round,pad=50",
                              facecolor=self.COLORS["equipment"], edgecolor="#996600", linewidth=2, alpha=0.8)
        self.ax.add_patch(rect)
        self.ax.text(cx, cy, eq.name, fontsize=7, color="white", ha="center", va="center", fontweight="bold",
                     path_effects=[pe.withStroke(linewidth=2, foreground="black")])

    def _draw_opening_2d(self, op):
        cx, cy = op.position.x, op.position.y
        w, h = op.width, op.height
        rect = Rectangle((cx - w/2, cy - h/2), w, h,
                         facecolor="none", edgecolor=self.COLORS["opening"],
                         linewidth=2, linestyle="--", alpha=0.9)
        self.ax.add_patch(rect)
        self.ax.text(cx, cy, op.name, fontsize=6, color=self.COLORS["opening"],
                     ha="center", va="center", fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7, edgecolor="none"))

    # ═══════════════════════════════════════════════════════════════════
    # ПІДКЛАДКА DXF/DWG
    # ═══════════════════════════════════════════════════════════════════

    def _load_background_dxf(self):
        """Завантажити DXF файл як підкладку для поточного поверху."""
        try:
            import ezdxf
        except ImportError:
            messagebox.showerror("Помилка", "Бібліотека ezdxf не встановлена.\nВиконайте: pip install ezdxf")
            return

        filepath = filedialog.askopenfilename(
            filetypes=[("DXF файли", "*.dxf"), ("Всі файли", "*.*")],
            title="Виберіть DXF підкладку",
        )
        if not filepath:
            return

        floor_name = self.floor_var.get()
        floor = None
        for f in self.project.arch_context.floors:
            if f.name == floor_name:
                floor = f
                break
        if not floor:
            messagebox.showerror("Помилка", "Спочатку створіть поверх.")
            return

        try:
            doc = ezdxf.readfile(filepath)
            msp = doc.modelspace()

            lines = []
            for entity in msp:
                if entity.dxftype() == "LINE":
                    s = entity.dxf.start
                    e = entity.dxf.end
                    lines.append((s[0], s[1], e[0], e[1]))
                elif entity.dxftype() == "LWPOLYLINE":
                    pts = list(entity.vertices_in_wcs())
                    for i in range(len(pts) - 1):
                        lines.append((pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]))
                elif entity.dxftype() == "POLYLINE":
                    pts = [(v.dxf.location[0], v.dxf.location[1]) for v in entity.vertices]
                    for i in range(len(pts) - 1):
                        lines.append((pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]))
                elif entity.dxftype() == "ARC":
                    # Спрощено: додаємо кілька точок дуги
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    start_angle = np.radians(entity.dxf.start_angle)
                    end_angle = np.radians(entity.dxf.end_angle)
                    if end_angle < start_angle:
                        end_angle += 2 * np.pi
                    n = max(3, int((end_angle - start_angle) / 0.1))
                    for i in range(n):
                        a1 = start_angle + i * (end_angle - start_angle) / n
                        a2 = start_angle + (i + 1) * (end_angle - start_angle) / n
                        lines.append((
                            center[0] + radius * np.cos(a1),
                            center[1] + radius * np.sin(a1),
                            center[0] + radius * np.cos(a2),
                            center[1] + radius * np.sin(a2),
                        ))
                elif entity.dxftype() == "CIRCLE":
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    n = 32
                    for i in range(n):
                        a1 = 2 * np.pi * i / n
                        a2 = 2 * np.pi * (i + 1) / n
                        lines.append((
                            center[0] + radius * np.cos(a1),
                            center[1] + radius * np.sin(a1),
                            center[0] + radius * np.cos(a2),
                            center[1] + radius * np.sin(a2),
                        ))

            if not lines:
                messagebox.showwarning("Увага", "У DXF не знайдено ліній для відображення.")
                return

            # Обчислюємо bounding box для авто-масштабування
            all_x = [c for line in lines for c in [line[0], line[2]]]
            all_y = [c for line in lines for c in [line[1], line[3]]]
            bb_min_x, bb_max_x = min(all_x), max(all_x)
            bb_min_y, bb_max_y = min(all_y), max(all_y)

            # Авто-масштаб: підігнати під ~10000 мм
            target_size = 10000.0
            current_size = max(bb_max_x - bb_min_x, bb_max_y - bb_min_y)
            auto_scale = target_size / current_size if current_size > 0 else 1.0

            floor.background = {
                "path": filepath,
                "scale": auto_scale,
                "offset_x": 0.0,
                "offset_y": 0.0,
                "rotation": 0.0,
                "lines": lines,
            }
            self._modified = True
            self._bg_has_dxf = True
            self.status_label.config(
                text=f"📥 Підкладка: {len(lines)} ліній з {os.path.basename(filepath)} | Масштаб: {auto_scale:.3f}",
                foreground="#0066cc",
            )
            self.refresh()

        except Exception as e:
            messagebox.showerror("Помилка завантаження DXF", str(e))

    def _draw_background(self):
        """Намалювати підкладку на плані."""
        floor_name = self.floor_var.get()
        floor = None
        for f in self.project.arch_context.floors:
            if f.name == floor_name:
                floor = f
                break
        if not floor or not floor.background:
            return

        bg = floor.background
        scale = bg.get("scale", 1.0)
        off_x = bg.get("offset_x", 0.0)
        off_y = bg.get("offset_y", 0.0)
        rotation = np.radians(bg.get("rotation", 0.0))
        lines = bg.get("lines", [])
        cos_r, sin_r = np.cos(rotation), np.sin(rotation)

        for x1, y1, x2, y2 in lines:
            # Масштабування
            x1s, y1s = x1 * scale, y1 * scale
            x2s, y2s = x2 * scale, y2 * scale
            # Обертання
            x1r = x1s * cos_r - y1s * sin_r
            y1r = x1s * sin_r + y1s * cos_r
            x2r = x2s * cos_r - y2s * sin_r
            y2r = x2s * sin_r + y2s * cos_r
            # Зсув
            x1f, y1f = x1r + off_x, y1r + off_y
            x2f, y2f = x2r + off_x, y2r + off_y
            self.ax.plot([x1f, x2f], [y1f, y2f], color="#aaaaaa", linewidth=0.6, alpha=0.5, zorder=0)

    def _adjust_background_dialog(self):
        """Діалог налаштування масштабу, зсуву та обертання підкладки."""
        floor_name = self.floor_var.get()
        floor = None
        for f in self.project.arch_context.floors:
            if f.name == floor_name:
                floor = f
                break
        if not floor or not floor.background:
            messagebox.showinfo("Інформація", "Спочатку завантажте підкладку (DXF).")
            return

        bg = floor.background
        dialog = tk.Toplevel(self)
        dialog.title("⚙️ Налаштування підкладки")
        dialog.geometry("400x350")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text=f"Файл: {os.path.basename(bg.get('path', ''))}", font=("Arial", 9, "bold")).pack(pady=5)

        # Поля
        fields = {}
        params = [
            ("Масштаб", "scale", bg.get("scale", 1.0), 0.001, 100.0, 0.001),
            ("Зсув X (мм)", "offset_x", bg.get("offset_x", 0.0), -50000.0, 50000.0, 10.0),
            ("Зсув Y (мм)", "offset_y", bg.get("offset_y", 0.0), -50000.0, 50000.0, 10.0),
            ("Обертання (°)", "rotation", bg.get("rotation", 0.0), -360.0, 360.0, 1.0),
        ]

        for label, key, default, from_, to_, inc in params:
            frm = ttk.Frame(dialog)
            frm.pack(fill=tk.X, padx=10, pady=3)
            ttk.Label(frm, text=label + ":", width=16).pack(side=tk.LEFT)
            var = tk.DoubleVar(value=default)
            spin = ttk.Spinbox(frm, from_=from_, to=to_, increment=inc, textvariable=var, width=15)
            spin.pack(side=tk.LEFT, padx=5)
            fields[key] = var

        # Кнопки швидкого масштабування
        quick_frm = ttk.Frame(dialog)
        quick_frm.pack(pady=5)
        ttk.Label(quick_frm, text="Швидко:").pack(side=tk.LEFT)
        for s in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
            ttk.Button(quick_frm, text=str(s), width=5,
                       command=lambda v=s, f=fields: f["scale"].set(v)).pack(side=tk.LEFT, padx=1)

        # Кнопки швидкого обертання
        rot_frm = ttk.Frame(dialog)
        rot_frm.pack(pady=5)
        ttk.Label(rot_frm, text="Повернути:").pack(side=tk.LEFT)
        for a in [0, 90, 180, 270]:
            ttk.Button(rot_frm, text=f"{a}°", width=5,
                       command=lambda v=a, f=fields: f["rotation"].set(v)).pack(side=tk.LEFT, padx=1)

        def on_ok():
            floor.background["scale"] = fields["scale"].get()
            floor.background["offset_x"] = fields["offset_x"].get()
            floor.background["offset_y"] = fields["offset_y"].get()
            floor.background["rotation"] = fields["rotation"].get()
            self._modified = True
            self.status_label.config(
                text=f"⚙️ Підкладка: масштаб={fields['scale'].get():.3f}, зсув=({fields['offset_x'].get():.0f}, {fields['offset_y'].get():.0f}), оберт={fields['rotation'].get():.0f}°",
                foreground="#0066cc",
            )
            dialog.destroy()
            self.refresh()

        def on_preview():
            floor.background["scale"] = fields["scale"].get()
            floor.background["offset_x"] = fields["offset_x"].get()
            floor.background["offset_y"] = fields["offset_y"].get()
            floor.background["rotation"] = fields["rotation"].get()
            self.refresh()

        btn_frm = ttk.Frame(dialog)
        btn_frm.pack(pady=15)
        ttk.Button(btn_frm, text="👁️ Попередній перегляд", command=on_preview).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frm, text="✅ Застосувати", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frm, text="❌ Скасувати", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _remove_background(self):
        """Видалити підкладку з поточного поверху."""
        floor_name = self.floor_var.get()
        floor = None
        for f in self.project.arch_context.floors:
            if f.name == floor_name:
                floor = f
                break
        if not floor or not floor.background:
            messagebox.showinfo("Інформація", "На цьому поверсі немає підкладки.")
            return
        if messagebox.askyesno("Підтвердження", f"Видалити підкладку з поверху '{floor_name}'?"):
            floor.background = None
            self._modified = True
            self._bg_has_dxf = False
            self.status_label.config(text="🗑️ Підкладку видалено", foreground="#cc0000")
            self.refresh()

    def _on_close(self):
        if self.on_close_callback:
            self.on_close_callback(self._modified)
        self.destroy()
