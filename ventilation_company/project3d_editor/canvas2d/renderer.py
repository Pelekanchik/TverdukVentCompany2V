"""2D-рендерер на tkinter Canvas — як у AutoCAD."""

from __future__ import annotations
import math
import tkinter as tk
from typing import List, Optional, Callable, Dict, Any

from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.core.bounds import Bounds
from ventilation_company.project3d_editor.scene.entity import Entity, EntityType
from ventilation_company.project3d_editor.scene.scene_graph import SceneGraph
from ventilation_company.project3d_editor.canvas2d.viewport import Viewport
from ventilation_company.project3d_editor.canvas2d.grid import Grid, GridSettings

from ventilation_company.project3d_editor.scene.entities.line import LineEntity
from ventilation_company.project3d_editor.scene.entities.wall import WallEntity
from ventilation_company.project3d_editor.scene.entities.rect import RectEntity
from ventilation_company.project3d_editor.scene.entities.circle import CircleEntity
from ventilation_company.project3d_editor.scene.entities.duct import DuctSegmentEntity
from ventilation_company.project3d_editor.scene.entities.fitting import DuctFittingEntity
from ventilation_company.project3d_editor.scene.entities.equipment import EquipmentEntity


class Canvas2DRenderer:
    """Професійний 2D-рендерер на tkinter Canvas."""

    COLORS = {
        "background": "#f5f5f5",
        "selection": "#00aaff",
        "selection_fill": "#00aaff",
        "hover": "#ff6600",
        "wall_load": "#555555",
        "wall_partition": "#888888",
        "duct_supply": "#0066cc",
        "duct_exhaust": "#009900",
        "duct_smoke": "#cc6600",
        "fitting": "#990099",
        "equipment": "#cc8800",
        "wall_load": "#555555",
        "wall_partition": "#888888",
        "opening": "#ff4444",
        "text": "#333333",
    }

    def __init__(self, parent: tk.Widget, scene: SceneGraph,
                 width: int = 1000, height: int = 700):
        self.parent = parent
        self.scene = scene
        self.viewport = Viewport(width=width, height=height)
        self.grid = Grid(GridSettings())

        self.canvas = tk.Canvas(
            parent, width=width, height=height,
            bg=self.COLORS["background"],
            highlightthickness=1, highlightbackground="#cccccc",
            cursor="crosshair",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._bind_events()

        self._hovered_entity_id: Optional[str] = None
        self._preview_items: List[int] = []
        self._entity_item_map: Dict[str, int] = {}
        self._item_entity_map: Dict[int, str] = {}

        self.on_mouse_move: Optional[Callable[[Point2D], None]] = None
        self.on_click: Optional[Callable[[Point2D, int], None]] = None
        self.on_drag: Optional[Callable[[Point2D, Point2D], None]] = None
        self.on_drag_end: Optional[Callable[[Point2D, Point2D], None]] = None
        self.on_double_click: Optional[Callable[[Point2D], None]] = None

        self._drag_start: Optional[Point2D] = None
        self._is_panning = False
        self._last_mouse_pos: Optional[Point2D] = None

        self.render()

    def _bind_events(self) -> None:
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<Button-1>", self._on_left_down)
        self.canvas.bind("<B1-Motion>", self._on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_up)
        self.canvas.bind("<Button-2>", self._on_middle_down)
        self.canvas.bind("<B2-Motion>", self._on_middle_drag)
        self.canvas.bind("<ButtonRelease-2>", self._on_middle_up)
        self.canvas.bind("<Button-3>", self._on_right_down)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Configure>", self._on_resize)

    def _on_mouse_move(self, event) -> None:
        world = self.viewport.screen_to_world(Point2D(event.x, event.y))
        snapped = self.grid.snap(world, self._get_snap_points())
        self._last_mouse_pos = snapped
        hit = self.scene.hit_test(snapped, tolerance=5.0 / self.viewport.transform.scale)
        if hit and hit.id != self._hovered_entity_id:
            self._hovered_entity_id = hit.id
            self._update_hover()
        elif hit is None and self._hovered_entity_id:
            self._hovered_entity_id = None
            self._update_hover()
        if self.on_mouse_move:
            self.on_mouse_move(snapped)

    def _on_left_down(self, event) -> None:
        world = self.viewport.screen_to_world(Point2D(event.x, event.y))
        snapped = self.grid.snap(world, self._get_snap_points())
        self._drag_start = snapped
        if self.on_click:
            self.on_click(snapped, 1)

    def _on_left_drag(self, event) -> None:
        if self._drag_start is None:
            return
        world = self.viewport.screen_to_world(Point2D(event.x, event.y))
        snapped = self.grid.snap(world, self._get_snap_points())
        if self.on_drag:
            self.on_drag(self._drag_start, snapped)

    def _on_left_up(self, event) -> None:
        if self._drag_start is None:
            return
        world = self.viewport.screen_to_world(Point2D(event.x, event.y))
        snapped = self.grid.snap(world, self._get_snap_points())
        if self.on_drag_end:
            self.on_drag_end(self._drag_start, snapped)
        self._drag_start = None

    def _on_middle_down(self, event) -> None:
        self._is_panning = True
        self._last_mouse_pos = Point2D(event.x, event.y)
        self.canvas.config(cursor="fleur")

    def _on_middle_drag(self, event) -> None:
        if not self._is_panning or self._last_mouse_pos is None:
            return
        dx = event.x - self._last_mouse_pos.x
        dy = event.y - self._last_mouse_pos.y
        self.viewport.pan(dx, dy)
        self._last_mouse_pos = Point2D(event.x, event.y)
        self.render()

    def _on_middle_up(self, event) -> None:
        self._is_panning = False
        self.canvas.config(cursor="crosshair")

    def _on_right_down(self, event) -> None:
        world = self.viewport.screen_to_world(Point2D(event.x, event.y))
        snapped = self.grid.snap(world, self._get_snap_points())
        if self.on_click:
            self.on_click(snapped, 3)

    def _on_double_click(self, event) -> None:
        world = self.viewport.screen_to_world(Point2D(event.x, event.y))
        if self.on_double_click:
            self.on_double_click(world)

    def _on_mouse_wheel(self, event) -> None:
        factor = 1.1 if event.delta > 0 else 0.9
        self.viewport.zoom(factor, event.x, event.y)
        self.render()

    def _on_resize(self, event) -> None:
        self.viewport.resize(event.width, event.height)
        self.render()

    def _get_snap_points(self) -> List[Point2D]:
        pts = []
        for e in self.scene.get_visible_entities():
            pts.extend(e.get_points())
        return pts

    def render(self) -> None:
        self.canvas.delete("all")
        self._entity_item_map.clear()
        self._item_entity_map.clear()
        self._draw_grid()
        for entity in self.scene.get_visible_entities():
            item_id = self._draw_entity(entity)
            if item_id:
                self._entity_item_map[entity.id] = item_id
                self._item_entity_map[item_id] = entity.id
        self._draw_hover()
        self._draw_selection_box()

    def _draw_grid(self) -> None:
        view_bounds = self.viewport.get_visible_world_bounds()
        v_lines, h_lines = self.grid.get_grid_lines(view_bounds)
        for x, is_major in v_lines:
            sx, _ = self.viewport.world_to_screen(Point2D(x, 0)).to_int_tuple()
            color = self.grid.settings.major_color if is_major else self.grid.settings.minor_color
            width = 1 if is_major else 0.5
            self.canvas.create_line(sx, 0, sx, self.viewport.height, fill=color, width=width, tags=("grid",))
        for y, is_major in h_lines:
            _, sy = self.viewport.world_to_screen(Point2D(0, y)).to_int_tuple()
            color = self.grid.settings.major_color if is_major else self.grid.settings.minor_color
            width = 1 if is_major else 0.5
            self.canvas.create_line(0, sy, self.viewport.width, sy, fill=color, width=width, tags=("grid",))
        for axis, val, _ in self.grid.get_axis_lines(view_bounds):
            if axis == "y_axis":
                sx, _ = self.viewport.world_to_screen(Point2D(val, 0)).to_int_tuple()
                self.canvas.create_line(sx, 0, sx, self.viewport.height,
                                        fill=self.grid.settings.axis_color, width=2, tags=("grid", "axis"))
            else:
                _, sy = self.viewport.world_to_screen(Point2D(0, val)).to_int_tuple()
                self.canvas.create_line(0, sy, self.viewport.width, sy,
                                        fill=self.grid.settings.axis_color, width=2, tags=("grid", "axis"))

    def _draw_entity(self, entity: Entity) -> Optional[int]:
        if not entity.visible:
            return None
        color = entity.color
        if entity.selected:
            color = self.COLORS["selection"]
        elif entity.id == self._hovered_entity_id:
            color = self.COLORS["hover"]
        lw = max(1, entity.line_width * self.viewport.transform.scale)
        lw = min(lw, 5)
        if isinstance(entity, LineEntity):
            return self._draw_line(entity, color, lw)
        elif isinstance(entity, WallEntity):
            return self._draw_wall(entity, color, lw)
        elif isinstance(entity, RectEntity):
            return self._draw_rect(entity, color, lw)
        elif isinstance(entity, CircleEntity):
            return self._draw_circle(entity, color, lw)
        elif isinstance(entity, DuctSegmentEntity):
            return self._draw_duct(entity, color, lw)
        elif isinstance(entity, DuctFittingEntity):
            return self._draw_fitting(entity, color, lw)
        elif isinstance(entity, EquipmentEntity):
            return self._draw_equipment(entity, color, lw)
        return None

    def _to_screen(self, p: Point2D) -> tuple:
        sp = self.viewport.world_to_screen(p)
        return sp.to_int_tuple()

    def _draw_line(self, e: LineEntity, color: str, lw: float) -> int:
        x1, y1 = self._to_screen(e.start)
        x2, y2 = self._to_screen(e.end)
        item = self.canvas.create_line(x1, y1, x2, y2, fill=color, width=lw, tags=("entity", e.id))
        if e.selected:
            self._draw_grips([e.start, e.end])
        return item

    def _draw_wall(self, e: WallEntity, color: str, lw: float) -> int:
        poly = e.get_polygon()
        pts = [coord for p in poly for coord in self._to_screen(p)]
        fill = self.COLORS["wall_load"] if e.is_load_bearing else self.COLORS["wall_partition"]
        item = self.canvas.create_polygon(pts, fill=fill, outline=color, width=lw, tags=("entity", e.id))
        if e.selected:
            self._draw_grips([e.start, e.end])
        return item

    def _draw_rect(self, e: RectEntity, color: str, lw: float) -> int:
        corners = e.get_corners()
        pts = [coord for p in corners for coord in self._to_screen(p)]
        if e.filled:
            item = self.canvas.create_polygon(pts, fill=e.fill_color, outline=color,
                                              width=lw, stipple="gray50", tags=("entity", e.id))
        else:
            item = self.canvas.create_polygon(pts, fill="", outline=color, width=lw, tags=("entity", e.id))
        if e.selected:
            self._draw_grips(corners)
        return item

    def _draw_circle(self, e: CircleEntity, color: str, lw: float) -> int:
        cx, cy = self._to_screen(e.center)
        r = e.radius * self.viewport.transform.scale
        item = self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                       fill=e.fill_color if e.filled else "",
                                       outline=color, width=lw, tags=("entity", e.id))
        if e.selected:
            self._draw_grips([e.center])
        return item

    def _draw_duct(self, e: DuctSegmentEntity, color: str, lw: float) -> int:
        import math
        col = e.get_system_color() if not e.selected else color

        # Товщина труби в світі (половина профілю)
        half_profile = max(e.width, e.height) / 2

        # Вектор сегмента
        dx = e.end.x - e.start.x
        dy = e.end.y - e.start.y
        seg_len = math.hypot(dx, dy)

        if seg_len == 0:
            # Точка — малюємо коло
            cx, cy = self._to_screen(e.start)
            r = half_profile * self.viewport.transform.scale
            item = self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                           fill=col, outline="black", width=1, tags=("entity", e.id))
        else:
            # Перпендикулярний вектор (нормалізований)
            nx, ny = dx / seg_len, dy / seg_len
            px, py = -ny * half_profile, nx * half_profile

            # 4 точки прямокутника труби
            poly_pts = [
                e.start + Point2D(px, py),
                e.start - Point2D(px, py),
                e.end - Point2D(px, py),
                e.end + Point2D(px, py),
            ]
            screen_pts = [coord for p in poly_pts for coord in self._to_screen(p)]
            item = self.canvas.create_polygon(screen_pts, fill=col, outline="black",
                                              width=1, tags=("entity", e.id))

        # Підпис розмірів — перпендикулярно до лінії, зміщений вбік
        if e.length() > 300:
            mid = (e.start + e.end) / 2
            mx, my = self._to_screen(mid)
            label = f"{e.width:.0f}×{e.height:.0f}"

            # Зміщення перпендикулярно до лінії (в екранних координатах)
            if seg_len > 0:
                # Екранний перпендикуляр (Y інвертований)
                screen_dx = (e.end.x - e.start.x) * self.viewport.transform.scale
                screen_dy = -(e.end.y - e.start.y) * self.viewport.transform.scale  # інверсія Y
                screen_len = math.hypot(screen_dx, screen_dy)
                if screen_len > 0:
                    perp_x = -screen_dy / screen_len * 15  # зміщення 15px вбік
                    perp_y = screen_dx / screen_len * 15
                    mx += int(perp_x)
                    my += int(perp_y)

            self.canvas.create_text(mx, my, text=label, fill="white" if not e.selected else "#ffffff",
                                    font=("Arial", 8, "bold"), tags=("entity", e.id, "label"))

        if e.selected:
            self._draw_grips([e.start, e.end])
        return item

    def _draw_fitting(self, e: DuctFittingEntity, color: str, lw: float) -> int:
        cx, cy = self._to_screen(e.position)
        size = e.get_display_size() * self.viewport.transform.scale
        col = e.get_system_color() if not e.selected else color
        pts = [cx, cy - size, cx + size, cy, cx, cy + size, cx - size, cy]
        item = self.canvas.create_polygon(pts, fill=col, outline="black", width=lw, tags=("entity", e.id))
        self.canvas.create_text(cx, cy, text=e.fitting_type[:3], fill="white",
                                font=("Arial", 7, "bold"), tags=("entity", e.id, "label"))
        if e.selected:
            self._draw_grips([e.position])
        return item

    def _draw_equipment(self, e: EquipmentEntity, color: str, lw: float) -> int:
        corners = e.get_corners()
        pts = [coord for p in corners for coord in self._to_screen(p)]
        col = self.COLORS["equipment"] if not e.selected else color
        item = self.canvas.create_polygon(pts, fill=col, outline="black", width=lw, tags=("entity", e.id))
        cx, cy = self._to_screen(e.position)
        self.canvas.create_text(cx, cy, text=e.name or e.equipment_type,
                                fill="white", font=("Arial", 8, "bold"),
                                tags=("entity", e.id, "label"))
        if e.selected:
            self._draw_grips(corners)
        return item

    def _draw_grips(self, points: List[Point2D]) -> None:
        grip_size = 4
        for p in points:
            sx, sy = self._to_screen(p)
            self.canvas.create_rectangle(sx - grip_size, sy - grip_size,
                                         sx + grip_size, sy + grip_size,
                                         fill=self.COLORS["selection"], outline="white",
                                         width=1, tags=("grip",))


    def _update_hover(self) -> None:
        """Оновити hover-підсвічування (перерендер hover-шару)."""
        # Видаляємо старі hover-елементи
        self.canvas.delete("hover")
        self._draw_hover()
    def _draw_hover(self) -> None:
        if not self._hovered_entity_id:
            return
        entity = self.scene.get_entity(self._hovered_entity_id)
        if not entity:
            return
        bounds = entity.get_bounds()
        if bounds.is_empty():
            return
        tl = self._to_screen(Point2D(bounds.min_x, bounds.max_y))
        br = self._to_screen(Point2D(bounds.max_x, bounds.min_y))
        self.canvas.create_rectangle(tl[0] - 2, tl[1] - 2, br[0] + 2, br[1] + 2,
                                     outline=self.COLORS["hover"], width=1, dash=(4, 4),
                                     tags=("hover",))

    def _draw_selection_box(self) -> None:
        for e in self.scene.get_selection():
            bounds = e.get_bounds()
            if bounds.is_empty():
                continue
            tl = self._to_screen(Point2D(bounds.min_x, bounds.max_y))
            br = self._to_screen(Point2D(bounds.max_x, bounds.min_y))
            self.canvas.create_rectangle(tl[0] - 3, tl[1] - 3, br[0] + 3, br[1] + 3,
                                         outline=self.COLORS["selection"], width=1, dash=(6, 3),
                                         tags=("selection_box",))

    def clear_preview(self) -> None:
        for item in self._preview_items:
            self.canvas.delete(item)
        self._preview_items.clear()

    def preview_line(self, p1: Point2D, p2: Point2D, color: str = "#ff6600", width: int = 1) -> None:
        x1, y1 = self._to_screen(p1)
        x2, y2 = self._to_screen(p2)
        item = self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width, dash=(6, 4), tags=("preview",))
        self._preview_items.append(item)

    def preview_rect(self, p1: Point2D, p2: Point2D, color: str = "#ff6600") -> None:
        x1, y1 = self._to_screen(p1)
        x2, y2 = self._to_screen(p2)
        item = self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=1, dash=(6, 4), tags=("preview",))
        self._preview_items.append(item)

    def preview_circle(self, center: Point2D, radius: float, color: str = "#ff6600") -> None:
        cx, cy = self._to_screen(center)
        r = radius * self.viewport.transform.scale
        item = self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                       outline=color, width=1, dash=(6, 4), tags=("preview",))
        self._preview_items.append(item)

    def preview_polygon(self, points: List[Point2D], color: str = "#ff6600", fill: str = "") -> None:
        pts = [coord for p in points for coord in self._to_screen(p)]
        item = self.canvas.create_polygon(pts, outline=color, fill=fill,
                                          width=1, tags=("preview",))
        self._preview_items.append(item)

    def preview_text(self, pos: Point2D, text: str, color: str = "#ff6600") -> None:
        sx, sy = self._to_screen(pos)
        item = self.canvas.create_text(sx, sy, text=text, fill=color, font=("Arial", 9), tags=("preview",))
        self._preview_items.append(item)

    def screen_to_world(self, x: int, y: int) -> Point2D:
        return self.viewport.screen_to_world(Point2D(x, y))

    def world_to_screen(self, p: Point2D) -> Point2D:
        return self.viewport.world_to_screen(p)

    def zoom_extents(self) -> None:
        bounds = self.scene.get_bounds()
        if not bounds.is_empty():
            self.viewport.fit_to_bounds(bounds)
            self.render()

    def set_snap_enabled(self, enabled: bool) -> None:
        self.grid.settings.snap_enabled = enabled

    def set_grid_enabled(self, enabled: bool) -> None:
        self.grid.settings.enabled = enabled
        self.render()
