"""Експорт плану розкрою у G-код для плазменного різака.

Підтримує:
    • Пробивка (pierce) з затримкою
    • Контурна різка деталей
    • Швидкість холостого ходу (G0) та різання (G1)
    • Включення/виключення плазми (M3/M5)
    • Межі листа (G0 на безпечній висоті)

ВСТАНОВЛЕННЯ:
    Скопіюйте у ventilation_company/gcode_exporter.py
"""

import math
from typing import List
from dataclasses import dataclass


@dataclass
class PlasmaSettings:
    """Налаштування плазменного різака."""
    feed_rate: float = 1500.0          # мм/хв — швидкість різання
    rapid_feed: float = 8000.0         # мм/хв — швидкість холостого ходу
    pierce_delay: float = 0.5          # сек — затримка пробивки
    pierce_height: float = 3.0         # мм — висота пробивки
    cut_height: float = 1.5            # мм — висота різання
    safe_height: float = 15.0          # мм — безпечна висота
    kerf_width: float = 1.5            # мм — ширина різу (компенсація)
    lead_in_length: float = 5.0        # мм — довжина підходу
    lead_out_length: float = 5.0       # мм — довжина відходу
    unit: str = "G21"                  # G21=мм, G20=дюйми


class GCodeExporter:
    """Генератор G-коду для плазменного різака."""

    def __init__(self, settings: PlasmaSettings = None):
        self.settings = settings or PlasmaSettings()

    def export_cutting_plan(self, plan, filepath: str):
        """Експортувати план розкрою у G-код.

        Args:
            plan: CuttingPlan з листами та деталями
            filepath: шлях для збереження .nc або .tap файлу
        """
        lines = []
        lines.append("; VentCompany — G-код для плазменного різака")
        lines.append("; Генеровано автоматично")
        lines.append("")
        lines.append(self.settings.unit)       # мм
        lines.append("G90")                     # Абсолютні координати
        lines.append("G17")                     # Плоскість XY
        lines.append("G40")                     # Відміна компенсації радіуса
        lines.append("G49")                     # Відміна корекції довжини інструменту
        lines.append("G80")                     # Відміна циклів
        lines.append("")
        lines.append(f"; Налаштування плазми:")
        lines.append(f"; Швидкість різання: {self.settings.feed_rate} мм/хв")
        lines.append(f"; Швидкість холостого ходу: {self.settings.rapid_feed} мм/хв")
        lines.append(f"; Затримка пробивки: {self.settings.pierce_delay} сек")
        lines.append(f"; Висота різання: {self.settings.cut_height} мм")
        lines.append(f"; Ширина різу: {self.settings.kerf_width} мм")
        lines.append("")

        for sheet_idx, sheet in enumerate(plan.sheets):
            lines.append(f"; === ЛИСТ {sheet_idx + 1} ===")
            lines.append(f"; Розмір: {sheet.width:.0f} x {sheet.height:.0f} мм")
            lines.append("")

            # Межі листа (для візуальної перевірки)
            lines.append("; Межі листа")
            lines.append(f"G0 Z{self.settings.safe_height:.1f}")
            lines.append(f"G0 X0 Y0")
            lines.append(f"G1 X{sheet.width:.1f} Y0 F{self.settings.feed_rate:.0f}")
            lines.append(f"G1 X{sheet.width:.1f} Y{sheet.height:.1f}")
            lines.append(f"G1 X0 Y{sheet.height:.1f}")
            lines.append(f"G1 X0 Y0")
            lines.append("")

            for detail_idx, placed in enumerate(sheet.placed_details):
                d = placed.detail
                x, y = placed.x, placed.y
                w, h = placed.width, placed.height
                rotated = placed.rotated

                lines.append(f"; Деталь {detail_idx + 1}: {d.name}")
                lines.append(f"; Розмір: {w:.1f} x {h:.1f} мм")
                if rotated:
                    lines.append("; ПОВЕРНУТА на 90°")
                lines.append("")

                # Розрахунко контуру з компенсацією різу
                contour = self._calculate_contour(x, y, w, h, rotated)

                # Підхід до точки пробивки (lead-in)
                lead_in = contour[0]
                lines.append(f"; Підхід")
                lines.append(f"G0 Z{self.settings.safe_height:.1f}")
                lines.append(f"G0 X{lead_in[0]:.2f} Y{lead_in[1]:.2f}")
                lines.append("")

                # Пробивка
                lines.append("; Пробивка")
                lines.append(f"G0 Z{self.settings.pierce_height:.1f}")
                lines.append("M3 S1")          # Включити плазму
                lines.append(f"G4 P{self.settings.pierce_delay:.1f}")  # Затримка
                lines.append(f"G1 Z{self.settings.cut_height:.1f} F{self.settings.feed_rate:.0f}")
                lines.append("")

                # Контур
                lines.append("; Контур")
                for i, (cx, cy) in enumerate(contour):
                    if i == 0:
                        lines.append(f"G1 X{cx:.2f} Y{cy:.2f} F{self.settings.feed_rate:.0f}")
                    else:
                        lines.append(f"G1 X{cx:.2f} Y{cy:.2f}")
                lines.append("")

                # Відхід (lead-out)
                lines.append("; Відхід")
                lines.append(f"G1 X{contour[-1][0]:.2f} Y{contour[-1][1]:.2f}")
                lines.append("M5")              # Вимкнути плазму
                lines.append(f"G0 Z{self.settings.safe_height:.1f}")
                lines.append("")

        # Завершення
        lines.append("; ЗАВЕРШЕННЯ")
        lines.append(f"G0 Z{self.settings.safe_height:.1f}")
        lines.append("G0 X0 Y0")
        lines.append("M30")                     # Кінець програми
        lines.append("%")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _calculate_contour(self, x: float, y: float, w: float, h: float, rotated: bool) -> List[tuple]:
        """Розрахувати контур деталі з компенсацією різу.

        Повертає список (X, Y) точок контуру за годинниковою стрілкою.
        """
        k = self.settings.kerf_width / 2  # половина ширини різу

        if rotated:
            # Якщо повернута — міняємо ширину і висоту місцями
            w, h = h, w

        # Контур зсунутий всередину на k (компенсація різу)
        points = [
            (x + k, y + k),           # лівий нижній
            (x + w - k, y + k),       # правий нижній
            (x + w - k, y + h - k),   # правий верхній
            (x + k, y + h - k),       # лівий верхній
            (x + k, y + k),           # замикаємо
        ]
        return points

    def export_single_sheet(self, sheet, filepath: str):
        """Експортувати один лист (для ручного вибору)."""
        class FakePlan:
            def __init__(self, sheets):
                self.sheets = sheets
        self.export_cutting_plan(FakePlan([sheet]), filepath)
