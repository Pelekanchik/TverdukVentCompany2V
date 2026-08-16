"""Експорт плану розкрою у DXF (AutoCAD) для гільйотини/лазера.

Формат:
    • Кожна деталь — замкнений контур (LWPOLYLINE)
    • Текст-маркування з артикулом та розмірами
    • Межі листа
    • Координати від лівого нижнього кута листа

ВСТАНОВЛЕННЯ:
    Скопіюйте у ventilation_company/dxf_exporter.py
"""

import math
from typing import List
from dataclasses import dataclass


@dataclass
class DXFSettings:
    """Налаштування DXF-експорту."""
    layer_details: str = "DETAILS"
    layer_text: str = "TEXT"
    layer_sheet: str = "SHEET"
    text_height: float = 8.0
    color_details: int = 1      # Червоний
    color_text: int = 7         # Білий/чорний
    color_sheet: int = 8        # Сірий


class DXFExporter:
    """Генератор DXF-файлу для плану розкрою."""

    def __init__(self, settings: DXFSettings = None):
        self.settings = settings or DXFSettings()

    def export_cutting_plan(self, plan, filepath: str):
        """Експортувати план розкрою у DXF.

        Args:
            plan: CuttingPlan з листами та деталями
            filepath: шлях для збереження .dxf файлу
        """
        dxf_lines = []
        dxf_lines.extend(self._header())
        dxf_lines.extend(self._tables())
        dxf_lines.extend(self._blocks())
        dxf_lines.append("0")
        dxf_lines.append("ENTITIES")

        for sheet_idx, sheet in enumerate(plan.sheets):
            # Межі листа
            dxf_lines.extend(self._draw_rectangle(
                0, 0, sheet.width, sheet.height,
                layer=self.settings.layer_sheet,
                color=self.settings.color_sheet,
                line_type="CONTINUOUS",
            ))

            # Деталі
            for placed in sheet.placed_details:
                d = placed.detail
                x, y = placed.x, placed.y
                w, h = placed.width, placed.height

                # Контур деталі
                dxf_lines.extend(self._draw_rectangle(
                    x, y, w, h,
                    layer=self.settings.layer_details,
                    color=self.settings.color_details,
                    line_type="CONTINUOUS",
                ))

                # Текст-маркування (артикул + розміри)
                label = f"{d.name} {d.width:.0f}x{d.height:.0f}"
                dxf_lines.extend(self._draw_text(
                    x + w / 2, y + h / 2,
                    label,
                    height=self.settings.text_height,
                    layer=self.settings.layer_text,
                    color=self.settings.color_text,
                ))

                # Маркування повороту
                if placed.rotated:
                    dxf_lines.extend(self._draw_text(
                        x + w / 2, y + h / 2 - self.settings.text_height * 1.5,
                        "(90°)",
                        height=self.settings.text_height * 0.7,
                        layer=self.settings.layer_text,
                        color=self.settings.color_text,
                    ))

        dxf_lines.extend(self._footer())

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(dxf_lines))

    def export_single_sheet(self, sheet, filepath: str):
        """Експортувати один лист."""
        class FakePlan:
            def __init__(self, sheets):
                self.sheets = sheets
        self.export_cutting_plan(FakePlan([sheet]), filepath)

    # ── DXF примітиви ──

    def _draw_rectangle(self, x: float, y: float, w: float, h: float,
                        layer: str, color: int, line_type: str) -> List[str]:
        """LWPOLYLINE — прямокутник."""
        return [
            "0", "LWPOLYLINE",
            "5", self._next_handle(),
            "8", layer,
            "62", str(color),
            "6", line_type,
            "90", "4",       # Кількість вершин
            "70", "1",       # Замкнений
            "43", "0.0",     # Ширина
            "10", f"{x:.2f}", "20", f"{y:.2f}",
            "10", f"{x + w:.2f}", "20", f"{y:.2f}",
            "10", f"{x + w:.2f}", "20", f"{y + h:.2f}",
            "10", f"{x:.2f}", "20", f"{y + h:.2f}",
        ]

    def _draw_text(self, x: float, y: float, text: str,
                   height: float, layer: str, color: int) -> List[str]:
        """TEXT — текстова мітка."""
        return [
            "0", "TEXT",
            "5", self._next_handle(),
            "8", layer,
            "62", str(color),
            "10", f"{x:.2f}",
            "20", f"{y:.2f}",
            "30", "0.0",
            "40", f"{height:.2f}",
            "1", text,
            "72", "1",       # Горизонтальне вирівнювання по центру
            "11", f"{x:.2f}",
            "21", f"{y:.2f}",
            "31", "0.0",
        ]

    def _next_handle(self) -> str:
        self._handle_counter = getattr(self, '_handle_counter', 0) + 1
        return f"{self._handle_counter:04X}"

    # ── DXF структура ──

    def _header(self) -> List[str]:
        return [
            "0", "SECTION",
            "2", "HEADER",
            "9", "$ACADVER",
            "1", "AC1009",
            "9", "$INSUNITS",
            "70", "4",       # Міліметри
            "0", "ENDSEC",
        ]

    def _tables(self) -> List[str]:
        layers = [
            (self.settings.layer_details, self.settings.color_details),
            (self.settings.layer_text, self.settings.color_text),
            (self.settings.layer_sheet, self.settings.color_sheet),
        ]
        lines = ["0", "SECTION", "2", "TABLES"]
        lines.extend(["0", "TABLE", "2", "LAYER", "70", str(len(layers))])
        for name, color in layers:
            lines.extend([
                "0", "LAYER",
                "2", name,
                "70", "0",
                "62", str(color),
                "6", "CONTINUOUS",
            ])
        lines.extend(["0", "ENDTAB", "0", "ENDSEC"])
        return lines

    def _blocks(self) -> List[str]:
        return ["0", "SECTION", "2", "BLOCKS", "0", "ENDSEC"]

    def _footer(self) -> List[str]:
        return ["0", "ENDSEC", "0", "EOF"]
