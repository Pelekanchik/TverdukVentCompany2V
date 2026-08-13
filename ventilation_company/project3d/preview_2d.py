"""2D-перегляд креслень проєкту через matplotlib.

Відображає плани поверхів з накладанням вентиляції.
ТІЛЬКИ ПЕРЕГЛЯД — без режиму креслення.
"""

import os
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, Polygon
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe
import numpy as np

from ventilation_company.project3d.project_model import VentProject
from ventilation_company.project3d.vent_system import DuctShape


class Project2DPreview:
    """2D-перегляд плану поверху з вентиляцією (тільки перегляд)."""

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
    }

    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.project: Optional[VentProject] = None
        self.current_floor: Optional[str] = None
        self._zoom_level = 1.0
        self._build_ui()
        self._connect_events()

    def _build_ui(self):
        ctrl = ttk.Frame(self.parent)
        ctrl.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(ctrl, text="Поверх:").pack(side=tk.LEFT)
        self.floor_var = tk.StringVar(value="Поверх 1")
        self.floor_combo = ttk.Combobox(ctrl, textvariable=self.floor_var,
                                        values=["Поверх 1"], state="readonly", width=16)
        self.floor_combo.pack(side=tk.LEFT, padx=2)
        self.floor_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        ttk.Separator(ctrl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        self.wall_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="Стіни", variable=self.wall_var, command=self.refresh).pack(side=tk.LEFT, padx=2)
        self.duct_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="Повітропроводи", variable=self.duct_var, command=self.refresh).pack(side=tk.LEFT, padx=2)
        self.eq_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="Обладнання", variable=self.eq_var, command=self.refresh).pack(side=tk.LEFT, padx=2)
        self.dim_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="Розміри", variable=self.dim_var, command=self.refresh).pack(side=tk.LEFT, padx=2)
        ttk.Separator(ctrl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(ctrl, text="🔍 +", command=self._zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="🔍 -", command=self._zoom_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="🔄 Центрувати", command=self._center_view).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="🖨️ Друк", command=self._print).pack(side=tk.LEFT, padx=2)
        self.figure = Figure(figsize=(10, 7), dpi=100, facecolor=self.COLORS["bg"])
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor(self.COLORS["bg"])
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        toolbar = NavigationToolbar2Tk(self.canvas, self.parent)
        toolbar.update()
        hint = ttk.Label(self.parent,
                         text="💡 Колесо миші — масштаб | Перетягування — панорама | 🖨️ Друк",
                         foreground="#666", font=("Arial", 8))
        hint.pack(anchor=tk.W, padx=5)

    def _connect_events(self):
        self.canvas.mpl_connect("scroll_event", self._on_scroll)

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

    def set_project(self, project: VentProject):
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

    def _get_system_color(self, system_type: str) -> str:
        """Визначити колір системи за її типом."""
        st = system_type.lower()
        if "витяж" in st or "exhaust" in st:
            return self.COLORS["duct_exhaust"]
        if "дим" in st or "smoke" in st:
            return self.COLORS["duct_smoke"]
        # За замовчуванням — приплив (синій)
        return self.COLORS["duct_supply"]

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
        show_walls = self.wall_var.get()
        show_ducts = self.duct_var.get()
        show_eq = self.eq_var.get()
        show_dims = self.dim_var.get()
        all_x, all_y = [], []
        self.ax.grid(True, color=self.COLORS["grid"], linestyle="-", linewidth=0.5, alpha=0.5)
        self.ax.set_axisbelow(True)

        # Отвори (двері, вікна)
        for op in floor.openings:
            self._draw_opening_2d(op)
            all_x.extend([op.position.x - op.width/2, op.position.x + op.width/2])
            all_y.extend([op.position.y - op.height/2, op.position.y + op.height/2])

        if show_walls:
            for wall in floor.walls:
                self._draw_wall_2d(wall)
                all_x.extend([wall.start.x, wall.end.x])
                all_y.extend([wall.start.y, wall.end.y])

        if show_ducts:
            for system in self.project.ventilation_systems:
                color = self._get_system_color(system.system_type)
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
                        self._draw_duct_segment_2d(seg, color, show_dims)
                        all_x.extend([seg.start.x, seg.end.x])
                        all_y.extend([seg.start.y, seg.end.y])
                    for fitting in trunk.fittings:
                        self._draw_fitting_2d(fitting)
                        all_x.append(fitting.position.x)
                        all_y.append(fitting.position.y)

        if show_eq:
            for system in self.project.ventilation_systems:
                for trunk in system.trunks:
                    for eq in trunk.equipment:
                        self._draw_equipment_2d(eq)
                        all_x.extend([eq.position.x - eq.width/2, eq.position.x + eq.width/2])
                        all_y.extend([eq.position.y - eq.height/2, eq.position.y + eq.height/2])

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
        self.canvas.draw()

    def _draw_wall_2d(self, wall):
        import math
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

    def export_image(self, filepath: str):
        if self.figure:
            self.figure.savefig(filepath, dpi=200, bbox_inches="tight", facecolor=self.figure.get_facecolor())
