"""Інструмент розміщення обладнання."""

from __future__ import annotations

from ventilation_company.project3d_editor.tools.base_tool import BaseTool
from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.scene.entities.equipment import EquipmentEntity


class EquipmentTool(BaseTool):
    """Розміщення вентиляційного обладнання."""

    name = "Обладнання"
    icon = "⚙️"
    cursor = "crosshair"

    def __init__(self, renderer, scene):
        super().__init__(renderer, scene)
        self.equipment_type: str = "вентилятор"
        self.width: float = 500.0
        self.height: float = 500.0
        self.depth: float = 500.0
        self.rotation: float = 0.0
        self.air_flow: float = 0.0
        self.pressure: float = 0.0
        self.power: float = 0.0
        self.z_position: float = 2500.0

    def on_activate(self) -> None:
        pass

    def on_mouse_move(self, point: Point2D) -> None:
        self.renderer.clear_preview()
        import math
        rad = math.radians(self.rotation)
        cos_r, sin_r = math.cos(rad), math.sin(rad)
        w, h = self.width, self.height
        local = [
            Point2D(-w/2, -h/2),
            Point2D(w/2, -h/2),
            Point2D(w/2, h/2),
            Point2D(-w/2, h/2),
        ]
        corners = [point + Point2D(p.x * cos_r - p.y * sin_r, p.x * sin_r + p.y * cos_r) for p in local]
        self.renderer.preview_polygon(corners, color="#cc8800", fill="#cc8800")
        self.renderer.preview_text(point, self.equipment_type)

    def on_click(self, point: Point2D, button: int) -> None:
        if button == 1:
            equip = EquipmentEntity(
                position=point,
                width=self.width,
                height=self.height,
                depth=self.depth,
                rotation=self.rotation,
                equipment_type=self.equipment_type,
                air_flow=self.air_flow,
                pressure=self.pressure,
                power=self.power,
                z_position=self.z_position,
                layer_id=self.scene.layer_manager.active_layer_id,
                color="#cc8800",
            )
            self.scene.add_entity(equip)
            self.renderer.render()
        elif button == 3:
            self.rotation = (self.rotation + 90) % 360
            self.on_mouse_move(point)

    def on_key(self, event) -> None:
        if event.keysym == "r" or event.keysym == "R":
            self.rotation = (self.rotation + 45) % 360
            if self.renderer._last_mouse_pos:
                self.on_mouse_move(self.renderer._last_mouse_pos)
        elif event.keysym == "Escape":
            self.renderer.clear_preview()
