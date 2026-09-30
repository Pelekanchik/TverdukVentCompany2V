"""Генератор акта виконаних робіт (PDF).

Документ для підписання з замовником: перелік виконаних робіт/поставлених
виробів з кількістю та цінами, загальна сума з ПДВ, реквізити сторін,
підписи. Реквізити фірми (Виконавця) підставляються з
«Налаштування → Бізнес» (services/business_settings.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ventilation_company.proposal_generator import _clean, _find_fonts

try:
    from fpdf import FPDF
except ImportError:
    raise ImportError("Бібліотека fpdf2 не встановлена. Виконайте: pip install fpdf2") from None

_ONES = [
    "",
    "одна",
    "дві",
    "три",
    "чотири",
    "п'ять",
    "шість",
    "сім",
    "вісім",
    "дев'ять",
    "десять",
    "одинадцять",
    "дванадцять",
    "тринадцять",
    "чотирнадцять",
    "п'ятнадцять",
    "шістнадцять",
    "сімнадцять",
    "вісімнадцять",
    "дев'ятнадцять",
]
_TENS = [
    "",
    "",
    "двадцять",
    "тридцять",
    "сорок",
    "п'ятдесят",
    "шістдесят",
    "сімдесят",
    "вісімдесят",
    "дев'яносто",
]
_HUNDREDS = [
    "",
    "сто",
    "двісті",
    "триста",
    "чотириста",
    "п'ятсот",
    "шістсот",
    "сімсот",
    "вісімсот",
    "дев'ятсот",
]


def _triad_words(n: int) -> str:
    """Число 0..999 словами (жіночий рід для «тисячі»/«одна»)."""
    parts = []
    if n >= 100:
        parts.append(_HUNDREDS[n // 100])
        n %= 100
    if n >= 20:
        parts.append(_TENS[n // 10])
        n %= 10
    if n > 0:
        parts.append(_ONES[n])
    return " ".join(p for p in parts if p)


def amount_in_words(amount: float) -> str:
    """Сума прописом українською: 1234.50 → «одна тисяча ... гривень 50 копійок»."""
    total_kop = round(amount * 100)
    hryvnias, kopecks = divmod(int(total_kop), 100)
    if hryvnias == 0:
        words = "нуль"
    else:
        groups = []
        rest = hryvnias
        scales = [
            (10**9, "мільярд", "мільярди", "мільярдів"),
            (10**6, "мільйон", "мільйони", "мільйонів"),
            (10**3, "тисяча", "тисячі", "тисяч"),
        ]
        for scale, one, few, many in scales:
            count, rest = divmod(rest, scale)
            if count:
                if scale == 10**3:
                    w = _triad_words(count)
                else:
                    w = _triad_words(count).replace("одна", "один").replace("дві", "два")
                if count % 10 == 1 and count % 100 != 11:
                    suffix = one
                elif 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
                    suffix = few
                else:
                    suffix = many
                groups.append(f"{w} {suffix}")
        groups.append(_triad_words(rest))
        words = " ".join(g for g in groups if g).strip() or "нуль"
    h_mod100 = hryvnias % 100
    if h_mod100 % 10 == 1 and h_mod100 != 11:
        unit = "гривня"
    elif 2 <= h_mod100 % 10 <= 4 and not 12 <= h_mod100 <= 14:
        unit = "гривні"
    else:
        unit = "гривень"
    return f"{words} {unit} {kopecks:02d} копійок"


@dataclass
class ActItem:
    """Одна позиція акта: робота або виріб."""

    name: str = ""
    description: str = ""
    quantity: float = 1.0
    unit: str = "шт"
    price_per_unit: float = 0.0
    total: float = 0.0


@dataclass
class ActData:
    """Дані для акта виконаних робіт."""

    # Фірма (Виконавець)
    company_name: str = "ТОВ «ВентКомпані»"
    company_address: str = "м. Київ, вул. Промислова, 15"
    company_phone: str = "+38 (044) 123-45-67"
    company_edrpou: str = "12345678"
    company_signatory: str = "Директор Іваненко І.І."

    # Клієнт (Замовник)
    client_name: str = ""
    client_address: str = ""
    client_signatory: str = ""

    # Акт
    act_number: str = ""
    date: str = field(default_factory=lambda: datetime.now().strftime("%d.%m.%Y"))
    city: str = "м. Київ"

    # Підстава та зміст
    contract_number: str = ""
    project_name: str = ""
    project_number: str = ""
    items: list[ActItem] = field(default_factory=list)
    vat_percent: float = 20.0
    notes: str = ""


class ActPDF(FPDF):
    """PDF-документ акта виконаних робіт (класичний текстовий формат)."""

    def __init__(self, data: ActData):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.data = data
        self.regular_font, self.bold_font = _find_fonts()
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)
        self.add_font("Main", "", self.regular_font)
        self.add_font("Main", "B", self.bold_font)
        self._build()

    # ── Шрифти ──

    def _regular(self, size: int = 11):
        self.set_font("Main", "", size)

    def _bold(self, size: int = 11):
        self.set_font("Main", "B", size)

    def _mc(self, h: float, text: str, align: str = "L"):
        """Текстовий блок: завжди з лівого поля, після — новий рядок зліва."""
        self.set_x(self.l_margin)
        self.multi_cell(170, h, text, align=align, new_x="LMARGIN", new_y="NEXT")

    # ── Побудова ──

    def _build(self):
        self.add_page()
        self._header()
        self._intro()
        self._items_table()
        self._totals()
        self._claim()
        self._signatures()

    def _header(self):
        self._bold(10)
        self.set_text_color(60, 60, 60)
        self._mc(5, _clean(self.data.company_name), align="R")
        self._mc(5, f"ЄДРПОУ {_clean(self.data.company_edrpou)}", align="R")
        self._mc(5, _clean(self.data.company_address), align="R")
        self.ln(4)

        self.set_text_color(0, 0, 0)
        self._bold(14)
        self._mc(8, "АКТ", align="C")
        self._bold(11)
        self._mc(6, f"виконаних робіт № {_clean(self.data.act_number)}", align="C")
        self._regular(11)
        self._mc(
            6,
            f"{_clean(self.data.city)}                                                                 "
            f"«{_clean(self.data.date)}»",
            align="L",
        )
        self.ln(2)

    def _intro(self):
        basis = (
            f"до договору № {_clean(self.data.contract_number)}"
            if self.data.contract_number
            else "____________________"
        )
        text = (
            f"{_clean(self.data.company_name)}, надалі — «Виконавець», в особі "
            f"{_clean(self.data.company_signatory)}, і "
            f"{_clean(self.data.client_name) or '____________________'}, надалі — «Замовник», "
            f"в особі {_clean(self.data.client_signatory) or '____________________'}, "
            f"склали цей Акт про те, що на підставі {basis} Виконавцем виконано, "
            "а Замовником прийнято наступні роботи:"
        )
        self._regular(11)
        self._mc(5.5, text)
        self.ln(2)

    def _items_table(self):
        cols = [
            ("№", 10),
            ("Найменування робіт / виробів", 78),
            ("К-ть", 16),
            ("Од.", 12),
            ("Ціна, грн", 26),
            ("Сума, грн", 28),
        ]
        header_h = 7

        def draw_header():
            self.set_x(self.l_margin)
            self._bold(9)
            self.set_fill_color(230, 230, 230)
            for title, w in cols:
                self.cell(w, header_h, title, border=1, fill=True, align="C")
            self.ln(header_h)

        draw_header()
        self._regular(9)
        for i, item in enumerate(self.data.items, 1):
            name = _clean(item.name)
            if item.description:
                name = f"{name} ({_clean(item.description)})"
            split = self.multi_cell(cols[1][1], 5, name, split_only=True)
            lines = split if isinstance(split, list) else [name]
            row_h = max(6, 5 * len(lines) + 1)
            if self.get_y() + row_h > 275:
                self.add_page()
                draw_header()
                self._regular(9)

            y = self.get_y()
            x = self.l_margin
            self.set_xy(x, y)
            self.cell(cols[0][1], row_h, str(i), border=1, align="C")
            self.multi_cell(
                cols[1][1],
                5,
                name,
                border=1,
                align="L",
                new_x="RIGHT",
                new_y="TOP",
            )
            self.cell(cols[2][1], row_h, f"{item.quantity:g}", border=1, align="C")
            self.cell(cols[3][1], row_h, _clean(item.unit), border=1, align="C")
            self.cell(cols[4][1], row_h, f"{item.price_per_unit:,.2f}", border=1, align="R")
            self.cell(cols[5][1], row_h, f"{item.total:,.2f}", border=1, align="R")
            self.ln(row_h)

    def _totals(self):
        subtotal = round(sum(i.total for i in self.data.items), 2)
        vat = round(subtotal * self.data.vat_percent / 100, 2)
        total = round(subtotal + vat, 2)
        self.ln(2)
        self._regular(10)
        rows = [
            ("Разом без ПДВ:", f"{subtotal:,.2f} грн"),
            (f"ПДВ {self.data.vat_percent:.0f}%:", f"{vat:,.2f} грн"),
            ("Всього з ПДВ:", f"{total:,.2f} грн"),
        ]
        for label, value in rows:
            self.set_x(self.l_margin)
            self.cell(120, 6, label, align="R")
            self.cell(50, 6, value, align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self._bold(10)
        self._mc(5.5, f"Загальна вартість виконаних робіт становить {amount_in_words(total)}.")
        self._regular(10)
        if self.data.notes:
            self._mc(5, f"Примітка: {_clean(self.data.notes)}")

    def _claim(self):
        self.ln(2)
        self._regular(11)
        self._mc(
            5.5,
            "Роботи виконані повністю, якісно та в строк. Замовник претензій до Виконавця "
            "не має. Цей Акт є підставою для остаточного розрахунку.",
        )

    def _signatures(self):
        if self.get_y() > 235:
            self.add_page()
        self.ln(6)

        col_w = 85
        self._bold(10)
        y = self.get_y()
        self.set_xy(self.l_margin, y)
        self.cell(col_w, 6, "ВИКОНАВЕЦЬ:", new_x="RIGHT", new_y="TOP")
        self.cell(col_w, 6, "ЗАМОВНИК:", new_x="RIGHT", new_y="NEXT")
        self.set_x(self.l_margin)
        self._regular(10)
        pairs = [
            (_clean(self.data.company_name), _clean(self.data.client_name)),
            (f"ЄДРПОУ {_clean(self.data.company_edrpou)}", ""),
            (f"Тел.: {_clean(self.data.company_phone)}", ""),
        ]
        for left, right in pairs:
            y = self.get_y()
            self.set_xy(self.l_margin, y)
            self.cell(col_w, 5.5, left, new_x="RIGHT", new_y="TOP")
            self.cell(col_w, 5.5, right, new_x="RIGHT", new_y="NEXT")
        self.ln(10)
        for line_left, line_right in [
            ("____________________", "____________________"),
            (
                f"{_clean(self.data.company_signatory)}",
                f"{_clean(self.data.client_signatory) or '____________________'}",
            ),
            ("(підпис, М.П.)", "(підпис, М.П.)"),
        ]:
            y = self.get_y()
            self.set_xy(self.l_margin, y)
            self.cell(col_w, 5.5, line_left, new_x="RIGHT", new_y="TOP")
            self.cell(col_w, 5.5, line_right, new_x="RIGHT", new_y="NEXT")


def generate_act(project_data: dict, items: list[dict], output_path: str) -> str:
    """Згенерувати акт виконаних робіт з даних проєкту."""
    data = ActData()
    data.act_number = project_data.get("act_number", f"АКТ-{datetime.now().strftime('%Y%m%d')}-001")
    data.project_name = project_data.get("name", "")
    data.project_number = project_data.get("project_number", "")
    data.client_name = project_data.get("client", "")
    data.client_address = project_data.get("address", "")
    data.client_signatory = project_data.get("client_signatory", "")
    data.contract_number = project_data.get("contract_number", "")
    if project_data.get("notes"):
        data.notes = str(project_data["notes"])

    data.items = []
    for it in items:
        qty = float(it.get("quantity", 1))
        price = float(it.get("price", 0))
        data.items.append(
            ActItem(
                name=it.get("name", ""),
                description=it.get("description", ""),
                quantity=qty,
                unit=it.get("unit", "шт"),
                price_per_unit=price,
                total=round(qty * price, 2),
            )
        )

    company = project_data.get("company") or {}
    if isinstance(company, dict):
        data.company_name = str(company.get("name") or data.company_name)
        data.company_address = str(company.get("address") or data.company_address)
        data.company_phone = str(company.get("phone") or data.company_phone)
        data.company_edrpou = str(company.get("edrpou") or data.company_edrpou)
        data.company_signatory = str(company.get("signatory") or data.company_signatory)
        data.city = str(company.get("city") or data.city)

    pdf = ActPDF(data)
    pdf.output(output_path)
    return output_path
