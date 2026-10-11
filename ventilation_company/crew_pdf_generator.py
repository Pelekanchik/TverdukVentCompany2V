"""Єдиний генератор PDF-документів для монтажних бригад.

Два режими (mode) на одному класі:
  • "plan"   — щотижневий план робіт по бригадах (суми для орієнту);
  • "report" — чек-лист виконаних робіт з квадратиками «виконано»
               та підписами (бригадир / інженер).

Раніше існували два майже ідентичні модулі (crew_plan_generator.py та
crew_report_generator.py, ~70 % спільного коду) — будь-яка зміна друку
доводилася вносити двічі. Тепер спільна логіка тут; старі модулі
залишені як тонкі обгортки для зворотної сумісності.

Використання:
    generate_crew_plan(works, crew, date_from, date_to, path, company)
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

# Ширини колонок таблиці (мм, разом 170) для кожного режиму.
_COLUMNS = {
    "plan": {"date": 24, "project": 68, "work": 55, "price": 23},
    "report": {"check": 14, "date": 22, "project": 62, "work": 48, "price": 24},
}

_TITLES = {
    "plan": ("ПЛАН МОНТАЖНИХ РОБІТ", 15),
    "report": ("ЗВІТ БРИГАДИ ПРО ВИКОНАНІ РОБОТИ", 14),
}

_MODE_HINT = {
    "report": "Бригадир ставить позначку у квадратику навпроти виконаної роботи.",
}

# Назви колонок — спільні для обох режимів (у "plan" колонки «check» немає).


class CrewPDF(FPDF):
    """PDF-документ для монтажних бригад (план або чек-лист звіту)."""

    def __init__(
        self,
        works: list[dict],
        crew: str,
        date_from: date,
        date_to: date,
        company: dict,
        mode: str = "plan",
    ):
        if mode not in _COLUMNS:
            raise ValueError(f"Невідомий режим CrewPDF: {mode!r} (очікується plan|report)")
        super().__init__(orientation="P", unit="mm", format="A4")
        self.works = works
        self.crew = crew
        self.date_from = date_from
        self.date_to = date_to
        self.company = company or {}
        self.mode = mode
        self.col = _COLUMNS[mode]
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
        if self.mode == "report":
            self._signatures()
        else:
            self._footer()

    def _header(self):
        name = _clean(self.company.get("name") or "")
        if name:
            self._bold(9)
            self.set_text_color(90, 90, 90)
            self.cell(0, 5, name, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        title, size = _TITLES[self.mode]
        self._bold(size)
        self.cell(0, 9, title, align="C", new_x="LMARGIN", new_y="NEXT")
        self._regular(10)
        period = f"{self.date_from.strftime('%d.%m.%Y')} – {self.date_to.strftime('%d.%m.%Y')}"
        crew_txt = _clean(self.crew) or "усі бригади"
        self.cell(0, 5, f"Бригада: {crew_txt}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 5, f"Період: {period}", align="C", new_x="LMARGIN", new_y="NEXT")
        hint = _MODE_HINT.get(self.mode)
        if hint:
            self._regular(9)
            self.set_text_color(107, 114, 128)
            self.cell(0, 5, hint, align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0, 0, 0)
            self.ln(2)
        else:
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
        if self.mode == "report":
            self.cell(self.col["check"], 6, "", fill=True)
        self.cell(self.col["date"], 6, " Дата", fill=True)
        self.cell(self.col["project"], 6, " Проєкт / адреса", fill=True)
        self.cell(self.col["work"], 6, " Робота", fill=True)
        self.cell(self.col["price"], 6, " Сума, ₴", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def _checkbox(self, x: float, y: float, size: float = 4.5):
        """Порожній квадратик для галочки (малюємо рамку, символ шрифту не потрібен)."""
        self.set_draw_color(31, 41, 55)
        self.set_line_width(0.3)
        self.rect(x, y, size, size)
        self.set_line_width(0.2)

    def _crew_section(self, crew_name: str, rows: list[dict]):
        # Заголовок бригади
        if self.get_y() > 250:
            self.add_page()
        self.set_fill_color(232, 238, 252)
        self._bold(11)
        if self.mode == "report":
            title = f"{crew_name}   ({len(rows)} роб.)"
        else:
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

            if self.mode == "report":
                y0_check = self.get_y()
                self.cell(self.col["check"], height, "", fill=shade)
                # Квадратик для галочки — по центру комірки
                self._checkbox(
                    self.get_x() - self.col["check"] / 2 - 2.25, y0_check + height / 2 - 2.25
                )

            x0 = self.get_x()
            y0 = self.get_y()
            self.cell(self.col["date"], height, f" {date_txt}", fill=shade)
            # Проєкт: номер+назва жирно, адреса — нижче сірим
            x_proj = self.get_x()
            self.cell(self.col["project"], height, "", fill=shade)
            self.set_xy(x_proj, y0 + 1)
            self._bold(9)
            self.multi_cell(
                self.col["project"],
                4,
                _clean(project) or "—",
                new_x="RIGHT",
                new_y="TOP",
            )
            if address:
                self.set_xy(x_proj, y0 + 5.5)
                self._regular(8)
                self.set_text_color(107, 114, 128)
                self.multi_cell(self.col["project"], 4, address, new_x="RIGHT", new_y="TOP")
                self.set_text_color(0, 0, 0)
            self.set_xy(x_proj + self.col["project"], y0)
            self._regular(9)
            self.cell(self.col["work"], height, f" {work}", fill=shade)
            self.cell(
                self.col["price"],
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


def _generate(
    works: list[dict],
    crew: str,
    date_from: date,
    date_to: date,
    output_path: str,
    company: dict | None,
    mode: str,
) -> str:
    pdf = CrewPDF(works, crew, date_from, date_to, company or {}, mode=mode)
    pdf.output(output_path)
    return output_path


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
    return _generate(works, crew, date_from, date_to, output_path, company, "plan")


def generate_crew_report(
    works: list[dict],
    crew: str,
    date_from: date,
    date_to: date,
    output_path: str,
    company: dict | None = None,
) -> str:
    """Згенерувати PDF-звіт бригади про виконання (чек-лист).

    Параметри — як у generate_crew_plan.
    """
    return _generate(works, crew, date_from, date_to, output_path, company, "report")
