"""Професійний 2D CAD-редактор на tkinter Canvas.

Вигляд як у CAMduct / AutoCAD — без matplotlib.
"""

import math
import os
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Optional, Callable, Tuple, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

import numpy as np
from PIL import Image

try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

from ventilation_company.project3d.project_model import VentProject
from ventilation_company.project3d.vent_system import DuctSegment, Point3D, DuctShape, DuctType
from ventilation_company.project3d.arch_context import Wall, Opening, Floor, WallMaterial


class DrawingTool(Enum):
    SELECT = "select"
    WALL = "wall"
    OPENING = "opening"
    DUCT = "duct"
    RECTANGLE = "rectangle"
    MEASURE = "measure"


@dataclass
class BackgroundImage:
    filepath: str
    pil_image: Any  # PIL Image
    offset_x: float = 0.0
    offset_y: float = 0.0
    scale: float = 1.0
    opacity: float = 0.45
    visible: bool = True


class CADCanvas(tk.Canvas):
    """Професійний CAD-Canvas з навігацією та рендерингом."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#f5f5f5", highlightthickness=0, **kwargs)
        self._scale = 1.0  # пікселів на мм
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._dragging = False
        self._drag_start = None

        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Button-4>", self._on_wheel)
        self.bind("<Button-5>", self._on_wheel)
        self.bind("<Motion>", self._on_move)

    def world_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        """Перетворення світових координат (мм) в екранні (пікселі)."""
        sx = (x - self._offset_x) * self._scale + self.winfo_width() / 2
        sy = self.winfo_height() / 2 - (y - self._offset_y) * self._scale
        return (sx, sy)

    def screen_to_world(self, sx: float, sy: float) -> Tuple[float, float]:
        """Перетворення екранних координат в світові (мм)."""
        x = (sx - self.winfo_width() / 2) / self._scale + self._offset_x
        y = (self.winfo_height() / 2 - sy) / self._scale + self._offset_y
        return (x, y)

    def _on_press(self, event):
        self._dragging = True
        self._drag_start = (event.x, event.y)

    def _on_drag(self, event):
        if self._dragging and self._drag_start:
            dx = event.x - self._drag_start[0]
            dy = event.y - self._drag_start[1]
            self._offset_x -= dx / self._scale
            self._offset_y += dy / self._scale
            self._drag_start = (event.x, event.y)
            self.event_generate("<<CanvasPan>>")

    def _on_release(self, event):
        self._dragging = False
        self._drag_start = None

    def _on_wheel(self, event):
        factor = 1.15 if event.delta > 0 else 0.85
        if event.num == 4:
            factor = 1.15
        elif event.num == 5:
            factor = 0.85

        mx, my = event.x, event.y
        wx, wy = self.screen_to_world(mx, my)

        self._scale *= factor
        self._scale = max(0.001, min(10.0, self._scale))

        # Зберегти позицію миші
        self._offset_x = wx - (mx - self.winfo_width()/2) / self._scale
        self._offset_y = wy - (self.winfo_height()/2 - my) / self._scale

        self.event_generate("<<CanvasZoom>>")

    def _on_move(self, event):
        wx, wy = self.screen_to_world(event.x, event.y)
        self.event_generate("<<CanvasMove>>", x=wx, y=wy)


class Project2DPreview:
    """Професійний 2D CAD-редактор."""

    COLORS = {
        "wall_fill": "#b8b8b8",
        "wall_edge": "#3a3a3a",
        "wall_selected": "#ff4444",
        "opening": "#c0392b",
        "opening_fill": "#f5b7b1",
        "duct_supply": "#2980b9",
        "duct_exhaust": "#27ae60",
        "duct_smoke": "#e67e22",
        "duct_selected": "#f39c12",
        "equipment": "#8e44ad",
        "grid_major": "#d0d0d0",
        "grid_minor": "#e8e8e8",
        "axis": "#e74c3c",
        "temp_line": "#7f8c8d",
        "snap_point": "#2ecc71",
        "measure": "#9b59b6",
        "text": "#2c3e50",
        "bg": "#f5f5f5",
    }

    def __init__(self, parent: tk.Widget, on_select_callback: Optional[Callable] = None):
        self.parent = parent
        self.on_select_callback = on_select_callback
        self.project: Optional[VentProject] = None
        self.current_floor: Optional[Floor] = None

        self.current_tool = DrawingTool.SELECT
        self.drawing_state = None
        self.p1: Optional[Tuple[float, float]] = None

        self.selected_object = None
        self.selected_type = None

        self.snap_grid = 50.0
        self.ortho_mode = False

        self.background: Optional[BackgroundImage] = None
        self.bg_photo = None

        self.layers = {
            "background": tk.BooleanVar(value=True),
            "walls": tk.BooleanVar(value=True),
            "openings": tk.BooleanVar(value=True),
            "ducts": tk.BooleanVar(value=True),
            "grid": tk.BooleanVar(value=True),
            "dimensions": tk.BooleanVar(value=True),
        }

        self._build_ui()

    def _build_ui(self):
        # Тулбар
        toolbar = ttk.Frame(self.parent, padding=2)
        toolbar.pack(fill=tk.X)

        # Інструменти
        tf = ttk.LabelFrame(toolbar, text="Інструменти", padding=2)
        tf.pack(side=tk.LEFT, padx=2)
        self.tool_btns = {}
        tools = [
            ("select", "🖱️ Вибір", DrawingTool.SELECT),
            ("wall", "━━ Стіна", DrawingTool.WALL),
            ("opening", "☐ Отвір", DrawingTool.OPENING),
            ("duct", "══ Повітр.", DrawingTool.DUCT),
            ("rectangle", "⬛ Прямок.", DrawingTool.RECTANGLE),
            ("measure", "📏 Вимір.", DrawingTool.MEASURE),
        ]
        for key, label, tool in tools:
            btn = tk.Button(tf, text=label, width=10, relief=tk.RAISED, font=("Arial", 9),
                          command=lambda t=tool, k=key: self._set_tool(t, k))
            btn.pack(side=tk.LEFT, padx=1)
            self.tool_btns[key] = btn
        self._hl_tool("select")

        # Налаштування
        sf = ttk.LabelFrame(toolbar, text="Налаштування", padding=2)
        sf.pack(side=tk.LEFT, padx=(8,2))
        tk.Label(sf, text="Snap:", font=("Arial", 9)).pack(side=tk.LEFT)
        self.snap_var = tk.DoubleVar(value=50)
        ttk.Combobox(sf, textvariable=self.snap_var, values=[10,25,50,100,250,500], 
                    state="readonly", width=5).pack(side=tk.LEFT, padx=2)
        self.snap_var.trace_add("write", lambda *a: setattr(self, "snap_grid", self.snap_var.get()))
        self.ortho_var = tk.BooleanVar(value=False)
        tk.Checkbutton(sf, text="Ortho", variable=self.ortho_var, font=("Arial", 9),
                      command=lambda: setattr(self, "ortho_mode", self.ortho_var.get())).pack(side=tk.LEFT, padx=5)
        tk.Button(sf, text="🗑️ Видалити", command=self._delete_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(sf, text="↩️ Скасувати", command=self._undo).pack(side=tk.LEFT, padx=2)

        # Фон
        bf = ttk.LabelFrame(toolbar, text="Фон", padding=2)
        bf.pack(side=tk.LEFT, padx=(8,2))
        tk.Button(bf, text="📁 Завантажити", command=self._load_bg).pack(side=tk.LEFT, padx=1)
        tk.Button(bf, text="📐 Калібрувати", command=self._calibrate).pack(side=tk.LEFT, padx=1)
        tk.Button(bf, text="❌ Прибрати", command=self._remove_bg).pack(side=tk.LEFT, padx=1)

        # Шари
        lf = ttk.LabelFrame(toolbar, text="Шари", padding=2)
        lf.pack(side=tk.LEFT, padx=(8,2))
        for key, label in [("walls","Стіни"),("openings","Отвори"),("ducts","Повітр."),
                           ("grid","Сітка"),("dimensions","Розміри")]:
            tk.Checkbutton(lf, text=label, variable=self.layers[key], font=("Arial", 8),
                          command=self.refresh).pack(side=tk.LEFT, padx=2)

        # Навігація
        nf = ttk.Frame(toolbar)
        nf.pack(side=tk.RIGHT, padx=5)
        tk.Button(nf, text="🔍+", command=self._zoom_in, width=4).pack(side=tk.LEFT, padx=1)
        tk.Button(nf, text="🔍-", command=self._zoom_out, width=4).pack(side=tk.LEFT, padx=1)
        tk.Button(nf, text="🎯 Центр", command=self._center).pack(side=tk.LEFT, padx=1)
        tk.Button(nf, text="🖨️ Друк", command=self._print).pack(side=tk.LEFT, padx=1)

        # Координати
        self.coord_lbl = tk.Label(toolbar, text="X: 0  Y: 0", font=("Consolas", 9), fg="#666")
        self.coord_lbl.pack(side=tk.RIGHT, padx=10)

        # Canvas
        self.canvas = CADCanvas(self.parent, width=1200, height=800)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.canvas.bind("<<CanvasPan>>", lambda e: self.refresh())
        self.canvas.bind("<<CanvasZoom>>", lambda e: self.refresh())
        self.canvas.bind("<<CanvasMove>>", self._on_canvas_move)
        self.canvas.bind("<Button-1>", self._on_click, add="+")
        self.canvas.bind("<Motion>", self._on_hover, add="+")

        # Підказка
        self.hint = tk.Label(self.parent, text="🖱️ Вибір: клік — вибрати | ━━ Стіна: 2 кліки | Колесо — масштаб | ЛКМ+drag — панорама",
                            fg="#666", font=("Arial", 8), anchor=tk.W)
        self.hint.pack(fill=tk.X, padx=5)

        # Масштаб за замовчуванням
        self.canvas._scale = 0.1  # 0.1 px/mm = 1:10 при 96 DPI

    def _set_tool(self, tool, key):
        self.current_tool = tool
        self.drawing_state = None
        self.p1 = None
        self._hl_tool(key)
        hints = {
            "select": "🖱️ Вибір: клік — вибрати об'єкт",
            "wall": "━━ Стіна: клік 1 — початок, клік 2 — кінець",
            "opening": "☐ Отвір: клік — центр",
            "duct": "══ Повітр.: клік 1 — початок, клік 2 — кінець",
            "rectangle": "⬛ Прямок.: клік 1 — кут, клік 2 — протилежний",
            "measure": "📏 Вимір.: клік 1 — початок, клік 2 — кінець",
        }
        self.hint.config(text=hints.get(key, ""))

    def _hl_tool(self, active_key):
        for key, btn in self.tool_btns.items():
            if key == active_key:
                btn.config(relief=tk.SUNKEN, bg="#d0e8ff")
            else:
                btn.config(relief=tk.RAISED, bg="SystemButtonFace")

    def _snap(self, x, y):
        g = self.snap_grid
        return (round(x/g)*g, round(y/g)*g)

    def _ortho(self, x1, y1, x2, y2):
        if not self.ortho_mode:
            return (x2, y2)
        dx, dy = abs(x2-x1), abs(y2-y1)
        return (x2, y1) if dx > dy else (x1, y2)

    def _on_canvas_move(self, event):
        self.coord_lbl.config(text=f"X: {event.x:.0f}  Y: {event.y:.0f}")

    def _on_click(self, event):
        wx, wy = self.canvas.screen_to_world(event.x, event.y)
        wx, wy = self._snap(wx, wy)

        if self.current_tool == DrawingTool.SELECT:
            self._do_select(wx, wy)
        elif self.current_tool == DrawingTool.WALL:
            self._do_wall(wx, wy)
        elif self.current_tool == DrawingTool.OPENING:
            self._do_opening(wx, wy)
        elif self.current_tool == DrawingTool.DUCT:
            self._do_duct(wx, wy)
        elif self.current_tool == DrawingTool.RECTANGLE:
            self._do_rect(wx, wy)
        elif self.current_tool == DrawingTool.MEASURE:
            self._do_measure(wx, wy)

    def _on_hover(self, event):
        if self.drawing_state == "p1" and self.p1:
            wx, wy = self.canvas.screen_to_world(event.x, event.y)
            wx, wy = self._snap(wx, wy)
            x2, y2 = self._ortho(self.p1[0], self.p1[1], wx, wy)
            self.refresh()
            self._draw_temp(self.p1[0], self.p1[1], x2, y2)

    def _draw_temp(self, x1, y1, x2, y2):
        c = self.COLORS["temp_line"]
        if self.current_tool == DrawingTool.WALL:
            c = self.COLORS["wall_edge"]
        elif self.current_tool == DrawingTool.DUCT:
            c = self.COLORS["duct_supply"]
        sx1, sy1 = self.canvas.world_to_screen(x1, y1)
        sx2, sy2 = self.canvas.world_to_screen(x2, y2)
        self.canvas.create_line(sx1, sy1, sx2, sy2, fill=c, width=2, dash=(8,4), tags="temp")
        self.canvas.create_oval(sx2-4, sy2-4, sx2+4, sy2+4, fill=self.COLORS["snap_point"], outline="", tags="temp")
        dist = math.hypot(x2-x1, y2-y1)
        self.canvas.create_text((sx1+sx2)/2, (sy1+sy2)/2-15, text=f"{dist:.0f} мм", 
                               fill=c, font=("Arial", 8), tags="temp")

    def _do_select(self, x, y):
        obj, otype = self._find_nearest(x, y)
        self.selected_object = obj
        self.selected_type = otype
        if obj and self.on_select_callback:
            self._show_props(obj, otype)
        elif self.on_select_callback:
            self.on_select_callback(None, "", "")
        self.refresh()

    def _do_wall(self, x, y):
        if self.drawing_state is None:
            self.p1 = (x, y)
            self.drawing_state = "p1"
        else:
            x2, y2 = self._ortho(self.p1[0], self.p1[1], x, y)
            self._make_wall(self.p1[0], self.p1[1], x2, y2)
            self.drawing_state = None
            self.p1 = None
            self.refresh()

    def _do_opening(self, x, y):
        self._make_opening(x, y)

    def _do_duct(self, x, y):
        if self.drawing_state is None:
            self.p1 = (x, y)
            self.drawing_state = "p1"
        else:
            x2, y2 = self._ortho(self.p1[0], self.p1[1], x, y)
            self._make_duct(self.p1[0], self.p1[1], x2, y2)
            self.drawing_state = None
            self.p1 = None
            self.refresh()

    def _do_rect(self, x, y):
        if self.drawing_state is None:
            self.p1 = (x, y)
            self.drawing_state = "p1"
        else:
            self._make_rect(self.p1[0], self.p1[1], x, y)
            self.drawing_state = None
            self.p1 = None
            self.refresh()

    def _do_measure(self, x, y):
        if self.drawing_state is None:
            self.p1 = (x, y)
            self.drawing_state = "p1"
        else:
            dist = math.hypot(x-self.p1[0], y-self.p1[1])
            messagebox.showinfo("Вимірювання", f"Відстань: {dist:.1f} мм = {dist/1000:.2f} м")
            self.drawing_state = None
            self.p1 = None
            self.refresh()

    def _get_floor(self):
        if not self.project or not self.project.arch_context:
            return None
        name = self.current_floor.name if self.current_floor else "Поверх 1"
        for f in self.project.arch_context.floors:
            if f.name == name:
                return f
        if not self.project.arch_context.floors:
            f = Floor(name="Поверх 1", level=3000, height=3000)
            self.project.arch_context.floors.append(f)
            return f
        return self.project.arch_context.floors[0]

    def _make_wall(self, x1, y1, x2, y2):
        floor = self._get_floor()
        if not floor:
            return
        t = simpledialog.askinteger("Товщина", "Товщина стіни (мм):", initialvalue=200, minvalue=50, maxvalue=1000)
        if t is None:
            return
        h = simpledialog.askinteger("Висота", "Висота стіни (мм):", initialvalue=int(floor.height), minvalue=1000, maxvalue=10000)
        if h is None:
            h = floor.height
        floor.walls.append(Wall(
            name=f"Стіна {len(floor.walls)+1}",
            start=Point3D(x1, y1, floor.floor_z),
            end=Point3D(x2, y2, floor.floor_z),
            height=float(h), thickness=float(t)
        ))
        self.refresh()
        self._push_undo()

    def _make_opening(self, x, y):
        floor = self._get_floor()
        if not floor:
            return
        w = simpledialog.askinteger("Ширина", "Ширина отвору (мм):", initialvalue=400, minvalue=50, maxvalue=5000)
        if w is None:
            return
        h = simpledialog.askinteger("Висота", "Висота отвору (мм):", initialvalue=400, minvalue=50, maxvalue=5000)
        if h is None:
            return
        floor.openings.append(Opening(
            name=f"Отвір {len(floor.openings)+1}",
            position=Point3D(x, y, floor.floor_z+1000),
            width=float(w), height=float(h)
        ))
        self.refresh()
        self._push_undo()

    def _make_duct(self, x1, y1, x2, y2):
        if not self.project:
            return
        w = simpledialog.askinteger("Ширина", "Ширина каналу (мм):", initialvalue=300, minvalue=50, maxvalue=2000)
        if w is None:
            return
        h = simpledialog.askinteger("Висота", "Висота каналу (мм):", initialvalue=200, minvalue=50, maxvalue=2000)
        if h is None:
            return

        if not self.project.ventilation_systems:
            from ventilation_company.project3d.vent_system import VentilationSystem
            s = VentilationSystem(name="Система 1", system_type="припливно-витяжна")
            self.project.ventilation_systems.append(s)
        else:
            s = self.project.ventilation_systems[0]

        if not s.trunks:
            from ventilation_company.project3d.vent_system import VentilationTrunk
            t = VentilationTrunk(name="Траса 1")
            s.trunks.append(t)
        else:
            t = s.trunks[0]

        floor = self._get_floor()
        z = floor.floor_z + 2500 if floor else 2500

        t.segments.append(DuctSegment(
            start=Point3D(x1, y1, z), end=Point3D(x2, y2, z),
            width=float(w), height=float(h),
            shape=DuctShape.RECT, duct_type=DuctType.SUPPLY
        ))
        self.refresh()
        self._push_undo()

    def _make_rect(self, x1, y1, x2, y2):
        floor = self._get_floor()
        if not floor:
            return
        t = simpledialog.askinteger("Товщина", "Товщина стін (мм):", initialvalue=200, minvalue=50, maxvalue=1000)
        if t is None:
            return
        h = floor.height
        for wx1, wy1, wx2, wy2 in [(x1,y1,x2,y1),(x2,y1,x2,y2),(x2,y2,x1,y2),(x1,y2,x1,y1)]:
            floor.walls.append(Wall(
                name=f"Стіна {len(floor.walls)+1}",
                start=Point3D(wx1, wy1, floor.floor_z),
                end=Point3D(wx2, wy2, floor.floor_z),
                height=h, thickness=float(t)
            ))
        self.refresh()
        self._push_undo()

    def _find_nearest(self, x, y, thr=300):
        floor = self._get_floor()
        if not floor:
            return None, None
        bd, bo, bt = thr, None, None
        if self.layers["walls"].get():
            for w in floor.walls:
                d = self._seg_dist(x, y, w.start.x, w.start.y, w.end.x, w.end.y)
                if d < bd:
                    bd, bo, bt = d, w, "wall"
        if self.layers["openings"].get():
            for o in floor.openings:
                d = math.hypot(x-o.position.x, y-o.position.y)
                if d < bd:
                    bd, bo, bt = d, o, "opening"
        if self.layers["ducts"].get():
            for s in (self.project.ventilation_systems if self.project else []):
                for t in s.trunks:
                    for seg in t.segments:
                        d = self._seg_dist(x, y, seg.start.x, seg.start.y, seg.end.x, seg.end.y)
                        if d < bd:
                            bd, bo, bt = d, seg, "segment"
        return bo, bt

    def _seg_dist(self, px, py, x1, y1, x2, y2):
        dx, dy = x2-x1, y2-y1
        l2 = dx*dx + dy*dy
        if l2 == 0:
            return math.hypot(px-x1, py-y1)
        t = max(0, min(1, ((px-x1)*dx + (py-y1)*dy) / l2))
        return math.hypot(px - (x1+t*dx), py - (y1+t*dy))

    def _show_props(self, obj, otype):
        lines = []
        if otype == "wall":
            lines = [f"Тип: Стіна", f"Назва: {obj.name}", f"Довжина: {obj.length:.1f} мм",
                    f"Товщина: {obj.thickness:.0f} мм", f"Висота: {obj.height:.0f} мм",
                    f"Початок: ({obj.start.x:.0f}, {obj.start.y:.0f})", f"Кінець: ({obj.end.x:.0f}, {obj.end.y:.0f})"]
        elif otype == "opening":
            lines = [f"Тип: Отвір", f"Назва: {obj.name}", f"Ширина: {obj.width:.0f} мм",
                    f"Висота: {obj.height:.0f} мм", f"Позиція: ({obj.position.x:.0f}, {obj.position.y:.0f})"]
        elif otype == "segment":
            lines = [f"Тип: Сегмент", f"Ширина: {obj.width:.0f} мм", f"Висота: {obj.height:.0f} мм",
                    f"Довжина: {obj.length:.0f} мм", f"Початок: ({obj.start.x:.0f}, {obj.start.y:.0f})",
                    f"Кінець: ({obj.end.x:.0f}, {obj.end.y:.0f})"]
        if self.on_select_callback:
            self.on_select_callback(obj, otype, "\n".join(lines))

    def _delete_selected(self):
        if not self.selected_object or not self.selected_type:
            messagebox.showwarning("Увага", "Спочатку виберіть об'єкт")
            return
        floor = self._get_floor()
        if not floor:
            return
        if self.selected_type == "wall" and self.selected_object in floor.walls:
            floor.walls.remove(self.selected_object)
        elif self.selected_type == "opening" and self.selected_object in floor.openings:
            floor.openings.remove(self.selected_object)
        elif self.selected_type == "segment":
            for s in (self.project.ventilation_systems if self.project else []):
                for t in s.trunks:
                    if self.selected_object in t.segments:
                        t.segments.remove(self.selected_object)
                        break
        self.selected_object = None
        self.selected_type = None
        if self.on_select_callback:
            self.on_select_callback(None, "", "")
        self.refresh()
        self._push_undo()

    def _push_undo(self):
        if not self.project:
            return
        if not hasattr(self, "_undo_stack"):
            self._undo_stack = []
        import json
        try:
            state = json.dumps(self.project.to_dict())
            self._undo_stack.append(state)
            if len(self._undo_stack) > 20:
                self._undo_stack.pop(0)
        except Exception:
            pass

    def _undo(self):
        if not hasattr(self, "_undo_stack") or not self._undo_stack:
            messagebox.showinfo("Скасувати", "Немає дій для скасування")
            return
        import json
        try:
            state = self._undo_stack.pop()
            data = json.loads(state)
            self.project = VentProject.from_dict(data)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося скасувати: {e}")

    def _load_bg(self):
        filetypes = [("Зображення", "*.png *.jpg *.jpeg *.bmp *.tiff"), ("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg"),
                     ("PDF", "*.pdf"), ("Всі файли", "*.*")]
        fp = filedialog.askopenfilename(title="Архітектурний план", filetypes=filetypes)
        if not fp:
            return
        try:
            ext = os.path.splitext(fp)[1].lower()
            if ext == ".pdf":
                if not HAS_PYMUPDF:
                    messagebox.showwarning("PyMuPDF", "pip install PyMuPDF")
                    return
                doc = fitz.open(fp)
                pix = doc[0].get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                doc.close()
            else:
                img = Image.open(fp).convert("RGB")
            mx = 3000
            if max(img.size) > mx:
                r = mx / max(img.size)
                img = img.resize((int(img.width*r), int(img.height*r)), Image.LANCZOS)
            self.background = BackgroundImage(filepath=fp, pil_image=img, scale=1.0, opacity=0.45, visible=True)
            self.layers["background"].set(True)
            self.refresh()
            messagebox.showinfo("Успіх", f"Фон завантажено:\n{os.path.basename(fp)}")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))

    def _remove_bg(self):
        self.background = None
        self.bg_photo = None
        self.refresh()

    def _calibrate(self):
        if not self.background:
            messagebox.showwarning("Увага", "Спочатку завантажте фон")
            return
        d = tk.Toplevel(self.parent)
        d.title("Калібрування")
        d.geometry("380x200")
        d.transient(self.parent)
        d.grab_set()
        tk.Label(d, text="Відома відстань (мм):", font=("Arial", 10)).pack(pady=5)
        dv = tk.DoubleVar(value=6000)
        tk.Spinbox(d, from_=100, to=50000, textvariable=dv, width=12).pack()
        tk.Label(d, text="Кількість пікселів:").pack(pady=5)
        pv = tk.DoubleVar(value=1000)
        tk.Spinbox(d, from_=1, to=10000, textvariable=pv, width=12).pack()
        def apply():
            self.background.scale = dv.get() / pv.get()
            d.destroy()
            self.refresh()
        tk.Button(d, text="✅ Застосувати", command=apply).pack(pady=10)

    def refresh(self):
        self.canvas.delete("all")
        floor = self._get_floor()

        # Фон
        if self.background and self.background.visible and self.layers["background"].get():
            self._draw_bg()

        # Сітка
        if self.layers["grid"].get():
            self._draw_grid()

        # Стіни
        if self.layers["walls"].get() and floor:
            for w in floor.walls:
                sel = (self.selected_object == w and self.selected_type == "wall")
                self._draw_wall(w, sel)

        # Отвори
        if self.layers["openings"].get() and floor:
            for o in floor.openings:
                sel = (self.selected_object == o and self.selected_type == "opening")
                self._draw_opening(o, sel)

        # Повітропроводи
        if self.layers["ducts"].get() and self.project:
            for sys in self.project.ventilation_systems:
                c = self._sys_color(sys.system_type)
                for t in sys.trunks:
                    for seg in t.segments:
                        sel = (self.selected_object == seg and self.selected_type == "segment")
                        self._draw_duct(seg, c, sel)

        # Масштабна лінійка
        self._draw_scalebar()

    def _draw_bg(self):
        bg = self.background
        w, h = bg.pil_image.size
        wmm, hmm = w * bg.scale, h * bg.scale
        sx1, sy1 = self.canvas.world_to_screen(bg.offset_x, bg.offset_y + hmm)
        sx2, sy2 = self.canvas.world_to_screen(bg.offset_x + wmm, bg.offset_y)
        # Конвертуємо PIL в PhotoImage
        from PIL import ImageTk
        # Масштабуємо під екран
        sw, sh = int(abs(sx2-sx1)), int(abs(sy2-sy1))
        if sw > 1 and sh > 1:
            resized = bg.pil_image.resize((sw, sh), Image.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(resized)
            self.canvas.create_image(min(sx1,sx2), min(sy1,sy2), anchor=tk.NW, image=self.bg_photo, tags="bg")

    def _draw_grid(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 10 or h < 10:
            return
        x1, y1 = self.canvas.screen_to_world(0, 0)
        x2, y2 = self.canvas.screen_to_world(w, h)

        # Дрібна сітка
        step = 100
        start_x = math.floor(min(x1,x2) / step) * step
        end_x = math.ceil(max(x1,x2) / step) * step
        start_y = math.floor(min(y1,y2) / step) * step
        end_y = math.ceil(max(y1,y2) / step) * step

        for x in range(int(start_x), int(end_x)+1, step):
            sx, _ = self.canvas.world_to_screen(x, 0)
            self.canvas.create_line(sx, 0, sx, h, fill=self.COLORS["grid_minor"], width=0.5, tags="grid")
        for y in range(int(start_y), int(end_y)+1, step):
            _, sy = self.canvas.world_to_screen(0, y)
            self.canvas.create_line(0, sy, w, sy, fill=self.COLORS["grid_minor"], width=0.5, tags="grid")

        # Основна сітка + підписи
        major = 1000
        start_x = math.floor(min(x1,x2) / major) * major
        end_x = math.ceil(max(x1,x2) / major) * major
        start_y = math.floor(min(y1,y2) / major) * major
        end_y = math.ceil(max(y1,y2) / major) * major

        for x in range(int(start_x), int(end_x)+1, major):
            sx, _ = self.canvas.world_to_screen(x, 0)
            self.canvas.create_line(sx, 0, sx, h, fill=self.COLORS["grid_major"], width=1, tags="grid")
            self.canvas.create_text(sx+3, h-10, text=f"{x:.0f}", anchor=tk.W, font=("Arial", 7), fill="#999", tags="grid")
        for y in range(int(start_y), int(end_y)+1, major):
            _, sy = self.canvas.world_to_screen(0, y)
            self.canvas.create_line(0, sy, w, sy, fill=self.COLORS["grid_major"], width=1, tags="grid")
            self.canvas.create_text(5, sy-3, text=f"{y:.0f}", anchor=tk.SW, font=("Arial", 7), fill="#999", tags="grid")

    def _draw_wall(self, wall, selected=False):
        dx = wall.end.x - wall.start.x
        dy = wall.end.y - wall.start.y
        L = math.sqrt(dx*dx + dy*dy)
        if L == 0:
            return
        nx, ny = dx/L, dy/L
        px, py = -ny, nx
        hw = wall.thickness / 2

        pts = [
            (wall.start.x + px*hw, wall.start.y + py*hw),
            (wall.start.x - px*hw, wall.start.y - py*hw),
            (wall.end.x - px*hw, wall.end.y - py*hw),
            (wall.end.x + px*hw, wall.end.y + py*hw),
        ]

        scr = [self.canvas.world_to_screen(p[0], p[1]) for p in pts]
        flat = [c for p in scr for c in p]

        if selected:
            self.canvas.create_polygon(flat, fill=self.COLORS["wall_selected"], outline="#cc0000", width=2, tags="wall")
            self.canvas.create_oval(scr[0][0]-5, scr[0][1]-5, scr[0][0]+5, scr[0][1]+5, fill="green", tags="wall")
            self.canvas.create_oval(scr[2][0]-5, scr[2][1]-5, scr[2][0]+5, scr[2][1]+5, fill="red", tags="wall")
        else:
            fc = self.COLORS["wall_fill"] if wall.is_load_bearing else "#d0d0d0"
            self.canvas.create_polygon(flat, fill=fc, outline=self.COLORS["wall_edge"], width=1.5, tags="wall")

    def _draw_opening(self, op, selected=False):
        cx, cy = op.position.x, op.position.y
        w, h = op.width/2, op.height/2
        pts = [(cx-w, cy-h), (cx+w, cy-h), (cx+w, cy+h), (cx-w, cy+h)]
        scr = [self.canvas.world_to_screen(p[0], p[1]) for p in pts]
        flat = [c for p in scr for c in p]
        c = self.COLORS["wall_selected"] if selected else self.COLORS["opening"]
        self.canvas.create_polygon(flat, fill=self.COLORS["opening_fill"], outline=c, width=2, tags="opening")
        # Діагоналі
        self.canvas.create_line(scr[0][0], scr[0][1], scr[2][0], scr[2][1], fill=c, width=1, dash=(4,2), tags="opening")
        self.canvas.create_line(scr[1][0], scr[1][1], scr[3][0], scr[3][1], fill=c, width=1, dash=(4,2), tags="opening")
        self.canvas.create_text((scr[0][0]+scr[2][0])/2, scr[0][1]-10, text=op.name, 
                               fill=c, font=("Arial", 7, "bold"), tags="opening")

    def _draw_duct(self, seg, color, selected=False):
        x1, y1 = seg.start.x, seg.start.y
        x2, y2 = seg.end.x, seg.end.y
        dx, dy = x2-x1, y2-y1
        L = math.hypot(dx, dy)
        if L < 0.1:
            return
        nx, ny = -dy/L, dx/L
        hh = seg.height / 2

        # 4 точки контуру каналу
        ox, oy = nx*hh, ny*hh
        p1 = (x1+ox, y1+oy)
        p2 = (x2+ox, y2+oy)
        p3 = (x2-ox, y2-oy)
        p4 = (x1-ox, y1-oy)

        s1 = self.canvas.world_to_screen(*p1)
        s2 = self.canvas.world_to_screen(*p2)
        s3 = self.canvas.world_to_screen(*p3)
        s4 = self.canvas.world_to_screen(*p4)

        lw = 3.5 if selected else 2.0
        c = self.COLORS["duct_selected"] if selected else color

        # Контур
        self.canvas.create_line(s1[0], s1[1], s2[0], s2[1], fill=c, width=lw, tags="duct")
        self.canvas.create_line(s4[0], s4[1], s3[0], s3[1], fill=c, width=lw, tags="duct")
        self.canvas.create_line(s1[0], s1[1], s4[0], s4[1], fill=c, width=lw, tags="duct")
        self.canvas.create_line(s2[0], s2[1], s3[0], s3[1], fill=c, width=lw, tags="duct")

        # Заливка
        if not selected:
            self.canvas.create_polygon(s1[0], s1[1], s2[0], s2[1], s3[0], s3[1], s4[0], s4[1],
                                      fill=c, stipple="gray50", tags="duct")

        if selected:
            self.canvas.create_oval(s1[0]-5, s1[1]-5, s1[0]+5, s1[1]+5, fill="green", tags="duct")
            self.canvas.create_oval(s2[0]-5, s2[1]-5, s2[0]+5, s2[1]+5, fill="red", tags="duct")

        # Виноска
        if self.layers["dimensions"].get() and seg.length > 500 and not selected:
            cx, cy = (x1+x2)/2, (y1+y2)/2
            off_x, off_y = nx*(hh+120), ny*(hh+120)
            sc = self.canvas.world_to_screen(cx+off_x, cy+off_y)
            self.canvas.create_text(sc[0], sc[1], text=f"{seg.width:.0f}×{seg.height:.0f}",
                                   fill=color, font=("Arial", 8, "bold"), tags="duct")

    def _draw_scalebar(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        x = w * 0.02
        y = h * 0.97
        bar_px = 100
        self.canvas.create_line(x, y, x+bar_px, y, fill="#333", width=3)
        self.canvas.create_line(x, y-3, x, y+3, fill="#333", width=2)
        self.canvas.create_line(x+bar_px, y-3, x+bar_px, y+3, fill="#333", width=2)
        mm = bar_px / self.canvas._scale
        label = f"{mm:.0f} мм" if mm < 1000 else f"{mm/1000:.1f} м"
        self.canvas.create_text(x+bar_px/2, y-10, text=label, fill="#333", font=("Arial", 8, "bold"))

    def _sys_color(self, st):
        s = st.lower()
        if "витяж" in s or "exhaust" in s:
            return self.COLORS["duct_exhaust"]
        if "дим" in s or "smoke" in s:
            return self.COLORS["duct_smoke"]
        return self.COLORS["duct_supply"]

    def set_project(self, project):
        self.project = project
        self.current_floor = project.arch_context.floors[0] if project and project.arch_context.floors else None
        self.refresh()

    def set_floor(self, name):
        if self.project and self.project.arch_context:
            for f in self.project.arch_context.floors:
                if f.name == name:
                    self.current_floor = f
                    self.refresh()
                    return

    def _zoom_in(self):
        self.canvas._scale *= 1.2
        self.refresh()

    def _zoom_out(self):
        self.canvas._scale /= 1.2
        self.refresh()

    def _center(self):
        floor = self._get_floor()
        if floor and floor.walls:
            xs = [p for w in floor.walls for p in [w.start.x, w.end.x]]
            ys = [p for w in floor.walls for p in [w.start.y, w.end.y]]
            self.canvas._offset_x = (min(xs) + max(xs)) / 2
            self.canvas._offset_y = (min(ys) + max(ys)) / 2
        else:
            self.canvas._offset_x = 5000
            self.canvas._offset_y = 5000
        self.refresh()

    def _print(self):
        try:
            from PIL import ImageGrab
            x = self.canvas.winfo_rootx()
            y = self.canvas.winfo_rooty()
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            img = ImageGrab.grab(bbox=(x, y, x+w, y+h))
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                img.save(tmp.name, dpi=(300,300))
                os.startfile(tmp.name)
            messagebox.showinfo("Друк", "Зображення збережено та відкрито.")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))

    def export_image(self, filepath):
        try:
            from PIL import ImageGrab
            x = self.canvas.winfo_rootx()
            y = self.canvas.winfo_rooty()
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            ImageGrab.grab(bbox=(x, y, x+w, y+h)).save(filepath)
        except Exception as e:
            messagebox.showerror("Помилка", str(e))
