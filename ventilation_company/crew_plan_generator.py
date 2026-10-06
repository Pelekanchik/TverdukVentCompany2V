"""Генератор PDF-плану монтажних робіт для бригад.

Щотижневий друкований документ: роботи з датами згруповані по бригадах
(усередині — по днях), з адресами проєктів та сумами. Призначений для
роздачі бригадирам — щоб не переписувати завдання з екрана.

Використання:
    generate_crew_plan(works, crew, date_from, date_to, path, company)
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
_COL_DATE = 24
_COL_PROJECT = 68
_COL_WORK = 55
_COL_PRICE = 23


class CrewPlanPDF(FPDF):
    """PDF-документ: план монтажів по бригадах."""

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
        self._footer()

    def _header(self):
        name = _clean(self.company.get("name") or "")
        if name:
            self._bold(9)
            self.set_text_color(90, 90, 90)
            self.cell(0, 5, name, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self._bold(15)
        self.cell(0, 9, "ПЛАН МОНТАЖНИХ РОБІТ", align="C", new_x="LMARGIN", new_y="NEXT")
        self._regular(10)
        period = f"{self.date_from.strftime('%d.%m.%Y')} – {self.date_to.strftime('%d.%m.%Y')}"
        crew_txt = _clean(self.crew) or "усі бригади"
        self.cell(0, 5, f"Бригада: {crew_txt}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 5, f"Період: {period}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def _group_by_crew(self) -> list[tuple[str, list[dict]]]:
        """Роботи, згруповані по бригадах (без бригади — в кінці), у кожній — по даті."""
        groups: dict[str, list[dict]] = {}
        order: list[str] = []
        for w in self.works:
            key = (w.get("crew") or "").strip() or "— без бригади —"
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(w)
        order.sort(key=str.lower)
        # «без бригади» — завжди останньою
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
        self.cell(_COL_DATE, 6, " Дата", fill=True)
        self.cell(_COL_PROJECT, 6, " Проєкт / адреса", fill=True)
        self.cell(_COL_WORK, 6, " Робота", fill=True)
        self.cell(_COL_PRICE, 6, " Сума, ₴", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def _crew_section(self, crew_name: str, rows: list[dict]):
        # Заголовок бригади
        if self.get_y() > 250:
            self.add_page()
        self.set_fill_color(232, 238, 252)
        self._bold(11)
        total = sum(float(r.get("total_price") or 0) for r in rows)
        title = f"{crew_name}   ({len(rows)} роб. | {total:,.2f} ₴)"
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

            # Висота рядка: проєкт (2 рядки, якщо є адреса)
            height = 10 if address else 6
            if self.get_y() + height > 280:
                self.add_page()
                self._table_header()

            # Чергування фону; роздільна лінія між днями
            shade = (d != prev_date) and d is not None
            if shade:
                self.set_fill_color(245, 247, 251)
            self._regular(9)

            x0 = self.get_x()
            y0 = self.get_y()
            self.cell(_COL_DATE, height, f" {date_txt}", fill=shade)
            # Проєкт: номер+назва жирно, адреса — нижче сірим
            x_proj = self.get_x()
            self.cell(_COL_PROJECT, height, "", fill=shade)
            self.set_xy(x_proj, y0 + 1)
            self._bold(9)
            self.multi_cell(
                _COL_PROJECT,
                4,
                _clean(project) or "—",
                new_x="RIGHT",
                new_y="TOP",
            )
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

    def _footer(self):
        if self.get_y() > 255:
            self.add_page()
        self._regular(9)
        self.set_text_color(107, 114, 128)
        generated = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.cell(0, 5, f"Сформовано: {generated}", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(6)
        self._regular(10)
        self.cell(0, 6, "Бригадир: _______________________", new_x="LMARGIN", new_y="NEXT")


def generate_crew_plan(
    works: list[dict],
    crew: str,
    date_from: date,
    date_to: date,
    output_path: str,
    company: dict | None = None,
) -> str:
    """Згенерувати PDF-план монтажів для бригад.

    Параметри:
        works — рядки з list_scheduled_works() (work_date, project_number,
                project_name, address, work_name, crew, total_price);
        crew — назва бригади для шапки ("" — усі бригади);
        date_from/date_to — межі періоду для шапки;
        company — реквізити фірми (BusinessSettings.get_company()).
    """
    pdf = CrewPlanPDF(works, crew, date_from, date_to, company or {})
    pdf.output(output_path)
    return output_path
