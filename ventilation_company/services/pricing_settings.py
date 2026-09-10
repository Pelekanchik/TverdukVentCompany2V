"""Pricing settings service extracted from legacy Tkinter GUI."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field

from ventilation_company.calculations.safe_evaluator import SafeFormulaEvaluator
from ventilation_company.services.markup_matrix import (
    PRODUCT_TYPE_LABELS,
    build_default_markup_matrix,
    classify_product,
    is_standard_size,
)

SETTINGS_FILE = "data/pricing_settings.json"

DEFAULT_MATERIAL_PRICES = {
    "оцинкована сталь": {
        "0.5": 450.0,
        "0.7": 580.0,
        "0.9": 650.0,
        "1.0": 750.0,
        "1.2": 850.0,
        "1.5": 950.0,
        "2.0": 1200.0,
    },
    "нержавіюча сталь": {
        "0.5": 950.0,
        "0.7": 1100.0,
        "0.9": 1200.0,
        "1.0": 1200.0,
        "1.2": 1400.0,
        "1.5": 1600.0,
        "2.0": 2000.0,
    },
    "алюміній": {
        "0.5": 320.0,
        "0.7": 380.0,
        "0.9": 420.0,
        "1.0": 450.0,
        "1.2": 500.0,
        "1.5": 600.0,
        "2.0": 750.0,
    },
}

DEFAULT_OVERHEAD = {
    "electricity_per_kg": 2.5,
    "rent_per_month": 15000.0,
    "transport_per_project": 500.0,
    "waste_percent": 8.0,
}

DEFAULT_DEPRECIATION = {
    "guillotine_percent": 5.0,
    "bending_percent": 4.0,
    "welding_percent": 3.0,
    "plasma_percent": 6.0,
}

DEFAULT_CATEGORY_WASTE_FACTORS = {
    "rect_duct": 0.0,  # прямокутні труби
    "rect_fitting": 0.0,  # прямокутні фасонні
    "round_duct": 0.0,  # круглі труби
    "round_fitting": 0.0,  # круглі фасонні
}

DEFAULT_MARKUP_PERCENT = 30.0
DEFAULT_MARKUP_MATRIX = build_default_markup_matrix()

DEFAULT_LABOR_RATES = {
    "повітропровід прямокутний": {"rate_per_m2": 120.0, "difficulty_percent": 0.0},
    "повітропровід круглий": {"rate_per_m2": 130.0, "difficulty_percent": 5.0},
    "фланець прямокутний": {"rate_per_m2": 200.0, "difficulty_percent": 15.0},
    "фланець круглий": {"rate_per_m2": 180.0, "difficulty_percent": 10.0},
    "трійник прямокутний": {"rate_per_m2": 250.0, "difficulty_percent": 25.0},
    "трійник круглий": {"rate_per_m2": 280.0, "difficulty_percent": 30.0},
    "перехід прямокутний": {"rate_per_m2": 180.0, "difficulty_percent": 15.0},
    "перехід круглий": {"rate_per_m2": 200.0, "difficulty_percent": 20.0},
    "відвід прямокутний": {"rate_per_m2": 220.0, "difficulty_percent": 20.0},
    "відвід круглий": {"rate_per_m2": 240.0, "difficulty_percent": 25.0},
    "заглушка прямокутна": {"rate_per_m2": 150.0, "difficulty_percent": 5.0},
    "заглушка кругла": {"rate_per_m2": 160.0, "difficulty_percent": 5.0},
    "гнучка вставка": {"rate_per_m2": 80.0, "difficulty_percent": 0.0},
}

DEFAULT_CUSTOM_PARAMS = {
    "flange_price": 150.0,
    "coating_price": 0.0,
    "transport_km": 0.0,
}

DEFAULT_PRODUCTS = [
    {
        "name": "Повітропровід прямокутний",
        "formula": "metal_area * material_price * 1.15",
        "labor_hours": 0.15,
        "description": "Прямокутний канал — розгортка + згин",
    },
    {
        "name": "Повітропровід круглий",
        "formula": "metal_area * material_price * 1.20",
        "labor_hours": 0.20,
        "description": "Спірально-навивна труба",
    },
    {
        "name": "Фланець прямокутний",
        "formula": "metal_area * material_price * 1.30 + bolt_count * 2.5",
        "labor_hours": 0.25,
        "description": "Розкрій + свердління отворів",
    },
    {
        "name": "Фланець круглий",
        "formula": "metal_area * material_price * 1.30 + bolt_count * 2.5",
        "labor_hours": 0.25,
        "description": "Токарка + свердління",
    },
    {
        "name": "Трійник прямокутний",
        "formula": "metal_area * material_price * 1.50",
        "labor_hours": 0.80,
        "description": "Розкрій + врізка + згин",
    },
    {
        "name": "Трійник круглий",
        "formula": "metal_area * material_price * 1.55",
        "labor_hours": 0.90,
        "description": "Врізка в трубу + зварка",
    },
    {
        "name": "Перехід прямокутний",
        "formula": "metal_area * material_price * 1.40",
        "labor_hours": 0.60,
        "description": "Трапецієподібна розгортка",
    },
    {
        "name": "Перехід круглий",
        "formula": "metal_area * material_price * 1.45",
        "labor_hours": 0.70,
        "description": "Конусна розгортка",
    },
    {
        "name": "Відвід прямокутний",
        "formula": "(2*(A+B)/1000) * ((D+E)/1000 + (F+B/2)*C*math.pi/180/1000) * material_price * 1.60",
        "labor_hours": 1.00,
        "description": "Сегментне коліно",
    },
    {
        "name": "Відвід круглий",
        "formula": "(math.pi*A/1000) * ((D+E)/1000 + (F+A/2)*C*math.pi/180/1000) * material_price * 1.65",
        "labor_hours": 1.10,
        "description": "Гнуте коліно",
    },
    {
        "name": "Заглушка прямокутна",
        "formula": "metal_area * material_price * 1.25",
        "labor_hours": 0.20,
        "description": "Дно + фальци",
    },
    {
        "name": "Заглушка кругла",
        "formula": "metal_area * material_price * 1.25",
        "labor_hours": 0.20,
        "description": "Витиск + фальци",
    },
    {
        "name": "Гнучка вставка",
        "formula": "metal_area * 35.0 + 25.0",
        "labor_hours": 0.10,
        "description": "Тканина + обжим",
    },
]


@dataclass
class PriceStep:
    """Один крок розрахунку ціни."""

    name: str
    calc: str
    value: float


@dataclass
class PriceBreakdown:
    """Повний результат розрахунку ціни виробу.

    Містить і фінальну ціну (total), і покрокове розбиття (steps) —
    замінює колишнє дублювання calculate_product_price /
    calculate_product_price_detailed.
    """

    formula: str
    steps: list = field(default_factory=list)
    total: float = 0.0

    def to_dict(self) -> dict:
        """Серіалізація у формат колишнього calculate_product_price_detailed."""
        return {
            "formula": self.formula,
            "steps": [{"name": s.name, "calc": s.calc, "value": s.value} for s in self.steps],
            "total": self.total,
        }


class PricingSettings:
    """Менеджер налаштувань ціноутворення (Singleton з файловим блокуванням).

    Гарантує, що всі вкладки GUI працюють з одним і тим самим
    екземпляром даних, і запис у файл є атомарним.
    """

    _instance: "PricingSettings | None" = None
    _lock = threading.Lock()

    def __new__(cls, filepath: str = SETTINGS_FILE) -> "PricingSettings":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls, filepath: str = SETTINGS_FILE) -> "PricingSettings":
        """Отримати єдиний екземпляр налаштувань."""
        return cls(filepath)

    def __init__(self, filepath: str = SETTINGS_FILE):
        # Ініціалізуємо лише один раз (singleton)
        if self._initialized:
            return
        self._initialized = True

        self.filepath = filepath
        self._file_lock = threading.Lock()
        self._last_modified: float = 0.0

        # Дані
        self.material_prices: dict = {}
        self.overhead: dict = {}
        self.depreciation: dict = {}
        self.markup_percent: float = DEFAULT_MARKUP_PERCENT
        self.markup_matrix: dict = {}
        self.products: list = []
        self.custom_params: dict = {}
        self.labor_rates: dict = {}
        self.category_waste_factors: dict = {}

        self.load()

    # ── Файлові операції з блокуванням ──

    def _atomic_write(self, data: dict) -> None:
        """Атомарний запис: спочатку у тимчасовий файл, потім rename."""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        temp_path = self.filepath + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, self.filepath)
        self._last_modified = os.path.getmtime(self.filepath)

    def _read_file(self) -> dict:
        """Безпечне читання файлу з блокуванням."""
        with self._file_lock:
            if not os.path.exists(self.filepath):
                return {}
            with open(self.filepath, encoding="utf-8") as f:
                return json.load(f)

    def reload(self) -> None:
        """Перечитати файл, якщо він змінився ззовні."""
        if os.path.exists(self.filepath):
            mtime = os.path.getmtime(self.filepath)
            if mtime > self._last_modified:
                self.load()

    def load(self) -> None:
        """Завантажити налаштування з файлу або встановити за замовчуванням."""
        data = self._read_file()
        if data:
            self.material_prices = data.get("material_prices", DEFAULT_MATERIAL_PRICES)
            self.overhead = data.get("overhead", DEFAULT_OVERHEAD)
            self.depreciation = data.get("depreciation", DEFAULT_DEPRECIATION)
            self.markup_percent = data.get("markup_percent", DEFAULT_MARKUP_PERCENT)
            self.markup_matrix = data.get("markup_matrix", build_default_markup_matrix())
            self.products = data.get("products", DEFAULT_PRODUCTS)
            self.custom_params = data.get("custom_params", DEFAULT_CUSTOM_PARAMS.copy())
            self.labor_rates = data.get("labor_rates", DEFAULT_LABOR_RATES.copy())
            self.category_waste_factors = data.get(
                "category_waste_factors", DEFAULT_CATEGORY_WASTE_FACTORS.copy()
            )
            self.sync_labor_rates()
            self.save()
        else:
            self.material_prices = DEFAULT_MATERIAL_PRICES.copy()
            self.overhead = DEFAULT_OVERHEAD.copy()
            self.depreciation = DEFAULT_DEPRECIATION.copy()
            self.markup_percent = DEFAULT_MARKUP_PERCENT
            self.markup_matrix = build_default_markup_matrix()
            self.products = [p.copy() for p in DEFAULT_PRODUCTS]
            self.custom_params = DEFAULT_CUSTOM_PARAMS.copy()
            self.labor_rates = DEFAULT_LABOR_RATES.copy()
            self.category_waste_factors = DEFAULT_CATEGORY_WASTE_FACTORS.copy()
            self.save()

    def save(self) -> None:
        """Зберегти налаштування атомарно."""
        data = {
            "material_prices": self.material_prices,
            "overhead": self.overhead,
            "depreciation": self.depreciation,
            "markup_percent": self.markup_percent,
            "markup_matrix": self.markup_matrix,
            "products": self.products,
            "custom_params": self.custom_params,
            "labor_rates": self.labor_rates,
            "category_waste_factors": self.category_waste_factors,
        }
        with self._file_lock:
            self._atomic_write(data)

    def get_material_price(self, material, thickness):
        self.reload()
        mat = self.material_prices.get(material, {})
        return mat.get(str(thickness), 55.0)

    def get_labor_rate(self, product_type: str) -> dict:
        """Отримати ставку зарплати та %% важкості для типу виробу.

        ВИПРАВЛЕНО v2: працює з назвами ("Перехід 400×200→300×150"),
        типами ("rect_transition") та англійськими ключами.
        """
        self.reload()
        ptype = product_type.lower().strip()

        # === 1. Мапінг англійських product_type → українські ===
        type_map = {
            "rect_duct": "повітропровід прямокутний",
            "round_duct": "повітропровід круглий",
            "rect_flange": "фланець прямокутний",
            "round_flange": "фланець круглий",
            "rect_tee": "трійник прямокутний",
            "round_tee": "трійник круглий",
            "rect_transition": "перехід прямокутний",
            "round_transition": "перехід круглий",
            "rect_elbow": "відвід прямокутний",
            "round_elbow": "відвід круглий",
            "rect_cap": "заглушка прямокутна",
            "round_cap": "заглушка кругла",
            "flexible": "гнучка вставка",
        }
        if ptype in type_map:
            ptype = type_map[ptype]
            if ptype in self.labor_rates:
                return self.labor_rates[ptype]

        # === 2. Прямий пошук ===
        if ptype in self.labor_rates:
            return self.labor_rates[ptype]

        # === 3. Fuzzy пошук (підрядок) ===
        for key, value in self.labor_rates.items():
            if key in ptype or ptype in key:
                return value

        # === 4. Розумний аналіз назви з розмірами ===
        # Приклад: "перехід 400×200→300×150" → перше слово "перехід"
        words = ptype.split()
        if not words:
            return {"rate_per_m2": 120.0, "difficulty_percent": 0.0}

        first_word = words[0]  # "перехід", "відвід", "трійник"...

        # Визначаємо форму за наявністю символів
        has_rect = "прямокут" in ptype or "×" in ptype or "x" in ptype
        has_round = "кругл" in ptype or "ø" in ptype or "Ø" in ptype

        # Формуємо кандидатів
        candidates = []
        if has_rect and not has_round:
            candidates.append(f"{first_word} прямокутний")
        elif has_round and not has_rect:
            candidates.append(f"{first_word} круглий")
        else:
            candidates.extend([f"{first_word} прямокутний", f"{first_word} круглий"])

        for cand in candidates:
            if cand in self.labor_rates:
                return self.labor_rates[cand]
            for key, value in self.labor_rates.items():
                if cand in key or key in cand:
                    return value

        # === 5. Остання спроба — за першим словом ===
        for key, value in self.labor_rates.items():
            if first_word in key:
                return value

        return {"rate_per_m2": 120.0, "difficulty_percent": 0.0}

    def get_category_waste_factor(self, product_type: str) -> float:
        """Отримати %% запасу на брак/поворот для категорії виробу."""
        self.reload()
        ptype = product_type.lower().strip()
        # Визначаємо категорію
        category = self._classify_category(ptype)
        return self.category_waste_factors.get(category, 0.0)

    def _classify_category(self, product_type: str) -> str:
        """Класифікувати виріб у одну з 4 категорій."""
        pt = product_type.lower().strip()
        if "повітропровід прямокутний" in pt:
            return "rect_duct"
        elif "повітропровід круглий" in pt:
            return "round_duct"
        elif any(
            k in pt
            for k in [
                "фланець прямокутний",
                "трійник прямокутний",
                "перехід прямокутний",
                "відвід прямокутний",
                "заглушка прямокутна",
            ]
        ):
            return "rect_fitting"
        elif any(
            k in pt
            for k in [
                "фланець круглий",
                "трійник круглий",
                "перехід круглий",
                "відвід круглий",
                "заглушка кругла",
            ]
        ):
            return "round_fitting"
        else:
            return "rect_duct"  # fallback

    def get_markup_percent(self, product_data: dict) -> float:
        self.reload()
        name = product_data.get("name", "")
        ptype = product_data.get("type", product_data.get("product_type", ""))
        material = product_data.get("material", "оцинкована сталь")
        thickness = str(product_data.get("thickness", 0.7))
        width = product_data.get("width", 0)
        height = product_data.get("height", 0)
        length = product_data.get("length", 0)
        diameter = product_data.get("diameter", 0)
        mat_key, cat_key = classify_product(name, ptype, material)
        is_std = is_standard_size(width, height, length, diameter)
        size_key = "standard" if is_std else "nonstandard"
        mat_data = self.markup_matrix.get(mat_key, {})
        cat_data = mat_data.get(cat_key, {})
        th_data = cat_data.get(thickness, {})
        return th_data.get(size_key, 30.0)

    def sync_labor_rates(self):
        normalized = {}
        for key, value in self.labor_rates.items():
            lower_key = key.lower().strip()
            if lower_key not in normalized:
                normalized[lower_key] = value
        self.labor_rates = normalized
        for p in self.products:
            name = p.get("name", "").strip()
            lower_name = name.lower()
            if name and lower_name not in self.labor_rates:
                rate = 120.0
                diff = 0.0
                if "трійник" in lower_name:
                    rate, diff = 250.0, 25.0
                elif "перехід" in lower_name:
                    rate, diff = 180.0, 15.0
                elif "відвід" in lower_name or "коліно" in lower_name:
                    rate, diff = 220.0, 20.0
                elif "фланець" in lower_name:
                    rate, diff = 200.0, 15.0
                elif "заглушка" in lower_name:
                    rate, diff = 150.0, 5.0
                elif "гнучка" in lower_name:
                    rate, diff = 80.0, 0.0
                elif "кругл" in lower_name and "повітропровід" in lower_name:
                    rate, diff = 130.0, 5.0
                elif "прямокутн" in lower_name and "повітропровід" in lower_name:
                    rate, diff = 120.0, 0.0
                self.labor_rates[lower_name] = {"rate_per_m2": rate, "difficulty_percent": diff}

    def calculate_price_breakdown(self, product_data) -> PriceBreakdown:
        """Єдина точка розрахунку ціни виробу.

        Повертає PriceBreakdown: total — кінцева ціна, steps — проміжні
        кроки розрахунку. Короткий і детальний варіанти нижче є просто
        різними уявленнями цього результату.
        """
        self.reload()
        material = product_data.get("material", "оцинкована сталь")
        thickness = product_data.get("thickness", 0.7)
        metal_area = product_data.get("metal_area_m2", product_data.get("metal_area", 0))
        weight = product_data.get("weight_kg", product_data.get("weight", 0))
        quantity = product_data.get("quantity", 1)
        bolt_count = product_data.get("bolt_count", 0)
        ptype = product_data.get("type", product_data.get("product_type", ""))
        material_price = self.get_material_price(material, thickness)
        formula = "metal_area * material_price * 1.15"
        labor_hours = 0.15
        for p in self.products:
            if p["name"].lower() in ptype.lower() or ptype.lower() in p["name"].lower():
                formula = p.get("formula", formula)
                labor_hours = p.get("labor_hours", 0.15)
                break
        try:
            namespace = {
                "metal_area": metal_area,
                "metal_area_m2": metal_area,
                "thickness": thickness,
                "material_price": material_price,
                "weight": weight,
                "weight_kg": weight,
                "quantity": quantity,
                "bolt_count": bolt_count,
                "length": product_data.get("length", 0),
                "profile": product_data.get("profile", 30.0),
                "A": product_data.get("width", 0),
                "B": product_data.get("height", 0),
                "C": product_data.get("angle", 90),
                "D": product_data.get("top_extension", 100),
                "E": product_data.get("bottom_extension", 100),
                "F": product_data.get("radius", 50),
                "pi": 3.141592653589793,
            }
            namespace.update(self.custom_params)
            for key, value in product_data.items():
                if (
                    key not in namespace
                    and isinstance(value, (int, float))
                    and not key.startswith("_")
                ):
                    namespace[key] = value
            evaluator = SafeFormulaEvaluator()
            base_price = evaluator.eval(formula, namespace)
        except (ValueError, ZeroDivisionError, TypeError) as exc:
            print(f'[PricingSettings] Помилка формули "{formula}": {exc}. Використано fallback.')
            base_price = (
                metal_area * material_price * 1.15
                if metal_area > 0
                else weight * material_price * 1.15
            )
        waste_pct = self.overhead.get("waste_percent", 8)
        waste_mult = 1 + waste_pct / 100
        after_waste = base_price * waste_mult
        labor_info = self.get_labor_rate(ptype)
        rate_per_m2 = labor_info.get("rate_per_m2", 120.0)
        difficulty = labor_info.get("difficulty_percent", 0.0)
        labor_cost = metal_area * rate_per_m2 * (1 + difficulty / 100)
        after_labor = after_waste + labor_cost
        depr = sum(self.depreciation.values()) / len(self.depreciation) if self.depreciation else 4
        after_depr = after_labor * (1 + depr / 100)
        elec_rate = self.overhead.get("electricity_per_kg", 2.5)
        elec_cost = weight * elec_rate
        after_elec = after_depr + elec_cost
        markup_pct = self.get_markup_percent(product_data)
        final_price = after_elec * (1 + markup_pct / 100)
        mat_key, cat_key = classify_product(product_data.get("name", ""), ptype, material)
        is_std = is_standard_size(
            product_data.get("width", 0),
            product_data.get("height", 0),
            product_data.get("length", 0),
            product_data.get("diameter", 0),
        )
        size_label = "стандарт" if is_std else "нестандарт"
        return PriceBreakdown(
            formula=formula,
            steps=[
                PriceStep(
                    "1. Базова ціна (метал)",
                    f"{metal_area:.4f} м² × {material_price:.2f} грн/м² × коеф.",
                    round(base_price, 2),
                ),
                PriceStep(
                    "2. Відходи металу",
                    f"× (1 + {waste_pct:.1f}%) = × {waste_mult:.3f}",
                    round(after_waste, 2),
                ),
                PriceStep(
                    "3. Зарплата робітників",
                    f"{metal_area:.4f} м² × {rate_per_m2:.2f} грн/м² × (1 + {difficulty:.1f}%)",
                    round(labor_cost, 2),
                ),
                PriceStep(
                    "4. Після зарплати",
                    f"{after_waste:.2f} + {labor_cost:.2f}",
                    round(after_labor, 2),
                ),
                PriceStep(
                    "5. Амортизація обладнання", f"× (1 + {depr:.2f}%)", round(after_depr, 2)
                ),
                PriceStep(
                    "6. Електроенергія",
                    f"{weight:.3f} кг × {elec_rate:.2f} грн/кг",
                    round(elec_cost, 2),
                ),
                PriceStep(
                    "7. Процентна націнка",
                    f"× (1 + {markup_pct:.1f}%) — {mat_key} / {PRODUCT_TYPE_LABELS.get(cat_key, cat_key)} / {thickness} мм / {size_label}",
                    round(final_price, 2),
                ),
            ],
            total=round(final_price, 2),
        )

    def calculate_product_price(self, product_data):
        """Ціна виробу (коротка форма) — обгортка над calculate_price_breakdown."""
        return self.calculate_price_breakdown(product_data).total

    def calculate_product_price_detailed(self, product_data):
        """Ціна з покроковим розбиттям — обгортка над calculate_price_breakdown."""
        return self.calculate_price_breakdown(product_data).to_dict()
