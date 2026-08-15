"""Інструмент малювання повітропроводів — розтягування як стіна."""

from __future__ import annotations
from typing import Optional

from ventilation_company.project3d_editor.tools.base_tool import BaseTool
from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.scene.entities.duct import DuctSegmentEntity


class DuctTool(BaseTool):
    """Малювання сегментів повітропроводу — точка + напрямок (як стіна)."""

    name = "Повітропровід"
    icon = "🌬️"
    cursor = "crosshair"

    def __init__(self, renderer, scene):
        super().__init__(renderer, scene)
        self._start_point: Optional[Point2D] = None
        self.width: float = 200.0
        self.height: float = 200.0
        self.is_round: bool = False
        self.duct_type: str = "приплив"
        self.material: str = "оцинкована сталь"
        self.thickness: float = 0.7
        self.z_start: float = 2500.0
        self.z_end: float = 2500.0

    def _get_color(self) -> str:
        """Колір за типом системи."""
        t = self.duct_type.lower()
        if "витяж" in t or "exhaust" in t:
            return "#009900"
        if "дим" in t or "smoke" in t:
            return "#cc6600"
        return "#0066cc"  # приплив

    def on_activate(self) -> None:
        self._start_point = None

    def on_mouse_move(self, point: Point2D) -> None:
        if self._start_point is not None:
            import math
            self.renderer.clear_preview()
            col = self._get_color()

            # Малюємо preview труби як полігон
            half = max(self.width, self.height) / 2
            dx = point.x - self._start_point.x
            dy = point.y - self._start_point.y
            seg_len = math.hypot(dx, dy)

            if seg_len > 0:
                nx, ny = dx / seg_len, dy / seg_len
                px, py = -ny * half, nx * half
                poly_pts = [
                    self._start_point + Point2D(px, py),
                    self._start_point - Point2D(px, py),
                    point - Point2D(px, py),
                    point + Point2D(px, py),
                ]
                self.renderer.preview_polygon(poly_pts, color=col, fill=col)
            else:
                self.renderer.preview_circle(self._start_point, half, color=col)

            # Підпис — перпендикулярно до лінії, зміщений вбік
            length = self._start_point.distance_to(point)
            mid = (self._start_point + point) / 2
            label = f"{self.width:.0f}×{self.height:.0f}  L={length:.0f}"

            # Зміщення тексту перпендикулярно (в світових координатах)
            if seg_len > 0:
                scale = self.renderer.viewport.transform.scale
                screen_dx = dx * scale
                screen_dy = -dy * scale  # інверсія Y
                screen_len = math.hypot(screen_dx, screen_dy)
                if screen_len > 0:
                    # Зміщення в пікселях → світові координати
                    perp_screen_x = -screen_dy / screen_len * 20
                    perp_screen_y = screen_dx / screen_len * 20
                    perp_world_x = perp_screen_x / scale
                    perp_world_y = -perp_screen_y / scale  # назад інверсія Y
                    text_pos = mid + Point2D(perp_world_x, perp_world_y)
                    self.renderer.preview_text(text_pos, label, color="#ffffff")
                else:
                    self.renderer.preview_text(mid, label, color="#ffffff")
            else:
                self.renderer.preview_text(mid, label, color="#ffffff")

    def on_click(self, point: Point2D, button: int) -> None:
        if button == 1:
            if self._start_point is None:
                self._start_point = point
            else:
                duct = DuctSegmentEntity(
                    start=self._start_point,
                    end=point,
                    width=self.width,
                    height=self.height,
                    is_round=self.is_round,
                    duct_type=self.duct_type,
                    material=self.material,
                    thickness=self.thickness,
                    z_start=self.z_start,
                    z_end=self.z_end,
                    layer_id=self.scene.layer_manager.active_layer_id,
                    color=self._get_color(),
                )
                self.scene.add_entity(duct)
                self._start_point = point  # Ланцюжок — продовжуємо з кінця
                self.renderer.render()
        elif button == 3:
            # ПКМ — завершити ланцюжок
            self._start_point = None
            self.renderer.clear_preview()

    def on_key(self, event) -> None:
        if event.keysym == "Escape":
            self._start_point = None
            self.renderer.clear_preview()
