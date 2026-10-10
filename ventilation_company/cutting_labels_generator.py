"""Етикетки з QR-кодами для деталей розкрою (A4, сітка 2×5).

Кожна етикетка ~95×50 мм: QR-код із коротким описом деталі +
текст: номер, назва, розміри, координати на листі, матеріал.
Нумерація суцільна по всіх листах плану (співпадає з номерами
у PDF-плані розкрою — перший лист 1..N, далі наступний лист).
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

from fpdf import FPDF

from ventilation_company.proposal_generator import _clean, _find_fonts

try:  # qrcode[pil] — опційна залежність (є в requirements)
    import qrcode
except ImportError:  # pragma: no cover
    qrcode = None  # type: ignore[assignment]

# Геометрія сітки етикеток (мм).
LABEL_W = 95.0
LABEL_H = 50.0
MARGIN_X = 10.0
MARGIN_Y = 10.0
COLS = 2
ROWS = 5


def _qr_image(text: str) -> BytesIO | None:
    """PNG QR-коду в буфері; None якщо qrcode недоступний."""
    if qrcode is None:
        return None
    img = qrcode.make(text, box_size=4, border=1)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


class _LabelsPDF(FPDF):
    def __init__(self, plan, meta: dict | None = None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.plan = plan
        self.meta = meta or {}
        regular, bold = _find_fonts()
        self.add_font("Main", "", regular)
        self.add_font("Main", "B", bold)
        self.set_auto_page_break(auto=False)  # сітка фіксована, розриви сторінок вручну
        self._build()

    def _build(self):
        labels = self._collect_labels()
        if not labels:
            return
        per_page = COLS * ROWS
        for start in range(0, len(labels), per_page):
            self.add_page()
            page_labels = labels[start : start + per_page]
            for idx, label in enumerate(page_labels):
                col = idx % COLS
                row = idx // COLS
                x = MARGIN_X + col * LABEL_W
                y = MARGIN_Y + row * LABEL_H
                self._draw_label(x, y, label)

    def _collect_labels(self) -> list[dict]:
        """Усі розміщені деталі всіх листів, суцільна нумерація."""
        material = self.meta.get("material", "")
        thickness = self.meta.get("thickness", "")
        labels = []
        n = 0
        for sheet in self.plan.sheets:
            for p in sheet.placed_details:
                n += 1
                name = p.detail.name
                qr_text = (
                    f"#{n}|{name[:40]}|{p.width:.0f}x{p.height:.0f}|" f"{material} {thickness}mm"
                )
                labels.append(
                    {
                        "num": n,
                        "name": name,
                        "width": p.width,
                        "height": p.height,
                        "x": p.x,
                        "y": p.y,
                        "qr": qr_text,
                    }
                )
        return labels

    def _draw_label(self, x: float, y: float, label: dict) -> None:
        # Рамка етикетки
        self.set_draw_color(40, 40, 60)
        self.set_line_width(0.3)
        self.rect(x, y, LABEL_W, LABEL_H)

        qr_buf = _qr_image(label["qr"])
        qr_size = 34.0
        if qr_buf is not None:
            self.image(qr_buf, x=x + 3, y=y + 3, w=qr_size, h=qr_size)
        else:  # qrcode недоступний — великий номер замість QR
            self.set_xy(x + 3, y + 8)
            self.set_font("Main", "B", 26)
            self.set_text_color(30, 30, 40)
            self.cell(qr_size, 16, f"№{label['num']}", align="C")

        # Текст праворуч від QR
        tx = x + qr_size + 7
        self.set_xy(tx, y + 4)
        self.set_text_color(30, 30, 40)
        self.set_font("Main", "B", 13)
        self.cell(LABEL_W - (tx - x) - 3, 7, f"№ {label['num']}")

        self.set_x(tx)
        self.set_font("Main", "", 8.5)
        name = _clean(str(label["name"]))[:30]
        self.cell(LABEL_W - (tx - x) - 3, 6, name, new_x="LMARGIN", new_y="NEXT")

        self.set_x(tx)
        self.set_font("Main", "B", 10)
        self.cell(
            LABEL_W - (tx - x) - 3,
            6,
            f"{label['width']:.0f} × {label['height']:.0f} мм",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_x(tx)
        self.set_font("Main", "", 8.5)
        self.cell(
            LABEL_W - (tx - x) - 3,
            6,
            _clean(f"X: {label['x']:.0f}   Y: {label['y']:.0f}"),
            new_x="LMARGIN",
            new_y="NEXT",
        )

        # Нижній рядок: матеріал
        self.set_xy(x + 3, y + LABEL_H - 8)
        self.set_font("Main", "", 7.5)
        self.set_text_color(100, 100, 110)
        info = _clean(
            f"{self.meta.get('material', '—')} {self.meta.get('thickness', '')} мм"
            f"  •  VentCompany {datetime.now():%d.%m.%Y}"
        )
        self.cell(LABEL_W - 6, 6, info[:52])


def generate_labels_pdf(plan, output_path: str, meta: dict | None = None) -> str:
    """Згенерувати PDF етикеток для всіх деталей плану. Повертає шлях."""
    pdf = _LabelsPDF(plan, meta)
    pdf.output(output_path)
    return output_path
