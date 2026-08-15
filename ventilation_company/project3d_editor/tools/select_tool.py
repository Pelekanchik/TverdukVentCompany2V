"""Інструмент вибору об'єктів."""

from __future__ import annotations
from typing import Optional

from ventilation_company.project3d_editor.tools.base_tool import BaseTool
from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.scene.entity import Entity


class SelectTool(BaseTool):
    """Вибір об'єктів: клік, рамка, переміщення."""

    name = "Вибір"
    icon = "🔍"
    cursor = "arrow"

    def __init__(self, renderer, scene):
        super().__init__(renderer, scene)
        self._drag_start: Optional[Point2D] = None
        self._is_dragging = False
        self._is_moving = False
        self._move_start: Optional[Point2D] = None
        self._selection_on_drag_start: list = []

    def on_click(self, point: Point2D, button: int) -> None:
        if button == 1:
            hit = self.scene.hit_test(point, tolerance=5.0 / self.renderer.viewport.transform.scale)
            if hit:
                # Shift/Ctrl — додати до вибору
                additive = False  # TODO: перевірити модифікатори
                if hit.selected:
                    self.scene.deselect(hit.id)
                else:
                    self.scene.select(hit.id, additive=additive)
            else:
                self.scene.deselect_all()
            self.renderer.render()
        elif button == 3:
            # ПКМ — контекстне меню (TODO)
            pass

    def on_drag(self, start: Point2D, current: Point2D) -> None:
        if not self._is_dragging:
            self._is_dragging = True
            self._drag_start = start
            # Перевіримо, чи почали перетягувати вибраний об'єкт
            hit = self.scene.hit_test(start, tolerance=5.0 / self.renderer.viewport.transform.scale)
            if hit and hit.selected:
                self._is_moving = True
                self._move_start = start
                self._selection_on_drag_start = self.scene.get_selected_ids()
            else:
                self._is_moving = False

        self.renderer.clear_preview()
        if self._is_moving:
            # Переміщення об'єктів
            delta = current - self._move_start
            for eid in self._selection_on_drag_start:
                e = self.scene.get_entity(eid)
                if e and not e.locked:
                    e.move(delta)
            self._move_start = current
            self.renderer.render()
        else:
            # Рамка вибору
            self.renderer.preview_rect(start, current, color="#00aaff")

    def on_drag_end(self, start: Point2D, end: Point2D) -> None:
        self.renderer.clear_preview()
        if self._is_moving:
            # Переміщення завершено — зберігаємо
            pass
        else:
            # Рамка вибору
            min_x = min(start.x, end.x)
            max_x = max(start.x, end.x)
            min_y = min(start.y, end.y)
            max_y = max(start.y, end.y)
            self.scene.box_select(Point2D(min_x, min_y), Point2D(max_x, max_y))
        self._is_dragging = False
        self._is_moving = False
        self._drag_start = None
        self.renderer.render()

    def on_double_click(self, point: Point2D) -> None:
        hit = self.scene.hit_test(point, tolerance=5.0 / self.renderer.viewport.transform.scale)
        if hit:
            # TODO: відкрити діалог властивостей
            pass

    def on_key(self, event) -> None:
        if event.keysym in ("Delete", "BackSpace"):
            self.scene.delete_selected()
            self.renderer.render()
        elif event.keysym == "Escape":
            self.scene.deselect_all()
            self.renderer.render()
