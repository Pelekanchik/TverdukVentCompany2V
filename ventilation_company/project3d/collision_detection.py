"""Перевірка зіткнень (Collision Detection) для 3D-проєкту.

Підсвічує червоним, якщо повітропровід перетинає:
  • стіну
  • балку (несучу стіну/перекриття)
  • інший повітропровід
  • обладнання

Проходження через отвір (Opening) — дозволяється.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Optional, Set

from ventilation_company.project3d.vent_system import (
    DuctSegment, DuctShape, Fitting, Equipment, Point3D,
)
from ventilation_company.project3d.arch_context import Wall, Opening


@dataclass
class Collision:
    """Опис одного зіткнення."""
    object_a_id: str
    object_a_type: str
    object_b_id: str
    object_b_type: str
    object_a_name: str = ""
    object_b_name: str = ""
    position: Optional[Point3D] = None
    message: str = ""


class CollisionDetector:
    """Двигун перевірки зіткнень у 3D-просторі."""

    # Допуски (зазори) — мм
    DUCT_WALL_CLEARANCE = 50.0
    DUCT_DUCT_CLEARANCE = 30.0
    DUCT_BEAM_CLEARANCE = 100.0

    def __init__(self, project):
        self.project = project
        self.collisions: List[Collision] = []
        self._collision_ids: Set[str] = set()
        self._collision_pairs: Set[Tuple[str, str]] = set()

    def check_all(self) -> List[Collision]:
        """Повна перевірка всього проєкту."""
        self.collisions.clear()
        self._collision_ids.clear()
        self._collision_pairs.clear()

        all_segments = []
        all_fittings = []
        all_equipment = []
        all_walls = []
        all_openings = []

        for floor in self.project.arch_context.floors:
            all_walls.extend(floor.walls)
            all_openings.extend(floor.openings)

        for system in self.project.ventilation_systems:
            for trunk in system.trunks:
                all_segments.extend([(seg, trunk, system) for seg in trunk.segments])
                all_fittings.extend([(fit, trunk, system) for fit in trunk.fittings])
                all_equipment.extend([(eq, trunk, system) for eq in trunk.equipment])

        # 1. Сегмент vs Стіна / Балка
        for seg, trunk, system in all_segments:
            for wall in all_walls:
                if self._segment_hits_wall(seg, wall, all_openings):
                    self._add_collision(
                        seg.id, "segment", f"Сегмент {seg.width:.0f}×{seg.height:.0f}",
                        wall.id, "wall", wall.name,
                        seg.center,
                        f"Сегмент перетинає стіну '{wall.name}'"
                    )

        # 2. Сегмент vs Сегмент
        for i, (seg_a, trunk_a, sys_a) in enumerate(all_segments):
            for seg_b, trunk_b, sys_b in all_segments[i + 1:]:
                if self._segment_hits_segment(seg_a, seg_b):
                    self._add_collision(
                        seg_a.id, "segment", f"Сегмент {seg_a.width:.0f}×{seg_a.height:.0f}",
                        seg_b.id, "segment", f"Сегмент {seg_b.width:.0f}×{seg_b.height:.0f}",
                        self._midpoint(seg_a.center, seg_b.center),
                        "Повітропроводи перетинаються"
                    )

        # 3. Фасонний виріб vs Стіна
        for fit, trunk, system in all_fittings:
            for wall in all_walls:
                if self._fitting_hits_wall(fit, wall, all_openings):
                    self._add_collision(
                        fit.id, "fitting", fit.fitting_type,
                        wall.id, "wall", wall.name,
                        fit.position,
                        f"Фасонний виріб '{fit.fitting_type}' перетинає стіну '{wall.name}'"
                    )

        # 4. Обладнання vs Стіна
        for eq, trunk, system in all_equipment:
            for wall in all_walls:
                if self._equipment_hits_wall(eq, wall):
                    self._add_collision(
                        eq.id, "equipment", eq.name,
                        wall.id, "wall", wall.name,
                        eq.position,
                        f"Обладнання '{eq.name}' перетинає стіну '{wall.name}'"
                    )

        # 5. Сегмент vs Обладнання
        for seg, trunk, system in all_segments:
            for eq, trunk_b, sys_b in all_equipment:
                if self._segment_hits_equipment(seg, eq):
                    self._add_collision(
                        seg.id, "segment", f"Сегмент {seg.width:.0f}×{seg.height:.0f}",
                        eq.id, "equipment", eq.name,
                        self._midpoint(seg.center, eq.position),
                        f"Повітропровід перетинає обладнання '{eq.name}'"
                    )

        return self.collisions

    def _add_collision(self, id_a, type_a, name_a, id_b, type_b, name_b, position, message):
        key = tuple(sorted([id_a, id_b]))
        if key not in self._collision_pairs:
            self._collision_pairs.add(key)
            self.collisions.append(Collision(
                object_a_id=id_a,
                object_a_type=type_a,
                object_a_name=name_a,
                object_b_id=id_b,
                object_b_type=type_b,
                object_b_name=name_b,
                position=position,
                message=message,
            ))
            self._collision_ids.add(id_a)
            self._collision_ids.add(id_b)

    # ── Геометричні перевірки ──

    def _segment_hits_wall(self, seg: DuctSegment, wall: Wall, openings: List[Opening]) -> bool:
        for opening in openings:
            if opening.wall_id == wall.id:
                if self._segment_passes_through_opening(seg, opening):
                    return False
        dist = self._distance_segment_to_wall(seg, wall)
        clearance = self.DUCT_BEAM_CLEARANCE if wall.is_load_bearing else self.DUCT_WALL_CLEARANCE
        if seg.shape == DuctShape.RECT:
            radius = math.sqrt(seg.width ** 2 + seg.height ** 2) / 2
        else:
            radius = seg.width / 2
        return dist < (clearance + radius)

    def _segment_hits_segment(self, seg_a: DuctSegment, seg_b: DuctSegment) -> bool:
        dist = self._distance_segment_to_segment(seg_a, seg_b)
        if seg_a.shape == DuctShape.RECT:
            r_a = math.sqrt(seg_a.width ** 2 + seg_a.height ** 2) / 2
        else:
            r_a = seg_a.width / 2
        if seg_b.shape == DuctShape.RECT:
            r_b = math.sqrt(seg_b.width ** 2 + seg_b.height ** 2) / 2
        else:
            r_b = seg_b.width / 2
        return dist < (self.DUCT_DUCT_CLEARANCE + r_a + r_b)

    def _fitting_hits_wall(self, fit: Fitting, wall: Wall, openings: List[Opening]) -> bool:
        for opening in openings:
            if opening.wall_id == wall.id:
                if self._point_in_opening(fit.position, opening):
                    return False
        dist = self._distance_point_to_wall(fit.position, wall)
        size = max(fit.width_in, fit.height_in, fit.width_out, fit.height_out) / 2
        clearance = self.DUCT_BEAM_CLEARANCE if wall.is_load_bearing else self.DUCT_WALL_CLEARANCE
        return dist < (clearance + size)

    def _equipment_hits_wall(self, eq: Equipment, wall: Wall) -> bool:
        dist = self._distance_point_to_wall(eq.position, wall)
        size = max(eq.width, eq.height, eq.length) / 2
        clearance = self.DUCT_BEAM_CLEARANCE if wall.is_load_bearing else self.DUCT_WALL_CLEARANCE
        return dist < (clearance + size)

    def _segment_hits_equipment(self, seg: DuctSegment, eq: Equipment) -> bool:
        dist = self._distance_segment_to_point(seg, eq.position)
        if seg.shape == DuctShape.RECT:
            r_seg = math.sqrt(seg.width ** 2 + seg.height ** 2) / 2
        else:
            r_seg = seg.width / 2
        r_eq = max(eq.width, eq.height, eq.length) / 2
        return dist < (r_seg + r_eq + self.DUCT_DUCT_CLEARANCE)

    # ── Допоміжні геометричні функції ──

    def _distance_segment_to_wall(self, seg: DuctSegment, wall: Wall) -> float:
        d1 = self._distance_point_to_wall(seg.start, wall)
        d2 = self._distance_point_to_wall(seg.end, wall)
        d_center = self._distance_point_to_wall(seg.center, wall)
        return min(d1, d2, d_center)

    def _distance_point_to_wall(self, point: Point3D, wall: Wall) -> float:
        n = wall.normal
        d = wall.direction
        hw = wall.thickness / 2
        v = Point3D(point.x - wall.start.x, point.y - wall.start.y, point.z - wall.start.z)
        proj_n = v.x * n.x + v.y * n.y
        proj_d = v.x * d.x + v.y * d.y
        proj_z = point.z - wall.start.z
        wall_length = wall.length
        in_length = 0 <= proj_d <= wall_length
        in_height = 0 <= proj_z <= wall.height
        if in_length and in_height:
            return abs(abs(proj_n) - hw)
        elif in_length:
            dz = min(abs(proj_z), abs(proj_z - wall.height))
            return math.sqrt(max(0, (abs(proj_n) - hw)) ** 2 + dz ** 2)
        elif in_height:
            dd = min(abs(proj_d), abs(proj_d - wall_length))
            return math.sqrt(max(0, (abs(proj_n) - hw)) ** 2 + dd ** 2)
        else:
            dz = min(abs(proj_z), abs(proj_z - wall.height))
            dd = min(abs(proj_d), abs(proj_d - wall_length))
            return math.sqrt(max(0, (abs(proj_n) - hw)) ** 2 + dd ** 2 + dz ** 2)

    def _distance_segment_to_segment(self, seg_a: DuctSegment, seg_b: DuctSegment) -> float:
        ends_a = [seg_a.start, seg_a.end]
        ends_b = [seg_b.start, seg_b.end]
        min_dist = float("inf")
        for pa in ends_a:
            for pb in ends_b:
                dist = pa.distance(pb)
                if dist < min_dist:
                    min_dist = dist
        center_dist = seg_a.center.distance(seg_b.center)
        return min(min_dist, center_dist)

    def _distance_segment_to_point(self, seg: DuctSegment, point: Point3D) -> float:
        ab = seg.end - seg.start
        ap = point - seg.start
        ab_len_sq = ab.x ** 2 + ab.y ** 2 + ab.z ** 2
        if ab_len_sq == 0:
            return seg.start.distance(point)
        t = max(0, min(1, (ap.x * ab.x + ap.y * ab.y + ap.z * ab.z) / ab_len_sq))
        closest = Point3D(
            seg.start.x + t * ab.x,
            seg.start.y + t * ab.y,
            seg.start.z + t * ab.z,
        )
        return closest.distance(point)

    def _segment_passes_through_opening(self, seg: DuctSegment, opening: Opening) -> bool:
        if self._point_in_opening(seg.start, opening) or self._point_in_opening(seg.end, opening):
            return True
        center = opening.position
        dist = self._distance_segment_to_point(seg, center)
        return dist < max(opening.width, opening.height) / 2

    def _point_in_opening(self, point: Point3D, opening: Opening) -> bool:
        dx = abs(point.x - opening.position.x)
        dy = abs(point.y - opening.position.y)
        dz = abs(point.z - opening.position.z)
        if opening.shape == "круглий":
            r = opening.diameter / 2
            return math.sqrt(dx ** 2 + dy ** 2) < r and dz < opening.height / 2
        else:
            return dx < opening.width / 2 and dy < opening.width / 2 and dz < opening.height / 2

    def _midpoint(self, a: Point3D, b: Point3D) -> Point3D:
        return Point3D((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2)

    def get_colliding_ids(self) -> Set[str]:
        return self._collision_ids.copy()
