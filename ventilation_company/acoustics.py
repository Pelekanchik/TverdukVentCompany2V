"""Акустичний розрахунок вентиляційних систем.

Розрахунок рівня шуму від:
  • Вентиляторів (звукова потужність Lw)
  • Повітряного потоку в повітропроводах
  • Місцевих опорів (відводи, трійники, решітки)
  • Підбір шумоглушників
  • Підсумковий рівень шуму у приміщенні Lp

Норми згідно з ДБН В.1.1-31:2013, СНиП 23-03-2003.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── НОРМИ ШУМУ ДЛЯ РІЗНИХ ПРИМІЩЕНЬ (дБА) ──
NOISE_LIMITS = {
    "офіс": 45,
    "житлове": 40,
    "готель": 35,
    "лікарня": 35,
    "школа_клас": 40,
    "ресторан": 55,
    "магазин": 55,
    "виробництво_легке": 65,
    "виробництво_важке": 75,
    "коридор": 50,
    "технічне": 70,
}


# ── ОКТАВНІ СМУГИ (Гц) ──
OCTAVE_BANDS = [63, 125, 250, 500, 1000, 2000, 4000, 8000]


class SilencerType(Enum):
    """Тип шумоглушника."""
    PLATE = "пластинчастий"
    BAFFLE = "ламельний"
    CIRCULAR = "круглий"
    ACTIVE = "активний (електронний)"


@dataclass
class Silencer:
    """Шумоглушник."""
    name: str
    silencer_type: SilencerType
    length_mm: float
    width_mm: float
    height_mm: float
    # Зниження шуму по октавних смугах (дБ)
    attenuation: dict[int, float] = field(default_factory=dict)
    pressure_drop_pa: float = 50.0
    price: float = 0.0

    def get_attenuation_db(self, frequency: int) -> float:
        """Отримати зниження для конкретної частоти."""
        return self.attenuation.get(frequency, 0.0)

    def get_total_attenuation(self) -> float:
        """Середнє зниження по октавах."""
        if not self.attenuation:
            return 0.0
        return sum(self.attenuation.values()) / len(self.attenuation)


# ── КАТАЛОГ ШУМОГЛУШНИКІВ ──
SILENCER_CATALOG = [
    Silencer(
        name="Шумоглушник пластинчастий СП-300×200-600",
        silencer_type=SilencerType.PLATE,
        length_mm=600, width_mm=300, height_mm=200,
        attenuation={63: 3, 125: 8, 250: 15, 500: 22, 1000: 28, 2000: 25, 4000: 18, 8000: 12},
        pressure_drop_pa=45, price=4200,
    ),
    Silencer(
        name="Шумоглушник пластинчастий СП-300×200-900",
        silencer_type=SilencerType.PLATE,
        length_mm=900, width_mm=300, height_mm=200,
        attenuation={63: 5, 125: 12, 250: 22, 500: 32, 1000: 38, 2000: 35, 4000: 25, 8000: 18},
        pressure_drop_pa=65, price=5800,
    ),
    Silencer(
        name="Шумоглушник пластинчастий СП-400×300-1200",
        silencer_type=SilencerType.PLATE,
        length_mm=1200, width_mm=400, height_mm=300,
        attenuation={63: 8, 125: 18, 250: 28, 500: 38, 1000: 45, 2000: 42, 4000: 32, 8000: 22},
        pressure_drop_pa=85, price=8500,
    ),
    Silencer(
        name="Шумоглушник ламельний СЛ-315-600 (круглий)",
        silencer_type=SilencerType.BAFFLE,
        length_mm=600, width_mm=315, height_mm=315,
        attenuation={63: 4, 125: 10, 250: 18, 500: 26, 1000: 32, 2000: 30, 4000: 22, 8000: 15},
        pressure_drop_pa=40, price=6500,
    ),
    Silencer(
        name="Шумоглушник ламельний СЛ-315-900 (круглий)",
        silencer_type=SilencerType.BAFFLE,
        length_mm=900, width_mm=315, height_mm=315,
        attenuation={63: 6, 125: 15, 250: 25, 500: 35, 1000: 42, 2000: 38, 4000: 28, 8000: 20},
        pressure_drop_pa=60, price=9200,
    ),
    Silencer(
        name="Шумоглушник круглий СК-200-600",
        silencer_type=SilencerType.CIRCULAR,
        length_mm=600, width_mm=200, height_mm=200,
        attenuation={63: 2, 125: 6, 250: 12, 500: 18, 1000: 24, 2000: 22, 4000: 16, 8000: 10},
        pressure_drop_pa=30, price=3800,
    ),
    Silencer(
        name="Шумоглушник круглий СК-250-900",
        silencer_type=SilencerType.CIRCULAR,
        length_mm=900, width_mm=250, height_mm=250,
        attenuation={63: 4, 125: 10, 250: 18, 500: 26, 1000: 32, 2000: 30, 4000: 22, 8000: 15},
        pressure_drop_pa=45, price=5200,
    ),
]


@dataclass
class NoiseSource:
    """Джерело шуму (вентилятор, потік, решітка)."""
    name: str
    source_type: str  # "fan", "flow", "grille", "damper"
    # Звукова потужність Lw (дБ) по октавних смугах
    lw_octave: dict[int, float] = field(default_factory=dict)
    # Загальний LwA (дБА)
    lwa: float = 0.0

    def get_lw_total(self) -> float:
        """Загальний рівень звукової потужності."""
        if self.lwa > 0:
            return self.lwa
        if self.lw_octave:
            # Сума енергетична
            total = 10 * math.log10(sum(10 ** (v / 10) for v in self.lw_octave.values()))
            return total
        return 0.0


@dataclass
class DuctPath:
    """Акустичний шлях від джерела до приміщення."""
    name: str
    length_m: float = 0.0
    diameter_mm: float = 300.0
    is_circular: bool = False
    # Зниження шуму на шляху поширення (дБ/м)
    attenuation_per_meter: float = 0.5
    # Кількість відводів, трійників
    elbow_count: int = 0
    tee_count: int = 0
    # Зниження на кожен відвід/трійник (дБ)
    elbow_attenuation: float = 3.0
    tee_attenuation: float = 4.0
    # Решітка на виході
    has_grille: bool = False
    grille_attenuation: float = 0.0  # решітка НЕ знижує, а додає шум

    def get_path_attenuation(self) -> float:
        """Загальне зниження на шляху (дБ)."""
        duct_att = self.length_m * self.attenuation_per_meter
        fitting_att = self.elbow_count * self.elbow_attenuation + self.tee_count * self.tee_attenuation
        return duct_att + fitting_att


@dataclass
class Room:
    """Приміщення-рецептор шуму."""
    name: str
    room_type: str = "офіс"  # ключ з NOISE_LIMITS
    volume_m3: float = 50.0
    absorption_m2: float = 10.0  # еквівалентна площа поглинання

    @property
    def noise_limit_dba(self) -> int:
        return NOISE_LIMITS.get(self.room_type, 45)

    def calculate_lp(self, lw_source: float, path_attenuation: float = 0.0,
                     silencer_attenuation: float = 0.0) -> float:
        """Розрахувати рівень звукового тиску у приміщенні.

        Lp = Lw - path_attenuation - silencer_attenuation - 10*log10(A) + 6
        де A — еквівалентна площа поглинання
        """
        if self.absorption_m2 <= 0:
            self.absorption_m2 = 1.0
        lp = lw_source - path_attenuation - silencer_attenuation
        lp -= 10 * math.log10(self.absorption_m2)
        lp += 6  # поправка на дифузне поле
        return lp


class AcousticCalculator:
    """Калькулятор акустичного розрахунку."""

    # Коефіцієнти для розрахунку шуму вентилятора
    # Lw = Lw_ref + 10*log10(Q) + 20*log10(p) + correction
    FAN_NOISE_BASE = {
        "осьовий": 35,
        "радіальний": 40,
        "канальний": 30,
        "діагональний": 32,
    }

    # Шум від повітряного потоку
    # Lw_flow = 10*log10(v^8 * S) + const
    FLOW_NOISE_CONST = -60

    @staticmethod
    def calculate_fan_noise(fan_type: str, air_flow_m3h: float, pressure_pa: float,
                            fan_power_kw: float = 0.0) -> NoiseSource:
        """Розрахувати шум вентилятора.

        Args:
            fan_type: тип вентилятора (осьовий/радіальний/канальний)
            air_flow_m3h: повітряний потік, м³/год
            pressure_pa: тиск, Па
            fan_power_kw: потужність, кВт
        """
        base = AcousticCalculator.FAN_NOISE_BASE.get(fan_type, 40)

        # Основна формула: Lw ≈ base + 10*log10(Q) + 20*log10(p/100)
        q_term = 10 * math.log10(max(air_flow_m3h, 1))
        p_term = 20 * math.log10(max(pressure_pa / 100, 1))

        lwa = base + q_term + p_term

        # Корекція по потужності
        if fan_power_kw > 0:
            lwa += 5 * math.log10(max(fan_power_kw, 0.1))

        # Розподіл по октавах (типовий спектр для вентилятора)
        # Низькі частоти сильніші
        octave_distribution = {
            63: 1.0, 125: 0.9, 250: 0.85, 500: 0.8,
            1000: 0.75, 2000: 0.7, 4000: 0.6, 8000: 0.5,
        }

        lw_octave = {}
        for freq, coeff in octave_distribution.items():
            lw_octave[freq] = lwa + 10 * math.log10(coeff)

        return NoiseSource(
            name=f"Вентилятор {fan_type}",
            source_type="fan",
            lw_octave=lw_octave,
            lwa=lwa,
        )

    @staticmethod
    def calculate_flow_noise(velocity_ms: float, duct_area_m2: float) -> NoiseSource:
        """Розрахувати шум від повітряного потоку.

        Args:
            velocity_ms: швидкість повітря, м/с
            duct_area_m2: площа перерізу, м²
        """
        if velocity_ms < 3:
            lwa = 0  # нижче 3 м/с шум незначний
        else:
            # Емпірична формула
            lwa = 10 * math.log10(velocity_ms ** 8 * duct_area_m2) + AcousticCalculator.FLOW_NOISE_CONST
            lwa = max(0, lwa)

        return NoiseSource(
            name="Повітряний потік",
            source_type="flow",
            lwa=lwa,
        )

    @staticmethod
    def calculate_grille_noise(velocity_ms: float, grille_area_m2: float) -> NoiseSource:
        """Розрахувати шум від решітки/дифузора.

        Високошвидкісні решітки створюють значний шум.
        """
        if velocity_ms < 2:
            lwa = 0
        else:
            # Lw = 10*log10(v^6 * A) + const
            lwa = 10 * math.log10(velocity_ms ** 6 * grille_area_m2) - 45
            lwa = max(0, lwa)

        return NoiseSource(
            name="Решітка/дифузор",
            source_type="grille",
            lwa=lwa,
        )

    @staticmethod
    def calculate_total_noise(sources: list[NoiseSource]) -> float:
        """Сумарний рівень шуму від кількох джерел (енергетичне складання)."""
        total = 0.0
        for src in sources:
            total += 10 ** (src.get_lw_total() / 10)
        if total <= 0:
            return 0.0
        return 10 * math.log10(total)

    @staticmethod
    def select_silencer(required_attenuation: float, duct_width: float, duct_height: float,
                        max_pressure_drop: float = 100.0) -> Optional[Silencer]:
        """Підібрати шумоглушник.

        Args:
            required_attenuation: необхідне зниження, дБ
            duct_width: ширина повітропроводу, мм
            duct_height: висота, мм
            max_pressure_drop: максимальні втрати тиску, Па
        """
        candidates = []
        for sil in SILENCER_CATALOG:
            # Перевірка розміру
            if sil.width_mm < duct_width * 0.8 or sil.height_mm < duct_height * 0.8:
                continue
            if sil.width_mm > duct_width * 1.5 or sil.height_mm > duct_height * 1.5:
                continue
            if sil.pressure_drop_pa > max_pressure_drop:
                continue
            att = sil.get_total_attenuation()
            if att >= required_attenuation * 0.7:  # допуск 30%
                score = att - required_attenuation
                candidates.append((score, sil))

        if candidates:
            candidates.sort(key=lambda x: abs(x[0]))
            return candidates[0][1]
        return None


@dataclass
class AcousticReport:
    """Повний акустичний звіт."""
    room_name: str
    room_type: str
    noise_limit: int
    sources: list[NoiseSource] = field(default_factory=list)
    duct_path: Optional[DuctPath] = None
    silencer: Optional[Silencer] = None

    @property
    def source_lw_total(self) -> float:
        return AcousticCalculator.calculate_total_noise(self.sources)

    @property
    def path_attenuation(self) -> float:
        if self.duct_path:
            return self.duct_path.get_path_attenuation()
        return 0.0

    @property
    def silencer_attenuation(self) -> float:
        if self.silencer:
            return self.silencer.get_total_attenuation()
        return 0.0

    @property
    def resulting_lp(self) -> float:
        room = Room(name=self.room_name, room_type=self.room_type)
        return room.calculate_lp(
            self.source_lw_total,
            self.path_attenuation,
            self.silencer_attenuation,
        )

    @property
    def excess_db(self) -> float:
        return max(0, self.resulting_lp - self.noise_limit)

    @property
    def is_compliant(self) -> bool:
        return self.excess_db <= 0

    def get_summary(self) -> dict:
        return {
            "room": self.room_name,
            "room_type": self.room_type,
            "noise_limit_dba": self.noise_limit,
            "source_lw": round(self.source_lw_total, 1),
            "path_attenuation": round(self.path_attenuation, 1),
            "silencer_attenuation": round(self.silencer_attenuation, 1),
            "resulting_lp": round(self.resulting_lp, 1),
            "excess": round(self.excess_db, 1),
            "compliant": self.is_compliant,
            "silencer_name": self.silencer.name if self.silencer else "не встановлено",
        }
