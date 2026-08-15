"""Базовий клас інструменту редагування."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ventilation_company.project3d_editor.canvas2d.renderer import Canvas2DRenderer
    from ventilation_company.project3d_editor.scene.scene_graph import SceneGraph
    from ventilation_company.project3d_editor.core.point import Point2D


class BaseTool(ABC):
    """Базовий клас будь-якого інструменту."""

    name: str = "Інструмент"
    icon: str = "🔧"
    cursor: str = "crosshair"

    def __init__(self, renderer: Canvas2DRenderer, scene: SceneGraph):
        self.renderer = renderer
        self.scene = scene
        self._active = False

    def activate(self) -> None:
        """Викликається при активації інструменту."""
        self._active = True
        self.renderer.canvas.config(cursor=self.cursor)
        self.on_activate()

    def deactivate(self) -> None:
        """Викликається при деактивації інструменту."""
        self._active = False
        self.renderer.clear_preview()
        self.on_deactivate()

    def on_activate(self) -> None:
        """Перевизначається в підкласах."""
        pass

    def on_deactivate(self) -> None:
        """Перевизначається в підкласах."""
        pass

    def on_mouse_move(self, point: Point2D) -> None:
        """Рух миші."""
        pass

    def on_click(self, point: Point2D, button: int) -> None:
        """Клік миші (button: 1=ЛКМ, 2=СКМ, 3=ПКМ)."""
        pass

    def on_drag(self, start: Point2D, current: Point2D) -> None:
        """Перетягування (ЛКМ + рух)."""
        pass

    def on_drag_end(self, start: Point2D, end: Point2D) -> None:
        """Кінець перетягування."""
        pass

    def on_double_click(self, point: Point2D) -> None:
        """Подвійний клік."""
        pass

    def on_key(self, event) -> None:
        """Натискання клавіші."""
        pass

    def is_active(self) -> bool:
        return self._active
