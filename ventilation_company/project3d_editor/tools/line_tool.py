"""Інструмент малювання ліній."""

from __future__ import annotations
from typing import Optional

from ventilation_company.project3d_editor.tools.base_tool import BaseTool
from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.scene.entities.line import LineEntity


class LineTool(BaseTool):
    """Малювання відрізків прямої."""

    name = "Лінія"
    icon = "📏"
    cursor = "crosshair"

    def __init__(self, renderer, scene):
        super().__init__(renderer, scene)
        self._start_point: Optional[Point2D] = None
        self._snap_points: list = []

    def on_activate(self) -> None:
        self._start_point = None
        self._snap_points = []
        for e in self.scene.get_visible_entities():
            self._snap_points.extend(e.get_points())

    def on_mouse_move(self, point: Point2D) -> None:
        if self._start_point is not None:
            self.renderer.clear_preview()
            self.renderer.preview_line(self._start_point, point)
            # Показати довжину
            length = self._start_point.distance_to(point)
            mid = (self._start_point + point) / 2
            self.renderer.preview_text(mid, f"{length:.0f} мм")

    def on_click(self, point: Point2D, button: int) -> None:
        if button == 1:
            if self._start_point is None:
                self._start_point = point
            else:
                line = LineEntity(
                    start=self._start_point,
                    end=point,
                    layer_id=self.scene.layer_manager.active_layer_id,
                    color=self.scene.layer_manager.active_layer.color,
                )
                self.scene.add_entity(line)
                self._start_point = point  # Ланцюжок ліній
                self.renderer.render()
        elif button == 3:
            # ПКМ — скасувати поточну лінію
            self._start_point = None
            self.renderer.clear_preview()

    def on_key(self, event) -> None:
        if event.keysym == "Escape":
            self._start_point = None
            self.renderer.clear_preview()
