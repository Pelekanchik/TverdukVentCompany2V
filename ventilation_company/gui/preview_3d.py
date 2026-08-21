"""Покращене 3D прев'ю виробів за допомогою matplotlib.

Заповнені поверхні, кольори, освітлення — без FreeCAD.
"""

import tkinter as tk
from tkinter import ttk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


# ═══════════════════════════════════════════════════════════
# КОЛІРНА СХЕМА
# ═══════════════════════════════════════════════════════════

COLORS = {
    "rect_duct":    {"face": "#42A5F5", "edge": "#1565C0", "alpha": 0.75},
    "round_duct":   {"face": "#66BB6A", "edge": "#2E7D32", "alpha": 0.70},
    "elbow":        {"face": "#AB47BC", "edge": "#6A1B9A", "alpha": 0.75},
    "flange":       {"face": "#FFA726", "edge": "#EF6C00", "alpha": 0.80},
    "cap":          {"face": "#EF5350", "edge": "#C62828", "alpha": 0.80},
    "transition":   {"face": "#26C6DA", "edge": "#00838F", "alpha": 0.75},
    "tee":          {"face": "#EC407A", "edge": "#AD1457", "alpha": 0.75},
    "flexible":     {"face": "#8D6E63", "edge": "#4E342E", "alpha": 0.60},
    "generic":      {"face": "#78909C", "edge": "#37474F", "alpha": 0.70},
}


def _get_color(ptype: str) -> dict:
    ptype = ptype.lower()
    if "повітропровід" in ptype and "прямокутн" in ptype:
        return COLORS["rect_duct"]
    if "повітропровід" in ptype and "кругл" in ptype:
        return COLORS["round_duct"]
    if "фланець" in ptype:
        return COLORS["flange"]
    if "заглушка" in ptype:
        return COLORS["cap"]
    if "відвід" in ptype or "коліно" in ptype:
        return COLORS["elbow"]
    if "перехід" in ptype:
        return COLORS["transition"]
    if "трійник" in ptype:
        return COLORS["tee"]
    if "гнучк" in ptype or "вставк" in ptype:
        return COLORS["flexible"]
    return COLORS["generic"]


class ProductPreview3D:
    """Віджет 3D прев'ю виробу для tkinter."""

    def __init__(self, parent: tk.Widget, width: int = 400, height: int = 350):
        self.parent = parent
        self.width = width
        self.height = height

        self.fig = Figure(figsize=(width / 100, height / 100), dpi=100, facecolor="#fafafa")
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.ax.set_facecolor("#fafafa")
        self.ax.set_box_aspect([1, 1, 1])

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.configure(width=width, height=height)

    def pack(self, **kwargs):
        self.canvas_widget.pack(**kwargs)

    def grid(self, **kwargs):
        self.canvas_widget.grid(**kwargs)

    def clear(self):
        self.ax.clear()
        self.ax.set_facecolor("#fafafa")
        self.ax.set_box_aspect([1, 1, 1])

    def draw(self):
        self.canvas.draw()

    def show_product(self, product):
        """Показати 3D модель виробу."""
        self.clear()
        ptype = product.product_type.lower()
        is_round = "кругл" in ptype

        if "повітропровід" in ptype and "прямокутн" in ptype:
            self._draw_rect_duct(product)
        elif "повітропровід" in ptype and "кругл" in ptype:
            self._draw_round_duct(product)
        elif "фланець" in ptype:
            if is_round:
                self._draw_round_flange(product)
            else:
                self._draw_flange(product)
        elif "заглушка" in ptype:
            if is_round:
                self._draw_round_cap(product)
            else:
                self._draw_cap(product)
        elif "відвід" in ptype or "коліно" in ptype:
            if is_round:
                self._draw_round_elbow(product)
            else:
                self._draw_elbow(product)
        elif "перехід" in ptype:
            if is_round:
                self._draw_round_transition(product)
            else:
                self._draw_transition(product)
        elif "трійник" in ptype:
            if is_round:
                self._draw_round_tee(product)
            else:
                self._draw_tee(product)
        elif "гнучк" in ptype or "вставк" in ptype:
            self._draw_flexible(product)
        else:
            self._draw_generic_box(product)

        self.ax.set_xlabel("X, мм", fontsize=8)
        self.ax.set_ylabel("Y, мм", fontsize=8)
        self.ax.set_zlabel("Z, мм", fontsize=8)
        self.ax.tick_params(labelsize=7)
        self.draw()

    # ─────────────────────────────────────────────────────────
    #  ЗАПОВНЕНІ ПОВЕРХНІ — ХЕЛПЕРИ
    # ─────────────────────────────────────────────────────────

    def _add_box(self, w, h, l, cx=0, cy=0, cz=0, color_key="generic"):
        """Намалювати заповнений прямокутний паралелепіпед."""
        color = COLORS.get(color_key, COLORS["generic"])
        verts = np.array([
            [cx, cy, cz], [cx+w, cy, cz], [cx+w, cy+h, cz], [cx, cy+h, cz],
            [cx, cy, cz+l], [cx+w, cy, cz+l], [cx+w, cy+h, cz+l], [cx, cy+h, cz+l],
        ])
        faces = [
            [verts[0], verts[1], verts[2], verts[3]],
            [verts[4], verts[5], verts[6], verts[7]],
            [verts[0], verts[1], verts[5], verts[4]],
            [verts[2], verts[3], verts[7], verts[6]],
            [verts[1], verts[2], verts[6], verts[5]],
            [verts[0], verts[3], verts[7], verts[4]],
        ]
        poly3d = Poly3DCollection(faces, facecolors=color["face"], edgecolors=color["edge"],
                                   linewidths=0.6, alpha=color["alpha"], shade=True)
        self.ax.add_collection3d(poly3d)

    def _add_cylinder(self, r, l, cx=0, cy=0, cz=0, axis="z", segments=30, color_key="generic"):
        """Намалювати заповнений циліндр вздовж заданої осі."""
        color = COLORS.get(color_key, COLORS["generic"])
        theta = np.linspace(0, 2*np.pi, segments)
        t_vals = np.linspace(0, l, 10)
        theta_grid, t_grid = np.meshgrid(theta, t_vals)

        if axis == "z":
            x = cx + r * np.cos(theta_grid)
            y = cy + r * np.sin(theta_grid)
            z = cz + t_grid
        elif axis == "x":
            x = cx + t_grid
            y = cy + r * np.cos(theta_grid)
            z = cz + r * np.sin(theta_grid)
        elif axis == "y":
            x = cx + r * np.cos(theta_grid)
            y = cy + t_grid
            z = cz + r * np.sin(theta_grid)
        else:
            x = cx + r * np.cos(theta_grid)
            y = cy + r * np.sin(theta_grid)
            z = cz + t_grid

        self.ax.plot_surface(x, y, z, alpha=color["alpha"], color=color["face"],
                             edgecolor=color["edge"], linewidth=0.3, shade=True)

    def _add_torus_segment(self, R, r, angle_deg, segments_u=30, segments_v=20, color_key="generic"):
        """Намалювати частину тора (дуга круглої труби)."""
        color = COLORS.get(color_key, COLORS["generic"])
        u = np.radians(np.linspace(0, angle_deg, segments_u))
        v = np.linspace(0, 2*np.pi, segments_v)
        u_grid, v_grid = np.meshgrid(u, v)

        x = (R + r * np.cos(v_grid)) * np.cos(u_grid)
        y = (R + r * np.cos(v_grid)) * np.sin(u_grid)
        z = r * np.sin(v_grid)

        self.ax.plot_surface(x, y, z, alpha=color["alpha"], color=color["face"],
                             edgecolor=color["edge"], linewidth=0.3, shade=True)

    def _add_cone_frustum(self, r1, r2, l, segments=30, color_key="generic"):
        """Намалювати усечений конус (круглий перехід)."""
        color = COLORS.get(color_key, COLORS["generic"])
        theta = np.linspace(0, 2*np.pi, segments)
        t_vals = np.linspace(0, l, 10)
        theta_grid, t_grid = np.meshgrid(theta, t_vals)

        radius = r1 + (r2 - r1) * (t_grid / l)
        x = radius * np.cos(theta_grid)
        y = radius * np.sin(theta_grid)
        z = t_grid

        self.ax.plot_surface(x, y, z, alpha=color["alpha"], color=color["face"],
                             edgecolor=color["edge"], linewidth=0.3, shade=True)

    def _add_sphere_cap(self, r, segments=30, color_key="generic"):
        """Намалювати півсферу (кругла заглушка)."""
        color = COLORS.get(color_key, COLORS["generic"])
        u = np.linspace(0, 2*np.pi, segments)
        v = np.linspace(0, np.pi/2, 15)
        u_grid, v_grid = np.meshgrid(u, v)

        x = r * np.cos(u_grid) * np.sin(v_grid)
        y = r * np.sin(u_grid) * np.sin(v_grid)
        z = r * np.cos(v_grid)

        self.ax.plot_surface(x, y, z, alpha=color["alpha"], color=color["face"],
                             edgecolor=color["edge"], linewidth=0.3, shade=True)

    # ─────────────────────────────────────────────────────────
    #  МОДЕЛІ ВИРОБІВ
    # ─────────────────────────────────────────────────────────

    def _draw_rect_duct(self, product):
        w, h, l = product.width, product.height, product.length
        self._add_box(w, h, l, color_key="rect_duct")
        self._draw_dimension(0, -50, 0, w, -50, 0, f"{w:.0f}")
        self._draw_dimension(w+30, 0, 0, w+30, h, 0, f"{h:.0f}")
        self._draw_dimension(0, h+30, 0, 0, h+30, l, f"{l:.0f}")
        self._center_view(w, h, l)

    def _draw_round_duct(self, product):
        d, l = product.width, product.length
        r = d / 2
        self._add_cylinder(r, l, color_key="round_duct")
        self._draw_dimension(-r, -r-40, 0, r, -r-40, 0, f"Ø{d:.0f}")
        self._draw_dimension(r+30, 0, 0, r+30, 0, l, f"{l:.0f}")
        self._center_view(d, d, l)

    def _draw_flange(self, product):
        w, h = product.width, product.height
        p = getattr(product, "profile", 30)
        outer_w, outer_h = w + 2*p, h + 2*p
        self._add_box(outer_w, outer_h, 5, color_key="flange")
        hole_x = (outer_w - w) / 2
        hole_y = (outer_h - h) / 2
        self._add_box(w, h, 5, cx=hole_x, cy=hole_y, cz=0, color_key="generic")
        self._draw_dimension(0, -30, 0, outer_w, -30, 0, f"{outer_w:.0f}")
        self._draw_dimension(outer_w+20, 0, 0, outer_w+20, outer_h, 0, f"{outer_h:.0f}")
        self._center_view(outer_w, outer_h, 80)

    def _draw_round_flange(self, product):
        d = product.width
        p = getattr(product, "profile", 30)
        outer_r = (d / 2) + p
        self._add_cylinder(outer_r, 5, color_key="flange")
        # Отвір — циліндр "всередині" з іншим кольором
        hole_r = d / 2
        self._add_cylinder(hole_r, 5, color_key="generic")
        self._draw_dimension(-outer_r, -outer_r-40, 0, outer_r, -outer_r-40, 0, f"Ø{d:.0f}")
        self._center_view(outer_r*2, outer_r*2, 50)

    def _draw_cap(self, product):
        w, h = product.width, product.height
        self._add_box(w, h, 30, color_key="cap")
        self._draw_dimension(0, -30, 0, w, -30, 0, f"{w:.0f}")
        self._draw_dimension(w+20, 0, 0, w+20, h, 0, f"{h:.0f}")
        self._center_view(w, h, 100)

    def _draw_round_cap(self, product):
        d = product.width
        r = d / 2
        depth = getattr(product, "depth", 30)
        self._add_cylinder(r, depth, color_key="cap")
        self._add_sphere_cap(r, color_key="cap")
        self._draw_dimension(-r, -r-40, 0, r, -r-40, 0, f"Ø{d:.0f}")
        self._center_view(d, d, depth + r)

    def _draw_elbow(self, product):
        angle = getattr(product, "angle", 90)
        radius = getattr(product, "radius", 150)
        w, h = product.width, product.height
        color = COLORS["elbow"]

        theta = np.radians(np.linspace(0, angle, 40))
        offsets = [(0, 0), (w, 0), (w, h), (0, h)]
        for (ox, oy) in offsets:
            r_eff = radius + ox
            x = r_eff * np.cos(theta)
            z = r_eff * np.sin(theta)
            y = np.full_like(theta, oy)
            self.ax.plot3D(x, y, z, color=color["edge"], lw=2.5)

        for th in np.radians(np.arange(0, angle+1, 15)):
            pts = []
            for (ox, oy) in offsets:
                r_eff = radius + ox
                x = r_eff * np.cos(th)
                z = r_eff * np.sin(th)
                pts.append([x, oy, z])
            pts.append(pts[0])
            arr = np.array(pts)
            self.ax.plot3D(arr[:,0], arr[:,1], arr[:,2], color=color["edge"], lw=1.0)

        for th in [0, np.radians(angle)]:
            face_pts = []
            for (ox, oy) in offsets:
                r_eff = radius + ox
                x = r_eff * np.cos(th)
                z = r_eff * np.sin(th)
                face_pts.append([x, oy, z])
            poly = Poly3DCollection([np.array(face_pts)], facecolors=color["face"],
                                    edgecolors=color["edge"], linewidths=0.5,
                                    alpha=color["alpha"], shade=True)
            self.ax.add_collection3d(poly)

        self._draw_dimension(radius, -30, 0, radius+w, -30, 0, f"{w:.0f}")
        self._draw_dimension(radius+w+20, 0, 0, radius+w+20, h, 0, f"{h:.0f}")
        self._draw_dimension(0, -30, 0, radius, -30, 0, f"R{radius:.0f}")
        self._center_view(radius*2 + w, h, radius*2 + w)

    def _draw_round_elbow(self, product):
        """Круглий відвід — частина тора."""
        angle = getattr(product, "angle", 90)
        radius = getattr(product, "radius", 150)
        d = product.width
        r = d / 2

        self._add_torus_segment(radius, r, angle, color_key="elbow")

        self._draw_dimension(radius, -r-40, 0, radius+d, -r-40, 0, f"Ø{d:.0f}")
        self._draw_dimension(0, -r-40, 0, radius, -r-40, 0, f"R{radius:.0f}")
        self._center_view(radius*2 + d, d, radius*2 + d)

    def _draw_transition(self, product):
        w1, h1 = product.width, product.height
        ew = getattr(product, "end_width", w1 * 0.7)
        eh = getattr(product, "end_height", h1 * 0.7)
        l = product.length
        color = COLORS["transition"]

        verts = np.array([
            [0, 0, 0], [w1, 0, 0], [w1, h1, 0], [0, h1, 0],
            [(w1-ew)/2, (h1-eh)/2, l], [(w1+ew)/2, (h1-eh)/2, l],
            [(w1+ew)/2, (h1+eh)/2, l], [(w1-ew)/2, (h1+eh)/2, l],
        ])
        faces = [
            [verts[0], verts[1], verts[2], verts[3]],
            [verts[4], verts[5], verts[6], verts[7]],
            [verts[0], verts[1], verts[5], verts[4]],
            [verts[2], verts[3], verts[7], verts[6]],
            [verts[1], verts[2], verts[6], verts[5]],
            [verts[0], verts[3], verts[7], verts[4]],
        ]
        poly3d = Poly3DCollection(faces, facecolors=color["face"], edgecolors=color["edge"],
                                   linewidths=0.6, alpha=color["alpha"], shade=True)
        self.ax.add_collection3d(poly3d)
        self._draw_dimension(0, -30, 0, w1, -30, 0, f"{w1:.0f}")
        self._draw_dimension(w1+20, 0, 0, w1+20, h1, 0, f"{h1:.0f}")
        self._draw_dimension(0, h1+30, 0, 0, h1+30, l, f"{l:.0f}")
        self._center_view(max(w1, ew), max(h1, eh), l)

    def _draw_round_transition(self, product):
        """Круглий перехід — усечений конус."""
        d1 = product.width
        d2 = getattr(product, "end_diameter", d1 * 0.7)
        l = product.length
        r1, r2 = d1 / 2, d2 / 2

        self._add_cone_frustum(r1, r2, l, color_key="transition")
        self._draw_dimension(-r1, -r1-40, 0, r1, -r1-40, 0, f"Ø{d1:.0f}")
        self._draw_dimension(-r2, -r2-40, l, r2, -r2-40, l, f"Ø{d2:.0f}")
        self._draw_dimension(r1+30, 0, 0, r1+30, 0, l, f"{l:.0f}")
        self._center_view(max(d1, d2), max(d1, d2), l)

    def _draw_tee(self, product):
        """Реалістичний прямокутний трійник з косими гранями переходу."""
        w, h, l = product.width, product.height, product.length
        bw = getattr(product, "branch_width", w * 0.7)
        bh = getattr(product, "branch_height", h * 0.7)
        bl = getattr(product, "branch_length", l * 0.5)
        color = COLORS["tee"]

        self._add_box(w, h, l, color_key="tee")

        offset_x = (w - bw) / 2
        offset_y = (h - bh) / 2

        v0 = [0, 0, l]
        v1 = [w, 0, l]
        v2 = [w, h, l]
        v3 = [0, h, l]
        v4 = [offset_x, offset_y, l + bl]
        v5 = [offset_x + bw, offset_y, l + bl]
        v6 = [offset_x + bw, offset_y + bh, l + bl]
        v7 = [offset_x, offset_y + bh, l + bl]

        verts = np.array([v0, v1, v2, v3, v4, v5, v6, v7])
        faces = [
            [verts[0], verts[1], verts[5], verts[4]],
            [verts[2], verts[3], verts[7], verts[6]],
            [verts[1], verts[2], verts[6], verts[5]],
            [verts[0], verts[3], verts[7], verts[4]],
            [verts[4], verts[5], verts[6], verts[7]],
        ]
        poly3d = Poly3DCollection(faces, facecolors=color["face"], edgecolors=color["edge"],
                                   linewidths=0.5, alpha=color["alpha"], shade=True)
        self.ax.add_collection3d(poly3d)

        self._draw_dimension(0, -50, 0, w, -50, 0, f"{w:.0f}")
        self._draw_dimension(w+30, 0, 0, w+30, h, 0, f"{h:.0f}")
        self._draw_dimension(0, h+30, 0, 0, h+30, l, f"{l:.0f}")
        self._draw_dimension(offset_x, -50, l+bl, offset_x+bw, -50, l+bl, f"{bw:.0f}")
        self._draw_dimension(w+30, offset_y, l+bl, w+30, offset_y+bh, l+bl, f"{bh:.0f}")
        self._center_view(max(w, bw), max(h, bh), l + bl)

    def _draw_round_tee(self, product):
        """Круглий трійник — основний циліндр + гілка-циліндр."""
        d, l = product.width, product.length
        r = d / 2
        bd = getattr(product, "branch_diameter", d * 0.7)
        br = bd / 2
        bl = getattr(product, "branch_length", l * 0.5)

        self._add_cylinder(r, l, axis="z", color_key="tee")
        self._add_cylinder(br, bl, cx=0, cy=-br, cz=l, axis="y", color_key="tee")

        self._draw_dimension(-r, -r-40, 0, r, -r-40, 0, f"Ø{d:.0f}")
        self._draw_dimension(r+30, 0, 0, r+30, 0, l, f"{l:.0f}")
        self._draw_dimension(-br, -br-bl, l, br, -br-bl, l, f"Ø{bd:.0f}")
        self._center_view(max(d, bd), max(d, bl), l + bl)

    def _draw_flexible(self, product):
        w, h, l = product.width, product.height, product.length
        color = COLORS["flexible"]
        segments = 8
        seg_len = l / segments
        for i in range(segments):
            z = i * seg_len
            scale = 1.0 if i % 2 == 0 else 0.92
            self._add_box(w*scale, h*scale, seg_len, cx=(w-w*scale)/2, cy=(h-h*scale)/2, cz=z, color_key="flexible")
        self._draw_dimension(0, -30, 0, w, -30, 0, f"{w:.0f}")
        self._draw_dimension(w+20, 0, 0, w+20, h, 0, f"{h:.0f}")
        self._draw_dimension(0, h+30, 0, 0, h+30, l, f"{l:.0f}")
        self._center_view(w, h, l)

    def _draw_generic_box(self, product):
        w, h, l = product.width, product.height, product.length
        self._add_box(w, h, l, color_key="generic")
        self._draw_dimension(0, -30, 0, w, -30, 0, f"{w:.0f}")
        self._draw_dimension(w+20, 0, 0, w+20, h, 0, f"{h:.0f}")
        self._draw_dimension(0, h+30, 0, 0, h+30, l, f"{l:.0f}")
        self._center_view(w, h, l)

    # ─────────────────────────────────────────────────────────
    #  РОЗМІРИ ТА КАМЕРА
    # ─────────────────────────────────────────────────────────

    def _draw_dimension(self, x1, y1, z1, x2, y2, z2, text: str):
        self.ax.plot3D([x1, x2], [y1, y2], [z1, z2], color="#37474F", lw=1.0)
        mx, my, mz = (x1+x2)/2, (y1+y2)/2, (z1+z2)/2
        self.ax.text(mx, my, mz, text, color="#C62828", fontsize=8, fontweight="bold")

    def _center_view(self, w, h, l):
        max_dim = max(w, h, l, 1)
        pad = max_dim * 0.4
        self.ax.set_xlim(-pad, max_dim + pad)
        self.ax.set_ylim(-pad, max_dim + pad)
        self.ax.set_zlim(-pad, max_dim + pad)
