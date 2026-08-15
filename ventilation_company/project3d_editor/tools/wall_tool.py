"""Інструмент малювання стін."""

from __future__ import annotations
from typing import Optional

from ventilation_company.project3d_editor.tools.base_tool import BaseTool
from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.scene.entities.wall import WallEntity


class WallTool(BaseTool):
    """Малювання архітектурних стін."""

    name = "Стіна"
    icon = "🧱"
    cursor = "crosshair"

    def __init__(self, renderer, scene):
        super().__init__(renderer, scene)
        self._start_point: Optional[Point2D] = None
        self.thickness: float = 200.0
        self.height: float = 3000.0
        self.is_load_bearing: bool = False
        self.material: str = "Цегла"

    def on_activate(self) -> None:
        self._start_point = None

    def on_mouse_move(self, point: Point2D) -> None:
        if self._start_point is not None:
            self.renderer.clear_preview()
            wall = WallEntity(
                start=self._start_point,
                end=point,
                thickness=self.thickness,
                height=self.height,
                is_load_bearing=self.is_load_bearing,
                material=self.material,
                layer_id=self.scene.layer_manager.active_layer_id,
                color="#555555" if self.is_load_bearing else "#888888",
            )
            poly = wall.get_polygon()
            self.renderer.preview_polygon(poly, color="#555555", fill="#cccccc")
            length = self._start_point.distance_to(point)
            mid = (self._start_point + point) / 2
            self.renderer.preview_text(mid, f"{length:.0f} мм")

    def on_click(self, point: Point2D, button: int) -> None:
        if button == 1:
            if self._start_point is None:
                self._start_point = point
            else:
                wall = WallEntity(
                    start=self._start_point,
                    end=point,
                    thickness=self.thickness,
                    height=self.height,
                    is_load_bearing=self.is_load_bearing,
                    material=self.material,
                    layer_id=self.scene.layer_manager.active_layer_id,
                    color="#555555" if self.is_load_bearing else "#888888",
                )
                self.scene.add_entity(wall)
                self._start_point = point  # Ланцюжок стін
                self.renderer.render()
        elif button == 3:
            self._start_point = None
            self.renderer.clear_preview()

    def on_key(self, event) -> None:
        if event.keysym == "Escape":
            self._start_point = None
            self.renderer.clear_preview()
