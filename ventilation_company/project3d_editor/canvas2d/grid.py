"""Сітка та прив'язка (Snap) — як у CAD."""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import math

from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.core.bounds import Bounds


@dataclass
class GridSettings:
    """Налаштування сітки."""
    enabled: bool = True
    snap_enabled: bool = True
    snap_size: float = 50.0    # мм (крок прив'язки)
    major_spacing: float = 1000.0  # мм (основна сітка)
    minor_spacing: float = 100.0   # мм (допоміжна сітка)
    show_minor: bool = True
    major_color: str = "#cccccc"
    minor_color: str = "#e8e8e8"
    axis_color: str = "#ff0000"


class Grid:
    """Сітка та прив'язка до сітки/точок/ліній."""

    def __init__(self, settings: GridSettings = None):
        self.settings = settings or GridSettings()

    def snap(self, point: Point2D, snap_points: List[Point2D] = None,
             snap_entities=None, tolerance: float = 10.0) -> Point2D:
        """Прив'язка точки до сітки або інших об'єктів."""
        if not self.settings.snap_enabled:
            return point

        best = point
        best_dist = float("inf")

        # 1. Прив'язка до сітки
        if self.settings.snap_size > 0:
            sx = round(point.x / self.settings.snap_size) * self.settings.snap_size
            sy = round(point.y / self.settings.snap_size) * self.settings.snap_size
            grid_point = Point2D(sx, sy)
            d = point.distance_to(grid_point)
            if d < tolerance and d < best_dist:
                best = grid_point
                best_dist = d

        # 2. Прив'язка до точок
        if snap_points:
            for sp in snap_points:
                d = point.distance_to(sp)
                if d < tolerance and d < best_dist:
                    best = sp
                    best_dist = d

        # 3. Прив'язка до кінців ліній (endpoints)
        if snap_entities:
            for ent in snap_entities:
                for ep in ent.get_points():
                    d = point.distance_to(ep)
                    if d < tolerance and d < best_dist:
                        best = ep
                        best_dist = d

        return best

    def get_grid_lines(self, view_bounds: Bounds) -> Tuple[List[Tuple[float, bool]], List[Tuple[float, bool]]]:
        """Отримати лінії сітки для видимої області.
        Повертає (vertical_lines, horizontal_lines), де кожна лінія — (координата, is_major).
        """
        vertical = []
        horizontal = []

        if not self.settings.enabled:
            return vertical, horizontal

        # Допоміжна сітка
        if self.settings.show_minor and self.settings.minor_spacing > 0:
            xs = self._get_lines(view_bounds.min_x, view_bounds.max_x, self.settings.minor_spacing)
            for x in xs:
                vertical.append((x, False))
            ys = self._get_lines(view_bounds.min_y, view_bounds.max_y, self.settings.minor_spacing)
            for y in ys:
                horizontal.append((y, False))

        # Основна сітка
        if self.settings.major_spacing > 0:
            xs = self._get_lines(view_bounds.min_x, view_bounds.max_x, self.settings.major_spacing)
            for x in xs:
                vertical.append((x, True))
            ys = self._get_lines(view_bounds.min_y, view_bounds.max_y, self.settings.major_spacing)
            for y in ys:
                horizontal.append((y, True))

        return vertical, horizontal

    def _get_lines(self, min_val: float, max_val: float, spacing: float) -> List[float]:
        """Отримати координати ліній сітки в діапазоні."""
        start = math.floor(min_val / spacing) * spacing
        lines = []
        val = start
        while val <= max_val + spacing / 2:
            lines.append(val)
            val += spacing
        return lines

    def get_axis_lines(self, view_bounds: Bounds) -> List[Tuple[str, float, bool]]:
        """Отримати осі координат (X=0, Y=0)."""
        lines = []
        if view_bounds.min_x <= 0 <= view_bounds.max_x:
            lines.append(("y_axis", 0.0, True))
        if view_bounds.min_y <= 0 <= view_bounds.max_y:
            lines.append(("x_axis", 0.0, True))
        return lines
