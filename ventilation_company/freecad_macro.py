"""
FreeCAD macro for generating advanced 3D ventilation models.
Run by: freecadcmd.exe freecad_macro.py <json_path> <output_path> <format>

Improvements over v1:
  • Hollow ducts with real wall thickness
  • Sequential positioning along Z-axis
  • Color coding by product type
  • Flanges with bolt holes
  • Tees and transitions as fused shapes
  • Dimension annotations
  • Export to FCStd, STEP, STL, OBJ, IGES
"""

import json
import sys
import os
import math

# Fix Windows console encoding
try:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
except Exception:
    pass

try:
    import FreeCAD
    import Part
    import Draft
    FREECAD_OK = True
except ImportError:
    FREECAD_OK = False
    print("ERROR: FreeCAD modules not available")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════

def safe_name(name):
    """Transliterate Ukrainian/Russian to ASCII for FreeCAD object names."""
    translit = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','є':'ye','ж':'zh','з':'z',
        'и':'y','і':'i','ї':'yi','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o',
        'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch',
        'ш':'sh','щ':'shch','ь':'','ю':'yu','я':'ya',
        'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Є':'Ye','Ж':'Zh','З':'Z',
        'И':'Y','І':'I','Ї':'Yi','Й':'Y','К':'K','Л':'L','М':'M','Н':'N','О':'O',
        'П':'P','Р':'R','С':'S','Т':'T','У':'U','Ф':'F','Х':'Kh','Ц':'Ts','Ч':'Ch',
        'Ш':'Sh','Щ':'Shch','Ь':'','Ю':'Yu','Я':'Ya',
    }
    result = ""
    for c in str(name):
        if c in translit:
            result += translit[c]
        elif c.isalnum() or c == "_":
            result += c
        else:
            result += "_"
    if not result or not result[0].isalpha():
        result = "P_" + result
    return result[:50]


def detect_type(product_data):
    """Detect product type from data dict."""
    ptype = (product_data.get("product_type", "") + " " + product_data.get("name", "")).lower()
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
    w = product_data.get("width", 0)
    h = product_data.get("height", 0)
    if h > 0 and abs(w - h) > 1:
        return "rect_duct"
    if w > 0 and h == 0:
        return "round_duct"
    return "default"


TYPE_COLORS = {
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


def set_color(obj, color):
    """Set object color if ViewObject is available."""
    if hasattr(obj, "ViewObject") and obj.ViewObject:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineColor = color


# ═══════════════════════════════════════════════════════════
# GEOMETRY BUILDERS
# ═══════════════════════════════════════════════════════════

def build_rect_duct(doc, name, width, height, length, thickness=0.7):
    """Hollow rectangular duct."""
    w = float(width)
    h = float(height)
    l = float(length)
    t = float(thickness)

    outer = Part.makeBox(w, h, l)
    outer.translate(FreeCAD.Vector(-w/2, -h/2, 0))

    if t > 0 and t < min(w, h) / 2:
        iw = w - 2*t
        ih = h - 2*t
        inner = Part.makeBox(iw, ih, l + 2)
        inner.translate(FreeCAD.Vector(-iw/2, -ih/2, -1))
        shape = outer.cut(inner)
    else:
        shape = outer

    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = shape
    return obj


def build_round_duct(doc, name, diameter, length, thickness=0.7):
    """Hollow round duct."""
    d = float(diameter)
    l = float(length)
    t = float(thickness)
    r = d / 2

    outer = Part.makeCylinder(r, l)

    if t > 0 and t < r:
        inner = Part.makeCylinder(r - t, l + 2)
        inner.translate(FreeCAD.Vector(0, 0, -1))
        shape = outer.cut(inner)
    else:
        shape = outer

    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = shape
    return obj


def build_rect_elbow(doc, name, width, height, angle=90, radius=150, thickness=0.7):
    """Rectangular elbow via sweep of rectangular profile along arc."""
    w = float(width)
    h = float(height)
    a = float(angle)
    r = float(radius)
    t = float(thickness)
    segments = max(3, int(a / 10))

    # Create arc path in XZ plane
    path_points = []
    rad = math.radians(a)
    for i in range(segments + 1):
        frac = i / segments
        angle_i = rad * frac
        x = r * math.sin(angle_i)
        z = r * (1 - math.cos(angle_i))
        path_points.append(FreeCAD.Vector(x, 0, z))

    path_wire = Part.makePolygon(path_points)

    # Create rectangular profile perpendicular to start of path
    # Profile at start (z=0, facing +Z direction, perpendicular to XY)
    # Actually for sweep, profile should be perpendicular to path
    # Simple approach: create a series of boxes rotated along the arc
    shapes = []
    for i in range(segments):
        frac1 = i / segments
        frac2 = (i + 1) / segments
        a1 = rad * frac1
        a2 = rad * frac2

        # Midpoint angle for this segment
        am = (a1 + a2) / 2
        xm = r * math.sin(am)
        zm = r * (1 - math.cos(am))

        # Segment length along arc
        seg_len = r * (a2 - a1)

        # Box oriented along tangent
        box = Part.makeBox(w, h, seg_len + 0.5)
        box.translate(FreeCAD.Vector(-w/2, -h/2, 0))

        # Rotate around Y axis by am, then translate to position
        box.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0), math.degrees(am))
        box.translate(FreeCAD.Vector(xm, 0, zm))
        shapes.append(box)

    if shapes:
        shape = shapes[0]
        for s in shapes[1:]:
            shape = shape.fuse(s)
        # shape = shape.removeSplitter()  # skipped for compatibility
    else:
        shape = Part.makeBox(w, h, 10)

    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = shape
    return obj


def build_round_elbow(doc, name, diameter, angle=90, radius=150, thickness=0.7):
    """Round elbow via torus section."""
    d = float(diameter)
    a = float(angle)
    r = float(radius)
    t = float(thickness)
    ro = d / 2

    # Torus: major radius = bend radius, minor radius = duct radius
    outer = Part.makeTorus(r, ro, 0, a)

    if t > 0 and t < ro:
        inner = Part.makeTorus(r, ro - t, 0, a)
        shape = outer.cut(inner)
    else:
        shape = outer

    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = shape
    return obj


def build_rect_flange(doc, name, width, height, profile=30, thickness=0.7):
    """Rectangular flange with bolt holes."""
    w = float(width)
    h = float(height)
    p = float(profile)
    t = float(thickness)

    ow = w + 2*p
    oh = h + 2*p

    outer = Part.makeBox(ow, oh, p)
    outer.translate(FreeCAD.Vector(-ow/2, -oh/2, 0))

    inner = Part.makeBox(w, h, p + 2)
    inner.translate(FreeCAD.Vector(-w/2, -h/2, -1))

    shape = outer.cut(inner)

    # Bolt holes
    bolt_d = 10
    bolt_r = bolt_d / 2
    bolt_h = p + 2
    spacing = min(150, (w + h) / 4)
    num_x = max(2, int(w / spacing) + 1)
    num_y = max(2, int(h / spacing) + 1)

    for i in range(num_x):
        for j in range(num_y):
            # Only place bolts at corners and edges, not inside
            if i == 0 or i == num_x - 1 or j == 0 or j == num_y - 1:
                bx = -w/2 + (w / max(1, num_x - 1)) * i
                by = -h/2 + (h / max(1, num_y - 1)) * j
                hole = Part.makeCylinder(bolt_r, bolt_h)
                hole.translate(FreeCAD.Vector(bx, by, -1))
                shape = shape.cut(hole)

    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = shape
    return obj


def build_round_flange(doc, name, diameter, profile=30, thickness=0.7):
    """Round flange with bolt holes."""
    d = float(diameter)
    p = float(profile)
    t = float(thickness)
    r = d / 2
    outer_r = r + p

    outer = Part.makeCylinder(outer_r, p)
    inner = Part.makeCylinder(r, p + 2)
    inner.translate(FreeCAD.Vector(0, 0, -1))
    shape = outer.cut(inner)

    # Bolt holes on bolt circle
    bolt_d = 10
    bolt_r = bolt_d / 2
    bolt_circle_r = (r + outer_r) / 2
    num_bolts = max(4, int(2 * math.pi * bolt_circle_r / 80))

    for i in range(num_bolts):
        angle = 2 * math.pi * i / num_bolts
        bx = bolt_circle_r * math.cos(angle)
        by = bolt_circle_r * math.sin(angle)
        hole = Part.makeCylinder(bolt_r, p + 2)
        hole.translate(FreeCAD.Vector(bx, by, -1))
        shape = shape.cut(hole)

    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = shape
    return obj


def build_rect_tee(doc, name, width, height, length,
                   branch_width=200, branch_height=200,
                   branch_length=400, branch_offset=300, thickness=0.7):
    """Rectangular tee — main duct + perpendicular branch."""
    w = float(width)
    h = float(height)
    l = float(length)
    bw = float(branch_width)
    bh = float(branch_height)
    bl = float(branch_length)
    t = float(thickness)

    # Main duct
    main = Part.makeBox(w, h, l)
    main.translate(FreeCAD.Vector(-w/2, -h/2, 0))

    if t > 0 and t < min(w, h)/2:
        main_inner = Part.makeBox(w - 2*t, h - 2*t, l + 2)
        main_inner.translate(FreeCAD.Vector(-(w-2*t)/2, -(h-2*t)/2, -1))
        main = main.cut(main_inner)

    # Branch duct (along Y axis, centered on main)
    branch = Part.makeBox(bw, bl, bh)
    branch.translate(FreeCAD.Vector(-bw/2, -bl/2, branch_offset - bh/2))

    if t > 0 and t < min(bw, bh)/2:
        branch_inner = Part.makeBox(bw - 2*t, bl + 2, bh - 2*t)
        branch_inner.translate(FreeCAD.Vector(-(bw-2*t)/2, -bl/2 - 1, branch_offset - (bh-2*t)/2))
        branch = branch.cut(branch_inner)

    shape = main.fuse(branch)
    # shape = shape.removeSplitter()  # skipped for compatibility

    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = shape
    return obj


def build_round_tee(doc, name, diameter, length,
                    branch_diameter=200, branch_length=400,
                    branch_offset=300, thickness=0.7):
    """Round tee — main duct + perpendicular branch."""
    d = float(diameter)
    l = float(length)
    bd = float(branch_diameter)
    bl = float(branch_length)
    t = float(thickness)
    r = d / 2
    br = bd / 2

    # Main duct
    main = Part.makeCylinder(r, l)
    if t > 0 and t < r:
        main_inner = Part.makeCylinder(r - t, l + 2)
        main_inner.translate(FreeCAD.Vector(0, 0, -1))
        main = main.cut(main_inner)

    # Branch (along Y)
    branch = Part.makeCylinder(br, bl)
    branch.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0, 0), 90)
    branch.translate(FreeCAD.Vector(0, -bl/2, branch_offset))

    if t > 0 and t < br:
        branch_inner = Part.makeCylinder(br - t, bl + 2)
        branch_inner.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0, 0), 90)
        branch_inner.translate(FreeCAD.Vector(0, -bl/2 - 1, branch_offset))
        branch = branch.cut(branch_inner)

    shape = main.fuse(branch)
    # shape = shape.removeSplitter()  # skipped for compatibility

    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = shape
    return obj


def build_rect_transition(doc, name, width, height, length,
                          end_width=300, end_height=150, thickness=0.7):
    """Rectangular transition — built as a simple tapered extrusion."""
    w1 = float(width)
    h1 = float(height)
    l = float(length)
    w2 = float(end_width)
    h2 = float(end_height)
    t = float(thickness)

    # Simple approach: create a wire profile and use makePrism or makeSweep
    # Actually, simplest reliable way: create a box and scale one end
    # But FreeCAD Part doesn't have simple taper. Use multiple boxes.

    segments = 8
    shapes = []
    for i in range(segments):
        z1 = l * i / segments
        z2 = l * (i + 1) / segments
        frac1 = i / segments
        frac2 = (i + 1) / segments

        cw1 = w1/2 + (w2/2 - w1/2) * frac1
        ch1 = h1/2 + (h2/2 - h1/2) * frac1
        cw2 = w1/2 + (w2/2 - w1/2) * frac2
        ch2 = h1/2 + (h2/2 - h1/2) * frac2

        # Average dimensions for this segment
        cw = (cw1 + cw2) / 2
        ch = (ch1 + ch2) / 2
        seg_len = z2 - z1 + 0.1

        box = Part.makeBox(2*cw, 2*ch, seg_len)
        box.translate(FreeCAD.Vector(-cw, -ch, z1))
        shapes.append(box)

    if shapes:
        shape = shapes[0]
        for s in shapes[1:]:
            shape = shape.fuse(s)
        # shape = shape.removeSplitter()  # skipped for compatibility
    else:
        shape = Part.makeBox(w1, h1, l)
        shape.translate(FreeCAD.Vector(-w1/2, -h1/2, 0))

    # Hollow
    if t > 0 and t < min(w1, h1, w2, h2) / 2:
        inner_shapes = []
        for i in range(segments):
            z1 = l * i / segments
            z2 = l * (i + 1) / segments
            frac1 = i / segments
            frac2 = (i + 1) / segments

            cw1 = (w1 - 2*t)/2 + ((w2 - 2*t)/2 - (w1 - 2*t)/2) * frac1
            ch1 = (h1 - 2*t)/2 + ((h2 - 2*t)/2 - (h1 - 2*t)/2) * frac1
            cw2 = (w1 - 2*t)/2 + ((w2 - 2*t)/2 - (w1 - 2*t)/2) * frac2
            ch2 = (h1 - 2*t)/2 + ((h2 - 2*t)/2 - (h1 - 2*t)/2) * frac2

            cw = (cw1 + cw2) / 2
            ch = (ch1 + ch2) / 2
            seg_len = z2 - z1 + 0.2

            box = Part.makeBox(2*cw, 2*ch, seg_len)
            box.translate(FreeCAD.Vector(-cw, -ch, z1 - 0.1))
            inner_shapes.append(box)

        if inner_shapes:
            inner = inner_shapes[0]
            for s in inner_shapes[1:]:
                inner = inner.fuse(s)
            # inner = inner.removeSplitter()  # skipped
            shape = shape.cut(inner)

    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = shape
    return obj


def build_round_transition(doc, name, diameter, length,
                           end_diameter=300, thickness=0.7):
    """Round transition — approximated as a truncated cone."""
    d1 = float(diameter)
    l = float(length)
    d2 = float(end_diameter)
    t = float(thickness)
    r1 = d1 / 2
    r2 = d2 / 2

    # Create truncated cone using makeCone
    # makeCone(radius1, radius2, height)
    # But we need it centered, so we adjust
    shape = Part.makeCone(r1, r2, l)
    # makeCone creates cone with apex at origin, base at z=height
    # We need to center it: shift so center is at z=l/2
    shape.translate(FreeCAD.Vector(0, 0, 0))

    if t > 0 and t < min(r1, r2):
        inner = Part.makeCone(r1 - t, r2 - t, l + 2)
        inner.translate(FreeCAD.Vector(0, 0, -1))
        shape = shape.cut(inner)

    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = shape
    return obj


def build_rect_cap(doc, name, width, height, profile=30, depth=30, thickness=0.7):
    """Rectangular cap."""
    w = float(width)
    h = float(height)
    p = float(profile)
    d = float(depth)
    t = float(thickness)
    ow = w + 2*p
    oh = h + 2*p

    outer = Part.makeBox(ow, oh, d)
    outer.translate(FreeCAD.Vector(-ow/2, -oh/2, 0))

    if t > 0 and t < min(ow, oh)/2:
        inner = Part.makeBox(ow - 2*t, oh - 2*t, d + 2)
        inner.translate(FreeCAD.Vector(-(ow-2*t)/2, -(oh-2*t)/2, -1))
        shape = outer.cut(inner)
    else:
        shape = outer

    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = shape
    return obj


def build_round_cap(doc, name, diameter, depth=30, thickness=0.7):
    """Round cap."""
    d = float(diameter)
    dep = float(depth)
    t = float(thickness)
    r = d / 2

    outer = Part.makeCylinder(r, dep)
    if t > 0 and t < r:
        inner = Part.makeCylinder(r - t, dep + 2)
        inner.translate(FreeCAD.Vector(0, 0, -1))
        shape = outer.cut(inner)
    else:
        shape = outer

    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = shape
    return obj


def build_flexible(doc, name, width, height, length):
    """Flexible connector — corrugated tube approximation."""
    w = float(width)
    h = float(height)
    l = float(length)
    # Approximate as a series of alternating cylinders
    segments = max(4, int(l / 50))
    shapes = []
    for i in range(segments):
        z = l * i / segments
        seg_len = l / segments + 0.5
        r = w/2 + 3 * math.sin(2 * math.pi * i / segments * 3)
        cyl = Part.makeCylinder(r, seg_len)
        cyl.translate(FreeCAD.Vector(0, 0, z))
        shapes.append(cyl)

    if shapes:
        shape = shapes[0]
        for s in shapes[1:]:
            shape = shape.fuse(s)
        # shape = shape.removeSplitter()  # skipped for compatibility
    else:
        shape = Part.makeCylinder(w/2, l)

    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = shape
    return obj


def build_default(doc, name, width, height, length, thickness=0.7):
    """Default fallback — simple box."""
    w = float(width) if width else 100
    h = float(height) if height else 100
    l = float(length) if length else 100
    box = Part.makeBox(w, h, l)
    box.translate(FreeCAD.Vector(-w/2, -h/2, 0))
    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = box
    return obj


# ═══════════════════════════════════════════════════════════
# POSITIONING
# ═══════════════════════════════════════════════════════════

def get_bounds(product_data):
    """Get bounding box depth for positioning."""
    ptype = detect_type(product_data)
    w = float(product_data.get("width", 100))
    h = float(product_data.get("height", 100))
    l = float(product_data.get("length", 1000))

    if ptype in ("rect_duct", "round_duct", "flexible"):
        return l
    elif ptype in ("rect_flange", "round_flange"):
        return float(product_data.get("profile", 30))
    elif ptype in ("rect_elbow", "round_elbow"):
        angle = float(product_data.get("angle", 90))
        radius = float(product_data.get("radius", 150))
        rad = math.radians(angle)
        return radius * math.sin(rad) + w * 0.5
    elif ptype in ("rect_tee", "round_tee"):
        return l
    elif ptype in ("rect_transition", "round_transition"):
        return l
    elif ptype in ("rect_cap", "round_cap"):
        return float(product_data.get("depth", 30))
    return l


def build_product(doc, product_data, index=0, z_offset=0):
    """Build a single product and position it."""
    name = product_data.get("name", "Product_" + str(index))
    ptype = detect_type(product_data)
    width = product_data.get("width", 100)
    height = product_data.get("height", 100)
    length = product_data.get("length", 1000)
    thickness = product_data.get("thickness", 0.7)

    pt = ptype

    if pt == "rect_duct":
        obj = build_rect_duct(doc, name, width, height, length, thickness)
    elif pt == "round_duct":
        obj = build_round_duct(doc, name, width, length, thickness)
    elif pt == "rect_flange":
        profile = product_data.get("profile", 30)
        obj = build_rect_flange(doc, name, width, height, profile, thickness)
    elif pt == "round_flange":
        profile = product_data.get("profile", 30)
        obj = build_round_flange(doc, name, width, profile, thickness)
    elif pt == "rect_elbow":
        angle = product_data.get("angle", 90)
        radius = product_data.get("radius", 150)
        obj = build_rect_elbow(doc, name, width, height, angle, radius, thickness)
    elif pt == "round_elbow":
        angle = product_data.get("angle", 90)
        radius = product_data.get("radius", 150)
        obj = build_round_elbow(doc, name, width, angle, radius, thickness)
    elif pt == "rect_tee":
        bw = product_data.get("branch_width", 200)
        bh = product_data.get("branch_height", 200)
        bl = product_data.get("branch_length", 400)
        bo = product_data.get("branch_offset", length/2)
        obj = build_rect_tee(doc, name, width, height, length, bw, bh, bl, bo, thickness)
    elif pt == "round_tee":
        bd = product_data.get("branch_diameter", 200)
        bl = product_data.get("branch_length", 400)
        bo = product_data.get("branch_offset", length/2)
        obj = build_round_tee(doc, name, width, length, bd, bl, bo, thickness)
    elif pt == "rect_transition":
        ew = product_data.get("end_width", 300)
        eh = product_data.get("end_height", 150)
        obj = build_rect_transition(doc, name, width, height, length, ew, eh, thickness)
    elif pt == "round_transition":
        ed = product_data.get("end_diameter", 300)
        obj = build_round_transition(doc, name, width, length, ed, thickness)
    elif pt == "rect_cap":
        profile = product_data.get("profile", 30)
        depth = product_data.get("depth", 30)
        obj = build_rect_cap(doc, name, width, height, profile, depth, thickness)
    elif pt == "round_cap":
        depth = product_data.get("depth", 30)
        obj = build_round_cap(doc, name, width, depth, thickness)
    elif pt == "flexible":
        obj = build_flexible(doc, name, width, height, length)
    else:
        obj = build_default(doc, name, width, height, length, thickness)

    # Apply positioning
    obj.Placement = FreeCAD.Placement(
        FreeCAD.Vector(0, 0, z_offset),
        FreeCAD.Rotation()
    )

    # Apply color
    color = TYPE_COLORS.get(pt, TYPE_COLORS["default"])
    set_color(obj, color)

    return obj


# ═══════════════════════════════════════════════════════════
# DIMENSIONS
# ═══════════════════════════════════════════════════════════

def add_dimension(doc, p1, p2, text, offset=20):
    """Add a dimension line between two points."""
    try:
        line = Draft.makeWire([FreeCAD.Vector(p1[0], p1[1], p1[2]),
                                FreeCAD.Vector(p2[0], p2[1], p2[2])])
        if hasattr(line, "ViewObject"):
            line.ViewObject.DrawStyle = "Dash"
            line.ViewObject.LineColor = (0.3, 0.3, 0.3)

        mid = [(p1[i] + p2[i])/2 for i in range(3)]
        # Offset text perpendicular to line (simplified: just offset in Y)
        label = Draft.makeText([text], placement=FreeCAD.Placement(
            FreeCAD.Vector(mid[0], mid[1] + offset, mid[2]),
            FreeCAD.Rotation()
        ))
        if hasattr(label, "ViewObject"):
            label.ViewObject.FontSize = 8
            label.ViewObject.TextColor = (0.2, 0.2, 0.2)
    except Exception as e:
        print("  Dimension error: " + str(e))


def add_product_dimensions(doc, product_data, z_offset):
    """Add dimensions for a product."""
    ptype = detect_type(product_data)
    w = float(product_data.get("width", 100))
    h = float(product_data.get("height", 100))
    l = float(product_data.get("length", 1000))

    # Overall length dimension
    add_dimension(doc,
                  (0, -h/2 - 30, z_offset),
                  (0, -h/2 - 30, z_offset + l),
                  str(int(l)) + " мм", offset=10)

    # Width/height at start
    if ptype.startswith("rect"):
        add_dimension(doc,
                      (-w/2, -h/2 - 30, z_offset),
                      (w/2, -h/2 - 30, z_offset),
                      str(int(w)) + "x" + str(int(h)), offset=10)
    elif ptype.startswith("round"):
        add_dimension(doc,
                      (-w/2, -h/2 - 30, z_offset),
                      (w/2, -h/2 - 30, z_offset),
                      "D=" + str(int(w)), offset=10)


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 4:
        print("Usage: freecadcmd.exe freecad_macro.py <json_path> <output_path> <format>")
        sys.exit(1)

    json_path = sys.argv[1]
    output_path = sys.argv[2]
    fmt = sys.argv[3].lower()

    import tempfile
    log_path = os.path.join(tempfile.gettempdir(), "freecad_export.log")

    if not os.path.exists(json_path):
        print("ERROR: JSON file not found: " + str(json_path))
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    print("Loaded " + str(len(products)) + " products")

    doc = FreeCAD.newDocument("Ventilation")
    spacing = 50.0
    z_offset = 0.0

    for i, product in enumerate(products):
        try:
            obj = build_product(doc, product, i, z_offset)
            print("  Built: " + str(product.get("name", "Unknown")) +
                  " [" + detect_type(product) + "] at Z=" + str(round(z_offset, 1)))
            z_offset += get_bounds(product) + spacing
        except Exception as e:
            print("  ERROR building " + str(product.get("name", "Unknown")) + ": " + str(e))
            import traceback
            traceback.print_exc()

    try:
        doc.recompute()
    except Exception as e:
        print("WARNING: recompute failed: " + str(e))

    # ═══ EXPORT ═══
    log_lines = []
    def _log(msg):
        line = str(msg)
        log_lines.append(line)
        print(line)

    _log("=== EXPORT START ===")
    _log("Format: " + fmt)
    _log("Output: " + str(output_path))
    _log("FreeCAD: " + str(FreeCAD.Version()))
    _log("Log: " + log_path)

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        try:
            os.makedirs(out_dir)
            _log("Created dir: " + out_dir)
        except Exception as e:
            _log("ERROR creating dir: " + str(e))

    export_objects = [obj for obj in doc.Objects if hasattr(obj, "Shape")]
    _log("Objects with Shape: " + str(len(export_objects)))

    if not export_objects:
        _log("ERROR: No objects")
        _write_log(log_path, log_lines)
        sys.exit(1)

    success = False

    if fmt == "fcstd":
        try:
            doc.saveAs(output_path)
            success = os.path.exists(output_path)
            _log("FCStd result: " + str(success))
        except Exception as e:
            _log("FCStd error: " + str(e))

    elif fmt in ("step", "stp"):
        try:
            import Import
            _log("Trying Import.export(objects)...")
            Import.export(export_objects, output_path)
            success = os.path.exists(output_path) and os.path.getsize(output_path) > 0
            _log("Result: " + str(success))
        except Exception as e:
            _log("Failed: " + str(e))

        if not success:
            try:
                _log("Trying Import.export([doc])...")
                Import.export([doc], output_path)
                success = os.path.exists(output_path) and os.path.getsize(output_path) > 0
                _log("Result: " + str(success))
            except Exception as e:
                _log("Failed: " + str(e))

        if not success:
            try:
                shapes = [obj.Shape for obj in export_objects]
                compound = Part.makeCompound(shapes)
                _log("Trying compound.exportStep...")
                compound.exportStep(output_path)
                success = os.path.exists(output_path) and os.path.getsize(output_path) > 0
                _log("Result: " + str(success))
            except Exception as e:
                _log("Failed: " + str(e))

    elif fmt == "stl":
        try:
            import Mesh
            meshes = []
            for obj in export_objects:
                try:
                    m = Mesh.Mesh(obj.Shape.tessellate(0.5))
                    meshes.append(m)
                except Exception as e:
                    _log("Mesh error: " + str(e))
            if meshes:
                Mesh.export(meshes, output_path)
                success = os.path.exists(output_path) and os.path.getsize(output_path) > 0
                _log("Result: " + str(success))
        except Exception as e:
            _log("Failed: " + str(e))

    elif fmt == "obj":
        try:
            meshes = []
            for obj in export_objects:
                try:
                    m = Mesh.Mesh(obj.Shape.tessellate(0.5))
                    meshes.append(m)
                except Exception as e:
                    _log("Mesh error: " + str(e))
            if meshes:
                Mesh.export(meshes, output_path)
                success = os.path.exists(output_path) and os.path.getsize(output_path) > 0
                _log("Result: " + str(success))
        except Exception as e:
            _log("Failed: " + str(e))

    elif fmt in ("iges", "igs"):
        try:
            Import.export(export_objects, output_path)
            success = os.path.exists(output_path) and os.path.getsize(output_path) > 0
            _log("Result: " + str(success))
        except Exception as e:
            _log("Failed: " + str(e))

    else:
        _log("ERROR: Unknown format: " + str(fmt))

    _write_log(log_path, log_lines)

    if not success:
        print("\n".join(log_lines))
        sys.exit(1)

    print("\n".join(log_lines))
    print("Done! Total Z-span: " + str(round(z_offset, 1)) + " mm")


def _write_log(log_path, lines):
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print("Log written to: " + log_path)
    except Exception as e:
        print("Could not write log: " + str(e))


if __name__ == "__main__":
    main()
