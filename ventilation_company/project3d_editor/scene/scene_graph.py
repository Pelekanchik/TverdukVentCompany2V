"""Граф сцени — зберігання та керування всіма сутностями."""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Callable
import copy

from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.core.bounds import Bounds
from ventilation_company.project3d_editor.scene.entity import Entity, EntityType
from ventilation_company.project3d_editor.scene.layer import LayerManager


class SceneGraph:
    """Головне сховище всіх об'єктів сцени."""

    def __init__(self):
        self._entities: Dict[str, Entity] = {}
        self._layer_manager = LayerManager()
        self._selection: List[str] = []
        self._modified = False
        self._change_callbacks: List[Callable] = []
        self._undo_stack: List[List[Dict[str, Any]]] = []
        self._redo_stack: List[List[Dict[str, Any]]] = []
        self._max_undo = 50

    # ── Підписки ──
    def on_change(self, callback: Callable) -> None:
        self._change_callbacks.append(callback)

    def _notify_change(self) -> None:
        self._modified = True
        for cb in self._change_callbacks:
            try:
                cb()
            except Exception:
                pass

    # ── Undo/Redo ──
    def _push_undo(self) -> None:
        state = [e.to_dict() for e in self._entities.values()]
        self._undo_stack.append(state)
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def undo(self) -> None:
        if not self.can_undo():
            return
        current = [e.to_dict() for e in self._entities.values()]
        self._redo_stack.append(current)
        state = self._undo_stack.pop()
        self._restore_state(state)
        self._notify_change()

    def redo(self) -> None:
        if not self.can_redo():
            return
        current = [e.to_dict() for e in self._entities.values()]
        self._undo_stack.append(current)
        state = self._redo_stack.pop()
        self._restore_state(state)
        self._notify_change()

    def _restore_state(self, state: List[Dict[str, Any]]) -> None:
        # Спрощена версія — в реальності потрібен фабричний метод
        self._entities.clear()
        # TODO: відновлення сутностей через фабрику

    # ── Сутності ──
    def add_entity(self, entity: Entity, record_undo: bool = True) -> None:
        if record_undo:
            self._push_undo()
        self._entities[entity.id] = entity
        self._notify_change()

    def remove_entity(self, entity_id: str, record_undo: bool = True) -> bool:
        if entity_id not in self._entities:
            return False
        if record_undo:
            self._push_undo()
        del self._entities[entity_id]
        if entity_id in self._selection:
            self._selection.remove(entity_id)
        self._notify_change()
        return True

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self._entities.get(entity_id)

    def get_all_entities(self) -> List[Entity]:
        return list(self._entities.values())

    def get_entities_by_layer(self, layer_id: str) -> List[Entity]:
        return [e for e in self._entities.values() if e.layer_id == layer_id]

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        return [e for e in self._entities.values() if e.entity_type == entity_type]

    def get_visible_entities(self) -> List[Entity]:
        visible_layers = {l.id for l in self._layer_manager.get_visible_layers()}
        return [e for e in self._entities.values()
                if e.visible and e.layer_id in visible_layers]

    def clear(self, record_undo: bool = True) -> None:
        if record_undo:
            self._push_undo()
        self._entities.clear()
        self._selection.clear()
        self._notify_change()

    # ── Вибір ──
    def select(self, entity_id: str, additive: bool = False) -> None:
        if not additive:
            self._selection.clear()
        if entity_id in self._entities and entity_id not in self._selection:
            self._selection.append(entity_id)
            self._entities[entity_id].selected = True
            self._notify_change()

    def deselect(self, entity_id: str) -> None:
        if entity_id in self._selection:
            self._selection.remove(entity_id)
            e = self._entities.get(entity_id)
            if e:
                e.selected = False
            self._notify_change()

    def deselect_all(self) -> None:
        for eid in self._selection:
            e = self._entities.get(eid)
            if e:
                e.selected = False
        self._selection.clear()
        self._notify_change()

    def get_selection(self) -> List[Entity]:
        return [self._entities[eid] for eid in self._selection if eid in self._entities]

    def get_selected_ids(self) -> List[str]:
        return list(self._selection)

    def delete_selected(self) -> None:
        if not self._selection:
            return
        self._push_undo()
        for eid in list(self._selection):
            if eid in self._entities:
                del self._entities[eid]
        self._selection.clear()
        self._notify_change()

    def move_selected(self, delta: Point2D) -> None:
        for eid in self._selection:
            e = self._entities.get(eid)
            if e and not e.locked:
                e.move(delta)
        self._notify_change()

    # ── Hit testing ──
    def hit_test(self, point: Point2D, tolerance: float = 5.0) -> Optional[Entity]:
        """Знайти найближчу сутність під точкою."""
        visible = self.get_visible_entities()
        # Спочатку шукаємо серед selected (пріоритет)
        for e in visible:
            if e.selected and e.is_hit(point, tolerance):
                return e
        for e in reversed(visible):  # Зверху вниз (останні зверху)
            if e.is_hit(point, tolerance):
                return e
        return None

    def hit_test_all(self, point: Point2D, tolerance: float = 5.0) -> List[Entity]:
        """Знайти всі сутності під точкою."""
        return [e for e in reversed(self.get_visible_entities()) if e.is_hit(point, tolerance)]

    def box_select(self, min_p: Point2D, max_p: Point2D, additive: bool = False) -> None:
        """Вибір рамкою."""
        if not additive:
            self.deselect_all()
        bounds = Bounds.from_points([min_p, max_p])
        for e in self.get_visible_entities():
            eb = e.get_bounds()
            if eb.intersects(bounds):
                if e.id not in self._selection:
                    self._selection.append(e.id)
                    e.selected = True
        self._notify_change()

    # ── Bounds ──
    def get_bounds(self) -> Bounds:
        b = Bounds()
        for e in self._entities.values():
            eb = e.get_bounds()
            if not eb.is_empty():
                b = Bounds.union(b, eb)
        return b

    # ── Шари ──
    @property
    def layer_manager(self) -> LayerManager:
        return self._layer_manager

    # ── Серіалізація ──
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self._entities.values()],
            "layer_manager": self._layer_manager.to_dict(),
        }
