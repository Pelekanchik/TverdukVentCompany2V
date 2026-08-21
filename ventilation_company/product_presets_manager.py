"""Менеджер бібліотеки типових виробів.

CRUD операції + збереження в JSON.
"""

import json
import os
import copy
from dataclasses import asdict
from pathlib import Path

from ventilation_company.standard_products import (
    RectDuct, RoundDuct, RectElbow, RoundElbow,
    RectFlange, RoundFlange, RectTee, RoundTee,
    RectTransition, RoundTransition, RectCap, RoundCap,
    FlexibleConnector, MaterialType, Thickness, StandardProduct,
)

# Мапінг типів виробів на класи
PRODUCT_CLASSES = {
    "rect_duct": RectDuct,
    "round_duct": RoundDuct,
    "rect_elbow": RectElbow,
    "round_elbow": RoundElbow,
    "rect_flange": RectFlange,
    "round_flange": RoundFlange,
    "rect_tee": RectTee,
    "round_tee": RoundTee,
    "rect_transition": RectTransition,
    "round_transition": RoundTransition,
    "rect_cap": RectCap,
    "round_cap": RoundCap,
    "flexible": FlexibleConnector,
}

DEFAULT_PRESETS_PATH = Path(__file__).parent.parent / "data" / "product_presets.json"

# Зворотна сумісність: українські назви → англійські ключі
_UA_TO_EN = {
    "повітропровід_прямокутний": "rect_duct",
    "повітропровід_круглий": "round_duct",
    "відвід_прямокутний": "rect_elbow",
    "відвід_круглий": "round_elbow",
    "фланець_прямокутний": "rect_flange",
    "фланець_круглий": "round_flange",
    "трійник_прямокутний": "rect_tee",
    "трійник_круглий": "round_tee",
    "перехід_прямокутний": "rect_transition",
    "перехід_круглий": "round_transition",
    "заглушка_прямокутна": "rect_cap",
    "заглушка_кругла": "round_cap",
    "гнучка_вставка": "flexible",
}


def _product_to_dict(product: StandardProduct) -> dict:
    """Серіалізувати продукт у dict (JSON-safe)."""
    from decimal import Decimal
    data = product.to_dict()
    # Конвертуємо Decimal → float для JSON
    for key in list(data.keys()):
        if isinstance(data[key], Decimal):
            data[key] = float(data[key])
    data["_preset_type"] = product._category.value
    return data


def _dict_to_product(data: dict) -> StandardProduct:
    """Десеріалізувати dict у продукт."""
    ptype = data.get("_preset_type", data.get("product_type", "").replace(" ", "_"))
    cls = PRODUCT_CLASSES.get(ptype)
    if cls is None:
        cls = PRODUCT_CLASSES.get(_UA_TO_EN.get(ptype))
    if cls is None:
        # fallback
        cls = StandardProduct
    return cls.from_dict(data)


class PresetsManager:
    """Менеджер бібліотеки пресетів з CRUD і збереженням у JSON."""

    def __init__(self, filepath: str | Path | None = None):
        self.filepath = Path(filepath) if filepath else DEFAULT_PRESETS_PATH
        self._presets: list[StandardProduct] = []
        self._load()

    def _load(self):
        """Завантажити пресети з JSON."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._presets = [_dict_to_product(d) for d in data]
                return
            except Exception as e:
                print(f"[PresetsManager] Помилка завантаження: {e}")
        # Якщо файлу немає — завантажуємо вбудовані
        from ventilation_company.product_presets import get_all_presets
        self._presets = get_all_presets()
        self._save()

    def _save(self):
        """Зберегти пресети у JSON."""
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            data = [_product_to_dict(p) for p in self._presets]
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[PresetsManager] Помилка збереження: {e}")

    def get_all(self) -> list[StandardProduct]:
        return copy.deepcopy(self._presets)

    def get_by_category(self) -> dict[str, list[StandardProduct]]:
        cats: dict[str, list] = {}
        for p in self._presets:
            cat = self._get_category(p)
            cats.setdefault(cat, []).append(copy.deepcopy(p))
        return cats

    def _get_category(self, product: StandardProduct) -> str:
        ptype = product.product_type.lower()
        if "повітропровід" in ptype and "прямокутн" in ptype:
            return "Прямокутні повітропроводи"
        elif "повітропровід" in ptype and "кругл" in ptype:
            return "Круглі повітропроводи"
        elif "фланець" in ptype:
            return "Фланці"
        elif "трійник" in ptype:
            return "Трійники"
        elif "перехід" in ptype:
            return "Переходи"
        elif "відвід" in ptype or "коліно" in ptype:
            return "Коліна / Відводи"
        elif "заглушка" in ptype:
            return "Заглушки"
        elif "гнучк" in ptype or "вставк" in ptype:
            return "Гнучкі вставки"
        return "Інші"

    def add(self, product: StandardProduct) -> bool:
        """Додати новий пресет."""
        # Перевірка на дублікат за назвою
        for p in self._presets:
            if p.name == product.name:
                return False
        self._presets.append(copy.deepcopy(product))
        self._save()
        return True

    def update(self, index: int, product: StandardProduct) -> bool:
        """Оновити пресет за індексом."""
        if 0 <= index < len(self._presets):
            self._presets[index] = copy.deepcopy(product)
            self._save()
            return True
        return False

    def remove(self, index: int) -> bool:
        """Видалити пресет за індексом."""
        if 0 <= index < len(self._presets):
            del self._presets[index]
            self._save()
            return True
        return False

    def find_by_name(self, name: str) -> StandardProduct | None:
        for p in self._presets:
            if p.name == name:
                return copy.deepcopy(p)
        return None

    def reset_to_defaults(self):
        """Скинути до вбудованих пресетів."""
        from ventilation_company.product_presets import get_all_presets
        self._presets = get_all_presets()
        self._save()
