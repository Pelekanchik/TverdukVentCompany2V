"""Модуль розкрою листового металу.
Алгоритми розкладки деталей на стандартних листах з мінімізацією відходів.
Підтримує Bottom-Left heuristic та Guillotine cutting.
"""

import math
from dataclasses import dataclass, field
from enum import Enum


class SheetSize(Enum):
    """Стандартні розміри листів металу (мм)."""

    SHEET_1250x2500 = (1250, 2500)
    SHEET_1000x2000 = (1000, 2000)
    SHEET_1500x3000 = (1500, 3000)
    SHEET_1250x3000 = (1250, 3000)


@dataclass
class Detail:
    name: str
    width: float
    height: float
    product_type: str = ""
    quantity: int = 1
    notes: str = ""
    material: str = ""
    thickness: float = 0.5

    # Припуски
    bend_allowance: float = 3.0  # мм, припуск на згин з кожного боку
    cut_allowance: float = 2.0  # мм, припуск на різ

    @property
    def total_width(self) -> float:
        """Повна ширина з припусками."""
        return self.width + 2 * self.cut_allowance

    @property
    def total_height(self) -> float:
        """Повна висота з припусками."""
        return self.height + 2 * self.cut_allowance + 2 * self.bend_allowance

    @property
    def area(self) -> float:
        """Площа однієї деталі (м²)."""
        return (self.total_width * self.total_height) / 1_000_000

    @property
    def total_area(self) -> float:
        """Загальна площа з урахуванням кількості."""
        return self.area * self.quantity


@dataclass
class PlacedDetail:
    """Деталь, розміщена на листі."""

    detail: Detail
    x: float  # мм, координата X лівого нижнього кута
    y: float  # мм, координата Y лівого нижнього кута
    rotated: bool = False  # чи повернута на 90°

    @property
    def width(self) -> float:
        return self.detail.total_height if self.rotated else self.detail.total_width

    @property
    def height(self) -> float:
        return self.detail.total_width if self.rotated else self.detail.total_height


@dataclass
class Sheet:
    """Лист металу для розкрою."""

    width: float  # мм
    height: float  # мм
    thickness: float  # мм
    material: str = "оцинкована сталь"

    placed_details: list[PlacedDetail] = field(default_factory=list)
    free_rectangles: list[tuple[float, float, float, float]] = field(default_factory=list)
    # (x, y, width, height) — вільні прямокутники

    def __post_init__(self):
        if not self.free_rectangles:
            self.free_rectangles = [(0, 0, self.width, self.height)]

    @property
    def total_area(self) -> float:
        return (self.width * self.height) / 1_000_000

    @property
    def used_area(self) -> float:
        return sum(p.width * p.height for p in self.placed_details) / 1_000_000

    @property
    def waste_area(self) -> float:
        return self.total_area - self.used_area

    @property
    def utilization(self) -> float:
        """Коефіцієнт використання листа (0-1)."""
        if self.total_area == 0:
            return 0
        return self.used_area / self.total_area

    def place_detail(self, detail: Detail, x: float, y: float, rotated: bool = False) -> bool:
        """Розмістити деталь на листі."""
        w = detail.total_height if rotated else detail.total_width
        h = detail.total_width if rotated else detail.total_height

        # Перевірка меж
        if x + w > self.width or y + h > self.height:
            return False

        # Перевірка перетину з іншими деталями
        for p in self.placed_details:
            if not (x + w <= p.x or p.x + p.width <= x or y + h <= p.y or p.y + p.height <= y):
                return False

        self.placed_details.append(PlacedDetail(detail, x, y, rotated))
        self._update_free_rectangles(x, y, w, h)
        return True

    def _update_free_rectangles(self, x: float, y: float, w: float, h: float):
        """Оновити список вільних прямокутників після розміщення деталі."""
        new_free = []
        for rx, ry, rw, rh in self.free_rectangles:
            # Перевіряємо перетин
            if x + w <= rx or rx + rw <= x or y + h <= ry or ry + rh <= y:
                new_free.append((rx, ry, rw, rh))
                continue

            # Розбиваємо вільний прямокутник
            # Зверху
            if y > ry:
                new_free.append((rx, ry, rw, y - ry))
            # Знизу
            if y + h < ry + rh:
                new_free.append((rx, y + h, rw, ry + rh - y - h))
            # Зліва
            if x > rx:
                new_free.append((rx, ry, x - rx, rh))
            # Справа
            if x + w < rx + rw:
                new_free.append((x + w, ry, rx + rw - x - w, rh))

        # Видаляємо вкладені та занадто маленькі прямокутники
        self.free_rectangles = self._clean_rectangles(new_free)

    def _clean_rectangles(
        self, rectangles: list[tuple[float, float, float, float]]
    ) -> list[tuple[float, float, float, float]]:
        """Очистити список прямокутників від вкладених та занадто малих."""
        # Фільтр за мінімальним розміром (10 мм)
        min_size = 10
        filtered = [(x, y, w, h) for x, y, w, h in rectangles if w >= min_size and h >= min_size]

        # Видалення вкладених
        result = []
        for i, (x1, y1, w1, h1) in enumerate(filtered):
            is_nested = False
            for j, (x2, y2, w2, h2) in enumerate(filtered):
                if i != j and x1 >= x2 and y1 >= y2 and x1 + w1 <= x2 + w2 and y1 + h1 <= y2 + h2:
                    is_nested = True
                    break
            if not is_nested:
                result.append((x1, y1, w1, h1))

        return result

    def find_best_position(self, detail: Detail) -> tuple[float, float, bool] | None:
        """Знайти найкращу позицію для деталі (Bottom-Left heuristic)."""
        best = None
        best_score = float("inf")

        for rx, ry, rw, rh in self.free_rectangles:
            for rotated in [False, True]:
                w = detail.total_height if rotated else detail.total_width
                h = detail.total_width if rotated else detail.total_height

                if w <= rw and h <= rh:
                    # Score: лівіше і нижче = краще
                    score = rx + ry * 2  # пріоритет нижнього розміщення
                    if score < best_score:
                        best_score = score
                        best = (rx, ry, rotated)

        return best

    def to_dict(self) -> dict:
        return {
            "sheet_size": f"{self.width}×{self.height} мм",
            "thickness": self.thickness,
            "material": self.material,
            "total_area_m2": round(self.total_area, 4),
            "used_area_m2": round(self.used_area, 4),
            "waste_area_m2": round(self.waste_area, 4),
            "utilization_percent": round(self.utilization * 100, 2),
            "details_count": len(self.placed_details),
            "details": [
                {
                    "name": p.detail.name,
                    "x": p.x,
                    "y": p.y,
                    "width": p.width,
                    "height": p.height,
                    "rotated": p.rotated,
                }
                for p in self.placed_details
            ],
        }


@dataclass
class CuttingPlan:
    """План розкрою — набір листів з розміщеними деталями."""

    sheets: list[Sheet] = field(default_factory=list)
    unplaced_details: list[Detail] = field(default_factory=list)

    @property
    def total_sheets(self) -> int:
        return len(self.sheets)

    @property
    def total_area(self) -> float:
        return sum(s.total_area for s in self.sheets)

    @property
    def total_used_area(self) -> float:
        return sum(s.used_area for s in self.sheets)

    @property
    def total_waste_area(self) -> float:
        return sum(s.waste_area for s in self.sheets)

    @property
    def overall_utilization(self) -> float:
        if self.total_area == 0:
            return 0
        return self.total_used_area / self.total_area

    @property
    def total_waste_percent(self) -> float:
        return (1 - self.overall_utilization) * 100

    def get_summary(self) -> dict:
        return {
            "total_sheets": self.total_sheets,
            "total_area_m2": round(self.total_area, 4),
            "used_area_m2": round(self.total_used_area, 4),
            "waste_area_m2": round(self.total_waste_area, 4),
            "utilization_percent": round(self.overall_utilization * 100, 2),
            "waste_percent": round(self.total_waste_percent, 2),
            "unplaced_count": len(self.unplaced_details),
        }

    def to_dict(self) -> dict:
        return {
            "summary": self.get_summary(),
            "sheets": [s.to_dict() for s in self.sheets],
            "unplaced": [
                {
                    "name": d.name,
                    "width": d.total_width,
                    "height": d.total_height,
                    "qty": d.quantity,
                }
                for d in self.unplaced_details
            ],
        }


class MetalCutter:
    """Головний клас для розрахунку розкрою металу."""

    def __init__(
        self,
        sheet_width: float = 1250,
        sheet_height: float = 2500,
        thickness: float = 0.7,
        material: str = "оцинкована сталь",
    ):
        self.sheet_width = sheet_width
        self.sheet_height = sheet_height
        self.thickness = thickness
        self.material = material

    def create_details_from_products(self, products: list[dict]) -> list[Detail]:
        """Створити деталі для розкрою зі списку виробів."""
        details = []
        for p in products:
            # Розгорнуті розміри залежать від типу виробу
            detail = self._product_to_detail(p)
            if detail:
                details.append(detail)
        return details

    def _product_to_detail(self, product: dict) -> Detail:
        """Перетворити виріб (dict) у деталь для розкрою з нормалізацією типу."""
        name = product.get("name", "Деталь")
        raw_type = product.get("product_type", product.get("type", "")).lower().strip()
        quantity = int(product.get("quantity", 1))
        notes = product.get("notes", "")

        # ── НОРМАЛІЗАЦІЯ ТИПУ ──
        pt = raw_type
        if "прямокутн" in pt and "повітропровід" in pt:
            product_type = "rect_duct"
        elif "кругл" in pt and "повітропровід" in pt:
            product_type = "round_duct"
        elif "фланець" in pt and "прямокутн" in pt:
            product_type = "rect_flange"
        elif "фланець" in pt and "кругл" in pt:
            product_type = "round_flange"
        elif "трійник" in pt and "прямокутн" in pt:
            product_type = "rect_tee"
        elif "трійник" in pt and "кругл" in pt:
            product_type = "round_tee"
        elif "перехід" in pt and "прямокутн" in pt:
            product_type = "rect_transition"
        elif "перехід" in pt and "кругл" in pt:
            product_type = "round_transition"
        elif ("відвід" in pt or "коліно" in pt) and "прямокутн" in pt:
            product_type = "rect_elbow"
        elif ("відвід" in pt or "коліно" in pt) and "кругл" in pt:
            product_type = "round_elbow"
        elif ("заглушка" in pt or "кап" in pt) and "прямокутн" in pt:
            product_type = "rect_cap"
        elif ("заглушка" in pt or "кап" in pt) and "кругл" in pt:
            product_type = "round_cap"
        elif "гнучк" in pt or "вставка" in pt:
            product_type = "flexible"
        elif "rect_duct" in pt:
            product_type = "rect_duct"
        elif "round_duct" in pt:
            product_type = "round_duct"
        elif "rect_flange" in pt:
            product_type = "rect_flange"
        elif "round_flange" in pt:
            product_type = "round_flange"
        elif "rect_tee" in pt:
            product_type = "rect_tee"
        elif "round_tee" in pt:
            product_type = "round_tee"
        elif "rect_transition" in pt:
            product_type = "rect_transition"
        elif "round_transition" in pt:
            product_type = "round_transition"
        elif "rect_elbow" in pt:
            product_type = "rect_elbow"
        elif "round_elbow" in pt:
            product_type = "round_elbow"
        elif "rect_cap" in pt:
            product_type = "rect_cap"
        elif "round_cap" in pt:
            product_type = "round_cap"
        else:
            product_type = pt

        # ── ПРЯМОКУТНИЙ ПОВІТРОПРОВІД ──
        if product_type == "rect_duct":
            width = float(product.get("width", 0))
            height = float(product.get("height", 0))
            length = float(product.get("length", 0))
            perimeter = 2 * (width + height)
            return Detail(
                name=name,
                width=perimeter,
                height=length,
                product_type="прямокутний повітропровід",
                quantity=quantity,
                notes=notes,
            )

        # ── КРУГЛИЙ ПОВІТРОПРОВІД ──
        elif product_type == "round_duct":
            diameter = float(product.get("width", product.get("height", 0)))
            length = float(product.get("length", 0))
            return Detail(
                name=name,
                width=3.141592653589793 * diameter,
                height=length,
                product_type="круглий повітропровід",
                quantity=quantity,
                notes=notes,
            )

        # ── ФЛАНЕЦЬ ПРЯМОКУТНИЙ ──
        elif product_type == "rect_flange":
            width = float(product.get("width", 0))
            height = float(product.get("height", 0))
            profile = float(product.get("profile", 30))
            return Detail(
                name=name,
                width=width + 2 * profile,
                height=height + 2 * profile,
                product_type="фланець прямокутний",
                quantity=quantity,
                notes=notes,
            )

        # ── ФЛАНЕЦЬ КРУГЛИЙ ──
        elif product_type == "round_flange":
            diameter = float(product.get("width", product.get("height", 0)))
            profile = float(product.get("profile", 30))
            return Detail(
                name=name,
                width=diameter + 2 * profile,
                height=diameter + 2 * profile,
                product_type="фланець круглий",
                quantity=quantity,
                notes=notes,
            )

        # ── ТРІЙНИК ПРЯМОКУТНИЙ ──
        elif product_type == "rect_tee":
            width = float(product.get("width", 0))
            height = float(product.get("height", 0))
            length = float(product.get("length", 0))
            branch_w = float(product.get("branch_width", width * 0.5))
            branch_h = float(product.get("branch_height", height * 0.5))
            branch_l = float(product.get("branch_length", 400))
            offset = float(product.get("branch_offset", 300))
            main_p = 2 * (width + height)
            branch_p = 2 * (branch_w + branch_h)
            return Detail(
                name=name,
                width=max(main_p, branch_p),
                height=length + branch_l + offset,
                product_type="трійник прямокутний",
                quantity=quantity,
                notes=notes,
            )

        # ── ТРІЙНИК КРУГЛИЙ ──
        elif product_type == "round_tee":
            d = float(product.get("width", product.get("height", 0)))
            length = float(product.get("length", 0))
            branch_d = float(product.get("branch_diameter", d * 0.5))
            branch_l = float(product.get("branch_length", 400))
            offset = float(product.get("branch_offset", 300))
            main_p = 3.141592653589793 * d
            branch_p = 3.141592653589793 * branch_d
            return Detail(
                name=name,
                width=max(main_p, branch_p),
                height=length + branch_l + offset,
                product_type="трійник круглий",
                quantity=quantity,
                notes=notes,
            )

        # ── ПЕРЕХІД ПРЯМОКУТНИЙ ──
        elif product_type == "rect_transition":
            width = float(product.get("width", 0))
            height = float(product.get("height", 0))
            length = float(product.get("length", 0))
            end_w = float(product.get("end_width", width * 0.5))
            end_h = float(product.get("end_height", height * 0.5))
            avg_p = 2 * ((width + end_w) / 2 + (height + end_h) / 2)
            return Detail(
                name=name,
                width=avg_p,
                height=length,
                product_type="перехід прямокутний",
                quantity=quantity,
                notes=notes,
            )

        # ── ПЕРЕХІД КРУГЛИЙ ──
        elif product_type == "round_transition":
            d = float(product.get("width", product.get("height", 0)))
            length = float(product.get("length", 0))
            end_d = float(product.get("end_diameter", d * 0.5))
            avg_p = 3.141592653589793 * (d + end_d) / 2
            return Detail(
                name=name,
                width=avg_p,
                height=length,
                product_type="перехід круглий",
                quantity=quantity,
                notes=notes,
            )

        # ── КОЛІНО ПРЯМОКУТНЕ ──
        elif product_type == "rect_elbow":
            width = float(product.get("width", 0))
            height = float(product.get("height", 0))
            angle = float(product.get("angle", 90))
            radius = float(product.get("radius", 150))
            arc = radius * math.radians(angle)
            p = 2 * (width + height)
            return Detail(
                name=name,
                width=p,
                height=arc,
                product_type="коліно прямокутне",
                quantity=quantity,
                notes=notes,
            )

        # ── КОЛІНО КРУГЛЕ ──
        elif product_type == "round_elbow":
            d = float(product.get("width", product.get("height", 0)))
            angle = float(product.get("angle", 90))
            radius = float(product.get("radius", 150))
            arc = radius * math.radians(angle)
            p = 3.141592653589793 * d
            return Detail(
                name=name,
                width=p,
                height=arc,
                product_type="коліно кругле",
                quantity=quantity,
                notes=notes,
            )

        # ── ЗАГЛУШКА ПРЯМОКУТНА ──
        elif product_type == "rect_cap":
            width = float(product.get("width", 0))
            height = float(product.get("height", 0))
            profile = float(product.get("profile", 30))
            return Detail(
                name=name,
                width=width + 2 * profile,
                height=height + 2 * profile,
                product_type="заглушка прямокутна",
                quantity=quantity,
                notes=notes,
            )

        # ── ЗАГЛУШКА КРУГЛА ──
        elif product_type == "round_cap":
            d = float(product.get("width", product.get("height", 0)))
            depth = float(product.get("depth", 30))
            return Detail(
                name=name,
                width=3.141592653589793 * d,
                height=depth,
                product_type="заглушка кругла",
                quantity=quantity,
                notes=notes,
            )

        # ── ГНУЧКА ВСТАВКА ──
        elif product_type == "flexible":
            width = float(product.get("width", 0))
            height = float(product.get("height", 0))
            length = float(product.get("length", 0))
            p = 2 * (width + height)
            return Detail(
                name=name,
                width=p,
                height=length,
                product_type="гнучка вставка",
                quantity=quantity,
                notes=notes,
            )

        else:
            # Невідомий тип — повертаємо як є
            width = float(product.get("width", 0))
            height = float(product.get("height", 0))
            return Detail(
                name=name,
                width=width,
                height=height,
                product_type=product_type,
                quantity=quantity,
                notes=notes,
            )

    def calculate_cutting(
        self, details: list[Detail], allow_rotation: bool = True, sort_by_area: bool = True
    ) -> CuttingPlan:
        """Розрахувати оптимальний розкрій."""
        plan = CuttingPlan()

        # Сортуємо деталі за площею (спочатку найбільші)
        if sort_by_area:
            details = sorted(details, key=lambda d: d.total_area, reverse=True)

        # Розгортаємо кількість у окремі деталі
        flat_details = []
        for d in details:
            for _ in range(d.quantity):
                flat_details.append(
                    Detail(
                        name=d.name,
                        width=d.width,
                        height=d.height,
                        quantity=1,
                        product_type=d.product_type,
                        bend_allowance=d.bend_allowance,
                        cut_allowance=d.cut_allowance,
                    )
                )

        unplaced = []

        for detail in flat_details:
            placed = False

            # Спробуємо розмістити на існуючих листах
            for sheet in plan.sheets:
                pos = sheet.find_best_position(detail)
                if pos:
                    x, y, rotated = pos
                    if sheet.place_detail(detail, x, y, rotated):
                        placed = True
                        break

            if not placed:
                # Створюємо новий лист
                new_sheet = Sheet(
                    width=self.sheet_width,
                    height=self.sheet_height,
                    thickness=self.thickness,
                    material=self.material,
                )
                pos = new_sheet.find_best_position(detail)
                if pos:
                    x, y, rotated = pos
                    if new_sheet.place_detail(detail, x, y, rotated):
                        plan.sheets.append(new_sheet)
                        placed = True

            if not placed:
                unplaced.append(detail)

        plan.unplaced_details = unplaced
        return plan

    def calculate_from_products(self, products: list[dict]) -> CuttingPlan:
        """Повний конвеєр: вироби → деталі → план розкрою."""
        details = self.create_details_from_products(products)
        return self.calculate_cutting(details)

    def get_metal_summary(self, products: list[dict]) -> dict:
        """Отримати зведену інформацію про потребу в металі."""
        details = self.create_details_from_products(products)
        plan = self.calculate_cutting(details)

        total_detail_area = sum(d.total_area for d in details)

        return {
            "details_count": sum(d.quantity for d in details),
            "details_area_m2": round(total_detail_area, 4),
            "sheets_required": plan.total_sheets,
            # FIX: self.height → self.sheet_height
            "sheet_size": f"{self.sheet_width}×{self.sheet_height} мм",
            "total_metal_area_m2": round(plan.total_area, 4),
            "waste_percent": round(plan.total_waste_percent, 2),
            "utilization_percent": round(plan.overall_utilization * 100, 2),
            "plan": plan.to_dict(),
        }


# =========================================================
# ШВИДКІ ФУНКЦІЇ
# =========================================================

def calculate_sheet_cutting(
    products: list[dict], sheet_size: tuple[float, float] = (1250, 2500), thickness: float = 0.7
) -> CuttingPlan:
    """Швидкий розрахунок розкрою зі списку виробів."""
    cutter = MetalCutter(sheet_width=sheet_size[0], sheet_height=sheet_size[1], thickness=thickness)
    return cutter.calculate_from_products(products)


def estimate_metal_needed(
    products: list[dict], sheet_size: tuple[float, float] = (1250, 2500), thickness: float = 0.7
) -> dict:
    """Оцінка необхідної кількості металу."""
    cutter = MetalCutter(sheet_width=sheet_size[0], sheet_height=sheet_size[1], thickness=thickness)
    return cutter.get_metal_summary(products)
