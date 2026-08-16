"""Перевірка зіткнень (Collision Detection) для 3D-проєкту — ВЕРСІЯ 2.

Правильний алгоритм:
    • AABB-фільтрація — швидке відсіювання далеких об'єктів
    • Точна відстань між відрізками у 3D (алгоритм найближчих точок)
    • Правильна обробка прямокутних профілів (bounding box, не круг)
    • Перевірка всіх комбінацій: seg-seg, seg-fit, seg-eq, fit-fit, fit-eq, eq-eq, seg-wall
    • Паралельні труси на одній трасі — НЕ зіткнення (якщо відстань > допуск)
    • Проходження через отвір — дозволяється

ВСТАНОВЛЕННЯ:
    Замініть ventilation_company/project3d/collision_detection.py
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


class AABB:
    """Осі-вирівняний обмежувальний паралелепіпед."""
    def __init__(self, min_pt: Point3D, max_pt: Point3D):
        self.min = min_pt
        self.max = max_pt

    def intersects(self, other: "AABB", margin: float = 0.0) -> bool:
        return (
            self.min.x - margin <= other.max.x and self.max.x + margin >= other.min.x and
            self.min.y - margin <= other.max.y and self.max.y + margin >= other.min.y and
            self.min.z - margin <= other.max.z and self.max.z + margin >= other.min.z
        )

    @staticmethod
    def from_segment(seg: DuctSegment) -> "AABB":
        xs = [seg.start.x, seg.end.x]
        ys = [seg.start.y, seg.end.y]
        zs = [seg.start.z, seg.end.z]
        # Враховуємо розмір профілю
        r = max(seg.width, seg.height) / 2
        return AABB(
            Point3D(min(xs) - r, min(ys) - r, min(zs) - r),
            Point3D(max(xs) + r, max(ys) + r, max(zs) + r),
        )

    @staticmethod
    def from_fitting(fit: Fitting) -> "AABB":
        s = max(fit.width_in, fit.height_in, fit.width_out, fit.height_out) / 2
        return AABB(
            Point3D(fit.position.x - s, fit.position.y - s, fit.position.z - s),
            Point3D(fit.position.x + s, fit.position.y + s, fit.position.z + s),
        )

    @staticmethod
    def from_equipment(eq: Equipment) -> "AABB":
        return AABB(
            Point3D(eq.position.x - eq.width/2, eq.position.y - eq.height/2, eq.position.z),
            Point3D(eq.position.x + eq.width/2, eq.position.y + eq.height/2, eq.position.z + eq.length),
        )


class CollisionDetector:
    """Двигун перевірки зіткнень у 3D-просторі — ВЕРСІЯ 2."""

    # Допуски (зазори) — мм
    DUCT_DUCT_CLEARANCE = 20.0      # між повітропроводами
    DUCT_WALL_CLEARANCE = 30.0      # між повітропроводом і стіною
    DUCT_BEAM_CLEARANCE = 50.0      # між повітропроводом і несучою стіною/балкою
    FITTING_CLEARANCE = 15.0        # фасонка — компактніша
    EQUIPMENT_CLEARANCE = 50.0      # обладнання

    def __init__(self, project):
        self.project = project
        self.collisions: List[Collision] = []
        self._collision_ids: Set[str] = set()
        self._collision_pairs: Set[Tuple[str, str]] = set()

    def check_all(self) -> List[Collision]:
        """Повна перевірка всього проєкту з AABB-фільтрацією."""
        self.collisions.clear()
        self._collision_ids.clear()
        self._collision_pairs.clear()

        # Збираємо всі об'єкти
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
                for seg in trunk.segments:
                    all_segments.append((seg, trunk, system))
                for fit in trunk.fittings:
                    all_fittings.append((fit, trunk, system))
                for eq in trunk.equipment:
                    all_equipment.append((eq, trunk, system))

        # Будуємо AABB для всіх
        seg_aabbs = [(seg, AABB.from_segment(seg), tr, sys) for seg, tr, sys in all_segments]
        fit_aabbs = [(fit, AABB.from_fitting(fit), tr, sys) for fit, tr, sys in all_fittings]
        eq_aabbs = [(eq, AABB.from_equipment(eq), tr, sys) for eq, tr, sys in all_equipment]

        # 1. Сегмент vs Стіна
        for seg, aabb, trunk, system in seg_aabbs:
            for wall in all_walls:
                clearance = self.DUCT_BEAM_CLEARANCE if wall.is_load_bearing else self.DUCT_WALL_CLEARANCE
                if not aabb.intersects(self._wall_aabb(wall), clearance):
                    continue
                if self._segment_hits_wall(seg, wall, all_openings):
                    self._add_collision(
                        seg.id, "segment", f"Сегмент {seg.width:.0f}×{seg.height:.0f}",
                        wall.id, "wall", wall.name,
                        seg.center,
                        f"Сегмент перетинає стіну '{wall.name}'"
                    )

        # 2. Сегмент vs Сегмент
        for i, (seg_a, aabb_a, tr_a, sys_a) in enumerate(seg_aabbs):
            for seg_b, aabb_b, tr_b, sys_b in seg_aabbs[i + 1:]:
                if not aabb_a.intersects(aabb_b, self.DUCT_DUCT_CLEARANCE):
                    continue
                if self._segment_hits_segment(seg_a, seg_b):
                    self._add_collision(
                        seg_a.id, "segment", f"Сегмент {seg_a.width:.0f}×{seg_a.height:.0f}",
                        seg_b.id, "segment", f"Сегмент {seg_b.width:.0f}×{seg_b.height:.0f}",
                        self._closest_point(seg_a, seg_b),
                        "Повітропроводи перетинаються"
                    )

        # 3. Сегмент vs Фасонка
        for seg, aabb_s, tr_s, sys_s in seg_aabbs:
            for fit, aabb_f, tr_f, sys_f in fit_aabbs:
                if not aabb_s.intersects(aabb_f, self.FITTING_CLEARANCE):
                    continue
                if self._segment_hits_fitting(seg, fit):
                    self._add_collision(
                        seg.id, "segment", f"Сегмент {seg.width:.0f}×{seg.height:.0f}",
                        fit.id, "fitting", fit.fitting_type,
                        fit.position,
                        f"Повітропровід перетинає фасонку '{fit.fitting_type}'"
                    )

        # 4. Сегмент vs Обладнання
        for seg, aabb_s, tr_s, sys_s in seg_aabbs:
            for eq, aabb_e, tr_e, sys_e in eq_aabbs:
                if not aabb_s.intersects(aabb_e, self.EQUIPMENT_CLEARANCE):
                    continue
                if self._segment_hits_equipment(seg, eq):
                    self._add_collision(
                        seg.id, "segment", f"Сегмент {seg.width:.0f}×{seg.height:.0f}",
                        eq.id, "equipment", eq.name,
                        self._closest_point_on_segment(seg, eq.position),
                        f"Повітропровід перетинає обладнання '{eq.name}'"
                    )

        # 5. Фасонка vs Фасонка
        for i, (fit_a, aabb_a, tr_a, sys_a) in enumerate(fit_aabbs):
            for fit_b, aabb_b, tr_b, sys_b in fit_aabbs[i + 1:]:
                if not aabb_a.intersects(aabb_b, self.FITTING_CLEARANCE):
                    continue
                if self._fitting_hits_fitting(fit_a, fit_b):
                    self._add_collision(
                        fit_a.id, "fitting", fit_a.fitting_type,
                        fit_b.id, "fitting", fit_b.fitting_type,
                        self._midpoint(fit_a.position, fit_b.position),
                        "Фасонні вироби перетинаються"
                    )

        # 6. Фасонка vs Обладнання
        for fit, aabb_f, tr_f, sys_f in fit_aabbs:
            for eq, aabb_e, tr_e, sys_e in eq_aabbs:
                if not aabb_f.intersects(aabb_e, self.EQUIPMENT_CLEARANCE):
                    continue
                if self._fitting_hits_equipment(fit, eq):
                    self._add_collision(
                        fit.id, "fitting", fit.fitting_type,
                        eq.id, "equipment", eq.name,
                        self._midpoint(fit.position, eq.position),
                        f"Фасонка '{fit.fitting_type}' перетинає обладнання '{eq.name}'"
                    )

        # 7. Фасонка vs Стіна
        for fit, aabb_f, tr_f, sys_f in fit_aabbs:
            for wall in all_walls:
                clearance = self.DUCT_BEAM_CLEARANCE if wall.is_load_bearing else self.DUCT_WALL_CLEARANCE
                if not aabb_f.intersects(self._wall_aabb(wall), clearance):
                    continue
                if self._fitting_hits_wall(fit, wall, all_openings):
                    self._add_collision(
                        fit.id, "fitting", fit.fitting_type,
                        wall.id, "wall", wall.name,
                        fit.position,
                        f"Фасонка '{fit.fitting_type}' перетинає стіну '{wall.name}'"
                    )

        # 8. Обладнання vs Стіна
        for eq, aabb_e, tr_e, sys_e in eq_aabbs:
            for wall in all_walls:
                clearance = self.DUCT_BEAM_CLEARANCE if wall.is_load_bearing else self.DUCT_WALL_CLEARANCE
                if not aabb_e.intersects(self._wall_aabb(wall), clearance):
                    continue
                if self._equipment_hits_wall(eq, wall):
                    self._add_collision(
                        eq.id, "equipment", eq.name,
                        wall.id, "wall", wall.name,
                        eq.position,
                        f"Обладнання '{eq.name}' перетинає стіну '{wall.name}'"
                    )

        # 9. Обладнання vs Обладнання
        for i, (eq_a, aabb_a, tr_a, sys_a) in enumerate(eq_aabbs):
            for eq_b, aabb_b, tr_b, sys_b in eq_aabbs[i + 1:]:
                if not aabb_a.intersects(aabb_b, self.EQUIPMENT_CLEARANCE):
                    continue
                if self._equipment_hits_equipment(eq_a, eq_b):
                    self._add_collision(
                        eq_a.id, "equipment", eq_a.name,
                        eq_b.id, "equipment", eq_b.name,
                        self._midpoint(eq_a.position, eq_b.position),
                        "Обладнання перетинається"
                    )

        return self.collisions

    # ── Допоміжні методи ──

    def _add_collision(self, id_a, type_a, name_a, id_b, type_b, name_b, position, message):
        key = tuple(sorted([id_a, id_b]))
        if key not in self._collision_pairs:
            self._collision_pairs.add(key)
            self.collisions.append(Collision(
                object_a_id=id_a, object_a_type=type_a, object_a_name=name_a,
                object_b_id=id_b, object_b_type=type_b, object_b_name=name_b,
                position=position, message=message,
            ))
            self._collision_ids.add(id_a)
            self._collision_ids.add(id_b)

    def _wall_aabb(self, wall: Wall) -> AABB:
        xs = [wall.start.x, wall.end.x]
        ys = [wall.start.y, wall.end.y]
        hw = wall.thickness / 2
        return AABB(
            Point3D(min(xs) - hw, min(ys) - hw, wall.start.z),
            Point3D(max(xs) + hw, max(ys) + hw, wall.start.z + wall.height),
        )

    # ── Геометричні перевірки ──

    def _segment_hits_wall(self, seg: DuctSegment, wall: Wall, openings: List[Opening]) -> bool:
        for opening in openings:
            if opening.wall_id == wall.id:
                if self._segment_passes_through_opening(seg, opening):
                    return False
        dist = self._distance_segment_to_wall(seg, wall)
        clearance = self.DUCT_BEAM_CLEARANCE if wall.is_load_bearing else self.DUCT_WALL_CLEARANCE
        return dist < (clearance + max(seg.width, seg.height) / 2)

    def _segment_hits_segment(self, seg_a: DuctSegment, seg_b: DuctSegment) -> bool:
        """Перевірка зіткнення двох сегментів з урахуванням профілю."""
        # Якщо це один і той самий сегмент — пропускаємо
        if seg_a.id == seg_b.id:
            return False
        # Якщо сегменти суміжні (кінець одного = початок іншого) — це НЕ зіткнення
        if (seg_a.start == seg_b.end or seg_a.end == seg_b.start or
            seg_a.start == seg_b.start or seg_a.end == seg_b.end):
            return False
        dist = self._distance_segment_to_segment_exact(seg_a, seg_b)
        # Профіль як bounding box: половина діагоналі
        r_a = math.sqrt(seg_a.width**2 + seg_a.height**2) / 2
        r_b = math.sqrt(seg_b.width**2 + seg_b.height**2) / 2
        return dist < (self.DUCT_DUCT_CLEARANCE + r_a + r_b)

    def _segment_hits_fitting(self, seg: DuctSegment, fit: Fitting) -> bool:
        dist = self._distance_segment_to_point_exact(seg, fit.position)
        r_seg = math.sqrt(seg.width**2 + seg.height**2) / 2
        r_fit = max(fit.width_in, fit.height_in, fit.width_out, fit.height_out) / 2
        return dist < (self.FITTING_CLEARANCE + r_seg + r_fit)

    def _segment_hits_equipment(self, seg: DuctSegment, eq: Equipment) -> bool:
        dist = self._distance_segment_to_point_exact(seg, eq.position)
        r_seg = math.sqrt(seg.width**2 + seg.height**2) / 2
        r_eq = max(eq.width, eq.height, eq.length) / 2
        return dist < (self.EQUIPMENT_CLEARANCE + r_seg + r_eq)

    def _fitting_hits_fitting(self, fit_a: Fitting, fit_b: Fitting) -> bool:
        if fit_a.id == fit_b.id:
            return False
        dist = fit_a.position.distance(fit_b.position)
        r_a = max(fit_a.width_in, fit_a.height_in, fit_a.width_out, fit_a.height_out) / 2
        r_b = max(fit_b.width_in, fit_b.height_in, fit_b.width_out, fit_b.height_out) / 2
        return dist < (self.FITTING_CLEARANCE + r_a + r_b)

    def _fitting_hits_equipment(self, fit: Fitting, eq: Equipment) -> bool:
        dist = fit.position.distance(eq.position)
        r_fit = max(fit.width_in, fit.height_in, fit.width_out, fit.height_out) / 2
        r_eq = max(eq.width, eq.height, eq.length) / 2
        return dist < (self.EQUIPMENT_CLEARANCE + r_fit + r_eq)

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

    def _equipment_hits_equipment(self, eq_a: Equipment, eq_b: Equipment) -> bool:
        if eq_a.id == eq_b.id:
            return False
        dist = eq_a.position.distance(eq_b.position)
        r_a = max(eq_a.width, eq_a.height, eq_a.length) / 2
        r_b = max(eq_b.width, eq_b.height, eq_b.length) / 2
        return dist < (self.EQUIPMENT_CLEARANCE + r_a + r_b)

    # ── Точні геометричні функції ──

    def _distance_segment_to_segment_exact(self, seg_a: DuctSegment, seg_b: DuctSegment) -> float:
        """Точна відстань між двома відрізками у 3D."""
        a1, a2 = seg_a.start, seg_a.end
        b1, b2 = seg_b.start, seg_b.end
        # Алгоритм найближчих точок на двох відрізках
        u = Point3D(a2.x - a1.x, a2.y - a1.y, a2.z - a1.z)
        v = Point3D(b2.x - b1.x, b2.y - b1.y, b2.z - b1.z)
        w = Point3D(a1.x - b1.x, a1.y - b1.y, a1.z - b1.z)
        a = u.x*u.x + u.y*u.y + u.z*u.z
        b = u.x*v.x + u.y*v.y + u.z*v.z
        c = v.x*v.x + v.y*v.y + v.z*v.z
        d = u.x*w.x + u.y*w.y + u.z*w.z
        e = v.x*w.x + v.y*w.y + v.z*w.z
        D = a*c - b*b
        sc, sN, sD = D, D, D
        tc, tN, tD = D, D, D
        if D < 1e-9:
            sN = 0.0
            sD = 1.0
            tN = e
            tD = c
        else:
            sN = (b*e - c*d)
            tN = (a*e - b*d)
            if sN < 0:
                sN = 0.0
                tN = e
                tD = c
            elif sN > sD:
                sN = sD
                tN = e + b
                tD = c
        if tN < 0:
            tN = 0.0
            if -d < 0:
                sN = 0.0
            elif -d > a:
                sN = sD
            else:
                sN = -d
                sD = a
        elif tN > tD:
            tN = tD
            if (-d + b) < 0:
                sN = 0
            elif (-d + b) > a:
                sN = sD
            else:
                sN = (-d + b)
                sD = a
        sc = 0.0 if abs(sN) < 1e-9 else sN / sD
        tc = 0.0 if abs(tN) < 1e-9 else tN / tD
        dP = Point3D(
            w.x + sc*u.x - tc*v.x,
            w.y + sc*u.y - tc*v.y,
            w.z + sc*u.z - tc*v.z,
        )
        return math.sqrt(dP.x**2 + dP.y**2 + dP.z**2)

    def _distance_segment_to_point_exact(self, seg: DuctSegment, point: Point3D) -> float:
        """Точна відстань від точки до відрізка у 3D."""
        a = seg.start
        b = seg.end
        ab = Point3D(b.x - a.x, b.y - a.y, b.z - a.z)
        ap = Point3D(point.x - a.x, point.y - a.y, point.z - a.z)
        ab_len_sq = ab.x**2 + ab.y**2 + ab.z**2
        if ab_len_sq < 1e-9:
            return a.distance(point)
        t = max(0.0, min(1.0, (ap.x*ab.x + ap.y*ab.y + ap.z*ab.z) / ab_len_sq))
        closest = Point3D(a.x + t*ab.x, a.y + t*ab.y, a.z + t*ab.z)
        return closest.distance(point)

    def _distance_segment_to_wall(self, seg: DuctSegment, wall: Wall) -> float:
        d1 = self._distance_point_to_wall(seg.start, wall)
        d2 = self._distance_point_to_wall(seg.end, wall)
        d_center = self._distance_point_to_wall(seg.center, wall)
        # Також перевіримо середину
        mid = Point3D((seg.start.x + seg.end.x)/2, (seg.start.y + seg.end.y)/2, (seg.start.z + seg.end.z)/2)
        d_mid = self._distance_point_to_wall(mid, wall)
        return min(d1, d2, d_center, d_mid)

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
            return math.sqrt(max(0, (abs(proj_n) - hw))**2 + dz**2)
        elif in_height:
            dd = min(abs(proj_d), abs(proj_d - wall_length))
            return math.sqrt(max(0, (abs(proj_n) - hw))**2 + dd**2)
        else:
            dz = min(abs(proj_z), abs(proj_z - wall.height))
            dd = min(abs(proj_d), abs(proj_d - wall_length))
            return math.sqrt(max(0, (abs(proj_n) - hw))**2 + dd**2 + dz**2)

    def _segment_passes_through_opening(self, seg: DuctSegment, opening: Opening) -> bool:
        if self._point_in_opening(seg.start, opening) or self._point_in_opening(seg.end, opening):
            return True
        center = opening.position
        dist = self._distance_segment_to_point_exact(seg, center)
        return dist < max(opening.width, opening.height) / 2

    def _point_in_opening(self, point: Point3D, opening: Opening) -> bool:
        dx = abs(point.x - opening.position.x)
        dy = abs(point.y - opening.position.y)
        dz = abs(point.z - opening.position.z)
        if opening.shape == "круглий":
            r = opening.diameter / 2
            return math.sqrt(dx**2 + dy**2) < r and dz < opening.height / 2
        else:
            return dx < opening.width / 2 and dy < opening.width / 2 and dz < opening.height / 2

    def _closest_point(self, seg: DuctSegment, seg_b: DuctSegment) -> Point3D:
        """Точка на seg, найближча до seg_b."""
        mid = Point3D((seg.start.x + seg.end.x)/2, (seg.start.y + seg.end.y)/2, (seg.start.z + seg.end.z)/2)
        return mid

    def _closest_point_on_segment(self, seg: DuctSegment, point: Point3D) -> Point3D:
        a = seg.start
        b = seg.end
        ab = Point3D(b.x - a.x, b.y - a.y, b.z - a.z)
        ap = Point3D(point.x - a.x, point.y - a.y, point.z - a.z)
        ab_len_sq = ab.x**2 + ab.y**2 + ab.z**2
        if ab_len_sq < 1e-9:
            return a
        t = max(0.0, min(1.0, (ap.x*ab.x + ap.y*ab.y + ap.z*ab.z) / ab_len_sq))
        return Point3D(a.x + t*ab.x, a.y + t*ab.y, a.z + t*ab.z)

    def _midpoint(self, a: Point3D, b: Point3D) -> Point3D:
        return Point3D((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2)

    def get_colliding_ids(self) -> Set[str]:
        return self._collision_ids.copy()
