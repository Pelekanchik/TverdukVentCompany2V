"""Експорт плану розкрою в формати ЧПУ: DXF та G-code.

Підтримує:
  • DXF — для AutoCAD / Компас / SolidWorks / LibreCAD
  • G-code — для плазмових та лазерних верстатів

Без зовнішніх залежностей — чистий Python.
"""

import os
from dataclasses import dataclass
from typing import Optional

from ventilation_company.metal_cutting import CuttingPlan, Sheet, PlacedDetail


@dataclass
class CNCSettings:
    """Налаштування ЧПУ верстата."""

    machine_type: str = "plasma"          # "plasma" | "laser" | "gas"
    feed_rate: float = 1500.0             # мм/хв — швидкість різу
    rapid_feed: float = 8000.0            # мм/хв — швидке переміщення
    pierce_height: float = 3.0            # мм — висота підпалу
    cut_height: float = 1.5               # мм — висота різу
    retract_height: float = 5.0           # мм — висота підйому між деталями
    pierce_delay: float = 0.5             # с — затримка підпалу
    lead_in_length: float = 3.0           # мм — довжина підходу
    lead_out_length: float = 3.0          # мм — довжина відходу
    kerf_width: float = 1.5               # мм — ширина пропилу (компенсація)
    use_kerf_compensation: bool = True    # компенсація пропилу
    units: str = "mm"                     # "mm" | "inch"
    decimal_places: int = 3

    def clone(self) -> "CNCSettings":
        return CNCSettings(
            machine_type=self.machine_type,
            feed_rate=self.feed_rate,
            rapid_feed=self.rapid_feed,
            pierce_height=self.pierce_height,
            cut_height=self.cut_height,
            retract_height=self.retract_height,
            pierce_delay=self.pierce_delay,
            lead_in_length=self.lead_in_length,
            lead_out_length=self.lead_out_length,
            kerf_width=self.kerf_width,
            use_kerf_compensation=self.use_kerf_compensation,
            units=self.units,
            decimal_places=self.decimal_places,
        )


class DXFExporter:
    """Генератор DXF-файлів (ASCII R14) без зовнішніх бібліотек."""

    def __init__(self, plan: CuttingPlan, settings: Optional[CNCSettings] = None):
        self.plan = plan
        self.settings = settings or CNCSettings()

    def _fmt(self, val: float) -> str:
        return f"{val:.{self.settings.decimal_places}f}"

    def _header(self) -> str:
        return (
            "  0\nSECTION\n  2\nHEADER\n  9\n$ACADVER\n  1\nAC1014\n"
            "  9\n$INSUNITS\n  70\n6\n  0\nENDSEC\n"
        )

    def _tables(self) -> str:
        layers = []
        for i in range(len(self.plan.sheets)):
            color = (i % 6) + 1
            layers.append(
                f"  0\nLAYER\n  2\nLIST_{i+1}\n  70\n0\n  62\n{color}\n  6\nCONTINUOUS\n"
            )
        layers_str = "".join(layers)
        return (
            "  0\nSECTION\n  2\nTABLES\n"
            "  0\nTABLE\n  2\nLTYPE\n  70\n1\n"
            "  0\nLTYPE\n  2\nCONTINUOUS\n  70\n0\n  3\nSolid line\n"
            "  72\n65\n  73\n0\n  40\n0.0\n"
            "  0\nENDTAB\n"
            "  0\nTABLE\n  2\nLAYER\n"
            f"  70\n{len(self.plan.sheets) + 1}\n"
            "  0\nLAYER\n  2\n0\n  70\n0\n  62\n7\n  6\nCONTINUOUS\n"
            + layers_str +
            "  0\nENDTAB\n  0\nENDSEC\n"
        )

    def _entities(self) -> str:
        lines = ["  0", "SECTION", "  2", "ENTITIES"]
        for sheet_idx, sheet in enumerate(self.plan.sheets):
            layer = f"LIST_{sheet_idx + 1}"
            # Контур листа
            lines.extend(self._rect_lwpolyline(
                0, 0, sheet.width, sheet.height, layer, closed=True, color=7
            ))
            # Деталі
            for placed in sheet.placed_details:
                lines.extend(self._rect_lwpolyline(
                    placed.x, placed.y,
                    placed.x + placed.width, placed.y + placed.height,
                    layer, closed=True
                ))
                # Текстова мітка
                cx = placed.x + placed.width / 2
                cy = placed.y + placed.height / 2
                lines.extend(self._text(
                    cx, cy, placed.detail.name[:20], layer, height=15
                ))
        lines.extend(["  0", "ENDSEC", "  0", "EOF"])
        return "\n".join(lines)

    def _rect_lwpolyline(
        self, x1: float, y1: float, x2: float, y2: float,
        layer: str, closed: bool = True, color: int = 256
    ) -> list[str]:
        flag = "1" if closed else "0"
        return [
            "  0", "LWPOLYLINE",
            "  8", layer,
            " 62", str(color),
            " 90", "4",
            " 70", flag,
            " 43", "0.0",
            " 38", "0.0",
            f" 10\n{self._fmt(x1)}",
            f" 20\n{self._fmt(y1)}",
            f" 10\n{self._fmt(x2)}",
            f" 20\n{self._fmt(y1)}",
            f" 10\n{self._fmt(x2)}",
            f" 20\n{self._fmt(y2)}",
            f" 10\n{self._fmt(x1)}",
            f" 20\n{self._fmt(y2)}",
        ]

    def _text(self, x: float, y: float, text: str, layer: str, height: float = 20) -> list[str]:
        safe = text.replace("\\", "\\\\").replace("\n", "\\P")
        return [
            "  0", "TEXT",
            "  8", layer,
            " 62", "7",
            f" 10\n{self._fmt(x)}",
            f" 20\n{self._fmt(y)}",
            f" 40\n{self._fmt(height)}",
            "  1", safe,
            " 50", "0.0",
            " 72", "1",
            " 11", self._fmt(x),
            " 21", self._fmt(y),
        ]

    def export(self, filepath: str) -> str:
        """Зберегти всі листи в один DXF-файл (різні шари)."""
        dxf = self._header() + self._tables() + self._entities()
        with open(filepath, "w", encoding="cp1251", errors="replace") as f:
            f.write(dxf)
        return filepath

    def export_per_sheet(self, directory: str, prefix: str = "sheet") -> list[str]:
        """Зберегти кожен лист окремим DXF-файлом."""
        os.makedirs(directory, exist_ok=True)
        paths = []
        for sheet_idx, sheet in enumerate(self.plan.sheets):
            fname = f"{prefix}_{sheet_idx + 1:02d}_{int(sheet.width)}x{int(sheet.height)}.dxf"
            fpath = os.path.join(directory, fname)
            mini_plan = CuttingPlan(sheets=[sheet])
            mini_exporter = DXFExporter(mini_plan, self.settings)
            mini_exporter.export(fpath)
            paths.append(fpath)
        return paths


class GCodeExporter:
    """Генератор G-code для плазмових/лазерних верстатів."""

    def __init__(self, plan: CuttingPlan, settings: Optional[CNCSettings] = None):
        self.plan = plan
        self.settings = settings or CNCSettings()
        self._sheet_idx = 0

    def _fmt(self, val: float) -> str:
        return f"{val:.{self.settings.decimal_places}f}"

    def _header(self, sheet: Sheet) -> list[str]:
        s = self.settings
        lines = [
            "; ============================================",
            f"; G-code для ЧПУ — Лист {self._sheet_idx + 1}",
            f"; Розмір листа: {sheet.width:.0f} x {sheet.height:.0f} мм",
            f"; Матеріал: {sheet.material}, товщина: {sheet.thickness} мм",
            f"; Тип верстата: {s.machine_type}",
            f"; Швидкість різу: {s.feed_rate:.0f} мм/хв",
            f"; Ширина пропилу: {s.kerf_width:.1f} мм",
            "; ============================================",
            "",
            "G21          ; Метрична система",
            "G90          ; Абсолютні координати",
            "G17          ; Площина XY",
            f"G0 Z{s._fmt(s.retract_height)}    ; Підняти головку",
            "",
        ]
        return lines

    def _footer(self) -> list[str]:
        s = self.settings
        return [
            "",
            "; === КІНЕЦЬ ПРОГРАМИ ===",
            f"G0 Z{s._fmt(s.retract_height)}    ; Підняти головку",
            "M5           ; Вимкнути плазму/лазер",
            "M30          ; Кінець програми",
            "",
        ]

    def _cut_rectangle(self, placed: PlacedDetail, sheet: Sheet) -> list[str]:
        """Траєкторія різу прямокутної деталі з lead-in / lead-out."""
        s = self.settings
        lines = []

        x0, y0 = placed.x, placed.y
        w, h = placed.width, placed.height

        # Компенсація пропилу (всередину деталі)
        k = s.kerf_width / 2 if s.use_kerf_compensation else 0
        x1, y1 = x0 + k, y0 + k
        x2, y2 = x0 + w - k, y0 + h - k

        # Lead-in: підхід з лівого нижнього кута вздовж нижньої сторони
        li = min(s.lead_in_length, w / 4)
        lo = min(s.lead_out_length, w / 4)

        start_x = x1 + li
        start_y = y1

        lines.append(f"; --- Деталь: {placed.detail.name} ---")
        lines.append(f"; Розмір: {w:.1f} x {h:.1f} мм | Повернуто: {placed.rotated}")

        # Швидке переміщення до точки підпалу
        lines.append(f"G0 X{s._fmt(start_x)} Y{s._fmt(start_y)}")
        lines.append(f"G0 Z{s._fmt(s.pierce_height)}    ; Опустити до висоти підпалу")
        lines.append("M3           ; Увімкнути плазму/лазер")
        if s.pierce_delay > 0:
            lines.append(f"G4 P{s._fmt(s.pierce_delay)}   ; Затримка підпалу")
        lines.append(f"G1 Z{s._fmt(s.cut_height)} F{s._fmt(s.feed_rate)}   ; Опустити до різу")

        # Різ по периметру (проти годинникової стрілки)
        lines.append(f"G1 X{s._fmt(x1)} Y{s._fmt(y1)} F{s._fmt(s.feed_rate)}   ; Lead-in завершення")
        lines.append(f"G1 X{s._fmt(x1)} Y{s._fmt(y2)} F{s._fmt(s.feed_rate)}   ; Ліва сторона")
        lines.append(f"G1 X{s._fmt(x2)} Y{s._fmt(y2)} F{s._fmt(s.feed_rate)}   ; Верх")
        lines.append(f"G1 X{s._fmt(x2)} Y{s._fmt(y1)} F{s._fmt(s.feed_rate)}   ; Права сторона")
        lines.append(f"G1 X{s._fmt(x1 + lo)} Y{s._fmt(y1)} F{s._fmt(s.feed_rate)}   ; Lead-out")

        lines.append("M5           ; Вимкнути плазму/лазер")
        lines.append(f"G0 Z{s._fmt(s.retract_height)}    ; Підняти головку")
        lines.append("")
        return lines

    def _cut_sheet_outline(self, sheet: Sheet) -> list[str]:
        """Контур листа (для перевірки/візуалізації, без різу)."""
        s = self.settings
        return [
            "",
            "; --- Контур листа (для довідки, НЕ різати) ---",
            f"; G0 X0 Y0",
            f"; G1 X{s._fmt(sheet.width)} Y0",
            f"; G1 X{s._fmt(sheet.width)} Y{s._fmt(sheet.height)}",
            f"; G1 X0 Y{s._fmt(sheet.height)}",
            f"; G1 X0 Y0",
            "",
        ]

    def export_sheet(self, sheet: Sheet, filepath: str) -> str:
        """Згенерувати G-code для одного листа."""
        self._sheet_idx += 1
        lines = self._header(sheet)
        for placed in sheet.placed_details:
            lines.extend(self._cut_rectangle(placed, sheet))
        lines.extend(self._cut_sheet_outline(sheet))
        lines.extend(self._footer())
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return filepath

    def export_all(self, directory: str, prefix: str = "cut") -> list[str]:
        """Згенерувати G-code для всіх листів."""
        os.makedirs(directory, exist_ok=True)
        paths = []
        for sheet_idx, sheet in enumerate(self.plan.sheets):
            self._sheet_idx = sheet_idx
            fname = f"{prefix}_{sheet_idx + 1:02d}_{int(sheet.width)}x{int(sheet.height)}.nc"
            fpath = os.path.join(directory, fname)
            self.export_sheet(sheet, fpath)
            paths.append(fpath)
        return paths


# =========================================================
# ФАСАДНІ ФУНКЦІЇ
# =========================================================

def export_to_dxf(plan: CuttingPlan, filepath: str, settings: Optional[CNCSettings] = None) -> str:
    """Експортувати план розкрою в DXF."""
    exporter = DXFExporter(plan, settings)
    return exporter.export(filepath)


def export_to_gcode(plan: CuttingPlan, directory: str, settings: Optional[CNCSettings] = None) -> list[str]:
    """Експортувати план розкрою в G-code (по файлу на лист)."""
    exporter = GCodeExporter(plan, settings)
    return exporter.export_all(directory)


def export_summary_text(plan: CuttingPlan, filepath: str) -> str:
    """Зберегти текстову зведення про розкрій (для оператора)."""
    s = plan.get_summary()
    lines = [
        "==============================================",
        "       ЗВЕДЕННЯ ПЛАНУ РОЗКРОЮ ДЛЯ ЧПУ",
        "==============================================",
        "",
        f"Листів потрібно:     {s['total_sheets']}",
        f"Загальна площа:      {s['total_area_m2']:.3f} м²",
        f"Використано:         {s['used_area_m2']:.3f} м²",
        f"Відходи:             {s['waste_area_m2']:.3f} м²",
        f"Використання:        {s['utilization_percent']:.1f}%",
        f"Нерозміщено:         {s['unplaced_count']} дет.",
        "",
        "--- Деталі по листах ---",
    ]
    for i, sheet in enumerate(plan.sheets):
        lines.append(f"\nЛист {i + 1}: {sheet.width:.0f}×{sheet.height:.0f} мм")
        lines.append(f"  Використання: {sheet.utilization * 100:.1f}%")
        for p in sheet.placed_details:
            lines.append(
                f"  • {p.detail.name:20s}  {p.width:7.1f}×{p.height:7.1f} мм  "
                f"@ ({p.x:7.1f}, {p.y:7.1f})  {'[R]' if p.rotated else ''}"
            )
    if plan.unplaced_details:
        lines.append("\n--- НЕ РОЗМІЩЕНО ---")
        for d in plan.unplaced_details:
            lines.append(f"  • {d.name}  {d.total_width:.1f}×{d.total_height:.1f} мм  qty={d.quantity}")
    lines.append("")
    lines.append("==============================================")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return filepath
