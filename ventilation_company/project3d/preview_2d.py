"""2D-перегляд креслень проєкту через matplotlib.

Відображає плани поверхів з накладанням вентиляції.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, List, Dict, Any, Callable

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, Polygon
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe
import numpy as np

from ventilation_company.project3d.project_model import VentProject
from ventilation_company.project3d.vent_system import Point3D, DuctShape


class Project2DPreview:
    """2D-перегляд плану поверху з вентиляцією + інтерактивне креслення."""

    COLORS = {
        "wall": "#555555",
        "wall_partition": "#888888",
        "opening": "#ff4444",
        "duct_supply": "#0066cc",
        "duct_exhaust": "#009900",
        "duct_smoke": "#cc6600",
        "fitting": "#990099",
        "equipment": "#cc9900",
        "grid": "#dddddd",
        "text": "#333333",
        "bg": "#fafafa",
        "draw_preview": "#ff6600",
        "draw_snap": "#00aa00",
    }

    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.project: Optional[VentProject] = None
        self.current_floor: Optional[str] = None
        self._show_walls = True
        self._show_ducts = True
        self._show_fittings = True
        self._show_equipment = True
        self._show_openings = True
        self._show_dimensions = True
        self._show_grid = True
        self._zoom_level = 1.0

        # ── Режим креслення ──
        self._draw_mode: Optional[str] = None   # "segment" | "wall" | None
        self._draw_start: Optional[Point3D] = None
        self._draw_temp_line: Optional[Line2D] = None
        self._draw_callback: Optional[Callable] = None
        self._draw_status_label: Optional[ttk.Label] = None
        self._tk_canvas: Optional[tk.Widget] = None  # tk.Canvas widget

        self._build_ui()
        self._connect_mouse_events()

    def _build_ui(self):
        # Controls
        ctrl = ttk.Frame(self.parent)
        ctrl.pack(fill=tk.X, padx=5, pady=2)

        self.floor_var = tk.StringVar(value="Поверх 1")
        ttk.Label(ctrl, text="Поверх:").pack(side=tk.LEFT)
        self.floor_combo = ttk.Combobox(ctrl, textvariable=self.floor_var,
                                         values=["Поверх 1"], state="readonly", width=16)
        self.floor_combo.pack(side=tk.LEFT, padx=2)
        self.floor_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Separator(ctrl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        self.wall_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="Стіни", variable=self.wall_var,
                        command=self.refresh).pack(side=tk.LEFT, padx=2)

        self.duct_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="Повітропроводи", variable=self.duct_var,
                        command=self.refresh).pack(side=tk.LEFT, padx=2)

        self.eq_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="Обладнання", variable=self.eq_var,
                        command=self.refresh).pack(side=tk.LEFT, padx=2)

        self.dim_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="Розміри", variable=self.dim_var,
                        command=self.refresh).pack(side=tk.LEFT, padx=2)

        ttk.Separator(ctrl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        ttk.Button(ctrl, text="🔍 +", command=self._zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="🔍 -", command=self._zoom_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="🔄 Центрувати", command=self._center_view).pack(side=tk.LEFT, padx=2)

        # 2D Canvas
        self.figure = Figure(figsize=(10, 7), dpi=100, facecolor=self.COLORS["bg"])
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor(self.COLORS["bg"])
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.parent)
        self.canvas.draw()
        self._tk_canvas = self.canvas.get_tk_widget()
        self._tk_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        toolbar = NavigationToolbar2Tk(self.canvas, self.parent)
        toolbar.update()

        # Статус креслення
        self._draw_status_label = ttk.Label(self.parent, text="",
                                             foreground="#0066cc", font=("Arial", 9, "bold"))
        self._draw_status_label.pack(anchor=tk.W, padx=5)

        # Підказка
        hint = ttk.Label(self.parent, text="💡 ЛКМ — вибір | ПКМ — контекстне меню | Колесо — масштаб",
                         foreground="#666", font=("Arial", 8))
        hint.pack(anchor=tk.W, padx=5)

    # ═══════════════════════════════════════════════════════════════
    # ІНТЕРАКТИВНЕ КРЕСЛЕННЯ МИШЕЮ (tkinter events)
    # ═══════════════════════════════════════════════════════════════

    def _connect_mouse_events(self):
        """Підключити обробники подій миші tkinter (надійніше ніж mpl_connect)."""
        if self._tk_canvas is None:
            return
        self._tk_canvas.bind("<ButtonPress-1>", self._on_tk_mouse_press)
        self._tk_canvas.bind("<B1-Motion>", self._on_tk_mouse_move)
        self._tk_canvas.bind("<ButtonRelease-1>", self._on_tk_mouse_release)

    def _tk_to_data_coords(self, x: int, y: int) -> Optional[tuple]:
        """Конвертувати tkinter пікселі (x,y) в координати даних matplotlib."""
        try:
            inv = self.ax.transData.inverted()
            data_x, data_y = inv.transform((x, y))
            return (data_x, data_y)
        except Exception:
            return None

    def set_draw_mode(self, mode: str, callback: Callable):
        """Активувати режим креслення."""
        self._draw_mode = mode
        self._draw_callback = callback
        self._draw_start = None
        if self._draw_temp_line:
            try:
                self._draw_temp_line.remove()
            except Exception:
                pass
            self._draw_temp_line = None

        # Скинути toolbar matplotlib (вийти з pan/zoom)
        try:
            self.canvas.toolbar.pan()
            self.canvas.toolbar.zoom()
        except Exception:
            pass

        if self._tk_canvas:
            self._tk_canvas.focus_set()
            self._tk_canvas.config(cursor="crosshair")

        if mode == "segment":
            self._draw_status_label.config(
                text="✏️ РЕЖИМ: Креслення сегмента → ЛКМ на плані, тягніть, відпустіть"
            )
        elif mode == "wall":
            self._draw_status_label.config(
                text="✏️ РЕЖИМ: Креслення стіни → ЛКМ на плані, тягніть, відпустіть"
            )
        else:
            self._draw_status_label.config(text="")
            if self._tk_canvas:
                self._tk_canvas.config(cursor="")

    def cancel_draw_mode(self):
        """Скасувати режим креслення."""
        self._draw_mode = None
        self._draw_callback = None
        self._draw_start = None
        if self._draw_temp_line:
            try:
                self._draw_temp_line.remove()
            except Exception:
                pass
            self._draw_temp_line = None
        self._draw_status_label.config(text="")
        if self._tk_canvas:
            self._tk_canvas.config(cursor="")
        self.canvas.draw_idle()

    def _get_floor_z(self) -> float:
        """Повернути Z-координату (висоту) поточного поверху."""
        floor_name = self.floor_var.get()
        if self.project and self.project.arch_context:
            for f in self.project.arch_context.floors:
                if f.name == floor_name:
                    return f.level
        return 2500.0

    def _on_tk_mouse_press(self, event):
        """Натискання ЛКМ — фіксація точки початку."""
        if not self._draw_mode:
            return
        coords = self._tk_to_data_coords(event.x, event.y)
        if coords is None:
            return
        data_x, data_y = coords
        z = self._get_floor_z()
        self._draw_start = Point3D(data_x, data_y, z)

        # Створити тимчасову лінію
        if self._draw_temp_line:
            try:
                self._draw_temp_line.remove()
            except Exception:
                pass
        self._draw_temp_line, = self.ax.plot(
            [data_x, data_x],
            [data_y, data_y],
            color=self.COLORS["draw_preview"],
            linewidth=2.5,
            linestyle="--",
            marker="o",
            markersize=6,
            markerfacecolor=self.COLORS["draw_snap"],
        )
        self.canvas.draw_idle()

    def _on_tk_mouse_move(self, event):
        """Рух миші з натиснутою ЛКМ — оновлення тимчасової лінії."""
        if not self._draw_mode or self._draw_start is None:
            return
        coords = self._tk_to_data_coords(event.x, event.y)
        if coords is None:
            return
        data_x, data_y = coords

        if self._draw_temp_line:
            self._draw_temp_line.set_data(
                [self._draw_start.x, data_x],
                [self._draw_start.y, data_y],
            )
            dx = data_x - self._draw_start.x
            dy = data_y - self._draw_start.y
            length = (dx**2 + dy**2) ** 0.5
            self._draw_status_label.config(
                text=f"✏️ {self._draw_mode.upper()}: L={length:.0f} мм | "
                     f"ΔX={dx:.0f}  ΔY={dy:.0f}  |  Відпустіть ЛКМ для фіксації"
            )
            self.canvas.draw_idle()

    def _on_tk_mouse_release(self, event):
        """Відпускання ЛКМ — фіксація кінцевої точки."""
        if not self._draw_mode or self._draw_start is None:
            return
        coords = self._tk_to_data_coords(event.x, event.y)
        if coords is None:
            self.cancel_draw_mode()
            return
        data_x, data_y = coords
        z = self._get_floor_z()
        end = Point3D(data_x, data_y, z)
        start = self._draw_start

        # Прибрати тимчасову лінію
        if self._draw_temp_line:
            try:
                self._draw_temp_line.remove()
            except Exception:
                pass
            self._draw_temp_line = None

        # Викликати callback
        callback = self._draw_callback
        self.cancel_draw_mode()

        if callback:
            try:
                callback(start, end)
            except Exception as e:
                import tkinter.messagebox as mb
                mb.showerror("Помилка креслення", str(e))

    # ═══════════════════════════════════════════════════════════════

    def _zoom_in(self):
        self._zoom_level *= 1.2
        self.refresh()

    def _zoom_out(self):
        self._zoom_level /= 1.2
        self.refresh()

    def _center_view(self):
        self._zoom_level = 1.0
        self.refresh()

    def set_project(self, project: VentProject):
        """Встановити проєкт для відображення."""
        self.project = project
        floors = []
        if project and project.arch_context:
            for f in project.arch_context.floors:
                floors.append(f.name)
        if not floors:
            floors = ["Поверх 1"]
        self.floor_combo["values"] = floors
        self.floor_var.set(floors[0])
        self.refresh()

    def refresh(self):
        """Перемалювати 2D-план."""
        self.ax.clear()
        self.ax.set_facecolor(self.COLORS["bg"])

        if not self.project:
            self.ax.text(0.5, 0.5, "Немає проєкту для відображення",
                         transform=self.ax.transAxes, fontsize=14, ha="center", color="#999")
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
            self.ax.text(0.5, 0.5, f"Поверх '{floor_name}' не знайдено",
                         transform=self.ax.transAxes, fontsize=14, ha="center", color="#999")
            self.ax.set_xlim(0, 1)
            self.ax.set_ylim(0, 1)
            self.canvas.draw()
            return

        show_walls = self.wall_var.get()
        show_ducts = self.duct_var.get()
        show_eq = self.eq_var.get()
        show_dims = self.dim_var.get()

        all_x, all_y = [], []

        # ── Сітка ──
        if self._show_grid:
            self.ax.grid(True, color=self.COLORS["grid"], linestyle="-", linewidth=0.5, alpha=0.5)
            self.ax.set_axisbelow(True)

        # ── Стіни ──
        if show_walls:
            for wall in floor.walls:
                self._draw_wall_2d(wall)
                all_x.extend([wall.start.x, wall.end.x])
                all_y.extend([wall.start.y, wall.end.y])

        # ── Отвори ──
        if self._show_openings:
            for opening in floor.openings:
                self._draw_opening_2d(opening)
                all_x.extend([opening.position.x - opening.width/2, opening.position.x + opening.width/2])
                all_y.extend([opening.position.y - opening.width/2, opening.position.y + opening.width/2])

        # ── Вентиляція ──
        if show_ducts:
            for system in self.project.ventilation_systems:
                color_key = "duct_supply"
                if "витяж" in system.system_type.lower() or "exhaust" in system.system_type.lower():
                    color_key = "duct_exhaust"
                elif "дим" in system.system_type.lower() or "smoke" in system.system_type.lower():
                    color_key = "duct_smoke"
                color = self.COLORS[color_key]

                for trunk in system.trunks:
                    # Перевіряємо, чи трасса на цьому поверсі
                    trunk_floor = str(trunk.floor) if hasattr(trunk, "floor") else ""
                    if trunk_floor not in floor_name and trunk.name != floor_name:
                        # Перевіряємо z-координату
                        z_min = min(s.start.z for s in trunk.segments) if trunk.segments else 0
                        z_max = max(s.end.z for s in trunk.segments) if trunk.segments else 0
                        floor_z = floor.floor_z
                        level = floor.level
                        if not (floor_z <= z_min <= level or floor_z <= z_max <= level):
                            continue

                    for seg in trunk.segments:
                        self._draw_duct_segment_2d(seg, color, show_dims)
                        all_x.extend([seg.start.x, seg.end.x])
                        all_y.extend([seg.start.y, seg.end.y])

                    for fitting in trunk.fittings:
                        self._draw_fitting_2d(fitting)
                        all_x.append(fitting.position.x)
                        all_y.append(fitting.position.y)

        # ── Обладнання ──
        if show_eq:
            for system in self.project.ventilation_systems:
                for trunk in system.trunks:
                    for eq in trunk.equipment:
                        self._draw_equipment_2d(eq)
                        all_x.extend([eq.position.x - eq.width/2, eq.position.x + eq.width/2])
                        all_y.extend([eq.position.y - eq.height/2, eq.position.y + eq.height/2])

        # ── Масштабування ──
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

        # Легенда
        legend_elements = [
            Line2D([0], [0], color=self.COLORS["wall"], lw=4, label="Стіна"),
            Line2D([0], [0], color=self.COLORS["duct_supply"], lw=3, label="Приплив"),
            Line2D([0], [0], color=self.COLORS["duct_exhaust"], lw=3, label="Витяжка"),
            Line2D([0], [0], marker="s", color="w", markerfacecolor=self.COLORS["equipment"],
                   markersize=10, label="Обладнання"),
        ]
        self.ax.legend(handles=legend_elements, loc="upper right", fontsize=8, framealpha=0.9)

        self.canvas.draw()

    def _draw_wall_2d(self, wall):
        """Намалювати стіну на плані."""
        import math
        dx = wall.end.x - wall.start.x
        dy = wall.end.y - wall.start.y
        length = math.sqrt(dx**2 + dy**2)
        if length == 0:
            return

        # Нормалізований напрямок
        nx, ny = dx / length, dy / length
        # Нормаль (перпендикуляр)
        perp_x, perp_y = -ny, nx
        hw = wall.thickness / 2

        # 4 кути прямокутника стіни
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

    def _draw_opening_2d(self, opening):
        """Намалювати отвір на плані."""
        cx, cy = opening.position.x, opening.position.y
        w, h = opening.width, opening.height
        if opening.shape == "круглий":
            circle = Circle((cx, cy), w / 2, facecolor=self.COLORS["opening"],
                            edgecolor="#cc0000", linewidth=1.5, alpha=0.7)
            self.ax.add_patch(circle)
        else:
            rect = Rectangle((cx - w/2, cy - h/2), w, h,
                             facecolor=self.COLORS["opening"],
                             edgecolor="#cc0000", linewidth=1.5, alpha=0.7)
            self.ax.add_patch(rect)

    def _draw_duct_segment_2d(self, seg, color: str, show_dims: bool):
        """Намалювати сегмент повітропроводу на плані."""
        x1, y1 = seg.start.x, seg.start.y
        x2, y2 = seg.end.x, seg.end.y

        # Лінія трасси
        self.ax.plot([x1, x2], [y1, y2], color=color, linewidth=3, solid_capstyle="round")

        # Профіль на кінцях
        if seg.shape == DuctShape.RECT:
            w, h = seg.width, seg.height
            self._draw_rect_profile(x1, y1, w, h, color)
            self._draw_rect_profile(x2, y2, w, h, color)
        else:
            d = seg.width
            self._draw_circle_profile(x1, y1, d, color)
            self._draw_circle_profile(x2, y2, d, color)

        # Розміри
        if show_dims and seg.length > 1000:
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            offset = max(seg.width, seg.height) / 2 + 150
            # Перпендикулярний зсув
            perp_angle = np.radians(angle + 90)
            ox = offset * np.cos(perp_angle)
            oy = offset * np.sin(perp_angle)

            label = f"{seg.width:.0f}×{seg.height:.0f}  L={seg.length:.0f}"
            self.ax.annotate(label, xy=(cx, cy), xytext=(cx + ox, cy + oy),
                            fontsize=7, color=color, fontweight="bold",
                            ha="center", va="center",
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8, edgecolor="none"),
                            arrowprops=dict(arrowstyle="->", color=color, lw=0.8))

    def _draw_rect_profile(self, x: float, y: float, w: float, h: float, color: str):
        """Намалювати прямокутний профіль."""
        rect = Rectangle((x - w/2, y - h/2), w, h,
                         facecolor=color, edgecolor="black", linewidth=0.5, alpha=0.4)
        self.ax.add_patch(rect)

    def _draw_circle_profile(self, x: float, y: float, d: float, color: str):
        """Намалювати круглий профіль."""
        circle = Circle((x, y), d/2, facecolor=color, edgecolor="black", linewidth=0.5, alpha=0.4)
        self.ax.add_patch(circle)

    def _draw_fitting_2d(self, fitting):
        """Намалювати фасонний виріб на плані."""
        cx, cy = fitting.position.x, fitting.position.y
        size = max(fitting.width_in, fitting.height_in, 100) / 2
        diamond = Polygon([(cx, cy + size), (cx + size, cy), (cx, cy - size), (cx - size, cy)],
                          closed=True, facecolor=self.COLORS["fitting"],
                          edgecolor="#660066", linewidth=1.5, alpha=0.7)
        self.ax.add_patch(diamond)
        self.ax.text(cx, cy, fitting.fitting_type[:3], fontsize=6, color="white",
                     ha="center", va="center", fontweight="bold")

    def _draw_equipment_2d(self, eq):
        """Намалювати обладнання на плані."""
        cx, cy = eq.position.x, eq.position.y
        w, h = eq.width, eq.height
        rect = FancyBboxPatch((cx - w/2, cy - h/2), w, h,
                              boxstyle="round,pad=50",
                              facecolor=self.COLORS["equipment"],
                              edgecolor="#996600", linewidth=2, alpha=0.8)
        self.ax.add_patch(rect)
        self.ax.text(cx, cy, eq.name, fontsize=7, color="white",
                     ha="center", va="center", fontweight="bold",
                     path_effects=[pe.withStroke(linewidth=2, foreground="black")])

    def export_image(self, filepath: str):
        """Експортувати план як PNG."""
        if self.figure:
            self.figure.savefig(filepath, dpi=200, bbox_inches="tight",
                                facecolor=self.figure.get_facecolor())
