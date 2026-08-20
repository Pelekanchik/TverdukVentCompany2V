"""Просте 3D прев'ю виробів за допомогою matplotlib.

Не вимагає FreeCAD — працює через matplotlib 3D (mplot3d).
"""

import tkinter as tk
from tkinter import ttk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import numpy as np


class ProductPreview3D:
    """Віджет 3D прев'ю виробу для tkinter."""

    def __init__(self, parent: tk.Widget, width: int = 400, height: int = 350):
        self.parent = parent
        self.width = width
        self.height = height

        self.fig = Figure(figsize=(width / 100, height / 100), dpi=100)
        self.ax = self.fig.add_subplot(111, projection="3d")
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
        self.ax.set_box_aspect([1, 1, 1])

    def draw(self):
        self.canvas.draw()

    def show_product(self, product):
        """Показати 3D модель виробу."""
        self.clear()
        ptype = product.product_type.lower()

        if "повітропровід" in ptype and "прямокутн" in ptype:
            self._draw_rect_duct(product)
        elif "повітропровід" in ptype and "кругл" in ptype:
            self._draw_round_duct(product)
        elif "фланець" in ptype:
            self._draw_flange(product)
        elif "заглушка" in ptype:
            self._draw_cap(product)
        elif "відвід" in ptype or "коліно" in ptype:
            self._draw_elbow(product)
        elif "перехід" in ptype:
            self._draw_transition(product)
        elif "трійник" in ptype:
            self._draw_tee(product)
        else:
            self._draw_generic_box(product)

        self.ax.set_xlabel("X, мм")
        self.ax.set_ylabel("Y, мм")
        self.ax.set_zlabel("Z, мм")
        self.draw()

    def _draw_rect_duct(self, product):
        w, h, l = product.width, product.height, product.length
        # 8 вершин прямокутної труби
        verts = np.array([
            [0, 0, 0], [w, 0, 0], [w, h, 0], [0, h, 0],
            [0, 0, l], [w, 0, l], [w, h, l], [0, h, l],
        ])
        # Ребра
        edges = [
            [0,1], [1,2], [2,3], [3,0],
            [4,5], [5,6], [6,7], [7,4],
            [0,4], [1,5], [2,6], [3,7],
        ]
        for e in edges:
            self.ax.plot3D(*zip(verts[e[0]], verts[e[1]]), color="#2196F3", lw=1.5)

        # Розміри
        self._draw_dimension(0, -50, 0, w, -50, 0, f"{w:.0f}")
        self._draw_dimension(w+30, 0, 0, w+30, h, 0, f"{h:.0f}")
        self._draw_dimension(0, h+30, 0, 0, h+30, l, f"{l:.0f}")

        # Центруємо
        self._center_view(w, h, l)

    def _draw_round_duct(self, product):
        d, l = product.width, product.length
        r = d / 2
        # Циліндр
        theta = np.linspace(0, 2*np.pi, 30)
        z = np.linspace(0, l, 10)
        theta, z = np.meshgrid(theta, z)
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        self.ax.plot_surface(x, y, z, alpha=0.3, color="#2196F3", edgecolor="#1565C0", lw=0.3)

        # Розміри
        self._draw_dimension(-r, -r-40, 0, r, -r-40, 0, f"Ø{d:.0f}")
        self._draw_dimension(r+30, 0, 0, r+30, 0, l, f"{l:.0f}")

        self._center_view(d, d, l)

    def _draw_flange(self, product):
        w, h = product.width, product.height
        p = getattr(product, "profile", 30)
        # Прямокутний фланець
        outer_w = w + 2 * p
        outer_h = h + 2 * p
        verts = np.array([
            [0, 0, 0], [outer_w, 0, 0], [outer_w, outer_h, 0], [0, outer_h, 0],
        ])
        edges = [[0,1], [1,2], [2,3], [3,0]]
        for e in edges:
            self.ax.plot3D(*zip(verts[e[0]], verts[e[1]]), color="#4CAF50", lw=2)
        # Отвір
        hole_x = (outer_w - w) / 2
        hole_y = (outer_h - h) / 2
        hole = np.array([
            [hole_x, hole_y, 0], [hole_x+w, hole_y, 0],
            [hole_x+w, hole_y+h, 0], [hole_x, hole_y+h, 0],
        ])
        for e in edges:
            self.ax.plot3D(*zip(hole[e[0]], hole[e[1]]), color="#F44336", lw=1.5, ls="--")

        self._draw_dimension(0, -30, 0, outer_w, -30, 0, f"{outer_w:.0f}")
        self._draw_dimension(outer_w+20, 0, 0, outer_w+20, outer_h, 0, f"{outer_h:.0f}")
        self._center_view(outer_w, outer_h, 50)

    def _draw_cap(self, product):
        w, h = product.width, product.height
        verts = np.array([
            [0, 0, 0], [w, 0, 0], [w, h, 0], [0, h, 0],
            [0, 0, 30], [w, 0, 30], [w, h, 30], [0, h, 30],
        ])
        edges = [
            [0,1], [1,2], [2,3], [3,0],
            [4,5], [5,6], [6,7], [7,4],
            [0,4], [1,5], [2,6], [3,7],
        ]
        for e in edges:
            self.ax.plot3D(*zip(verts[e[0]], verts[e[1]]), color="#FF9800", lw=1.5)
        self._center_view(w, h, 100)

    def _draw_elbow(self, product):
        # Спрощене відображення коліна — дуга
        angle = getattr(product, "angle", 90)
        r = getattr(product, "radius", 150)
        w, h = product.width, product.height
        theta = np.radians(np.linspace(0, angle, 20))
        x = r * np.cos(theta)
        y = np.zeros_like(theta)
        z = r * np.sin(theta)
        self.ax.plot3D(x, y, z, color="#9C27B0", lw=3)
        self.ax.plot3D(x, y+h, z, color="#9C27B0", lw=3)
        self._center_view(r*2, h, r*2)

    def _draw_transition(self, product):
        w1, h1 = product.width, product.height
        ew = getattr(product, "end_width", w1 * 0.7)
        eh = getattr(product, "end_height", h1 * 0.7)
        l = product.length
        # Перехідна форма
        verts = np.array([
            [0, 0, 0], [w1, 0, 0], [w1, h1, 0], [0, h1, 0],
            [(w1-ew)/2, (h1-eh)/2, l], [(w1+ew)/2, (h1-eh)/2, l],
            [(w1+ew)/2, (h1+eh)/2, l], [(w1-ew)/2, (h1+eh)/2, l],
        ])
        edges = [
            [0,1], [1,2], [2,3], [3,0],
            [4,5], [5,6], [6,7], [7,4],
            [0,4], [1,5], [2,6], [3,7],
        ]
        for e in edges:
            self.ax.plot3D(*zip(verts[e[0]], verts[e[1]]), color="#00BCD4", lw=1.5)
        self._center_view(w1, h1, l)

    def _draw_tee(self, product):
        # Спрощено — основна труба + гілка
        w, h, l = product.width, product.height, product.length
        self._draw_rect_duct(product)
        # Гілка (коротша)
        bw = getattr(product, "branch_width", w * 0.7)
        bh = getattr(product, "branch_height", h * 0.7)
        bl = getattr(product, "branch_length", l * 0.5)
        verts = np.array([
            [0, 0, l], [bw, 0, l], [bw, bh, l], [0, bh, l],
            [0, 0, l+bl], [bw, 0, l+bl], [bw, bh, l+bl], [0, bh, l+bl],
        ])
        edges = [
            [0,1], [1,2], [2,3], [3,0],
            [4,5], [5,6], [6,7], [7,4],
            [0,4], [1,5], [2,6], [3,7],
        ]
        for e in edges:
            self.ax.plot3D(*zip(verts[e[0]], verts[e[1]]), color="#E91E63", lw=1.5)

    def _draw_generic_box(self, product):
        w, h, l = product.width, product.height, product.length
        verts = np.array([
            [0, 0, 0], [w, 0, 0], [w, h, 0], [0, h, 0],
            [0, 0, l], [w, 0, l], [w, h, l], [0, h, l],
        ])
        edges = [
            [0,1], [1,2], [2,3], [3,0],
            [4,5], [5,6], [6,7], [7,4],
            [0,4], [1,5], [2,6], [3,7],
        ]
        for e in edges:
            self.ax.plot3D(*zip(verts[e[0]], verts[e[1]]), color="#607D8B", lw=1.5)
        self._center_view(w, h, l)

    def _draw_dimension(self, x1, y1, z1, x2, y2, z2, text: str):
        """Намалювати лінію розміру з текстом."""
        self.ax.plot3D([x1, x2], [y1, y2], [z1, z2], color="#333", lw=0.8)
        mx, my, mz = (x1+x2)/2, (y1+y2)/2, (z1+z2)/2
        self.ax.text(mx, my, mz, text, color="#D32F2F", fontsize=8)

    def _center_view(self, w, h, l):
        """Центрувати камеру."""
        max_dim = max(w, h, l, 1)
        self.ax.set_xlim(-max_dim * 0.3, max_dim * 1.3)
        self.ax.set_ylim(-max_dim * 0.3, max_dim * 1.3)
        self.ax.set_zlim(-max_dim * 0.3, max_dim * 1.3)
