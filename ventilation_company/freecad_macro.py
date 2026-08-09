"""
FreeCAD macro for generating 3D ventilation models.
Run by: freecadcmd.exe freecad_macro.py <json_path> <output_path> <format>
"""

import json
import sys
import os

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
    FREECAD_OK = True
except ImportError:
    FREECAD_OK = False
    print("ERROR: FreeCAD modules not available")
    sys.exit(1)


def safe_name(name):
    """Transliterate Ukrainian/Russian to ASCII for FreeCAD."""
    translit = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'є': 'ye',
        'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i', 'ї': 'yi', 'й': 'y', 'к': 'k',
        'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's',
        'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh',
        'щ': 'shch', 'ь': '', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Є': 'Ye',
        'Ж': 'Zh', 'З': 'Z', 'И': 'Y', 'І': 'I', 'Ї': 'Yi', 'Й': 'Y', 'К': 'K',
        'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S',
        'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh',
        'Щ': 'Shch', 'Ь': '', 'Ю': 'Yu', 'Я': 'Ya',
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


def build_rect_duct(doc, name, width, height, length, thickness=0.7):
    w = float(width) / 2
    h = float(height) / 2
    l = float(length)
    box = Part.makeBox(float(width), float(height), l)
    box.translate(FreeCAD.Vector(-w, -h, 0))
    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = box
    return obj


def build_round_duct(doc, name, diameter, length, thickness=0.7):
    d = float(diameter)
    l = float(length)
    r = d / 2
    cyl = Part.makeCylinder(r, l)
    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = cyl
    return obj


def build_rect_flange(doc, name, width, height, profile=30):
    w = float(width)
    h = float(height)
    p = float(profile)
    outer = Part.makeBox(w + 2*p, h + 2*p, p)
    outer.translate(FreeCAD.Vector(-(w+2*p)/2, -(h+2*p)/2, 0))
    inner = Part.makeBox(w, h, p)
    inner.translate(FreeCAD.Vector(-w/2, -h/2, 0))
    shape = outer.cut(inner)
    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = shape
    return obj


def build_round_flange(doc, name, diameter, profile=30):
    d = float(diameter)
    p = float(profile)
    r = d / 2
    outer = Part.makeCylinder(r + p, p)
    inner = Part.makeCylinder(r, p)
    shape = outer.cut(inner)
    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = shape
    return obj


def build_rect_elbow(doc, name, width, height, angle=90, radius=150):
    w = float(width)
    h = float(height)
    r = float(radius)
    box = Part.makeBox(w, h, r)
    box.translate(FreeCAD.Vector(-w/2, -h/2, 0))
    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = box
    return obj


def build_rect_cap(doc, name, width, height, border=25):
    w = float(width)
    h = float(height)
    b = float(border)
    box = Part.makeBox(w + 2*b, h + 2*b, b)
    box.translate(FreeCAD.Vector(-(w+2*b)/2, -(h+2*b)/2, 0))
    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = box
    return obj


def build_round_cap(doc, name, diameter, depth=30):
    d = float(diameter)
    dep = float(depth)
    r = d / 2
    cyl = Part.makeCylinder(r, dep)
    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = cyl
    return obj


def build_flexible(doc, name, width, height, length):
    w = float(width)
    h = float(height)
    l = float(length)
    box = Part.makeBox(w, h, l)
    box.translate(FreeCAD.Vector(-w/2, -h/2, 0))
    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = box
    return obj


def build_default(doc, name, width, height, length):
    w = float(width) if width else 100
    h = float(height) if height else 100
    l = float(length) if length else 100
    box = Part.makeBox(w, h, l)
    box.translate(FreeCAD.Vector(-w/2, -h/2, 0))
    obj = doc.addObject("Part::Feature", safe_name(name))
    obj.Shape = box
    return obj


def build_product(doc, product_data, index=0):
    name = product_data.get("name", "Product_" + str(index))
    ptype = product_data.get("product_type", product_data.get("type", "")).lower().strip()
    width = product_data.get("width", 100)
    height = product_data.get("height", 100)
    length = product_data.get("length", 100)
    thickness = product_data.get("thickness", 0.7)

    pt = ptype

    if "pryamokutn" in pt or ("rect" in pt and "duct" in pt):
        if "povitroprovid" in pt or "duct" in pt:
            return build_rect_duct(doc, name, width, height, length, thickness)
        elif "flanets" in pt or "flange" in pt:
            profile = product_data.get("profile", 30)
            return build_rect_flange(doc, name, width, height, profile)
        elif "vidvid" in pt or "elbow" in pt:
            angle = product_data.get("angle", 90)
            radius = product_data.get("radius", 150)
            return build_rect_elbow(doc, name, width, height, angle, radius)
        elif "zahlushka" in pt or "cap" in pt:
            border = product_data.get("border", 25)
            return build_rect_cap(doc, name, width, height, border)

    if "krugl" in pt or "round" in pt:
        if "povitroprovid" in pt or "duct" in pt:
            return build_round_duct(doc, name, width, length, thickness)
        elif "flanets" in pt or "flange" in pt:
            profile = product_data.get("profile", 30)
            return build_round_flange(doc, name, width, profile)
        elif "zahlushka" in pt or "cap" in pt:
            depth = product_data.get("depth", 30)
            return build_round_cap(doc, name, width, depth)

    if "hnuchk" in pt or "vstavka" in pt or "flexible" in pt:
        return build_flexible(doc, name, width, height, length)

    return build_default(doc, name, width, height, length)


def main():
    if len(sys.argv) < 4:
        print("Usage: freecadcmd.exe freecad_macro.py <json_path> <output_path> <format>")
        sys.exit(1)

    json_path = sys.argv[1]
    output_path = sys.argv[2]
    fmt = sys.argv[3].lower()

    if not os.path.exists(json_path):
        print("ERROR: JSON file not found: " + str(json_path))
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    print("Loaded " + str(len(products)) + " products")

    doc = FreeCAD.newDocument("Ventilation")

    for i, product in enumerate(products):
        try:
            build_product(doc, product, i)
            print("  Built: " + str(product.get("name", "Unknown")))
        except Exception as e:
            print("  ERROR building " + str(product.get("name", "Unknown")) + ": " + str(e))

    doc.recompute()

    if fmt == "fcstd":
        doc.saveAs(output_path)
        print("Saved FCStd: " + str(output_path))
    elif fmt in ("step", "stp"):
        try:
            import Import
            shapes = [obj for obj in doc.Objects if hasattr(obj, "Shape")]
            Import.export(shapes, output_path)
            print("Saved STEP: " + str(output_path))
        except Exception as e:
            print("ERROR exporting STEP: " + str(e))
            sys.exit(1)
    elif fmt == "stl":
        try:
            import Mesh
            shapes = [obj for obj in doc.Objects if hasattr(obj, "Shape")]
            if shapes:
                Mesh.export(shapes, output_path)
            print("Saved STL: " + str(output_path))
        except Exception as e:
            print("ERROR exporting STL: " + str(e))
            sys.exit(1)
    else:
        print("ERROR: Unknown format: " + str(fmt))
        sys.exit(1)

    print("Done!")


if __name__ == "__main__":
    main()
