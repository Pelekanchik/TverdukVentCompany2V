"""Акт виконаних робіт (послуг)."""

from datetime import datetime

from ventilation_company.documents.base import BaseDocument
from ventilation_company.documents.company_info import CompanyInfo


class WorkAct(BaseDocument):
    """Акт виконаних робіт (послуг)."""

    def __init__(self, company: CompanyInfo, client: CompanyInfo, act_number: str = ""):
        super().__init__(company, client, title="АКТ ВИКОНАНИХ РОБІТ")
        self.doc_number = act_number or f"АВР-{datetime.now().strftime('%Y%m%d-%H%M')}"
        self.contract_number = ""
        self.contract_date = ""

    def header(self):
        self.set_font("DejaVu", "B", 14)
        self.cell(0, 10, self.doc_title, ln=True, align="C")
        self.set_font("DejaVu", "", 10)
        self.cell(0, 6, f"№ {self.doc_number} від {self.doc_date}", ln=True, align="C")

        if self.contract_number:
            self.cell(0, 6, f"Договір № {self.contract_number} від {self.contract_date}", ln=True, align="C")
        self.ln(4)

        self._draw_company_block("Виконавець:", self.company, 10, self.get_y(), 90)
        self._draw_company_block("Замовник:", self.client, 110, self.get_y() - 25, 90)
        self.ln(10)

    def build(self, items: list[dict], filepath: str) -> str:
        self.add_page()  # header() викликається автоматично

        headers = ["№", "Найменування робіт (послуг)", "Од.", "К-ть", "Ціна", "Сума"]
        widths = [10, 90, 15, 15, 30, 35]

        self._draw_table_header(headers, widths, self.get_y())

        subtotal = 0.0
        for i, item in enumerate(items, 1):
            cells = [
                str(i),
                item.get("name", ""),
                item.get("unit", "шт"),
                str(item.get("qty", 1)),
                f"{item.get('price', 0):,.2f}",
                f"{item.get('total', 0):,.2f}",
            ]
            self._draw_table_row(cells, widths)
            subtotal += float(item.get("total", 0))

        self.ln(5)
        self._draw_totals(subtotal)

        # Текст акта
        self.ln(10)
        self.set_font("DejaVu", "", 10)
        text = (
            f"Всього виконано робіт (надано послуг) на суму {subtotal:,.2f} грн, "
            f"в тому числі ПДВ — {subtotal * 0.2:,.2f} грн. "
            f"Замовник претензій до якості та обсягу виконаних робіт не має."
        )
        self.multi_cell(0, 6, text)

        self.ln(10)
        self._draw_signatures(self.get_y())

        self.output(filepath)
        return filepath
