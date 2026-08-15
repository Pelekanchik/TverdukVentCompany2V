"""Інструмент розміщення фасонних виробів."""

from __future__ import annotations

from ventilation_company.project3d_editor.tools.base_tool import BaseTool
from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.scene.entities.fitting import DuctFittingEntity


class FittingTool(BaseTool):
    """Розміщення фасонних виробів (відводи, трійники тощо)."""

    name = "Фасонний виріб"
    icon = "🔀"
    cursor = "crosshair"

    def __init__(self, renderer, scene):
        super().__init__(renderer, scene)
        self.fitting_type: str = "відвід"
        self.width_in: float = 200.0
        self.height_in: float = 200.0
        self.width_out: float = 200.0
        self.height_out: float = 200.0
        self.angle: float = 90.0
        self.radius: float = 200.0
        self.duct_type: str = "приплив"
        self.rotation: float = 0.0

    def on_activate(self) -> None:
        pass

    def on_mouse_move(self, point: Point2D) -> None:
        self.renderer.clear_preview()
        # Попередній перегляд ромба
        size = max(self.width_in, self.height_in, 100) / 2
        pts = [
            point + Point2D(0, -size),
            point + Point2D(size, 0),
            point + Point2D(0, size),
            point + Point2D(-size, 0),
        ]
        col = "#0066cc"
        if "витяж" in self.duct_type.lower():
            col = "#009900"
        elif "дим" in self.duct_type.lower():
            col = "#cc6600"
        self.renderer.preview_polygon(pts, color=col, fill=col)
        self.renderer.preview_text(point, self.fitting_type[:3])

    def on_click(self, point: Point2D, button: int) -> None:
        if button == 1:
            fitting = DuctFittingEntity(
                position=point,
                fitting_type=self.fitting_type,
                width_in=self.width_in,
                height_in=self.height_in,
                width_out=self.width_out,
                height_out=self.height_out,
                angle=self.angle,
                radius=self.radius,
                rotation=self.rotation,
                duct_type=self.duct_type,
                layer_id=self.scene.layer_manager.active_layer_id,
                color="#990099",
            )
            self.scene.add_entity(fitting)
            self.renderer.render()
        elif button == 3:
            # ПКМ — повернути
            self.rotation = (self.rotation + 90) % 360
            self.on_mouse_move(point)

    def on_key(self, event) -> None:
        if event.keysym == "r" or event.keysym == "R":
            self.rotation = (self.rotation + 45) % 360
            # Оновити попередній перегляд
            if self.renderer._last_mouse_pos:
                self.on_mouse_move(self.renderer._last_mouse_pos)
        elif event.keysym == "Escape":
            self.renderer.clear_preview()
