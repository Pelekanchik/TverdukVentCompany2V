"""PDF-звіт плану розкрою для цеху.

Кожен лист — окрема сторінка A4: схема розкладки (масштабна, кольорові
позиції з номерами) + таблиця деталей з координатами. Шапка містить
матеріал, товщину, розмір листа та відсоток використання.
"""

from __future__ import annotations

from datetime import datetime

from fpdf import FPDF

from ventilation_company.proposal_generator import _clean, _find_fonts

# Кольори позицій — ті самі, що й на канвасі ( CuttingCanvas.DETAIL_COLORS ).
DETAIL_COLORS = [
    "#89b4fa",
    "#a6e3a1",
    "#f9e2af",
    "#f38ba8",
    "#cba6f7",
    "#74c7ec",
    "#fab387",
    "#94e2d5",
    "#b4befe",
    "#f5e0dc",
    "#a6adc8",
    "#f2cdcd",
]


def _hex_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class CuttingPlanPDF(FPDF):
    def __init__(self, plan, meta: dict | None = None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.plan = plan
        self.meta = meta or {}
        regular, bold = _find_fonts()
        self.add_font("Main", "", regular)
        self.add_font("Main", "B", bold)
        self.set_auto_page_break(auto=True, margin=15)
        self._build()

    # ── Сторінки ──

    def _build(self):
        summary = self.plan.get_summary()
        total = len(self.plan.sheets)
        for idx, sheet in enumerate(self.plan.sheets):
            self.add_page()
            self._header(idx + 1, total, summary)
            top_after_scheme = self._scheme(sheet)
            self._details_table(sheet, top_after_scheme)

    def _header(self, sheet_no: int, total: int, summary: dict):
        self.set_font("Main", "B", 14)
        self.cell(0, 8, "План розкрою металу", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Main", "", 9)
        meta = self.meta
        date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        info = (
            f"Дата: {date_str}   |   Лист {sheet_no} / {total}   |   "
            f"{meta.get('sheet_size', '')}   |   Матеріал: {meta.get('material', '—')}   |   "
            f"Товщина: {meta.get('thickness', '—')} мм"
        )
        self.cell(0, 5, _clean(info), new_x="LMARGIN", new_y="NEXT")
        self.cell(
            0,
            5,
            _clean(
                f"Використання: {summary.get('utilization_percent', 0):.1f} %   |   "
                f"Листів загалом: {summary.get('total_sheets', total)}   |   "
                f"Площа деталей: {summary.get('used_area_m2', 0):.3f} м²"
            ),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.ln(2)

    def _scheme(self, sheet) -> float:
        """Схема листа з деталями; повертає Y після схеми."""
        max_h = 150.0
        max_w = 120.0
        scale = min(max_w / sheet.width, max_h / sheet.height)
        w = sheet.width * scale
        h = sheet.height * scale
        x0 = (self.w - self.l_margin - self.r_margin - w) / 2 + self.l_margin
        y0 = self.get_y()

        # Рамка листа + підписи розмірів
        self.set_draw_color(40, 40, 60)
        self.set_line_width(0.4)
        self.rect(x0, y0, w, h)

        # Сітка 500 мм
        self.set_draw_color(200, 200, 210)
        self.set_line_width(0.1)
        step = 500 * scale
        gx = x0 + step
        while gx < x0 + w - 0.5:
            self.line(gx, y0, gx, y0 + h)
            gx += step
        gy = y0 + step
        while gy < y0 + h - 0.5:
            self.line(x0, gy, x0 + w, gy)
            gy += step

        # Деталі
        for i, p in enumerate(sheet.placed_details):
            r, g, b = _hex_rgb(DETAIL_COLORS[i % len(DETAIL_COLORS)])
            dx = x0 + p.x * scale
            dy = y0 + p.y * scale
            dw = max(p.width * scale, 0.5)
            dh = max(p.height * scale, 0.5)
            self.set_fill_color(r, g, b)
            self.set_draw_color(max(r - 60, 0), max(g - 60, 0), max(b - 60, 0))
            self.set_line_width(0.2)
            self.rect(dx, dy, dw, dh, style="DF")
            # Номер позиції по центру
            label = str(i + 1)
            self.set_font("Main", "B", 6 if min(dw, dh) < 8 else 8)
            tw = self.get_string_width(label)
            if tw < dw - 1 and min(dw, dh) >= 4:
                self.set_text_color(30, 30, 40)
                self.text(dx + (dw - tw) / 2, dy + dh / 2 + 1.5, label)

        # Розміри листа
        self.set_font("Main", "", 8)
        self.set_text_color(100, 100, 110)
        w_txt = f"{sheet.width:.0f} мм"
        self.text(x0 + (w - self.get_string_width(w_txt)) / 2, y0 + h + 4, w_txt)
        h_txt = f"{sheet.height:.0f} мм"
        self.set_xy(x0 + w + 2, y0)
        self.cell(0, 5, _clean(h_txt))

        return y0 + h + 8

    def _details_table(self, sheet, top: float):
        cols = [
            ("№", 10, "C"),
            ("Назва деталі", 78, "L"),
            ("Шир., мм", 20, "C"),
            ("Вис., мм", 20, "C"),
            ("X, мм", 20, "C"),
            ("Y, мм", 20, "C"),
            ("Повер.", 15, "C"),
        ]
        row_h = 6
        self.set_y(top + 2)

        def header_row():
            self.set_font("Main", "B", 8)
            self.set_fill_color(230, 235, 245)
            self.set_draw_color(120, 120, 135)
            self.set_text_color(30, 30, 40)
            for title, width, _align in cols:
                self.cell(width, row_h, _clean(title), border=1, align="C", fill=True)
            self.ln(row_h)

        header_row()
        self.set_font("Main", "", 8)
        self.set_draw_color(120, 120, 135)
        for i, p in enumerate(sheet.placed_details, 1):
            if self.get_y() + row_h > self.h - self.b_margin:
                self.add_page()
                header_row()
                self.set_font("Main", "", 8)
            self.set_text_color(30, 30, 40)
            self.cell(cols[0][1], row_h, str(i), border=1, align="C")
            self.cell(cols[1][1], row_h, _clean(p.detail.name)[:44], border=1, align="L")
            self.cell(cols[2][1], row_h, f"{p.width:.0f}", border=1, align="C")
            self.cell(cols[3][1], row_h, f"{p.height:.0f}", border=1, align="C")
            self.cell(cols[4][1], row_h, f"{p.x:.0f}", border=1, align="C")
            self.cell(cols[5][1], row_h, f"{p.y:.0f}", border=1, align="C")
            self.cell(cols[6][1], row_h, "Так" if p.rotated else "Ні", border=1, align="C")
            self.ln(row_h)


def generate_cutting_pdf(plan, output_path: str, meta: dict | None = None) -> str:
    """Згенерувати PDF плану розкрою. Повертає шлях до файлу."""
    pdf = CuttingPlanPDF(plan, meta)
    pdf.output(output_path)
    return output_path
