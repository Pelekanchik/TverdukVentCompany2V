"""Шари (Layers) — як у AutoCAD/Revit."""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class Layer:
    """Шар для групування сутностей."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Шар 0"
    visible: bool = True
    locked: bool = False
    color: str = "#000000"
    line_width: float = 1.0
    line_type: str = "solid"
    order: int = 0  # Порядок відображення (менше = нижче)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "visible": self.visible,
            "locked": self.locked,
            "color": self.color,
            "line_width": self.line_width,
            "line_type": self.line_type,
            "order": self.order,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Layer:
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Шар 0"),
            visible=data.get("visible", True),
            locked=data.get("locked", False),
            color=data.get("color", "#000000"),
            line_width=data.get("line_width", 1.0),
            line_type=data.get("line_type", "solid"),
            order=data.get("order", 0),
        )


class LayerManager:
    """Керування шарами."""

    def __init__(self):
        self._layers: Dict[str, Layer] = {}
        self._active_layer_id: str = ""
        self._create_default_layer()

    def _create_default_layer(self) -> None:
        default = Layer(id="default", name="0 — Основний", order=0)
        self._layers["default"] = default
        self._active_layer_id = "default"

    @property
    def active_layer(self) -> Layer:
        return self._layers.get(self._active_layer_id, self._layers["default"])

    @property
    def active_layer_id(self) -> str:
        return self._active_layer_id

    def set_active_layer(self, layer_id: str) -> None:
        if layer_id in self._layers:
            self._active_layer_id = layer_id

    def add_layer(self, name: str, color: str = "#000000", order: int = 0) -> Layer:
        layer = Layer(name=name, color=color, order=order)
        self._layers[layer.id] = layer
        return layer

    def remove_layer(self, layer_id: str) -> bool:
        if layer_id == "default":
            return False
        if layer_id in self._layers:
            del self._layers[layer_id]
            if self._active_layer_id == layer_id:
                self._active_layer_id = "default"
            return True
        return False

    def get_layer(self, layer_id: str) -> Layer:
        return self._layers.get(layer_id, self._layers["default"])

    def get_all_layers(self) -> List[Layer]:
        return sorted(self._layers.values(), key=lambda l: l.order)

    def get_visible_layers(self) -> List[Layer]:
        return [l for l in self.get_all_layers() if l.visible]

    def toggle_visibility(self, layer_id: str) -> None:
        layer = self._layers.get(layer_id)
        if layer:
            layer.visible = not layer.visible

    def toggle_lock(self, layer_id: str) -> None:
        layer = self._layers.get(layer_id)
        if layer:
            layer.locked = not layer.locked

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layers": {k: v.to_dict() for k, v in self._layers.items()},
            "active_layer_id": self._active_layer_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LayerManager:
        mgr = cls()
        mgr._layers.clear()
        for lid, ldata in data.get("layers", {}).items():
            mgr._layers[lid] = Layer.from_dict(ldata)
        mgr._active_layer_id = data.get("active_layer_id", "default")
        if mgr._active_layer_id not in mgr._layers:
            mgr._active_layer_id = "default"
        return mgr
