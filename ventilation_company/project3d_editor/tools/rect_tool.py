"""Інструмент малювання прямокутників."""

from __future__ import annotations
from typing import Optional

from ventilation_company.project3d_editor.tools.base_tool import BaseTool
from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.scene.entities.rect import RectEntity


class RectTool(BaseTool):
    """Малювання прямокутників (2 кути)."""

    name = "Прямокутник"
    icon = "▭"
    cursor = "crosshair"

    def __init__(self, renderer, scene):
        super().__init__(renderer, scene)
        self._start_point: Optional[Point2D] = None
        self.filled: bool = True
        self.fill_color: str = "#cccccc"

    def on_activate(self) -> None:
        self._start_point = None

    def on_mouse_move(self, point: Point2D) -> None:
        if self._start_point is not None:
            self.renderer.clear_preview()
            self.renderer.preview_rect(self._start_point, point)
            w = abs(point.x - self._start_point.x)
            h = abs(point.y - self._start_point.y)
            mid = (self._start_point + point) / 2
            self.renderer.preview_text(mid, f"{w:.0f} x {h:.0f}")

    def on_click(self, point: Point2D, button: int) -> None:
        if button == 1:
            if self._start_point is None:
                self._start_point = point
            else:
                min_x = min(self._start_point.x, point.x)
                min_y = min(self._start_point.y, point.y)
                w = abs(point.x - self._start_point.x)
                h = abs(point.y - self._start_point.y)
                rect = RectEntity(
                    corner=Point2D(min_x, min_y),
                    width=w,
                    height=h,
                    filled=self.filled,
                    fill_color=self.fill_color,
                    layer_id=self.scene.layer_manager.active_layer_id,
                    color=self.scene.layer_manager.active_layer.color,
                )
                self.scene.add_entity(rect)
                self._start_point = None
                self.renderer.clear_preview()
                self.renderer.render()
        elif button == 3:
            self._start_point = None
            self.renderer.clear_preview()

    def on_key(self, event) -> None:
        if event.keysym == "Escape":
            self._start_point = None
            self.renderer.clear_preview()
