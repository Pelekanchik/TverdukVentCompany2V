"""Pure-Python 3D geometry engine for ventilation products.
Generates mesh data for matplotlib preview and parameters for FreeCAD macro.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional


@dataclass
class MeshData:
    """3D mesh for visualization."""
    vertices: List[Tuple[float, float, float]]
    edges: List[Tuple[int, int]]
    faces: List[Tuple[int, ...]]
    color: Tuple[float, float, float] = (0.7, 0.7, 0.7)
    position: Tuple[float, float, float] = (0, 0, 0)
    name: str = ""
    bounds: Tuple[float, float, float] = (0, 0, 0)

    def transform(self, offset: Tuple[float, float, float]) -> "MeshData":
        ox, oy, oz = offset
        new_vertices = [(x + ox, y + oy, z + oz) for x, y, z in self.vertices]
        return MeshData(
            vertices=new_vertices,
            edges=self.edges,
            faces=self.faces,
            color=self.color,
            position=offset,
            name=self.name,
            bounds=self.bounds,
        )


class VentGeometry:
    """Geometry builder for all ventilation product types."""

    COLORS = {
        "rect_duct":    (0.50, 0.75, 0.90),
        "round_duct":   (0.50, 0.75, 0.90),
        "rect_elbow":   (0.90, 0.55, 0.55),
        "round_elbow":  (0.90, 0.55, 0.55),
        "rect_tee":     (0.55, 0.90, 0.55),
        "round_tee":    (0.55, 0.90, 0.55),
        "rect_transition": (0.90, 0.85, 0.40),
        "round_transition": (0.90, 0.85, 0.40),
        "rect_flange":  (0.60, 0.60, 0.60),
        "round_flange": (0.60, 0.60, 0.60),
        "rect_cap":     (0.80, 0.50, 0.80),
        "round_cap":    (0.80, 0.50, 0.80),
        "flexible":     (0.90, 0.65, 0.35),
        "default":      (0.70, 0.70, 0.70),
    }

    @classmethod
    def detect_type(cls, data: Dict[str, Any]) -> str:
        ptype = (data.get("product_type", "") + " " + data.get("name", "")).lower()
        if any(k in ptype for k in ("hnuchk", "vstavka", "flexible", "гнучк")):
            return "flexible"
        is_rect = any(k in ptype for k in ("pryamokutn", "rect", "прямокутн"))
        is_round = any(k in ptype for k in ("krugl", "round", "кругл"))
        if any(k in ptype for k in ("povitroprovid", "duct", "повітропровід")):
            return "rect_duct" if is_rect else "round_duct"
        if any(k in ptype for k in ("flanets", "flange", "фланець")):
            return "rect_flange" if is_rect else "round_flange"
        if any(k in ptype for k in ("vidvid", "elbow", "коліно")):
            return "rect_elbow" if is_rect else "round_elbow"
        if any(k in ptype for k in ("tr", "tee", "трійник")):
            return "rect_tee" if is_rect else "round_tee"
        if any(k in ptype for k in ("perekhid", "transition", "перехід")):
            return "rect_transition" if is_rect else "round_transition"
        if any(k in ptype for k in ("zahlushka", "cap", "заглушка")):
            return "rect_cap" if is_rect else "round_cap"
        w = data.get("width", 0)
        h = data.get("height", 0)
        if h > 0 and abs(w - h) > 1:
            return "rect_duct"
        if w > 0 and h == 0:
            return "round_duct"
        return "default"

    @classmethod
    def build(cls, data: Dict[str, Any], position=(0, 0, 0)) -> MeshData:
        ptype = cls.detect_type(data)
        method = getattr(cls, f"_build_{ptype}", cls._build_default)
        mesh = method(data)
        mesh.color = cls.COLORS.get(ptype, cls.COLORS["default"])
        mesh.position = position
        mesh.name = data.get("name", "Product")
        return mesh.transform(position)

    @classmethod
    def get_bounds(cls, data: Dict[str, Any]) -> Tuple[float, float, float]:
        ptype = cls.detect_type(data)
        w = float(data.get("width", 100))
        h = float(data.get("height", 100))
        l = float(data.get("length", 1000))
        if ptype in ("rect_duct", "round_duct", "flexible"):
            return (w, h, l)
        elif ptype in ("rect_flange", "round_flange"):
            profile = float(data.get("profile", 30))
            return (w + 2*profile, h + 2*profile if h > 0 else w + 2*profile, profile)
        elif ptype in ("rect_elbow", "round_elbow"):
            angle = float(data.get("angle", 90))
            radius = float(data.get("radius", 150))
            rad = math.radians(angle)
            depth = radius * math.sin(rad) + w * math.cos(rad) if ptype == "rect_elbow" else radius * math.sin(rad)
            span = 2 * radius * math.sin(rad/2) + w
            return (span, span, depth)
        elif ptype in ("rect_tee", "round_tee"):
            bw = float(data.get("branch_width", data.get("branch_diameter", 200)))
            bl = float(data.get("branch_length", 400))
            return (max(w, bw) + bl, max(h, bw) + bl, l)
        elif ptype in ("rect_transition", "round_transition"):
            ew = float(data.get("end_width", data.get("end_diameter", 300)))
            eh = float(data.get("end_height", 0))
            return (max(w, ew), max(h, eh) if eh > 0 else max(w, ew), l)
        elif ptype in ("rect_cap", "round_cap"):
            profile = float(data.get("profile", 30))
            depth = float(data.get("depth", 30))
            return (w + 2*profile, h + 2*profile if h > 0 else w + 2*profile, depth)
        return (w, h, l)

    @staticmethod
    def _box_wireframe(w, h, l, t=0):
        ow, oh = w/2, h/2
        outer = [
            (-ow, -oh, 0), (ow, -oh, 0), (ow, oh, 0), (-ow, oh, 0),
            (-ow, -oh, l), (ow, -oh, l), (ow, oh, l), (-ow, oh, l),
        ]
        edges = [
            (0,1),(1,2),(2,3),(3,0),
            (4,5),(5,6),(6,7),(7,4),
            (0,4),(1,5),(2,6),(3,7),
        ]
        faces = [
            (0, 1, 2, 3),
            (4, 7, 6, 5),
            (0, 4, 5, 1),
            (1, 5, 6, 2),
            (2, 6, 7, 3),
            (3, 7, 4, 0),
        ]
        if t > 0 and t < min(w, h)/2:
            iw, ih = ow - t, oh - t
            inner = [
                (-iw, -ih, 0), (iw, -ih, 0), (iw, ih, 0), (-iw, ih, 0),
                (-iw, -ih, l), (iw, -ih, l), (iw, ih, l), (-iw, ih, l),
            ]
            inner_edges = [
                (8,9),(9,10),(10,11),(11,8),
                (12,13),(13,14),(14,15),(15,12),
                (8,12),(9,13),(10,14),(11,15),
            ]
            return outer + inner, edges + inner_edges, faces
        return outer, edges, faces

    @staticmethod
    def _cylinder_wireframe(diameter, length, segments=16, t=0):
        r = diameter / 2
        vertices = []
        edges = []
        faces = []
        for z in [0, length]:
            base_idx = len(vertices)
            for i in range(segments):
                angle = 2 * math.pi * i / segments
                vertices.append((r * math.cos(angle), r * math.sin(angle), z))
            for i in range(segments):
                edges.append((base_idx + i, base_idx + (i + 1) % segments))
        for i in range(segments):
            edges.append((i, i + segments))
            jj = (i + 1) % segments
            faces.append((i, jj, jj + segments, i + segments))
        if t > 0 and t < r:
            ri = r - t
            for z in [0, length]:
                base_idx = len(vertices)
                for i in range(segments):
                    angle = 2 * math.pi * i / segments
                    vertices.append((ri * math.cos(angle), ri * math.sin(angle), z))
                for i in range(segments):
                    edges.append((base_idx + i, base_idx + (i + 1) % segments))
            for i in range(segments):
                edges.append((2*segments + i, 2*segments + i + segments))
                jj = (i + 1) % segments
                faces.append((2*segments + i, 2*segments + jj, jj + 3*segments, i + 3*segments))
        return vertices, edges, faces

    @classmethod
    def _build_rect_duct(cls, data):
        w = float(data.get("width", 100))
        h = float(data.get("height", 100))
        l = float(data.get("length", 1000))
        t = float(data.get("thickness", 0.7))
        vertices, edges, faces = cls._box_wireframe(w, h, l, t)
        return MeshData(vertices=vertices, edges=edges, faces=faces, bounds=(w, h, l))

    @classmethod
    def _build_round_duct(cls, data):
        d = float(data.get("width", data.get("diameter", 100)))
        l = float(data.get("length", 1000))
        t = float(data.get("thickness", 0.7))
        vertices, edges, faces = cls._cylinder_wireframe(d, l, t=t)
        return MeshData(vertices=vertices, edges=edges, faces=faces, bounds=(d, d, l))

    @classmethod
    def _build_rect_elbow(cls, data):
        w = float(data.get("width", 100))
        h = float(data.get("height", 100))
        angle = float(data.get("angle", 90))
        radius = float(data.get("radius", 150))
        top_ext = float(data.get("top_extension", 100))
        bottom_ext = float(data.get("bottom_extension", 100))
        t = float(data.get("thickness", 0.7))
        segments = max(3, int(angle / 15))
        vertices = []
        edges = []
        rad = math.radians(angle)
        ow, oh = w/2, h/2

        def add_cs(cx, cy, cz, nx, ny, nz, bx, by, bz):
            base = len(vertices)
            vertices.append((cx + nx*ow + bx*(-oh), cy + ny*ow + by*(-oh), cz + nz*ow + bz*(-oh)))
            vertices.append((cx + nx*(-ow) + bx*(-oh), cy + ny*(-ow) + by*(-oh), cz + nz*(-ow) + bz*(-oh)))
            vertices.append((cx + nx*(-ow) + bx*oh, cy + ny*(-ow) + by*oh, cz + nz*(-ow) + bz*oh))
            vertices.append((cx + nx*ow + bx*oh, cy + ny*ow + by*oh, cz + nz*ow + bz*oh))
            return base

        def connect(base):
            if base >= 4:
                prev = base - 4
                for j in range(4):
                    edges.append((prev + j, base + j))
                    edges.append((base + j, base + (j+1)%4))

        if bottom_ext > 0:
            bs = max(2, int(bottom_ext / 50))
            for i in range(bs + 1):
                z = -bottom_ext + bottom_ext * i / bs
                connect(add_cs(0, 0, z, 1, 0, 0, 0, 1, 0))
        arc_start = 1 if bottom_ext > 0 else 0
        for i in range(arc_start, segments + 1):
            a = rad * i / segments
            cx = radius * math.sin(a)
            cz = radius * (1 - math.cos(a))
            nx, nz = -math.sin(a), math.cos(a)
            connect(add_cs(cx, 0, cz, nx, 0, nz, 0, 1, 0))
        if top_ext > 0:
            ts = max(2, int(top_ext / 50))
            sx = radius * math.sin(rad)
            sz = radius * (1 - math.cos(rad))
            tx, tz = math.cos(rad), math.sin(rad)
            for i in range(1, ts + 1):
                d = top_ext * i / ts
                connect(add_cs(sx + tx*d, 0, sz + tz*d, -math.sin(rad), 0, math.cos(rad), 0, 1, 0))
        return MeshData(vertices=vertices, edges=edges, faces=[],
                         bounds=cls.get_bounds(data))

    @classmethod
    def _build_round_elbow(cls, data):
        d = float(data.get("width", data.get("diameter", 100)))
        angle = float(data.get("angle", 90))
        radius = float(data.get("radius", 150))
        top_ext = float(data.get("top_extension", 100))
        bottom_ext = float(data.get("bottom_extension", 100))
        t = float(data.get("thickness", 0.7))
        segments = max(8, int(angle / 5))
        ring_segments = 16
        vertices = []
        edges = []
        r = d / 2
        rad = math.radians(angle)

        def add_ring(cx, cy, cz, nx, ny, nz, bx, by, bz):
            base = len(vertices)
            for j in range(ring_segments):
                theta = 2 * math.pi * j / ring_segments
                vertices.append((
                    cx + nx * r * math.cos(theta) + bx * r * math.sin(theta),
                    cy + ny * r * math.cos(theta) + by * r * math.sin(theta),
                    cz + nz * r * math.cos(theta) + bz * r * math.sin(theta)
                ))
            return base

        def connect_ring(base):
            if base >= ring_segments:
                prev = base - ring_segments
                for j in range(ring_segments):
                    edges.append((prev + j, base + j))
                    edges.append((base + j, base + (j+1) % ring_segments))

        if bottom_ext > 0:
            bs = max(2, int(bottom_ext / 50))
            for i in range(bs + 1):
                z = -bottom_ext + bottom_ext * i / bs
                connect_ring(add_ring(0, 0, z, 1, 0, 0, 0, 1, 0))
        arc_start = 1 if bottom_ext > 0 else 0
        for i in range(arc_start, segments + 1):
            a = rad * i / segments
            cx = radius * math.sin(a)
            cz = radius * (1 - math.cos(a))
            nx, nz = -math.sin(a), math.cos(a)
            connect_ring(add_ring(cx, 0, cz, nx, 0, nz, 0, 1, 0))
        if top_ext > 0:
            ts = max(2, int(top_ext / 50))
            sx = radius * math.sin(rad)
            sz = radius * (1 - math.cos(rad))
            tx, tz = math.cos(rad), math.sin(rad)
            for i in range(1, ts + 1):
                d = top_ext * i / ts
                connect_ring(add_ring(sx + tx*d, 0, sz + tz*d, -math.sin(rad), 0, math.cos(rad), 0, 1, 0))
        return MeshData(vertices=vertices, edges=edges, faces=[],
                         bounds=cls.get_bounds(data))

    @classmethod
    def _build_rect_tee(cls, data):
        w = float(data.get("width", 100))
        h = float(data.get("height", 100))
        l = float(data.get("length", 1000))
        bw = float(data.get("branch_width", 200))
        bh = float(data.get("branch_height", 200))
        bl = float(data.get("branch_length", 400))
        t = float(data.get("thickness", 0.7))
        v1, e1, f1 = cls._box_wireframe(w, h, l, t)
        v2, e2, f2 = cls._box_wireframe(bw, bl, bh, t)
        offset_y = -bl/2
        offset_z = l/2 - bh/2
        v2 = [(x, y + offset_y, z + offset_z) for x, y, z in v2]
        e2 = [(i + len(v1), j + len(v1)) for i, j in e2]
        f2 = [tuple(i + len(v1) for i in face) for face in f2]
        return MeshData(vertices=v1+v2, edges=e1+e2, faces=f1+f2,
                         bounds=cls.get_bounds(data))

    @classmethod
    def _build_round_tee(cls, data):
        d = float(data.get("width", data.get("diameter", 100)))
        l = float(data.get("length", 1000))
        bd = float(data.get("branch_diameter", 200))
        bl = float(data.get("branch_length", 400))
        t = float(data.get("thickness", 0.7))
        v1, e1, f1 = cls._cylinder_wireframe(d, l, t=t)
        v2, e2, f2 = cls._cylinder_wireframe(bd, bl, t=t)
        v2 = [(x, z - bl/2, y + l/2) for x, y, z in v2]
        e2 = [(i + len(v1), j + len(v1)) for i, j in e2]
        f2 = [tuple(i + len(v1) for i in face) for face in f2]
        return MeshData(vertices=v1+v2, edges=e1+e2, faces=f1+f2,
                         bounds=cls.get_bounds(data))

    @classmethod
    def _build_rect_transition(cls, data):
        w1 = float(data.get("width", 100))
        h1 = float(data.get("height", 100))
        w2 = float(data.get("end_width", 300))
        h2 = float(data.get("end_height", 150))
        l = float(data.get("length", 1000))
        t = float(data.get("thickness", 0.7))
        segments = 8
        vertices = []
        edges = []
        faces = []
        for i in range(segments + 1):
            z = l * i / segments
            frac = i / segments
            cw = w1/2 + (w2/2 - w1/2) * frac
            ch = h1/2 + (h2/2 - h1/2) * frac
            base = len(vertices)
            for dx, dy in [(-cw, -ch), (cw, -ch), (cw, ch), (-cw, ch)]:
                vertices.append((dx, dy, z))
            if i > 0:
                prev = base - 4
                for j in range(4):
                    edges.append((prev + j, base + j))
                    edges.append((base + j, base + (j+1)%4))
                    faces.append((prev + j, prev + (j+1)%4, base + (j+1)%4, base + j))
        return MeshData(vertices=vertices, edges=edges, faces=faces,
                         bounds=cls.get_bounds(data))

    @classmethod
    def _build_round_transition(cls, data):
        d1 = float(data.get("width", data.get("diameter", 100)))
        d2 = float(data.get("end_diameter", 300))
        l = float(data.get("length", 1000))
        t = float(data.get("thickness", 0.7))
        segments = 8
        ring_segments = 16
        vertices = []
        edges = []
        faces = []
        for i in range(segments + 1):
            z = l * i / segments
            frac = i / segments
            r = d1/2 + (d2/2 - d1/2) * frac
            base = len(vertices)
            for j in range(ring_segments):
                theta = 2 * math.pi * j / ring_segments
                vertices.append((r * math.cos(theta), r * math.sin(theta), z))
            if i > 0:
                prev = base - ring_segments
                for j in range(ring_segments):
                    edges.append((prev + j, base + j))
                    edges.append((base + j, base + (j+1) % ring_segments))
                    jj = (j + 1) % ring_segments
                    faces.append((prev + j, prev + jj, base + jj, base + j))
        return MeshData(vertices=vertices, edges=edges, faces=faces,
                         bounds=cls.get_bounds(data))

    @classmethod
    def _build_rect_flange(cls, data):
        w = float(data.get("width", 100))
        h = float(data.get("height", 100))
        profile = float(data.get("profile", 30))
        t = float(data.get("thickness", 0.7))
        ow, oh = w/2 + profile, h/2 + profile
        iw, ih = w/2, h/2
        depth = profile
        v1, e1, f1 = cls._box_wireframe(2*ow, 2*oh, depth, 0)
        v2 = [
            (-iw, -ih, 0), (iw, -ih, 0), (iw, ih, 0), (-iw, ih, 0),
            (-iw, -ih, depth), (iw, -ih, depth), (iw, ih, depth), (-iw, ih, depth),
        ]
        e2 = [
            (8,9),(9,10),(10,11),(11,8),
            (12,13),(13,14),(14,15),(15,12),
            (8,12),(9,13),(10,14),(11,15),
        ]
        e2 = [(i + len(v1), j + len(v1)) for i, j in e2]
        bolt_r = 5
        bolt_segments = 8
        bolt_positions = [
            (-ow + 15, -oh + 15), (ow - 15, -oh + 15),
            (ow - 15, oh - 15), (-ow + 15, oh - 15),
        ]
        v3 = []
        e3 = []
        for bx, by in bolt_positions:
            base = len(v1) + len(v2) + len(v3)
            for j in range(bolt_segments):
                theta = 2 * math.pi * j / bolt_segments
                v3.append((bx + bolt_r * math.cos(theta), by + bolt_r * math.sin(theta), depth/2))
            for j in range(bolt_segments):
                e3.append((base + j, base + (j+1) % bolt_segments))
        return MeshData(vertices=v1+v2+v3, edges=e1+e2+e3, faces=f1,
                         bounds=(w + 2*profile, h + 2*profile, profile))

    @classmethod
    def _build_round_flange(cls, data):
        d = float(data.get("width", data.get("diameter", 100)))
        profile = float(data.get("profile", 30))
        t = float(data.get("thickness", 0.7))
        r = d / 2
        outer_r = r + profile
        depth = profile
        segments = 32
        vertices = []
        edges = []
        faces = []
        for z in [0, depth]:
            base = len(vertices)
            for i in range(segments):
                theta = 2 * math.pi * i / segments
                vertices.append((outer_r * math.cos(theta), outer_r * math.sin(theta), z))
            for i in range(segments):
                edges.append((base + i, base + (i+1) % segments))
        for i in range(segments):
            edges.append((i, i + segments))
            jj = (i + 1) % segments
            faces.append((i, jj, jj + segments, i + segments))
        for z in [0, depth]:
            base = len(vertices)
            for i in range(segments):
                theta = 2 * math.pi * i / segments
                vertices.append((r * math.cos(theta), r * math.sin(theta), z))
            for i in range(segments):
                edges.append((base + i, base + (i+1) % segments))
        for i in range(segments):
            edges.append((2*segments + i, 2*segments + i + segments))
        bolt_r = 5
        bolt_segments = 8
        bolt_circle_r = (r + outer_r) / 2
        v3 = []
        e3 = []
        for k in range(4):
            base = len(vertices) + len(v3)
            angle = 2 * math.pi * k / 4
            bx = bolt_circle_r * math.cos(angle)
            by = bolt_circle_r * math.sin(angle)
            for j in range(bolt_segments):
                theta = 2 * math.pi * j / bolt_segments
                v3.append((bx + bolt_r * math.cos(theta), by + bolt_r * math.sin(theta), depth/2))
            for j in range(bolt_segments):
                e3.append((base + j, base + (j+1) % bolt_segments))
        return MeshData(vertices=vertices+v3, edges=edges+e3, faces=faces,
                         bounds=(d + 2*profile, d + 2*profile, profile))

    @classmethod
    def _build_rect_cap(cls, data):
        w = float(data.get("width", 100))
        h = float(data.get("height", 100))
        profile = float(data.get("profile", 30))
        depth = float(data.get("depth", 30))
        t = float(data.get("thickness", 0.7))
        ow, oh = w/2 + profile, h/2 + profile
        v1, e1, f1 = cls._box_wireframe(2*ow, 2*oh, depth, t)
        return MeshData(vertices=v1, edges=e1, faces=f1,
                         bounds=(w + 2*profile, h + 2*profile, depth))

    @classmethod
    def _build_round_cap(cls, data):
        d = float(data.get("width", data.get("diameter", 100)))
        depth = float(data.get("depth", 30))
        t = float(data.get("thickness", 0.7))
        vertices, edges, faces = cls._cylinder_wireframe(d, depth, t=t)
        return MeshData(vertices=vertices, edges=edges, faces=faces,
                         bounds=(d, d, depth))

    @classmethod
    def _build_flexible(cls, data):
        w = float(data.get("width", 100))
        h = float(data.get("height", 100))
        l = float(data.get("length", 1000))
        vertices = []
        edges = []
        faces = []
        rings = max(4, int(l / 50))
        segments = 16
        amplitude = 3
        for i in range(rings + 1):
            z = l * i / rings
            r = w/2 + amplitude * math.sin(2 * math.pi * i / rings * 3)
            base = len(vertices)
            for j in range(segments):
                theta = 2 * math.pi * j / segments
                vertices.append((r * math.cos(theta), r * math.sin(theta), z))
            if i > 0:
                prev = base - segments
                for j in range(segments):
                    edges.append((prev + j, base + j))
                    edges.append((base + j, base + (j+1) % segments))
                    jj = (j + 1) % segments
                    faces.append((prev + j, prev + jj, base + jj, base + j))
        return MeshData(vertices=vertices, edges=edges, faces=faces,
                         bounds=(w + 2*amplitude, h + 2*amplitude, l))

    @classmethod
    def _build_default(cls, data):
        w = float(data.get("width", 100))
        h = float(data.get("height", 100))
        l = float(data.get("length", 100))
        vertices, edges, faces = cls._box_wireframe(w, h, l)
        return MeshData(vertices=vertices, edges=edges, faces=faces,
                         bounds=(w, h, l))


class ProductLayout:
    def __init__(self, spacing: float = 50.0, axis: str = "z"):
        self.spacing = spacing
        self.axis = axis.lower()
        self.positions: List[Tuple[float, float, float]] = []

    def layout(self, products: List[Dict[str, Any]]) -> List[Tuple[float, float, float]]:
        self.positions = []
        offset = 0.0
        axis_idx = {"x": 0, "y": 1, "z": 2}[self.axis]
        for data in products:
            bounds = VentGeometry.get_bounds(data)
            depth = bounds[2] if axis_idx == 2 else bounds[axis_idx]
            pos = [0.0, 0.0, 0.0]
            pos[axis_idx] = offset
            self.positions.append(tuple(pos))
            offset += depth + self.spacing
        return self.positions

    def build_all(self, products: List[Dict[str, Any]]) -> List[MeshData]:
        positions = self.layout(products)
        return [VentGeometry.build(p, pos) for p, pos in zip(products, positions)]
