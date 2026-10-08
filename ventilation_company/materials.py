"""Єдиний реєстр матеріалів (металів) VentCompany.

Список матеріалів — це ключі ``material_prices`` у PricingSettings
(користувач додає нові у вкладці «Ціноутворення → Ціни на метал»).
Густини зберігаються у ключі ``material_densities`` тому ж файлі —
використовуються для розрахунку ваги виробу.

Цей модуль — чисті функції без стану: його безпечно імпортувати
з будь-якого місця (включно з cost_engine).
"""

from __future__ import annotations

# Густини за замовчуванням, кг/м³ — для відомих матеріалів.
DEFAULT_MATERIAL_DENSITIES: dict[str, float] = {
    "оцинкована сталь": 7850.0,
    "нержавіюча сталь": 7900.0,
    "алюміній": 2700.0,
}

# Густина для матеріалу, якого немає в реєстрі (сталь як найтиповіша).
FALLBACK_DENSITY_KG_M3 = 7850.0

# Стандартні товщини листового металу (мм) для нового матеріалу.
DEFAULT_THICKNESSES = ["0.5", "0.7", "0.9", "1.0", "1.2", "1.5", "2.0"]


def _key(name: str) -> str:
    return str(name or "").strip().lower()


def resolve_density(densities: dict, material: str, default: float | None = None) -> float:
    """Густина матеріалу (кг/м³) з dict {назва: густина}.

    Пошук нечутливий до регістру; спочатку дивимося у переданих densities,
    потім у DEFAULT_MATERIAL_DENSITIES, нарешті — FALLBACK_DENSITY_KG_M3.
    """
    wanted = _key(material)
    for source in (densities or {}, DEFAULT_MATERIAL_DENSITIES):
        for name, value in (source or {}).items():
            if _key(name) == wanted:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
    return float(default if default is not None else FALLBACK_DENSITY_KG_M3)


def list_materials(material_prices: dict) -> list[str]:
    """Упорядкований список назв матеріалів з dict цін."""
    names = [str(n).strip() for n in (material_prices or {}) if str(n).strip()]
    return sorted(names, key=str.lower)
