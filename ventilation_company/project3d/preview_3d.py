"""Покращений 3D-перегляд проєкту через matplotlib.

Відображає архітектурний контекст + вентиляційні системи.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Dict, Any

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

from ventilation_company.project3d.project_model import VentProject
from ventilation_company.project3d.vent_system import Point3D


class Project3DPreview:
    """3D-перегляд проєкту: архітектура + вентиляція."""

    COLORS = {
        "wall": "#888888",
        "wall_load": "#666666",
        "opening": "#ff6666",
        "duct_supply": "#4da6ff",
        "duct_exhaust": "#66cc66",
        "duct_smoke": "#ff9944",
        "fitting": "#cc66cc",
        "equipment": "#ffcc44",
        "floor": "#eeeeee",
        "grid": "#cccccc",
    }

    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.project: Optional[VentProject] = None
        self.current_floor: Optional[str] = None
        self._show_arch = True
        self._show_vent = True
        self._show_labels = True
        self._show_equipment = True
        self._wireframe = False
        self._view_angle = (25, -60)

        self._build_ui()

    def _build_ui(self):
        # Controls
        ctrl = ttk.Frame(self.parent)
        ctrl.pack(fill=tk.X, padx=5, pady=2)

        self.floor_var = tk.StringVar(value="Всі поверхи")
        ttk.Label(ctrl, text="Поверх:").pack(side=tk.LEFT)
        self.floor_combo = ttk.Combobox(ctrl, textvariable=self.floor_var,
                                         values=["Всі поверхи"], state="readonly", width=16)
        self.floor_combo.pack(side=tk.LEFT, padx=2)
        self.floor_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Separator(ctrl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        self.arch_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="Архітектура", variable=self.arch_var,
                        command=self.refresh).pack(side=tk.LEFT, padx=2)

        self.vent_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="Вентиляція", variable=self.vent_var,
                        command=self.refresh).pack(side=tk.LEFT, padx=2)

        self.eq_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="Обладнання", variable=self.eq_var,
                        command=self.refresh).pack(side=tk.LEFT, padx=2)

        self.lbl_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="Підписи", variable=self.lbl_var,
                        command=self.refresh).pack(side=tk.LEFT, padx=2)

        ttk.Separator(ctrl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        ttk.Button(ctrl, text="⬆️ Зверху", command=lambda: self._set_view(90, -90)).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="➡️ Збоку", command=lambda: self._set_view(0, -90)).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="↗️ Ізометрія", command=lambda: self._set_view(25, -60)).pack(side=tk.LEFT, padx=2)

        # 3D Canvas
        self.figure = Figure(figsize=(10, 7), dpi=100, facecolor="#fafafa")
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        toolbar = NavigationToolbar2Tk(self.canvas, self.parent)
        toolbar.update()

    def _set_view(self, elev: float, azim: float):
        self._view_angle = (elev, azim)
        self.refresh()

    def set_project(self, project: VentProject):
        """Встановити проєкт для відображення."""
        self.project = project
        # Оновлюємо список поверхів
        floors = ["Всі поверхи"]
        if project and project.arch_context:
            for f in project.arch_context.floors:
                floors.append(f.name)
        self.floor_combo["values"] = floors
        self.floor_var.set(floors[0] if floors else "Всі поверхи")
        self.refresh()

    def refresh(self):
        """Перемалювати 3D-сцену."""
        self.figure.clear()
        self.ax = self.figure.add_subplot(111, projection="3d")
        self.ax.set_facecolor("#fafafa")

        if not self.project:
            self.ax.text(0, 0, 0, "Немає проєкту для відображення",
                         fontsize=14, ha="center", color="#999")
            self.ax.set_xlim(-100, 100)
            self.ax.set_ylim(-100, 100)
            self.ax.set_zlim(-100, 100)
            self.canvas.draw()
            return

        show_arch = self.arch_var.get()
        show_vent = self.vent_var.get()
        show_eq = self.eq_var.get()
        show_labels = self.lbl_var.get()
        floor_filter = self.floor_var.get()
        all_floors = floor_filter == "Всі поверхи"

        all_x, all_y, all_z = [], [], []

        # ── Архітектура ──
        if show_arch:
            for floor in self.project.arch_context.floors:
                if not all_floors and floor.name != floor_filter:
                    continue
                for wall in floor.walls:
                    self._draw_wall(wall, show_labels)
                    bb = wall.get_bounding_box()
                    all_x.extend([bb[0].x, bb[1].x])
                    all_y.extend([bb[0].y, bb[1].y])
                    all_z.extend([bb[0].z, bb[1].z])

                for opening in floor.openings:
                    self._draw_opening(opening)
                    all_x.extend([opening.position.x - opening.width/2, opening.position.x + opening.width/2])
                    all_y.extend([opening.position.y - opening.width/2, opening.position.y + opening.width/2])
                    all_z.extend([opening.position.z - opening.height/2, opening.position.z + opening.height/2])

        # ── Вентиляція ──
        if show_vent:
            for system in self.project.ventilation_systems:
                for trunk in system.trunks:
                    if not all_floors:
                        # Перевіряємо, чи трасса на цьому поверсі
                        trunk_floor = str(trunk.floor) if hasattr(trunk, "floor") else ""
                        if trunk_floor not in floor_filter and trunk.name != floor_filter:
                            continue
                    for seg in trunk.segments:
                        self._draw_duct_segment(seg, system.system_type, show_labels)
                        all_x.extend([seg.start.x, seg.end.x])
                        all_y.extend([seg.start.y, seg.end.y])
                        all_z.extend([seg.start.z, seg.end.z])

                    for fitting in trunk.fittings:
                        self._draw_fitting(fitting, show_labels)
                        all_x.append(fitting.position.x)
                        all_y.append(fitting.position.y)
                        all_z.append(fitting.position.z)

        # ── Обладнання ──
        if show_eq:
            for system in self.project.ventilation_systems:
                for trunk in system.trunks:
                    for eq in trunk.equipment:
                        self._draw_equipment(eq, show_labels)
                        all_x.extend([eq.position.x - eq.width/2, eq.position.x + eq.width/2])
                        all_y.extend([eq.position.y - eq.height/2, eq.position.y + eq.height/2])
                        all_z.extend([eq.position.z, eq.position.z + eq.length])

        # ── Масштабування ──
        if all_x and all_y and all_z:
            margin = max(max(all_x) - min(all_x), max(all_y) - min(all_y),
                         max(all_z) - min(all_z)) * 0.1 + 200
            self.ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
            self.ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
            self.ax.set_zlim(min(all_z) - margin, max(all_z) + margin)
        else:
            self.ax.set_xlim(-5000, 5000)
            self.ax.set_ylim(-5000, 5000)
            self.ax.set_zlim(0, 5000)

        self.ax.set_xlabel("X, мм")
        self.ax.set_ylabel("Y, мм")
        self.ax.set_zlabel("Z, мм")
        title = f"{self.project.name} — 3D"
        if not all_floors:
            title += f" ({floor_filter})"
        self.ax.set_title(title, fontsize=11, pad=10)

        elev, azim = self._view_angle
        self.ax.view_init(elev=elev, azim=azim)
        self.ax.set_box_aspect([1, 1, 0.5])

        self.canvas.draw()

    def _draw_wall(self, wall, show_labels: bool):
        """Намалювати стіну як прямокутник."""
        n = wall.normal
        hw = wall.thickness / 2
        h = wall.height

        # 4 кути стіни
        p1 = wall.start + Point3D(n.x * hw, n.y * hw, 0)
        p2 = wall.start - Point3D(n.x * hw, n.y * hw, 0)
        p3 = wall.end - Point3D(n.x * hw, n.y * hw, 0)
        p4 = wall.end + Point3D(n.x * hw, n.y * hw, 0)

        verts = [
            [p1.to_tuple(), p2.to_tuple(), p3.to_tuple(), p4.to_tuple()],  # низ
            [Point3D(p1.x, p1.y, h).to_tuple(), Point3D(p2.x, p2.y, h).to_tuple(),
             Point3D(p3.x, p3.y, h).to_tuple(), Point3D(p4.x, p4.y, h).to_tuple()],  # верх
            [p1.to_tuple(), p4.to_tuple(), Point3D(p4.x, p4.y, h).to_tuple(), Point3D(p1.x, p1.y, h).to_tuple()],
            [p2.to_tuple(), p3.to_tuple(), Point3D(p3.x, p3.y, h).to_tuple(), Point3D(p2.x, p2.y, h).to_tuple()],
            [p1.to_tuple(), p2.to_tuple(), Point3D(p2.x, p2.y, h).to_tuple(), Point3D(p1.x, p1.y, h).to_tuple()],
            [p4.to_tuple(), p3.to_tuple(), Point3D(p3.x, p3.y, h).to_tuple(), Point3D(p4.x, p4.y, h).to_tuple()],
        ]

        color = self.COLORS["wall_load"] if wall.is_load_bearing else self.COLORS["wall"]
        poly3d = Poly3DCollection(verts, alpha=0.35, facecolor=color,
                                  edgecolor=color, linewidth=0.3)
        self.ax.add_collection3d(poly3d)

        if show_labels and wall.length > 1000:
            cx = (wall.start.x + wall.end.x) / 2
            cy = (wall.start.y + wall.end.y) / 2
            cz = h + 100
            self.ax.text(cx, cy, cz, wall.name, fontsize=6, color="#444",
                         ha="center", va="bottom")

    def _draw_opening(self, opening):
        """Намалювати отвір як червоний прямокутник."""
        cx, cy, cz = opening.position.x, opening.position.y, opening.position.z
        w, h = opening.width / 2, opening.height / 2
        verts = [
            [(cx - w, cy - w, cz - h), (cx + w, cy - w, cz - h),
             (cx + w, cy + w, cz - h), (cx - w, cy + w, cz - h)],
            [(cx - w, cy - w, cz + h), (cx + w, cy - w, cz + h),
             (cx + w, cy + w, cz + h), (cx - w, cy + w, cz + h)],
        ]
        poly3d = Poly3DCollection(verts, alpha=0.6, facecolor=self.COLORS["opening"],
                                  edgecolor="#cc0000", linewidth=1)
        self.ax.add_collection3d(poly3d)

    def _draw_duct_segment(self, seg, system_type: str, show_labels: bool):
        """Намалювати сегмент повітропроводу."""
        color_key = "duct_supply"
        if "витяж" in system_type.lower() or "exhaust" in system_type.lower():
            color_key = "duct_exhaust"
        elif "дим" in system_type.lower() or "smoke" in system_type.lower():
            color_key = "duct_smoke"
        color = self.COLORS[color_key]

        # Лінія трасси
        self.ax.plot3D(
            [seg.start.x, seg.end.x],
            [seg.start.y, seg.end.y],
            [seg.start.z, seg.end.z],
            color=color, linewidth=3, alpha=0.9,
        )

        # Прямокутний профіль на кінцях (для наочності)
        if seg.shape.value == "прямокутний":
            self._draw_duct_box(seg.start, seg.width, seg.height, color, alpha=0.3)
            self._draw_duct_box(seg.end, seg.width, seg.height, color, alpha=0.3)
        else:
            self._draw_duct_circle(seg.start, seg.width, color, alpha=0.3)
            self._draw_duct_circle(seg.end, seg.width, color, alpha=0.3)

        if show_labels and seg.length > 1500:
            cx = (seg.start.x + seg.end.x) / 2
            cy = (seg.start.y + seg.end.y) / 2
            cz = max(seg.start.z, seg.end.z) + seg.height / 2 + 50
            label = f"{seg.width:.0f}×{seg.height:.0f}"
            self.ax.text(cx, cy, cz, label, fontsize=6, color=color,
                         ha="center", va="bottom",
                         bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7, edgecolor="none"))

    def _draw_duct_box(self, pos: Point3D, w: float, h: float, color: str, alpha: float):
        """Намалювати прямокутний профіль повітропроводу."""
        hw, hh = w / 2, h / 2
        verts = [
            [(pos.x - hw, pos.y - hh, pos.z), (pos.x + hw, pos.y - hh, pos.z),
             (pos.x + hw, pos.y + hh, pos.z), (pos.x - hw, pos.y + hh, pos.z)],
        ]
        poly3d = Poly3DCollection(verts, alpha=alpha, facecolor=color,
                                  edgecolor=color, linewidth=0.5)
        self.ax.add_collection3d(poly3d)

    def _draw_duct_circle(self, pos: Point3D, d: float, color: str, alpha: float):
        """Намалювати круглий профіль повітропроводу."""
        theta = np.linspace(0, 2 * np.pi, 16)
        r = d / 2
        xs = pos.x + r * np.cos(theta)
        ys = pos.y + r * np.sin(theta)
        zs = np.full_like(xs, pos.z)
        self.ax.plot3D(xs, ys, zs, color=color, linewidth=1, alpha=alpha + 0.3)

    def _draw_fitting(self, fitting, show_labels: bool):
        """Намалювати фасонний виріб як ромб."""
        cx, cy, cz = fitting.position.x, fitting.position.y, fitting.position.z
        size = max(fitting.width_in, fitting.height_in, 100) / 2
        verts = [
            [(cx - size, cy, cz), (cx, cy - size, cz), (cx + size, cy, cz), (cx, cy + size, cz)],
            [(cx - size, cy, cz + size/2), (cx, cy - size, cz + size/2),
             (cx + size, cy, cz + size/2), (cx, cy + size, cz + size/2)],
        ]
        poly3d = Poly3DCollection(verts, alpha=0.5, facecolor=self.COLORS["fitting"],
                                  edgecolor="#990099", linewidth=1)
        self.ax.add_collection3d(poly3d)

        if show_labels:
            self.ax.text(cx, cy, cz + size + 50, fitting.fitting_type,
                         fontsize=6, color="#990099", ha="center", va="bottom")

    def _draw_equipment(self, eq, show_labels: bool):
        """Намалювати обладнання як жовтий бокс."""
        cx, cy, cz = eq.position.x, eq.position.y, eq.position.z
        w, h, l = eq.width / 2, eq.height / 2, eq.length

        verts = [
            [(cx - w, cy - h, cz), (cx + w, cy - h, cz), (cx + w, cy + h, cz), (cx - w, cy + h, cz)],
            [(cx - w, cy - h, cz + l), (cx + w, cy - h, cz + l), (cx + w, cy + h, cz + l), (cx - w, cy + h, cz + l)],
            [(cx - w, cy - h, cz), (cx - w, cy - h, cz + l), (cx + w, cy - h, cz + l), (cx + w, cy - h, cz)],
            [(cx - w, cy + h, cz), (cx - w, cy + h, cz + l), (cx + w, cy + h, cz + l), (cx + w, cy + h, cz)],
            [(cx - w, cy - h, cz), (cx - w, cy - h, cz + l), (cx - w, cy + h, cz + l), (cx - w, cy + h, cz)],
            [(cx + w, cy - h, cz), (cx + w, cy - h, cz + l), (cx + w, cy + h, cz + l), (cx + w, cy + h, cz)],
        ]
        poly3d = Poly3DCollection(verts, alpha=0.5, facecolor=self.COLORS["equipment"],
                                  edgecolor="#cc8800", linewidth=1)
        self.ax.add_collection3d(poly3d)

        if show_labels:
            self.ax.text(cx, cy, cz + l + 100, eq.name,
                         fontsize=7, color="#cc8800", ha="center", va="bottom", fontweight="bold")

    def export_image(self, filepath: str):
        """Експортувати поточний вид як PNG."""
        if self.figure:
            self.figure.savefig(filepath, dpi=150, bbox_inches="tight",
                                facecolor=self.figure.get_facecolor())
