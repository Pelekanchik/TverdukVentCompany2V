"""Генератор PDF-звіту бригади про виконання робіт.

Друкований чек-лист: роботи з датами по бригадах з порожніми
квадратиками «виконано». Бригадир відмічає на папері виконані
роботи на об'єкті — відмічений звіт у офісі стає основою для актів.

Використання:
    generate_crew_report(works, crew, date_from, date_to, path, company)
"""

from __future__ import annotations

from datetime import date, datetime

from ventilation_company.proposal_generator import _clean, _find_fonts

try:
    from fpdf import FPDF
except ImportError:
    raise ImportError("Бібліотека fpdf2 не встановлена. Виконайте: pip install fpdf2") from None

_WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "нд"]

# Ширини колонок таблиці (мм, разом 170)
_COL_CHECK = 14
_COL_DATE = 22
_COL_PROJECT = 62
_COL_WORK = 48
_COL_PRICE = 24


class CrewReportPDF(FPDF):
    """PDF-документ: звіт бригади про виконання (чек-лист)."""

    def __init__(self, works: list[dict], crew: str, date_from: date, date_to: date, company: dict):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.works = works
        self.crew = crew
        self.date_from = date_from
        self.date_to = date_to
        self.company = company or {}
        self.regular_font, self.bold_font = _find_fonts()
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(20, 15, 20)
        self.add_font("Main", "", self.regular_font)
        self.add_font("Main", "B", self.bold_font)
        self._build()

    # ── Шрифти ──

    def _regular(self, size: int = 10):
        self.set_font("Main", "", size)

    def _bold(self, size: int = 10):
        self.set_font("Main", "B", size)

    # ── Побудова ──

    def _build(self):
        self.add_page()
        self._header()
        groups = self._group_by_crew()
        for crew_name, rows in groups:
            self._crew_section(crew_name, rows)
        self._signatures()

    def _header(self):
        name = _clean(self.company.get("name") or "")
        if name:
            self._bold(9)
            self.set_text_color(90, 90, 90)
            self.cell(0, 5, name, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self._bold(14)
        self.cell(
            0, 9, "ЗВІТ БРИГАДИ ПРО ВИКОНАНІ РОБОТИ", align="C", new_x="LMARGIN", new_y="NEXT"
        )
        self._regular(10)
        period = f"{self.date_from.strftime('%d.%m.%Y')} – {self.date_to.strftime('%d.%m.%Y')}"
        crew_txt = _clean(self.crew) or "усі бригади"
        self.cell(0, 5, f"Бригада: {crew_txt}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 5, f"Період: {period}", align="C", new_x="LMARGIN", new_y="NEXT")
        self._regular(9)
        self.set_text_color(107, 114, 128)
        self.cell(
            0,
            5,
            "Бригадир ставить позначку у квадратику навпроти виконаної роботи.",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def _group_by_crew(self) -> list[tuple[str, list[dict]]]:
        groups: dict[str, list[dict]] = {}
        order: list[str] = []
        for w in self.works:
            key = (w.get("crew") or "").strip() or "— без бригади —"
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(w)
        order.sort(key=str.lower)
        order = [o for o in order if not o.startswith("—")] + [
            o for o in order if o.startswith("—")
        ]
        for rows in groups.values():
            rows.sort(
                key=lambda w: (str(w.get("work_date") or ""), str(w.get("project_number") or ""))
            )
        return [(crew, groups[crew]) for crew in order]

    def _table_header(self):
        self.set_fill_color(37, 99, 235)
        self.set_text_color(255, 255, 255)
        self._bold(9)
        self.cell(_COL_CHECK, 6, "", fill=True)
        self.cell(_COL_DATE, 6, " Дата", fill=True)
        self.cell(_COL_PROJECT, 6, " Проєкт / адреса", fill=True)
        self.cell(_COL_WORK, 6, " Робота", fill=True)
        self.cell(_COL_PRICE, 6, " Сума, ₴", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def _checkbox(self, x: float, y: float, size: float = 4.5):
        """Порожній квадратик для галочки (малюємо рамку, символ шрифту не потрібен)."""
        self.set_draw_color(31, 41, 55)
        self.set_line_width(0.3)
        self.rect(x, y, size, size)
        self.set_line_width(0.2)

    def _crew_section(self, crew_name: str, rows: list[dict]):
        if self.get_y() > 250:
            self.add_page()
        self.set_fill_color(232, 238, 252)
        self._bold(11)
        title = f"{crew_name}   ({len(rows)} роб.)"
        self.cell(170, 7, f" {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self._table_header()

        prev_date = None
        for w in rows:
            raw_date = str(w.get("work_date") or "")
            try:
                d = date.fromisoformat(raw_date[:10])
                date_txt = f"{_WEEKDAYS[d.weekday()]} {d.strftime('%d.%m')}"
            except ValueError:
                d = None
                date_txt = raw_date or "—"
            project = f"{w.get('project_number') or ''} {w.get('project_name') or ''}".strip()
            address = _clean(w.get("address") or "")
            work = _clean(w.get("work_name") or "—")
            price = float(w.get("total_price") or 0)
            price_txt = f"{price:,.2f}" if price else "—"

            height = 10 if address else 6
            if self.get_y() + height > 280:
                self.add_page()
                self._table_header()

            shade = (d != prev_date) and d is not None
            if shade:
                self.set_fill_color(245, 247, 251)
            self._regular(9)

            y0 = self.get_y()
            self.cell(_COL_CHECK, height, "", fill=shade)
            # Квадратик для галочки — по центру комірки
            self._checkbox(self.get_x() - _COL_CHECK / 2 - 2.25, y0 + height / 2 - 2.25)

            self.cell(_COL_DATE, height, f" {date_txt}", fill=shade)
            x_proj = self.get_x()
            self.cell(_COL_PROJECT, height, "", fill=shade)
            self.set_xy(x_proj, y0 + 1)
            self._bold(9)
            self.multi_cell(_COL_PROJECT, 4, _clean(project) or "—", new_x="RIGHT", new_y="TOP")
            if address:
                self.set_xy(x_proj, y0 + 5.5)
                self._regular(8)
                self.set_text_color(107, 114, 128)
                self.multi_cell(_COL_PROJECT, 4, address, new_x="RIGHT", new_y="TOP")
                self.set_text_color(0, 0, 0)
            self.set_xy(x_proj + _COL_PROJECT, y0)
            self._regular(9)
            self.cell(_COL_WORK, height, f" {work}", fill=shade)
            self.cell(
                _COL_PRICE,
                height,
                f" {price_txt}",
                align="R",
                fill=shade,
                new_x="LMARGIN",
                new_y="NEXT",
            )
            prev_date = d
        self.ln(4)

    def _signatures(self):
        if self.get_y() > 240:
            self.add_page()
        self._regular(9)
        self.set_text_color(107, 114, 128)
        generated = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.cell(0, 5, f"Сформовано: {generated}", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(8)
        self._regular(10)
        self.cell(
            0,
            7,
            "Роботи виконали (члени бригади): _______________________________________",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.ln(5)
        self.cell(
            0,
            7,
            "Бригадир: _______________________        Дата: «____» ____________ 20____ р.",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.ln(5)
        self.cell(
            0,
            7,
            "Прийняв (інженер/менеджер): _______________________________        «____» ____________ 20____ р.",
            new_x="LMARGIN",
            new_y="NEXT",
        )


def generate_crew_report(
    works: list[dict],
    crew: str,
    date_from: date,
    date_to: date,
    output_path: str,
    company: dict | None = None,
) -> str:
    """Згенерувати PDF-звіт бригади про виконання (чек-лист).

    Параметри — як у generate_crew_plan (crew_plan_generator.py).
    """
    pdf = CrewReportPDF(works, crew, date_from, date_to, company or {})
    pdf.output(output_path)
    return output_path
