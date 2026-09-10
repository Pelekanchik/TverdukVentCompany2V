"""Pure markup-matrix helpers extracted from legacy Tkinter GUI."""

from __future__ import annotations

STANDARD_SIZES = {
    50,
    100,
    150,
    200,
    250,
    300,
    350,
    400,
    450,
    500,
    550,
    600,
    650,
    700,
    750,
    800,
    850,
    900,
    950,
    1000,
    1250,
}

MATERIALS = ["цинк", "нержавійка", "алюміній"]
PRODUCT_TYPES = [
    "прямокутні_труби",
    "прямокутні_фасонні",
    "круглі_труби",
    "круглі_фасонні",
]
PRODUCT_TYPE_LABELS = {
    "прямокутні_труби": "Прямокутні труби",
    "прямокутні_фасонні": "Прямокутні фасонні вироби",
    "круглі_труби": "Круглі труби",
    "круглі_фасонні": "Круглі фасонні вироби",
}
THICKNESSES = ["0.5", "0.7", "0.9", "1.0", "1.2", "1.5", "2.0"]


def is_standard_size(width=0, height=0, length=0, diameter=0):
    """Перевірити, чи всі розміри виробу стандартні."""
    dims = [d for d in [width, height, length, diameter] if d and d > 0]
    if not dims:
        return True
    return all(round(d) in STANDARD_SIZES for d in dims)


def classify_product(name="", product_type="", material=""):
    """Визначити матеріал і категорію виробу за назвою/типом/матеріалом."""
    mat_lower = material.lower()
    name_lower = (name + " " + product_type).lower()

    if "нержав" in mat_lower or "stainless" in mat_lower or "нерж" in name_lower:
        material_key = "нержавійка"
    elif "алюм" in mat_lower or "alumin" in mat_lower:
        material_key = "алюміній"
    else:
        material_key = "цинк"

    is_round = "кругл" in name_lower or "round" in name_lower or "спірал" in name_lower
    is_duct = "труб" in name_lower or "duct" in name_lower or "повітропровід" in name_lower

    if is_round:
        category = "круглі_труби" if is_duct else "круглі_фасонні"
    else:
        category = "прямокутні_труби" if is_duct else "прямокутні_фасонні"

    return material_key, category


def build_default_markup_matrix():
    """Побудувати матрицю націнок за замовчуванням."""
    matrix = {}
    for mat in MATERIALS:
        matrix[mat] = {}
        for ptype in PRODUCT_TYPES:
            matrix[mat][ptype] = {}
            for th in THICKNESSES:
                base = {"цинк": 30.0, "нержавійка": 45.0, "алюміній": 35.0}[mat]
                add = 5.0 if "фасонні" in ptype else 0.0
                th_add = float(th) * 2.0
                std = round(base + add + th_add, 1)
                nonstd = round(std + 5.0, 1)
                matrix[mat][ptype][th] = {"standard": std, "nonstandard": nonstd}
    return matrix
