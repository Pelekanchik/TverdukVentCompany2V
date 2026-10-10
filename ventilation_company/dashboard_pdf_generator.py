"""PDF-звіт дашборду для друку (A4, одна сторінка)."""

from __future__ import annotations

from datetime import datetime

from fpdf import FPDF

from ventilation_company.proposal_generator import _clean, _find_fonts

MONTH_NAMES = [
    "",
    "Січ",
    "Лют",
    "Бер",
    "Кві",
    "Тра",
    "Чер",
    "Лип",
    "Сер",
    "Вер",
    "Жов",
    "Лис",
    "Гру",
]


def _fmt_uah(amount: float) -> str:
    return "₴ " + f"{amount:,.0f}".replace(",", " ")


class _DashboardPDF(FPDF):
    def __init__(self, stats: dict):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.stats = stats
        regular, bold = _find_fonts()
        self.add_font("Main", "", regular)
        self.add_font("Main", "B", bold)
        self.set_auto_page_break(auto=True, margin=15)
        self._build()

    def _build(self):
        s = self.stats
        self.add_page()
        self.set_font("Main", "B", 16)
        self.cell(0, 9, "VentCompany — зведення дашборду", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Main", "", 9)
        self.set_text_color(90, 90, 105)
        self.cell(
            0,
            5,
            _clean(f"Сформовано: {datetime.now():%d.%m.%Y %H:%M}"),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_text_color(31, 41, 55)
        self.ln(3)

        # ── Ключові показники ──
        self.set_font("Main", "B", 11)
        self.cell(0, 7, "Ключові показники", new_x="LMARGIN", new_y="NEXT")
        rows = [
            ("Проєктів (активних)", f"{s['total_count']} ({s['active_count']})"),
            ("Договірна вартість", _fmt_uah(s["total_revenue"])),
            ("Отримано оплат", _fmt_uah(s["paid"])),
            ("Дебіторка (баланс)", _fmt_uah(s["debt"])),
            ("Клієнтів", str(s["clients"])),
            ("Завершено проєктів", str(s["done_count"])),
        ]
        if s.get("overpaid", 0) > 0:
            rows.append(("Передоплати", _fmt_uah(s["overpaid"])))
        self.set_font("Main", "", 10)
        for label, value in rows:
            self.cell(70, 6.5, _clean(label))
            self.set_font("Main", "B", 10)
            self.cell(0, 6.5, _clean(value), new_x="LMARGIN", new_y="NEXT")
            self.set_font("Main", "", 10)
        self.ln(3)

        # ── Таблиці по місяцях ──
        self._monthly_table(
            "Проєкти по місяцях (вартість, тис. ₴)",
            s["monthly"],
            lambda r: (
                MONTH_NAMES[r["month"]] + (f" ({r['count']})" if r["count"] != 1 else ""),
                f"{r['sum'] / 1000:.1f}",
            ),
        )
        self._monthly_table(
            "Надходження оплат по місяцях (тис. ₴)",
            s.get("payments_monthly", []),
            lambda r: (MONTH_NAMES[r["month"]], f"{r['sum'] / 1000:.1f}"),
        )

        # ── Статуси ──
        self.set_font("Main", "B", 11)
        self.cell(0, 7, "Розподіл проєктів за статусами", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Main", "", 10)
        for row in s["statuses"]:
            self.cell(70, 6.5, _clean(str(row["status"])))
            self.set_font("Main", "B", 10)
            self.cell(0, 6.5, str(row["count"]), new_x="LMARGIN", new_y="NEXT")
            self.set_font("Main", "", 10)

    def _monthly_table(self, title: str, rows: list[dict], fmt) -> None:
        self.set_font("Main", "B", 11)
        self.cell(0, 7, _clean(title), new_x="LMARGIN", new_y="NEXT")
        self.set_font("Main", "", 10)
        if not rows:
            self.set_text_color(120, 120, 135)
            self.cell(0, 6, "Немає даних", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(31, 41, 55)
            self.ln(2)
            return
        for row in rows:
            label, value = fmt(row)
            self.cell(70, 6.5, _clean(str(label)))
            self.set_font("Main", "B", 10)
            self.cell(0, 6.5, _clean(str(value)), new_x="LMARGIN", new_y="NEXT")
            self.set_font("Main", "", 10)
        self.ln(2)


def generate_dashboard_pdf(stats: dict, output_path: str) -> str:
    """Згенерувати односторінковий PDF-звіт дашборду; повертає шлях."""
    pdf = _DashboardPDF(stats)
    pdf.output(output_path)
    return output_path
