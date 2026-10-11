"""Генератор договору на виготовлення та монтаж вентиляційних систем (PDF).

Шаблон типового договору з автоматичним підставленням даних проєкту:
рекомендації сторін, предмет, ціна з ПДВ, строки, оплата, гарантія, підписи.
"""

from dataclasses import dataclass, field
from datetime import datetime

from ventilation_company.proposal_generator import _clean, _find_fonts

try:
    from fpdf import FPDF
except ImportError:
    raise ImportError("Бібліотека fpdf2 не встановлена. Виконайте: pip install fpdf2") from None


@dataclass
class ContractData:
    """Дані для договору."""

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

    # Договір
    contract_number: str = ""
    date: str = field(default_factory=lambda: datetime.now().strftime("%d.%m.%Y"))
    city: str = "м. Київ"

    # Предмет та гроші
    project_name: str = ""
    project_number: str = ""
    total_amount: float = 0.0
    vat_percent: float = 20.0
    delivery_days: int = 14
    installation_days: int = 7
    warranty_months: int = 24
    payment_terms: str = (
        "50% аванс протягом 5 банківських днів після підписання договору, 50% — після завершення монтажу"
    )


class ContractPDF(FPDF):
    """PDF-документ договору (класичний текстовий формат)."""

    def __init__(self, data: ContractData):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.data = data
        self.regular_font, self.bold_font = _find_fonts()
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)
        self.add_font("Main", "", self.regular_font)
        self.add_font("Main", "B", self.bold_font)
        self._build()

    def _regular(self, size: int = 11):
        self.set_font("Main", "", size)

    def _bold(self, size: int = 11):
        self.set_font("Main", "B", size)

    def _mc(self, h: float, text: str, align: str = "L"):
        """Текстовий блок: завжди з лівого поля, після — новий рядок зліва.

        Без цього multi_cell лишає x на правому краю й наступний блок
        з'їжджає за межі сторінки.
        """
        self.set_x(self.l_margin)
        self.multi_cell(170, h, text, align=align, new_x="LMARGIN", new_y="NEXT")

    def _build(self):
        self.add_page()
        self._header()
        self._parties()
        self._sections()
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
        self._mc(8, "ДОГОВІР", align="C")
        self._bold(11)
        self._mc(
            6,
            f"№ {_clean(self.data.contract_number)} на виготовлення та монтаж "
            "вентиляційних систем",
            align="C",
        )
        self._regular(11)
        self._mc(
            6,
            f"{_clean(self.data.city)}                                                                 "
            f"«{_clean(self.data.date)}»",
            align="L",
        )
        self.ln(2)

    def _parties(self):
        self._regular(11)
        text = (
            f"{_clean(self.data.company_name)}, надалі — «Виконавець», в особі "
            f"{_clean(self.data.company_signatory)}, з одного боку, та "
            f"{_clean(self.data.client_name) or '____________________'}, надалі — «Замовник», "
            f"в особі {_clean(self.data.client_signatory) or '____________________'}, "
            "з іншого боку, разом — «Сторони», уклали цей Договір про нижченаведене:"
        )
        self._mc(5.5, text)
        self.ln(2)

    def _sections(self):
        sections = [
            (
                "1. ПРЕДМЕТ ДОГОВОРУ",
                f"1.1. Виконавець зобов'язується виготовити та змонтувати вентиляційні "
                f"системи згідно з технічним завданням та специфікацією проєкту "
                f"«{_clean(self.data.project_name)}»"
                + (f" (№ {_clean(self.data.project_number)})" if self.data.project_number else "")
                + ", а Замовник зобов'язується прийняти та оплатити виконані роботи.\n"
                "1.2. Склад і кількість виробів, вартість робіт та матеріалів "
                "визначаються специфікацією, що є невід'ємною частиною цього Договору.",
            ),
            (
                "2. ЦІНА ДОГОВОРУ",
                f"2.1. Загальна вартість робіт за цим Договором становить "
                f"{self.data.total_amount:,.2f} грн, у тому числі ПДВ {self.data.vat_percent:.0f}%.\n"
                "2.2. Ціна є фіксованою і може бути змінена лише за письмовою згодою Сторін.",
            ),
            (
                "3. СТРОКИ ВИКОНАННЯ",
                f"3.1. Термін виготовлення виробів — {self.data.delivery_days} робочих днів "
                "з моменту отримання авансового платежу.\n"
                f"3.2. Термін монтажних робіт — {self.data.installation_days} робочих днів "
                "з моменту готовності об'єкта до монтажу.",
            ),
            (
                "4. ПОРЯДОК ОПЛАТИ",
                f"4.1. Оплата здійснюється Замовником у такому порядку: "
                f"{_clean(self.data.payment_terms)}.\n"
                "4.2. Зобов'язання Замовника вважаються виконаними з моменту зарахування "
                "коштів на розрахунковий рахунок Виконавця.",
            ),
            (
                "5. ГАРАНТІЙНІ ЗОБОВ'ЯЗАННЯ",
                f"5.1. Виконавець надає гарантію на вироби та монтажні роботи "
                f"терміном {self.data.warranty_months} місяців з дати підписання акту "
                "виконаних робіт.\n"
                "5.2. Гарантійне обслуговування включає усунення дефектів, що виникли "
                "з вини Виконавця.",
            ),
            (
                "6. ВІДПОВІДАЛЬНІСТЬ СТОРІН",
                "6.1. Сторони несуть відповідальність за невиконання або неналежне "
                "виконання зобов'язань відповідно до чинного законодавства України.\n"
                "6.2. У разі прострочення оплати Замовник сплачує пеню в розмірі "
                "подвійної облікової ставки НБУ від суми боргу за кожний день прострочення.",
            ),
            (
                "7. ПОРЯДОК ВИРІШЕННЯ СПОРІВ",
                "7.1. Спори вирішуються шляхом переговорів, а у разі недосягнення згоди — "
                "в судовому порядку відповідно до законодавства України.",
            ),
            (
                "8. ІНШІ УМОВИ",
                "8.1. Договір складено у двох примірниках, що мають однакову юридичну силу.\n"
                "8.2. Додатки та специфікації, підписані Сторонами, є невід'ємною "
                "частиною цього Договору.",
            ),
        ]
        for title, body in sections:
            if self.get_y() > 250:
                self.add_page()
            self._bold(11)
            self._mc(6, title)
            self._regular(11)
            self._mc(5.5, body)
            self.ln(2)

    def _signatures(self):
        if self.get_y() > 240:
            self.add_page()
        self.ln(4)
        self._bold(11)
        self._mc(6, "9. АДРЕСИ ТА РЕКВІЗИТИ СТОРІН")
        self.ln(2)

        col_w = 85
        y = self.get_y()
        self.set_xy(self.l_margin, y)
        self._bold(10)
        self.cell(col_w, 6, "ВИКОНАВЕЦЬ:", new_x="RIGHT", new_y="TOP")
        self.cell(col_w, 6, "ЗАМОВНИК:", new_x="RIGHT", new_y="NEXT")
        self.set_x(self.l_margin)
        self._regular(10)
        pairs = [
            (_clean(self.data.company_name), _clean(self.data.client_name)),
            (_clean(self.data.company_address), _clean(self.data.client_address)),
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


def generate_contract(project_data: dict, output_path: str) -> str:
    """Згенерувати договір з даних проєкту."""
    data = ContractData()
    data.contract_number = project_data.get(
        "contract_number", f"ДГ-{datetime.now().strftime('%Y%m%d')}-001"
    )
    data.project_name = project_data.get("name", "")
    data.project_number = project_data.get("project_number", "")
    data.client_name = project_data.get("client", "")
    data.client_address = project_data.get("address", "")
    data.client_signatory = project_data.get("client_signatory", "")
    data.total_amount = round(float(project_data.get("total_amount") or 0), 2)
    data.delivery_days = int(project_data.get("delivery_days") or 14)
    data.installation_days = int(project_data.get("installation_days") or 7)
    data.warranty_months = int(project_data.get("warranty_months") or 24)
    if project_data.get("payment_terms"):
        data.payment_terms = str(project_data["payment_terms"])
    company = project_data.get("company") or {}
    if isinstance(company, dict):
        data.company_name = str(company.get("name") or data.company_name)
        data.company_address = str(company.get("address") or data.company_address)
        data.company_phone = str(company.get("phone") or data.company_phone)
        data.company_edrpou = str(company.get("edrpou") or data.company_edrpou)
        data.company_signatory = str(company.get("signatory") or data.company_signatory)
        data.city = str(company.get("city") or data.city)

    pdf = ContractPDF(data)
    pdf.output(output_path)
    return output_path
