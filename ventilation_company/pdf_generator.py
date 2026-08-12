"""
Генератор PDF-звітів по проєктам вентиляційної фірми.
Використовує fpdf2 з підтримкою Unicode (кирилиця).
"""

import os
from datetime import datetime
from typing import List, Dict, Optional

try:
    from fpdf import FPDF
except ImportError:
    raise ImportError(
        "Бібліотека fpdf2 не встановлена. "
        "Виконайте: pip install fpdf2"
    )

_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("C:/Windows/Fonts/tahoma.ttf", "C:/Windows/Fonts/tahomabd.ttf"),
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
]

_FONT_CANDIDATES_LINUX = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/freefont/FreeSans.ttf",
     "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"),
]


def _find_fonts() -> tuple[str, str]:
    for regular, bold in _FONT_CANDIDATES + _FONT_CANDIDATES_LINUX:
        if os.path.exists(regular) and os.path.exists(bold):
            return regular, bold
    raise RuntimeError(
        "Не знайдено системний шрифт з підтримкою кирилиці. "
        "Встановіть DejaVu або переконайтесь, що шляхи до шрифтів коректні."
    )


def _clean_text(text) -> str:
    """Прибирає символи нового рядка — fpdf2 не може їх відобразити."""
    if text is None:
        return ""
    return str(text).replace("\n", " ").replace("\r", " ").replace("\t", " ")


class ProjectPDFReport(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.regular_font, self.bold_font = _find_fonts()
        self.set_auto_page_break(auto=True, margin=20)
        self.add_font("Main", "", self.regular_font, uni=True)
        self.add_font("Main", "B", self.bold_font, uni=True)
        self.add_page()
        self._set_font_regular(10)

    def _set_font_regular(self, size: int = 10):
        self.set_font("Main", "", size)

    def _set_font_bold(self, size: int = 10):
        self.set_font("Main", "B", size)

    def _cell_right(self, w: float, h: float, text: str, border=0):
        self.cell(w, h, text, border=border, align="R")

    def _cell_center(self, w: float, h: float, text: str, border=0):
        self.cell(w, h, text, border=border, align="C")

    def _draw_header(self, title: str):
        self._set_font_bold(18)
        self.set_text_color(21, 101, 192)
        self.cell(0, 10, _clean_text(title), ln=True, align="C")
        self._set_font_regular(9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f"Сформовано: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True, align="C")
        self.ln(3)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def _draw_footer(self):
        self.set_y(-15)
        self._set_font_regular(8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, _clean_text(f"Сторінка {self.page_no()}"), align="C")

    def build_report(self, project: dict, products: List[dict], output_path: str) -> str:
        self._draw_header("ЗВІТ ПО ПРОЄКТУ")

        self._section_title("Інформація про проєкт")
        info_rows = [
            ("Назва проєкту:", project.get("name", "—")),
            ("Клієнт:", project.get("client", "—")),
            ("ID проєкту:", str(project.get("id", "—"))),
            ("Дата створення:", str(project.get("created_at", ""))[:10]),
            ("Статус:", project.get("status", "—")),
        ]
        for label, value in info_rows:
            self._info_row(label, value)
        self.ln(3)

        self._section_title("Фінансовий звіт")
        cost_price = float(project.get("cost_price", 0) or 0)
        salary_total = float(project.get("salary_total", 0) or 0)
        customer_price = float(project.get("customer_price", 0) or 0)
        profit = float(project.get("profit", 0) or 0)
        markup = (customer_price / cost_price - 1) * 100 if cost_price else 0
        profitability = (profit / customer_price * 100) if customer_price else 0

        fin_rows = [
            ("Собівартість матеріалів та робіт:", cost_price),
            ("Зарплатний фонд (робітники):", salary_total),
            ("Націнка фірми:", f"{markup:.1f}%"),
            ("Ціна для замовника:", customer_price),
        ]
        for label, value in fin_rows:
            if isinstance(value, (int, float)):
                self._money_row(label, value)
            else:
                self._info_row(label, value)

        self.ln(2)
        if profit >= 0:
            self.set_text_color(46, 125, 50)
            profit_label = "Прибуток фірми:"
        else:
            self.set_text_color(198, 40, 40)
            profit_label = "Збиток фірми:"

        self._set_font_bold(12)
        self.cell(90, 8, profit_label, align="L")
        self._cell_right(90, 8, f"{profit:,.2f} грн")
        self.ln(6)

        self._set_font_regular(9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f"Рентабельність: {profitability:.1f}%", ln=True, align="R")
        self.set_text_color(0, 0, 0)
        self.ln(5)

        self._section_title("Вироби проєкту")
        if not products:
            self._set_font_regular(10)
            self.cell(0, 10, _clean_text("Вироби відсутні"), ln=True, align="C")
        else:
            self._draw_products_table(products)

        self.add_page()
        self._draw_header("ЗВЕДЕНІ ПІДСУМКИ")
        self._section_title("Зведені підсумки")

        total_qty = sum(p.get("quantity", 1) for p in products)
        total_weight = sum(p.get("weight_kg", 0) * p.get("quantity", 1) for p in products)
        total_area = sum(p.get("metal_area_m2", 0) * p.get("quantity", 1) for p in products)

        summary_data = [
            ("Загальна кількість виробів:", f"{len(products)} позицій / {total_qty} шт"),
            ("Загальна вага виробів:", f"{total_weight:,.3f} кг"),
            ("Загальна площа металу:", f"{total_area:,.4f} м²"),
            ("", ""),
            ("Собівартість:", f"{cost_price:,.2f} грн"),
            ("Зарплата робітників:", f"{salary_total:,.2f} грн"),
            ("Ціна для замовника:", f"{customer_price:,.2f} грн"),
        ]
        for label, value in summary_data:
            if label:
                self._summary_row(label, value)
            else:
                self.ln(3)

        self.ln(5)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

        if profit >= 0:
            self.set_text_color(46, 125, 50)
            final_text = f"ЧИСТИЙ ПРИБУТОК:  {profit:,.2f} грн"
        else:
            self.set_text_color(198, 40, 40)
            final_text = f"ЗБИТОК:  {profit:,.2f} грн"

        self._set_font_bold(16)
        self.cell(0, 12, _clean_text(final_text), ln=True, align="C")
        self.set_text_color(0, 0, 0)

        self.ln(10)
        self._set_font_regular(9)
        self.set_text_color(128, 128, 128)
        self.cell(0, 5, _clean_text("Сформовано системою VentCompany"), ln=True, align="C")

        self.output(output_path)
        return output_path

    def _section_title(self, title: str):
        self._set_font_bold(12)
        self.set_text_color(33, 33, 33)
        self.cell(0, 8, _clean_text(title), ln=True)
        self.set_draw_color(21, 101, 192)
        self.line(10, self.get_y(), 60, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def _info_row(self, label: str, value: str):
        self._set_font_bold(9)
        self.cell(60, 6, _clean_text(label), align="L")
        self._set_font_regular(9)
        self.cell(0, 6, _clean_text(value), ln=True, align="L")

    def _money_row(self, label: str, amount: float):
        self._set_font_bold(9)
        self.cell(110, 6, _clean_text(label), align="L")
        self._set_font_regular(9)
        self._cell_right(70, 6, f"{amount:,.2f} грн")
        self.ln()

    def _summary_row(self, label: str, value: str):
        self._set_font_bold(10)
        self.cell(90, 7, _clean_text(label), align="L")
        self._set_font_regular(10)
        self._cell_right(90, 7, _clean_text(value))
        self.ln()

    def _draw_products_table(self, products: List[dict]):
        col_widths = [8, 50, 28, 12, 10, 22, 22, 26, 26]
        headers = ["№", "Найменування", "Матеріал", "Товщ.", "К-ть", "Вага, кг", "Площа, м²", "Ціна за шт", "Ціна за позицію"]
        aligns = ["C", "L", "L", "C", "C", "R", "R", "R", "R"]
        row_h = 6

        self.set_fill_color(227, 242, 253)
        self.set_draw_color(180, 180, 180)
        self._set_font_bold(8)
        for w, h, a in zip(col_widths, headers, aligns):
            self.cell(w, row_h, h, border=1, align=a, fill=True)
        self.ln()

        self._set_font_regular(8)
        self.set_fill_color(255, 255, 255)

        for i, p in enumerate(products, 1):
            if self.get_y() + row_h * 2 > 270:
                self.add_page()
                self._draw_header("ВИРОБИ ПРОЄКТУ (продовження)")
                self.set_fill_color(227, 242, 253)
                self._set_font_bold(8)
                for w, h, a in zip(col_widths, headers, aligns):
                    self.cell(w, row_h, h, border=1, align=a, fill=True)
                self.ln()
                self._set_font_regular(8)
                self.set_fill_color(255, 255, 255)

            w_val = p.get("width", 0)
            h_val = p.get("height", 0)
            l_val = p.get("length", 0)
            dims = f"{w_val}×{h_val}×{l_val}" if l_val else f"{w_val}×{h_val}"
            qty = p.get("quantity", 1)
            weight = p.get("weight_kg", 0)
            area = p.get("metal_area_m2", 0)
            unit_price = float(p.get("unit_price", 0) or 0)
            if unit_price == 0 and p.get("metal_area_m2"):
                material_prices = {"оцинкована сталь": 120.0, "нержавіюча сталь": 350.0, "алюміній": 200.0}
                area_val = float(p.get("metal_area_m2", 0))
                mat = p.get("material", "оцинкована сталь")
                price_per_m2 = material_prices.get(mat, 120.0)
                unit_price = area_val * (price_per_m2 + 50)
            total_price = unit_price * int(qty)

            values = [
                str(i),
                f"{p.get('name', '')[:18]} ({dims})",
                p.get("material", "")[:16],
                f"{p.get('thickness', 0):.1f}",
                str(qty),
                f"{weight * qty:.2f}",
                f"{area * qty:.3f}",
                f"{unit_price:,.2f}",
                f"{total_price:,.2f}",
            ]
            for w, v, a in zip(col_widths, values, aligns):
                self.cell(w, row_h, _clean_text(v), border=1, align=a)
            self.ln()
        self.ln(3)


def generate_project_pdf(project: dict, products: List[dict], output_path: Optional[str] = None) -> str:
    if output_path is None:
        import tempfile
        fd, output_path = tempfile.mkstemp(suffix=".pdf", prefix="project_report_")
        os.close(fd)
    report = ProjectPDFReport()
    return report.build_report(project, products, output_path)
