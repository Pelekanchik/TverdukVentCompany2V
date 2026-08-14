"""Viewport — керування масштабом, панорамою, поворотом."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple

from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.core.transform import Transform2D
from ventilation_company.project3d_editor.core.bounds import Bounds


@dataclass
class Viewport:
    """Вьюпорт 2D-канваса."""
    width: int = 800
    height: int = 600
    transform: Transform2D = None
    _min_scale: float = 0.001   # 1 px = 1000 мм
    _max_scale: float = 10.0    # 1 px = 0.1 мм

    def __post_init__(self):
        if self.transform is None:
            self.transform = Transform2D(scale=0.1, offset_x=self.width / 2, offset_y=self.height / 2)

    def resize(self, width: int, height: int) -> None:
        """Оновити розміри вьюпорта."""
        old_cx, old_cy = self.width / 2, self.height / 2
        new_cx, new_cy = width / 2, height / 2
        self.transform.offset_x += new_cx - old_cx
        self.transform.offset_y += new_cy - old_cy
        self.width = width
        self.height = height

    def world_to_screen(self, p: Point2D) -> Point2D:
        return self.transform.world_to_screen(p)

    def screen_to_world(self, p: Point2D) -> Point2D:
        return self.transform.screen_to_world(p)

    def zoom(self, factor: float, screen_x: float, screen_y: float) -> None:
        """Масштабування відносно точки екрана."""
        new_scale = max(self._min_scale, min(self._max_scale, self.transform.scale * factor))
        if new_scale == self.transform.scale:
            return
        factor = new_scale / self.transform.scale
        self.transform.zoom_at(Point2D(screen_x, screen_y), factor)

    def pan(self, dx: float, dy: float) -> None:
        """Панорама."""
        self.transform.pan(dx, dy)

    def fit_to_bounds(self, bounds: Bounds, margin: float = 0.1) -> None:
        """Підігнати вигляд під bounds."""
        if bounds.is_empty():
            return
        bw = bounds.width()
        bh = bounds.height()
        if bw == 0:
            bw = 1000
        if bh == 0:
            bh = 1000
        scale_x = self.width / (bw * (1 + margin * 2))
        scale_y = self.height / (bh * (1 + margin * 2))
        self.transform.scale = min(scale_x, scale_y, self._max_scale)
        self.transform.scale = max(self.transform.scale, self._min_scale)
        center_screen = Point2D(self.width / 2, self.height / 2)
        center_world = bounds.center()
        # offset = screen - world * scale (з урахуванням інверсії Y)
        self.transform.offset_x = center_screen.x - center_world.x * self.transform.scale
        self.transform.offset_y = center_screen.y + center_world.y * self.transform.scale

    def get_visible_world_bounds(self) -> Bounds:
        """Bounds видимої області у світових координатах."""
        tl = self.screen_to_world(Point2D(0, 0))
        br = self.screen_to_world(Point2D(self.width, self.height))
        return Bounds(
            min_x=min(tl.x, br.x),
            min_y=min(tl.y, br.y),
            max_x=max(tl.x, br.x),
            max_y=max(tl.y, br.y),
        )

    def get_scale_str(self) -> str:
        """Текстове представлення масштабу (1:100 тощо)."""
        if self.transform.scale >= 1:
            return f"1:{1/self.transform.scale:.0f}"
        return f"{self.transform.scale*100:.1f}%"
