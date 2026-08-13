"""Аеродинамічний розрахунок вентиляційних систем.

Розрахунок втрат тиску в повітропроводах за методикою:
  • Втрати в прямих ділянках (тертя)
  • Місцеві опори (відводи, трійники, решітки, фільтри, клапани)
  • Динамічний тиск
  • Підбір вентилятора з каталогу

Формули згідно з ДБН В.2.5-67:2013 та методичними вказівками.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── ФІЗИЧНІ КОНСТАНТИ ──
AIR_DENSITY = 1.2          # кг/м³ — густина повітря при 20°C
AIR_VISCOSITY = 15.06e-6   # м²/с — кінематична в'язкість
GRAVITY = 9.81             # м/с²


class DuctShape(Enum):
    """Форма перерізу повітропроводу."""
    RECTANGULAR = "прямокутний"
    CIRCULAR = "круглий"
    OVAL = "овальний"


class FittingType(Enum):
    """Тип фітинга / місцевого опору."""
    ELBOW_90 = "відвід 90°"
    ELBOW_45 = "відвід 45°"
    TEE_STRAIGHT = "трійник прямий"
    TEE_BRANCH = "трійник бічний"
    TEE_CONVERGING = "трійник злиття"
    REDUCER = "перехід (звуження)"
    EXPANSION = "перехід (розширення)"
    GRILLE = "решітка"
    DIFFUSER = "дифузор"
    FILTER = "фільтр"
    DAMPER = "клапан регулювальний"
    FIRE_DAMPER = "клапан вогнезатримуючий"
    SILENCER = "шумоглушник"
    HOOD = "зонт витяжний"
    LOUVER = "жалюзі"


# ── КОЕФІЦІЄНТИ МІСЦЕВИХ ОПОРІВ (ζ) ──
# Значення з довідників для вентиляційних систем
FITTING_ZETA = {
    FittingType.ELBOW_90: {
        "default": 0.8,
        "r_d_1.0": 0.5,      # R/D = 1.0
        "r_d_0.5": 1.2,      # R/D = 0.5
        "rect_sharp": 1.1,   # прямокутний без закруглення
    },
    FittingType.ELBOW_45: {
        "default": 0.4,
    },
    FittingType.TEE_STRAIGHT: {
        "default": 0.15,
        "rect": 0.2,
    },
    FittingType.TEE_BRANCH: {
        "default": 0.8,
        "rect_90": 1.0,
    },
    FittingType.TEE_CONVERGING: {
        "default": 0.3,
    },
    FittingType.REDUCER: {
        "default": 0.15,
        "gradual": 0.05,
        "sharp": 0.3,
    },
    FittingType.EXPANSION: {
        "default": 0.3,
        "gradual": 0.1,
        "sharp": 0.5,
    },
    FittingType.GRILLE: {
        "default": 2.0,
        "adjustable": 3.0,
        "fixed": 1.5,
    },
    FittingType.DIFFUSER: {
        "default": 0.5,
    },
    FittingType.FILTER: {
        "default": 80.0,     # чистий
        "dirty": 150.0,      # забруднений
    },
    FittingType.DAMPER: {
        "default": 0.5,
        "fully_open": 0.2,
        "half_open": 2.0,
    },
    FittingType.FIRE_DAMPER: {
        "default": 0.8,
    },
    FittingType.SILENCER: {
        "default": 0.6,
        "plate": 0.5,
        "baffle": 0.8,
    },
    FittingType.HOOD: {
        "default": 0.2,
        "canopy": 0.15,
    },
    FittingType.LOUVER: {
        "default": 1.5,
    },
}


@dataclass
class DuctSection:
    """Пряма ділянка повітропроводу."""
    name: str
    length: float          # м
    width: float           # мм (діаметр для круглого)
    height: float = 0      # мм (0 для круглого)
    shape: DuctShape = DuctShape.RECTANGULAR
    air_flow: float = 0.0  # м³/год
    roughness: float = 0.0001  # м — шорсткість (оцинкована сталь)

    @property
    def is_circular(self) -> bool:
        return self.shape == DuctShape.CIRCULAR

    @property
    def diameter_mm(self) -> float:
        """Еквівалентний діаметр (мм)."""
        if self.is_circular:
            return self.width
        # Для прямокутного: De = 2*a*b / (a+b)
        return 2 * self.width * self.height / (self.width + self.height)

    @property
    def diameter_m(self) -> float:
        return self.diameter_mm / 1000.0

    @property
    def area_m2(self) -> float:
        """Площа перерізу (м²)."""
        if self.is_circular:
            return math.pi * (self.diameter_m / 2) ** 2
        return (self.width / 1000.0) * (self.height / 1000.0)

    @property
    def velocity(self) -> float:
        """Швидкість повітря (м/с)."""
        if self.area_m2 <= 0:
            return 0.0
        return (self.air_flow / 3600.0) / self.area_m2

    @property
    def dynamic_pressure(self) -> float:
        """Динамічний тиск (Па)."""
        v = self.velocity
        return 0.5 * AIR_DENSITY * v ** 2

    @property
    def reynolds(self) -> float:
        """Число Рейнольдса."""
        return self.velocity * self.diameter_m / AIR_VISCOSITY

    @property
    def friction_coefficient(self) -> float:
        """Коефіцієнт тертя λ (формула Альтшуля)."""
        re = self.reynolds
        if re < 2300:
            # Ламінарний режим: λ = 64/Re
            return 64.0 / re if re > 0 else 0.05
        # Турбулентний режим
        # λ = 0.11 * (68/Re + Δ/D)^0.25
        term = 68.0 / re + self.roughness / self.diameter_m
        return 0.11 * (term ** 0.25)

    def friction_loss(self) -> float:
        """Втрати тиску на тертя (Па)."""
        if self.length <= 0 or self.velocity <= 0:
            return 0.0
        return self.friction_coefficient * (self.length / self.diameter_m) * self.dynamic_pressure


@dataclass
class Fitting:
    """Місцевий опір (фітинг)."""
    name: str
    fitting_type: FittingType
    section: DuctSection   # до якої ділянки належить
    variant: str = "default"  # підтип з FITTING_ZETA
    quantity: int = 1

    @property
    def zeta(self) -> float:
        """Коефіцієнт місцевого опору."""
        variants = FITTING_ZETA.get(self.fitting_type, {})
        return variants.get(self.variant, variants.get("default", 1.0))

    def local_loss(self) -> float:
        """Втрати тиску на місцевий опір (Па)."""
        return self.zeta * self.section.dynamic_pressure * self.quantity


@dataclass
class AerodynamicRoute:
    """Траса повітропроводу з ділянками та фітингами."""
    name: str
    system_type: str = "припливна"  # припливна / витяжна / димовидалення
    sections: list[DuctSection] = field(default_factory=list)
    fittings: list[Fitting] = field(default_factory=list)

    @property
    def total_air_flow(self) -> float:
        """Загальний повітряний потік (м³/год)."""
        if self.sections:
            return self.sections[0].air_flow
        return 0.0

    @property
    def total_length(self) -> float:
        return sum(s.length for s in self.sections)

    @property
    def total_friction_loss(self) -> float:
        return sum(s.friction_loss() for s in self.sections)

    @property
    def total_local_loss(self) -> float:
        return sum(f.local_loss() for f in self.fittings)

    @property
    def total_pressure_loss(self) -> float:
        """Загальні втрати тиску (Па)."""
        return self.total_friction_loss + self.total_local_loss

    @property
    def total_pressure_loss_mm(self) -> float:
        """Втрати тиску в мм вод. ст."""
        return self.total_pressure_loss / GRAVITY

    def get_summary(self) -> dict:
        """Отримати зведення по трасі."""
        return {
            "route_name": self.name,
            "system_type": self.system_type,
            "total_air_flow": self.total_air_flow,
            "total_length": self.total_length,
            "friction_loss_pa": self.total_friction_loss,
            "local_loss_pa": self.total_local_loss,
            "total_loss_pa": self.total_pressure_loss,
            "total_loss_mm": self.total_pressure_loss_mm,
            "section_count": len(self.sections),
            "fitting_count": len(self.fittings),
        }


# ── КАТАЛОГ ВЕНТИЛЯТОРІВ ──
FAN_CATALOG = [
    {"name": "Вентилятор осьовий ВО-300", "type": "осьовий", "flow_min": 500, "flow_max": 2500, "pressure_min": 50, "pressure_max": 200, "power": 0.25, "price": 3500, "noise": 55},
    {"name": "Вентилятор осьовий ВО-400", "type": "осьовий", "flow_min": 1500, "flow_max": 5000, "pressure_min": 80, "pressure_max": 300, "power": 0.55, "price": 4200, "noise": 58},
    {"name": "Вентилятор осьовий ВО-500", "type": "осьовий", "flow_min": 3000, "flow_max": 10000, "pressure_min": 100, "pressure_max": 400, "power": 1.1, "price": 6800, "noise": 62},
    {"name": "Вентилятор радіальний ВР-80-75 №2.5", "type": "радіальний", "flow_min": 500, "flow_max": 2500, "pressure_min": 200, "pressure_max": 800, "power": 0.37, "price": 8500, "noise": 60},
    {"name": "Вентилятор радіальний ВР-80-75 №3.15", "type": "радіальний", "flow_min": 1000, "flow_max": 5000, "pressure_min": 300, "pressure_max": 1200, "power": 0.75, "price": 12000, "noise": 63},
    {"name": "Вентилятор радіальний ВР-80-75 №4.0", "type": "радіальний", "flow_min": 2000, "flow_max": 10000, "pressure_min": 400, "pressure_max": 1800, "power": 1.5, "price": 18500, "noise": 67},
    {"name": "Вентилятор радіальний ВР-80-75 №5.0", "type": "радіальний", "flow_min": 5000, "flow_max": 20000, "pressure_min": 500, "pressure_max": 2500, "power": 3.0, "price": 28000, "noise": 70},
    {"name": "Вентилятор канальний ВК-100", "type": "канальний", "flow_min": 100, "flow_max": 500, "pressure_min": 30, "pressure_max": 150, "power": 0.04, "price": 3200, "noise": 45},
    {"name": "Вентилятор канальний ВК-125", "type": "канальний", "flow_min": 200, "flow_max": 800, "pressure_min": 50, "pressure_max": 200, "power": 0.06, "price": 3800, "noise": 48},
    {"name": "Вентилятор канальний ВК-150", "type": "канальний", "flow_min": 300, "flow_max": 1200, "pressure_min": 60, "pressure_max": 250, "power": 0.09, "price": 4500, "noise": 50},
    {"name": "Вентилятор канальний ВК-200", "type": "канальний", "flow_min": 500, "flow_max": 2000, "pressure_min": 80, "pressure_max": 350, "power": 0.12, "price": 5200, "noise": 52},
    {"name": "Вентилятор канальний ВК-250", "type": "канальний", "flow_min": 800, "flow_max": 3500, "pressure_min": 100, "pressure_max": 450, "power": 0.18, "price": 6500, "noise": 54},
    {"name": "Вентилятор канальний ВК-315", "type": "канальний", "flow_min": 1200, "flow_max": 5500, "pressure_min": 120, "pressure_max": 550, "power": 0.25, "price": 8200, "noise": 56},
]


def select_fan(air_flow: float, pressure: float, fan_type: Optional[str] = None) -> Optional[dict]:
    """Підібрати вентилятор з каталогу.

    Args:
        air_flow: повітряний потік, м³/год
        pressure: необхідний тиск, Па
        fan_type: тип вентилятора (осьовий/радіальний/канальний) або None

    Returns:
        Словник з даними вентилятора або None
    """
    candidates = []
    for fan in FAN_CATALOG:
        if fan_type and fan["type"] != fan_type:
            continue
        # Запас 15% по потоку та тиску
        if fan["flow_min"] <= air_flow * 1.15 <= fan["flow_max"]:
            if fan["pressure_min"] <= pressure * 1.15 <= fan["pressure_max"]:
                # Рейтинг: чим ближче до середини діапазону, тим краще
                flow_mid = (fan["flow_min"] + fan["flow_max"]) / 2
                pressure_mid = (fan["pressure_min"] + fan["pressure_max"]) / 2
                flow_score = 1 - abs(air_flow - flow_mid) / flow_mid
                pressure_score = 1 - abs(pressure - pressure_mid) / pressure_mid
                score = flow_score + pressure_score
                candidates.append((score, fan))

    if not candidates:
        # Спробуємо знайти найближчий
        for fan in FAN_CATALOG:
            if fan_type and fan["type"] != fan_type:
                continue
            if fan["flow_max"] >= air_flow and fan["pressure_max"] >= pressure:
                candidates.append((0, fan))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    return None


def get_all_fan_types() -> list[str]:
    """Отримати список типів вентиляторів."""
    return sorted(set(f["type"] for f in FAN_CATALOG))


def get_fitting_types() -> list[str]:
    """Отримати список типів фітингів."""
    return [ft.value for ft in FittingType]
