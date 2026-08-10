"""Вбудований 3D-перегляд виробів через matplotlib.
Не потребує встановленого FreeCAD — працює автономно.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Optional, Tuple

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    from mpl_toolkits.mplot3d import Axes3D
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False

from ventilation_company.freecad_geometry import VentGeometry, ProductLayout, MeshData


class FreeCADPreview:
    """3D preview panel using matplotlib — works without FreeCAD."""

    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.figure: Optional[Figure] = None
        self.canvas: Optional[FigureCanvasTkAgg] = None
        self.ax: Optional[Any] = None
        self._meshes: List[MeshData] = []
        self._show_labels = True
        self._show_axes = True
        self._view_angle = (30, -60)  # elev, azim
        self._wireframe_only = False
        self._spacing = 50.0

        if not MATPLOTLIB_OK:
            self._build_error_ui()
        else:
            self._build_ui()

    def _build_error_ui(self):
        frame = ttk.Frame(self.parent)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            frame,
            text="⚠️ Matplotlib не встановлено",
            foreground="red",
            font=("Arial", 12, "bold"),
        ).pack(pady=20)
        ttk.Label(
            frame,
            text="Виконайте: pip install matplotlib",
            foreground="#666",
        ).pack()

    def _build_ui(self):
        """Build the preview UI with controls and 3D canvas."""
        # Controls
        ctrl = ttk.Frame(self.parent)
        ctrl.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(ctrl, text="Відстань:").pack(side=tk.LEFT)
        self.spacing_var = tk.DoubleVar(value=self._spacing)
        spin = ttk.Spinbox(ctrl, from_=0, to=500, increment=10,
                           textvariable=self.spacing_var, width=6)
        spin.pack(side=tk.LEFT, padx=2)
        spin.bind("<Return>", lambda e: self.refresh())

        ttk.Button(ctrl, text="🔄 Оновити", command=self.refresh).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="⬆️ Зверху", command=lambda: self._set_view(90, -90)).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="➡️ Збоку", command=lambda: self._set_view(0, -90)).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="↗️ Ізометрія", command=lambda: self._set_view(30, -60)).pack(side=tk.LEFT, padx=2)

        self.wire_var = tk.BooleanVar(value=self._wireframe_only)
        ttk.Checkbutton(ctrl, text="Каркас", variable=self.wire_var,
                        command=self.refresh).pack(side=tk.LEFT, padx=5)

        self.labels_var = tk.BooleanVar(value=self._show_labels)
        ttk.Checkbutton(ctrl, text="Підписи", variable=self.labels_var,
                        command=self.refresh).pack(side=tk.LEFT, padx=5)

        # 3D Canvas
        self.figure = Figure(figsize=(8, 6), dpi=100, facecolor="#f5f5f5")
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Toolbar
        toolbar = NavigationToolbar2Tk(self.canvas, self.parent)
        toolbar.update()

    def _set_view(self, elev: float, azim: float):
        self._view_angle = (elev, azim)
        self.refresh()

    def set_products(self, products: List[Any]):
        """Set products to display (accepts dicts or StandardProduct objects)."""
        self._products = []
        for p in products:
            if hasattr(p, "to_dict"):
                self._products.append(p.to_dict())
            elif isinstance(p, dict):
                self._products.append(p)
            else:
                self._products.append(dict(p))
        self.refresh()

    def refresh(self):
        """Redraw the 3D preview."""
        if not MATPLOTLIB_OK or self.figure is None:
            return

        self.figure.clear()
        self.ax = self.figure.add_subplot(111, projection="3d")
        self.ax.set_facecolor("#f5f5f5")

        if not hasattr(self, "_products") or not self._products:
            self.ax.text(0, 0, 0, "Немає виробів для відображення",
                         fontsize=14, ha="center", color="#999")
            self.ax.set_xlim(-100, 100)
            self.ax.set_ylim(-100, 100)
            self.ax.set_zlim(-100, 100)
            self.canvas.draw()
            return

        spacing = self.spacing_var.get()
        layout = ProductLayout(spacing=spacing, axis="z")
        meshes = layout.build_all(self._products)

        wireframe = self.wire_var.get()
        show_labels = self.labels_var.get()

        all_x, all_y, all_z = [], [], []

        for mesh in meshes:
            verts = mesh.vertices
            if not verts:
                continue

            xs = [v[0] for v in verts]
            ys = [v[1] for v in verts]
            zs = [v[2] for v in verts]
            all_x.extend(xs)
            all_y.extend(ys)
            all_z.extend(zs)

            color = mesh.color
            edges = mesh.edges

            if wireframe:
                # Draw wireframe edges
                for e in edges:
                    if e[0] < len(verts) and e[1] < len(verts):
                        v1, v2 = verts[e[0]], verts[e[1]]
                        self.ax.plot3D(
                            [v1[0], v2[0]], [v1[1], v2[1]], [v1[2], v2[2]],
                            color=color, linewidth=1.2, alpha=0.8
                        )
            else:
                # Draw faces as semi-transparent polygons
                if mesh.faces:
                    face_verts = []
                    for face in mesh.faces:
                        fv = [verts[i] for i in face if i < len(verts)]
                        if len(fv) >= 3:
                            face_verts.append(fv)
                    if face_verts:
                        poly3d = Poly3DCollection(face_verts, alpha=0.4,
                                                  facecolor=color,
                                                  edgecolor=color,
                                                  linewidth=0.5)
                        self.ax.add_collection3d(poly3d)
                else:
                    # Fallback to wireframe if no faces
                    for e in edges:
                        if e[0] < len(verts) and e[1] < len(verts):
                            v1, v2 = verts[e[0]], verts[e[1]]
                            self.ax.plot3D(
                                [v1[0], v2[0]], [v1[1], v2[1]], [v1[2], v2[2]],
                                color=color, linewidth=1.0, alpha=0.6
                            )

            # Product label at center
            if show_labels and verts:
                cx = sum(v[0] for v in verts) / len(verts)
                cy = sum(v[1] for v in verts) / len(verts)
                cz = max(v[2] for v in verts) + 20
                short_name = mesh.name[:20] if len(mesh.name) <= 20 else mesh.name[:17] + "..."
                self.ax.text(cx, cy, cz, short_name, fontsize=7, color="#333",
                             ha="center", va="bottom")

        # Auto-scale
        if all_x and all_y and all_z:
            margin = max(max(all_x) - min(all_x), max(all_y) - min(all_y),
                         max(all_z) - min(all_z)) * 0.1 + 50
            self.ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
            self.ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
            self.ax.set_zlim(min(all_z) - margin, max(all_z) + margin)

        self.ax.set_xlabel("X, мм")
        self.ax.set_ylabel("Y, мм")
        self.ax.set_zlabel("Z, мм")
        self.ax.set_title("3D-модель вентиляційної системи", fontsize=11, pad=10)

        elev, azim = self._view_angle
        self.ax.view_init(elev=elev, azim=azim)

        # Equal aspect ratio approximation
        self.ax.set_box_aspect([1, 1, 1])

        self.canvas.draw()

    def export_image(self, filepath: str):
        """Export current view as PNG."""
        if self.figure:
            self.figure.savefig(filepath, dpi=150, bbox_inches="tight",
                                facecolor=self.figure.get_facecolor())


def show_preview_dialog(parent: tk.Tk, products: List[Any]):
    """Show a modal preview dialog."""
    dialog = tk.Toplevel(parent)
    dialog.title("🔍 3D Перегляд — VentCompany")
    dialog.geometry("900x700")
    dialog.minsize(700, 500)

    preview = FreeCADPreview(dialog)
    preview.set_products(products)

    ttk.Button(dialog, text="Закрити", command=dialog.destroy).pack(pady=5)
