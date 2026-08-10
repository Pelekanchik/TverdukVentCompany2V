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
    bounds: Tuple[float, float, float] = (0, 0, 0)  # width, height, depth

    def transform(self, offset: Tuple[float, float, float]) -> "MeshData":
        """Return new MeshData with translated vertices."""
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
        "rect_duct":    (0.50, 0.75, 0.90),  # steel blue
        "round_duct":   (0.50, 0.75, 0.90),  # steel blue
        "rect_elbow":   (0.90, 0.55, 0.55),  # red
        "round_elbow":  (0.90, 0.55, 0.55),  # red
        "rect_tee":     (0.55, 0.90, 0.55),  # green
        "round_tee":    (0.55, 0.90, 0.55),  # green
        "rect_transition": (0.90, 0.85, 0.40),  # yellow
        "round_transition": (0.90, 0.85, 0.40), # yellow
        "rect_flange":  (0.60, 0.60, 0.60),  # dark gray
        "round_flange": (0.60, 0.60, 0.60),  # dark gray
        "rect_cap":     (0.80, 0.50, 0.80),  # purple
        "round_cap":    (0.80, 0.50, 0.80),  # purple
        "flexible":     (0.90, 0.65, 0.35),  # orange
        "default":      (0.70, 0.70, 0.70),  # gray
    }

    @classmethod
    def detect_type(cls, data: Dict[str, Any]) -> str:
        """Detect product type from dictionary data."""
        ptype = (data.get("product_type", "") + " " + data.get("name", "")).lower()

        # Check for flexible first
        if any(k in ptype for k in ("hnuchk", "vstavka", "flexible", "гнучк")):
            return "flexible"

        # Check shape
        is_rect = any(k in ptype for k in ("pryamokutn", "rect", "прямокутн"))
        is_round = any(k in ptype for k in ("krugl", "round", "кругл"))

        # Check product category
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

        # Fallback based on dimensions
        w = data.get("width", 0)
        h = data.get("height", 0)
        if h > 0 and abs(w - h) > 1:
            return "rect_duct"
        if w > 0 and h == 0:
            return "round_duct"
        return "default"

    @classmethod
    def build(cls, data: Dict[str, Any], position=(0, 0, 0)) -> MeshData:
        """Build mesh for a product at given position."""
        ptype = cls.detect_type(data)
        method = getattr(cls, f"_build_{ptype}", cls._build_default)
        mesh = method(data)
        mesh.color = cls.COLORS.get(ptype, cls.COLORS["default"])
        mesh.position = position
        mesh.name = data.get("name", "Product")
        return mesh.transform(position)

    @classmethod
    def get_bounds(cls, data: Dict[str, Any]) -> Tuple[float, float, float]:
        """Get bounding box (width, height, depth) for positioning."""
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

    # ── Helper: box wireframe ──
    @staticmethod
    def _box_wireframe(w, h, l, t=0):
        """Generate wireframe for a box. If t>0, both outer and inner."""
        ow, oh = w/2, h/2
        outer = [
            (-ow, -oh, 0), (ow, -oh, 0), (ow, oh, 0), (-ow, oh, 0),
            (-ow, -oh, l), (ow, -oh, l), (ow, oh, l), (-ow, oh, l),
        ]
        edges = [
            (0,1),(1,2),(2,3),(3,0),      # bottom
            (4,5),(5,6),(6,7),(7,4),      # top
            (0,4),(1,5),(2,6),(3,7),      # vertical
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
            return outer + inner, edges + inner_edges
        return outer, edges

    # ── Helper: cylinder wireframe ──
    @staticmethod
    def _cylinder_wireframe(diameter, length, segments=16, t=0):
        """Generate wireframe for a cylinder (hollow if t>0)."""
        r = diameter / 2
        vertices = []
        edges = []

        # Bottom and top circles
        for z in [0, length]:
            base_idx = len(vertices)
            for i in range(segments):
                angle = 2 * math.pi * i / segments
                vertices.append((r * math.cos(angle), r * math.sin(angle), z))
            for i in range(segments):
                edges.append((base_idx + i, base_idx + (i + 1) % segments))

        # Vertical lines
        for i in range(segments):
            edges.append((i, i + segments))

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

        return vertices, edges

    # ── Build methods ──
    @classmethod
    def _build_rect_duct(cls, data):
        w = float(data.get("width", 100))
        h = float(data.get("height", 100))
        l = float(data.get("length", 1000))
        t = float(data.get("thickness", 0.7))
        vertices, edges = cls._box_wireframe(w, h, l, t)
        return MeshData(vertices=vertices, edges=edges, faces=[], bounds=(w, h, l))

    @classmethod
    def _build_round_duct(cls, data):
        d = float(data.get("width", data.get("diameter", 100)))
        l = float(data.get("length", 1000))
        t = float(data.get("thickness", 0.7))
        vertices, edges = cls._cylinder_wireframe(d, l, t=t)
        return MeshData(vertices=vertices, edges=edges, faces=[], bounds=(d, d, l))

    @classmethod
    def _build_rect_elbow(cls, data):
        w = float(data.get("width", 100))
        h = float(data.get("height", 100))
        angle = float(data.get("angle", 90))
        radius = float(data.get("radius", 150))
        t = float(data.get("thickness", 0.7))
        segments = max(3, int(angle / 15))

        vertices = []
        edges = []
        rad = math.radians(angle)

        # Approximate elbow as series of small boxes rotated
        for i in range(segments + 1):
            a = rad * i / segments
            # Center of arc at (radius, 0, 0) in XY, then rotated
            # Actually for ventilation, elbow is in XZ plane typically
            # Position along arc
            cx = radius * math.sin(a)
            cz = radius * (1 - math.cos(a))
            # Box at this position
            ow, oh = w/2, h/2
            base = len(vertices)
            # 4 corners of the cross-section
            for dx, dy in [(-ow, -oh), (ow, -oh), (ow, oh), (-ow, oh)]:
                vertices.append((cx + dx, dy, cz))
            if i > 0:
                prev = base - 4
                for j in range(4):
                    edges.append((prev + j, base + j))
                    edges.append((base + j, base + (j+1)%4))

        return MeshData(vertices=vertices, edges=edges, faces=[],
                         bounds=cls.get_bounds(data))

    @classmethod
    def _build_round_elbow(cls, data):
        d = float(data.get("width", data.get("diameter", 100)))
        angle = float(data.get("angle", 90))
        radius = float(data.get("radius", 150))
        t = float(data.get("thickness", 0.7))
        segments = max(8, int(angle / 5))
        ring_segments = 16

        vertices = []
        edges = []
        r = d / 2
        rad = math.radians(angle)

        for i in range(segments + 1):
            a = rad * i / segments
            cx = radius * math.sin(a)
            cz = radius * (1 - math.cos(a))
            base = len(vertices)
            for j in range(ring_segments):
                theta = 2 * math.pi * j / ring_segments
                vertices.append((
                    cx + r * math.cos(theta) * math.cos(a),
                    r * math.sin(theta),
                    cz + r * math.cos(theta) * math.sin(a)
                ))
            if i > 0:
                prev = base - ring_segments
                for j in range(ring_segments):
                    edges.append((prev + j, base + j))
                    edges.append((base + j, base + (j+1) % ring_segments))

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

        # Main duct
        v1, e1 = cls._box_wireframe(w, h, l, t)
        # Branch duct (perpendicular, along Y)
        v2, e2 = cls._box_wireframe(bw, bl, bh, t)
        # Offset branch to center
        offset_y = -bl/2
        offset_z = l/2 - bh/2
        v2 = [(x, y + offset_y, z + offset_z) for x, y, z in v2]
        e2 = [(i + len(v1), j + len(v1)) for i, j in e2]

        return MeshData(vertices=v1+v2, edges=e1+e2, faces=[],
                         bounds=cls.get_bounds(data))

    @classmethod
    def _build_round_tee(cls, data):
        d = float(data.get("width", data.get("diameter", 100)))
        l = float(data.get("length", 1000))
        bd = float(data.get("branch_diameter", 200))
        bl = float(data.get("branch_length", 400))
        t = float(data.get("thickness", 0.7))

        v1, e1 = cls._cylinder_wireframe(d, l, t=t)
        v2, e2 = cls._cylinder_wireframe(bd, bl, t=t)
        # Rotate branch 90° around X, move to center
        v2 = [(x, z - bl/2, y + l/2) for x, y, z in v2]
        e2 = [(i + len(v1), j + len(v1)) for i, j in e2]

        return MeshData(vertices=v1+v2, edges=e1+e2, faces=[],
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

        return MeshData(vertices=vertices, edges=edges, faces=[],
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

        return MeshData(vertices=vertices, edges=edges, faces=[],
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

        # Outer frame
        v1, e1 = cls._box_wireframe(2*ow, 2*oh, depth, 0)
        # Inner cutout (wireframe only)
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

        # Bolt holes (small circles at corners)
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

        return MeshData(vertices=v1+v2+v3, edges=e1+e2+e3, faces=[],
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
        for z in [0, depth]:
            base = len(vertices)
            for i in range(segments):
                theta = 2 * math.pi * i / segments
                vertices.append((outer_r * math.cos(theta), outer_r * math.sin(theta), z))
            for i in range(segments):
                edges.append((base + i, base + (i+1) % segments))

        for i in range(segments):
            edges.append((i, i + segments))

        # Inner circle
        for z in [0, depth]:
            base = len(vertices)
            for i in range(segments):
                theta = 2 * math.pi * i / segments
                vertices.append((r * math.cos(theta), r * math.sin(theta), z))
            for i in range(segments):
                edges.append((base + i, base + (i+1) % segments))

        for i in range(segments):
            edges.append((2*segments + i, 2*segments + i + segments))

        # Bolt holes
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

        return MeshData(vertices=vertices+v3, edges=edges+e3, faces=[],
                         bounds=(d + 2*profile, d + 2*profile, profile))

    @classmethod
    def _build_rect_cap(cls, data):
        w = float(data.get("width", 100))
        h = float(data.get("height", 100))
        profile = float(data.get("profile", 30))
        depth = float(data.get("depth", 30))
        t = float(data.get("thickness", 0.7))
        ow, oh = w/2 + profile, h/2 + profile
        # Cap body
        v1, e1 = cls._box_wireframe(2*ow, 2*oh, depth, t)
        return MeshData(vertices=v1, edges=e1, faces=[],
                         bounds=(w + 2*profile, h + 2*profile, depth))

    @classmethod
    def _build_round_cap(cls, data):
        d = float(data.get("width", data.get("diameter", 100)))
        depth = float(data.get("depth", 30))
        t = float(data.get("thickness", 0.7))
        # Approximate as short cylinder
        vertices, edges = cls._cylinder_wireframe(d, depth, t=t)
        return MeshData(vertices=vertices, edges=edges, faces=[],
                         bounds=(d, d, depth))

    @classmethod
    def _build_flexible(cls, data):
        w = float(data.get("width", 100))
        h = float(data.get("height", 100))
        l = float(data.get("length", 1000))
        # Flexible connector as corrugated - approximate with multiple rings
        vertices = []
        edges = []
        rings = max(4, int(l / 50))
        segments = 16
        amplitude = 3  # corrugation amplitude

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

        return MeshData(vertices=vertices, edges=edges, faces=[],
                         bounds=(w + 2*amplitude, h + 2*amplitude, l))

    @classmethod
    def _build_default(cls, data):
        w = float(data.get("width", 100))
        h = float(data.get("height", 100))
        l = float(data.get("length", 100))
        vertices, edges = cls._box_wireframe(w, h, l)
        return MeshData(vertices=vertices, edges=edges, faces=[],
                         bounds=(w, h, l))


class ProductLayout:
    """Arranges products along an axis with configurable spacing."""

    def __init__(self, spacing: float = 50.0, axis: str = "z"):
        self.spacing = spacing
        self.axis = axis.lower()
        self.positions: List[Tuple[float, float, float]] = []

    def layout(self, products: List[Dict[str, Any]]) -> List[Tuple[float, float, float]]:
        """Calculate positions for a list of products."""
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
        """Build meshes for all products with layout."""
        positions = self.layout(products)
        return [VentGeometry.build(p, pos) for p, pos in zip(products, positions)]
