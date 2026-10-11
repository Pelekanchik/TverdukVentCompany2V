"""Імпорт деталей з DXF-креслень у замовлення на розкрій.

Розпізнає замкнуті контури (LWPOLYLINE, POLYLINE, HATCH) на всіх
модельних просторах листів, рахує їхні габаритні розміри в міліметрах,
групує однакові розміри в позиції з кількістю і перетворює їх у формат
виробів вкладки «Розкрій».

Вимагає пакет ezdxf; при його відсутності викидає ValueError із
зрозумілим повідомленням (не ImportError, щоб GUI міг показати діалог).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

# Деталі менші за ці значення по будь-якій осі — технічний шум (текст,
# засічки, маркери), їх ігноруємо.
MIN_PART_SIZE_MM = 20

# Сутності, що можуть описувати контур деталі. Тільки замкнуті!
_CLOSED_ENTITY_TYPES = ("LWPOLYLINE", "POLYLINE", "HATCH")


def _load_ezdxf():
    """Підвантажити ezdxf з читабельною помилкою, якщо його немає."""
    try:
        import ezdxf  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover
        raise ValueError(
            "Бібліотека ezdxf не встановлена. " "Виконайте: pip install ezdxf, і повторіть імпорт."
        ) from exc
    return ezdxf


def _entity_bbox(entity) -> tuple[float, float, float, float] | None:
    """Габаритний бокс сутності (min_x, min_y, max_x, max_y) або None.

    Товста лінія / незамкнений полілінійний контур дає None.
    """
    ezdxf = _load_ezdxf()
    try:
        from ezdxf import bbox  # noqa: PLC0415

        box = bbox.extents([entity], fast=True)
    except Exception:  # noqa: BLE001 — ezdxf кидає різні винятки на кривих DXF
        return None
    if box is None or not box.has_data:
        return None
    return (box.extmin.x, box.extmin.y, box.extmax.x, box.extmax.y)


def _is_closed(entity) -> bool:
    """Чи є сутність замкнутим контуром."""
    dxftype = entity.dxftype()
    if dxftype == "LWPOLYLINE":
        return bool(entity.closed)
    if dxftype == "POLYLINE":
        return bool(entity.is_2d_polyline_closed or entity.is_3d_polyline_closed)
    return dxftype == "HATCH"  # штриховка завжди замкнута


def _iter_modelspaces(doc):
    """Усі простори моделі документа (модель + паперові листи з моделлю)."""
    yield doc.modelspace()
    # Паперові листи зазвичай містять рамки/штампи — пропускаємо,
    # щоб не розпізнавати рамку креслення як деталь.


def parse_dxf_parts(path: str | Path) -> list[dict]:
    """Розпарсити DXF-файл і повернути список унікальних деталей.

    Args:
        path: Шлях до .dxf файлу.

    Returns:
        Список словників виду
        ``{"width": int, "height": int, "quantity": int}``
        відсортований за спаданням площі. Однакові розміри
        (незалежно від орієнтації, 500×300 ≡ 300×500) згруповані
        в одну позицію зі зведеною кількістю.

    Raises:
        ValueError: Файл не знайдено, пошкоджений, не читається
            або в ньому немає розпізнаних деталей.
    """
    ezdxf = _load_ezdxf()
    path = Path(path)
    if not path.exists():
        raise ValueError(f"Файл не знайдено: {path}")

    try:
        doc = ezdxf.readfile(str(path))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Не вдалося прочитати DXF-файл: {exc}") from exc

    sizes: Counter[tuple[int, int]] = Counter()
    for msp in _iter_modelspaces(doc):
        for entity in msp:
            if entity.dxftype() not in _CLOSED_ENTITY_TYPES:
                continue
            if not _is_closed(entity):
                continue
            box = _entity_bbox(entity)
            if box is None:
                continue
            min_x, min_y, max_x, max_y = box
            width = round(max_x - min_x)
            height = round(max_y - min_y)
            # Відсів шуму: точки, лінії, надто дрібні елементи
            if width < MIN_PART_SIZE_MM or height < MIN_PART_SIZE_MM:
                continue
            # Канонічний порядок розмірів, щоб 500×300 і 300×500
            # групувалися як одна деталь (у розкрої ротація дозволена)
            lo, hi = (width, height) if width <= height else (height, width)
            sizes[(lo, hi)] += 1

    if not sizes:
        raise ValueError(
            "У файлі не знайдено замкнутих контурів-деталей "
            "(LWPOLYLINE/POLYLINE/HATCH розміром від 20 мм)."
        )

    parts = [{"width": w, "height": h, "quantity": qty} for (w, h), qty in sizes.items()]
    parts.sort(key=lambda p: p["width"] * p["height"], reverse=True)
    return parts


def parts_to_products(parts: list[dict], prefix: str = "Деталь") -> list[dict]:
    """Перетворити деталі у формат виробів вкладки «Розкрій».

    Args:
        parts: Результат ``parse_dxf_parts``.
        prefix: Префікс назви виробу (напр. позначення листа/виробу).

    Returns:
        Список словників, сумісних із ``CuttingTab._products``.
    """
    products = []
    for part in parts:
        width = int(part["width"])
        height = int(part["height"])
        products.append(
            {
                "name": f"{prefix} {width}×{height}",
                "type": "деталь з DXF",
                "width": width,
                "height": height,
                "length": 0,
                "quantity": int(part["quantity"]),
            }
        )
    return products


def import_dxf_to_products(path: str | Path) -> list[dict]:
    """Комбінований помічник: DXF → готові вироби для розкрою."""
    return parts_to_products(parse_dxf_parts(path))
