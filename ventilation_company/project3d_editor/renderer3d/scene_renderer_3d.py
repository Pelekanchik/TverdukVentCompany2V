"""3D-рендерер сцени на базі matplotlib — ЕТАП 8."""

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Optional, Any

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False

from ventilation_company.project3d_editor.scene.scene_graph import SceneGraph
from ventilation_company.project3d_editor.scene.entities.wall import WallEntity
from ventilation_company.project3d_editor.scene.entities.duct import DuctSegmentEntity
from ventilation_company.project3d_editor.scene.entities.fitting import DuctFittingEntity
from ventilation_company.project3d_editor.scene.entities.equipment import EquipmentEntity


class Scene3DRenderer:
    """3D-перегляд сцени через matplotlib (без FreeCAD)."""

    def __init__(self, parent: tk.Widget, scene: SceneGraph):
        self.parent = parent
        self.scene = scene
        self.figure: Optional[Figure] = None
        self.canvas: Optional[FigureCanvasTkAgg] = None
        self.ax: Optional[Any] = None
        self._view_angle = (30, -60)  # elev, azim

        if not MATPLOTLIB_OK:
            self._build_error_ui()
        else:
            self._build_ui()

    def _build_error_ui(self):
        frame = ttk.Frame(self.parent)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="⚠️ Matplotlib не встановлено",
                  foreground="red", font=("Arial", 12, "bold")).pack(pady=20)
        ttk.Label(frame, text="Виконайте: pip install matplotlib",
                  foreground="#666").pack()

    def _build_ui(self):
        # Панель керування
        ctrl = ttk.Frame(self.parent)
        ctrl.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(ctrl, text="⬆️ Зверху",
                   command=lambda: self._set_view(90, -90)).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="➡️ Збоку",
                   command=lambda: self._set_view(0, -90)).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="↗️ Ізометрія",
                   command=lambda: self._set_view(30, -60)).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="🔄 Оновити",
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

    def refresh(self):
        """Перендерити 3D-сцену."""
        if not MATPLOTLIB_OK or self.figure is None:
            return

        self.figure.clear()
        self.ax = self.figure.add_subplot(111, projection="3d")
        self.ax.set_facecolor("#f5f5f5")

        entities = self.scene.get_visible_entities()
        if not entities:
            self.ax.text(0, 0, 0, "Сцена порожня",
                         fontsize=14, ha="center", color="#999")
            self.ax.set_xlim(-100, 100)
            self.ax.set_ylim(-100, 100)
            self.ax.set_zlim(-100, 100)
            self.canvas.draw()
            return

        all_x, all_y, all_z = [], [], []

        for entity in entities:
            mesh = self._build_mesh(entity)
            if mesh is None:
                continue
            verts, edges, faces, color, name = mesh
            if not verts:
                continue

            xs = [v[0] for v in verts]
            ys = [v[1] for v in verts]
            zs = [v[2] for v in verts]
            all_x.extend(xs)
            all_y.extend(ys)
            all_z.extend(zs)

            # Грані
            if faces:
                face_verts = []
                for face in faces:
                    fv = [verts[i] for i in face if i < len(verts)]
                    if len(fv) >= 3:
                        face_verts.append(fv)
                if face_verts:
                    poly3d = Poly3DCollection(
                        face_verts, alpha=0.45,
                        facecolor=color, edgecolor=color, linewidth=0.5
                    )
                    self.ax.add_collection3d(poly3d)

            # Ребра (каркас)
            for e in edges:
                if e[0] < len(verts) and e[1] < len(verts):
                    v1, v2 = verts[e[0]], verts[e[1]]
                    self.ax.plot3D(
                        [v1[0], v2[0]], [v1[1], v2[1]], [v1[2], v2[2]],
                        color=color, linewidth=1.0, alpha=0.8
                    )

            # Підпис
            if verts:
                cx = sum(v[0] for v in verts) / len(verts)
                cy = sum(v[1] for v in verts) / len(verts)
                cz = max(v[2] for v in verts) + 50
                short = name[:25] if len(name) <= 25 else name[:22] + "..."
                self.ax.text(cx, cy, cz, short, fontsize=7, color="#333",
                             ha="center", va="bottom")

        # Автомасштаб
        if all_x and all_y and all_z:
            margin = max(
                max(all_x) - min(all_x),
                max(all_y) - min(all_y),
                max(all_z) - min(all_z)
            ) * 0.1 + 100
            self.ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
            self.ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
            self.ax.set_zlim(min(all_z) - margin, max(all_z) + margin)

        self.ax.set_xlabel("X, мм")
        self.ax.set_ylabel("Y, мм")
        self.ax.set_zlabel("Z, мм")
        self.ax.set_title("3D-вигляд вентиляційної системи", fontsize=11, pad=10)

        elev, azim = self._view_angle
        self.ax.view_init(elev=elev, azim=azim)
        self.ax.set_box_aspect([1, 1, 1])

        self.canvas.draw()

    def _build_mesh(self, entity):
        """Побудувати меш для сутності. Повертає (verts, edges, faces, color, name)."""
        if isinstance(entity, WallEntity):
            return self._build_wall_mesh(entity)
        elif isinstance(entity, DuctSegmentEntity):
            return self._build_duct_mesh(entity)
        elif isinstance(entity, DuctFittingEntity):
            return self._build_fitting_mesh(entity)
        elif isinstance(entity, EquipmentEntity):
            return self._build_equipment_mesh(entity)
        return None

    def _build_wall_mesh(self, e: WallEntity):
        import math
        dx = e.end.x - e.start.x
        dy = e.end.y - e.start.y
        length = math.hypot(dx, dy)
        if length == 0:
            return None
        nx, ny = dx / length, dy / length
        px, py = -ny * e.thickness / 2, nx * e.thickness / 2

        b0 = (e.start.x + px, e.start.y + py, 0)
        b1 = (e.start.x - px, e.start.y - py, 0)
        b2 = (e.end.x   - px, e.end.y   - py, 0)
        b3 = (e.end.x   + px, e.end.y   + py, 0)
        t0 = (e.start.x + px, e.start.y + py, e.height)
        t1 = (e.start.x - px, e.start.y - py, e.height)
        t2 = (e.end.x   - px, e.end.y   - py, e.height)
        t3 = (e.end.x   + px, e.end.y   + py, e.height)

        verts = [b0, b1, b2, b3, t0, t1, t2, t3]
        edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
        faces = [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
        color = "#555555" if e.is_load_bearing else "#888888"
        return verts, edges, faces, color, e.name

    def _build_duct_mesh(self, e: DuctSegmentEntity):
        import math
        z = e.z_start
        dx = e.end.x - e.start.x
        dy = e.end.y - e.start.y
        seg_len = math.hypot(dx, dy)

        if e.is_round:
            r = e.width / 2
            segments = 16
            verts = []
            edges = []
            faces = []
            base0 = 0
            for i in range(segments):
                angle = 2 * math.pi * i / segments
                verts.append((
                    e.start.x + r * math.cos(angle),
                    e.start.y + r * math.sin(angle), z
                ))
            for i in range(segments):
                edges.append((base0 + i, base0 + (i + 1) % segments))
            base1 = segments
            for i in range(segments):
                angle = 2 * math.pi * i / segments
                verts.append((
                    e.end.x + r * math.cos(angle),
                    e.end.y + r * math.sin(angle), z
                ))
            for i in range(segments):
                edges.append((base1 + i, base1 + (i + 1) % segments))
                edges.append((base0 + i, base1 + i))
                jj = (i + 1) % segments
                faces.append((base0 + i, base0 + jj, base1 + jj, base1 + i))
            color = e.get_system_color()
            return verts, edges, faces, color, e.name
        else:
            w, h = e.width, e.height
            if seg_len == 0:
                return None
            nx, ny = dx / seg_len, dy / seg_len
            px, py = -ny * w / 2, nx * h / 2

            b0 = (e.start.x + px, e.start.y + py, z)
            b1 = (e.start.x - px, e.start.y - py, z)
            b2 = (e.end.x   - px, e.end.y   - py, z)
            b3 = (e.end.x   + px, e.end.y   + py, z)
            t0 = (e.start.x + px, e.start.y + py, z + h)
            t1 = (e.start.x - px, e.start.y - py, z + h)
            t2 = (e.end.x   - px, e.end.y   - py, z + h)
            t3 = (e.end.x   + px, e.end.y   + py, z + h)

            verts = [b0, b1, b2, b3, t0, t1, t2, t3]
            edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
            faces = [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
            color = e.get_system_color()
            return verts, edges, faces, color, e.name

    def _build_fitting_mesh(self, e: DuctFittingEntity):
        size = max(e.width_in, e.height_in) / 2
        z = e.z_position
        cx, cy = e.position.x, e.position.y

        verts = [
            (cx - size, cy, z),
            (cx, cy - size, z),
            (cx + size, cy, z),
            (cx, cy + size, z),
            (cx - size, cy, z + size),
            (cx, cy - size, z + size),
            (cx + size, cy, z + size),
            (cx, cy + size, z + size),
        ]
        edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
        faces = [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
        color = e.get_system_color()
        return verts, edges, faces, color, e.name

    def _build_equipment_mesh(self, e: EquipmentEntity):
        import math
        z = e.z_position
        cx, cy = e.position.x, e.position.y
        w, h = e.width, e.height
        d = e.depth

        rad = math.radians(e.rotation)
        cos_r, sin_r = math.cos(rad), math.sin(rad)

        local = [(-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)]
        rb = [(cx + lx * cos_r - ly * sin_r,
               cy + lx * sin_r + ly * cos_r, z) for lx, ly in local]
        rt = [(cx + lx * cos_r - ly * sin_r,
               cy + lx * sin_r + ly * cos_r, z + d) for lx, ly in local]

        verts = rb + rt
        edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
        faces = [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
        color = "#cc8800"
        return verts, edges, faces, color, e.name
