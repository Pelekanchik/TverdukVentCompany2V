from decimal import Decimal
"""Вкладка "💰 Ціноутворення" для GUI.

Налаштування:
 • Ціни на метал (за типом і товщиною)
 • Амортизація обладнання (%)
 • Інші витрати (електроенергія, оренда, транспорт)
 • Зарплата робітників (грн/м² + коефіцієнт важкості)
 • Каталог продукції з формулами розрахунку
 • Кастомні параметри для формул
 • Додавання / редагування / видалення продукції
"""

import contextlib
import json
import os
import threading
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import messagebox, ttk

from ventilation_company.gui.markup_matrix_tab import (
    MarkupMatrixTab,
    PRODUCT_TYPE_LABELS,
    build_default_markup_matrix,
    classify_product,
    is_standard_size,
)
from ventilation_company.gui.theme_manager import get_theme_manager

# ═══════════════════════════════════════════════════════════════════
# 🔒 БЕЗПЕКА: заміна небезпечного eval() на SafeFormulaEvaluator
# ═══════════════════════════════════════════════════════════════════
from ventilation_company.calculations.safe_evaluator import SafeFormulaEvaluator

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
    {"name": "Повітропровід прямокутний", "formula": "metal_area * material_price * 1.15", "labor_hours": 0.15, "description": "Прямокутний канал — розгортка + згин"},
    {"name": "Повітропровід круглий", "formula": "metal_area * material_price * 1.20", "labor_hours": 0.20, "description": "Спірально-навивна труба"},
    {"name": "Фланець прямокутний", "formula": "metal_area * material_price * 1.30 + bolt_count * 2.5", "labor_hours": 0.25, "description": "Розкрій + свердління отворів"},
    {"name": "Фланець круглий", "formula": "metal_area * material_price * 1.30 + bolt_count * 2.5", "labor_hours": 0.25, "description": "Токарка + свердління"},
    {"name": "Трійник прямокутний", "formula": "metal_area * material_price * 1.50", "labor_hours": 0.80, "description": "Розкрій + врізка + згин"},
    {"name": "Трійник круглий", "formula": "metal_area * material_price * 1.55", "labor_hours": 0.90, "description": "Врізка в трубу + зварка"},
    {"name": "Перехід прямокутний", "formula": "metal_area * material_price * 1.40", "labor_hours": 0.60, "description": "Трапецієподібна розгортка"},
    {"name": "Перехід круглий", "formula": "metal_area * material_price * 1.45", "labor_hours": 0.70, "description": "Конусна розгортка"},
    {"name": "Відвід прямокутний", "formula": "(2*(A+B)/1000) * ((D+E)/1000 + (F+B/2)*C*math.pi/180/1000) * material_price * 1.60", "labor_hours": 1.00, "description": "Сегментне коліно"},
    {"name": "Відвід круглий", "formula": "(math.pi*A/1000) * ((D+E)/1000 + (F+A/2)*C*math.pi/180/1000) * material_price * 1.65", "labor_hours": 1.10, "description": "Гнуте коліно"},
    {"name": "Заглушка прямокутна", "formula": "metal_area * material_price * 1.25", "labor_hours": 0.20, "description": "Дно + фальци"},
    {"name": "Заглушка кругла", "formula": "metal_area * material_price * 1.25", "labor_hours": 0.20, "description": "Витиск + фальци"},
    {"name": "Гнучка вставка", "formula": "metal_area * 35.0 + 25.0", "labor_hours": 0.10, "description": "Тканина + обжим"},
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
            "steps": [
                {"name": s.name, "calc": s.calc, "value": s.value} for s in self.steps
            ],
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
        }
        with self._file_lock:
            self._atomic_write(data)

    def get_material_price(self, material, thickness):
        self.reload()
        mat = self.material_prices.get(material, {})
        return mat.get(str(thickness), 55.0)

    def get_labor_rate(self, product_type: str) -> dict:
        self.reload()
        ptype = product_type.lower().strip()
        if ptype in self.labor_rates:
            return self.labor_rates[ptype]
        for key, value in self.labor_rates.items():
            if key in ptype or ptype in key:
                return value
        return {"rate_per_m2": 120.0, "difficulty_percent": 0.0}

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
                "metal_area": metal_area, "metal_area_m2": metal_area,
                "thickness": thickness, "material_price": material_price,
                "weight": weight, "weight_kg": weight,
                "quantity": quantity, "bolt_count": bolt_count,
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
                if key not in namespace and isinstance(value, (int, float)) and not key.startswith("_"):
                    namespace[key] = value
            evaluator = SafeFormulaEvaluator()
            base_price = evaluator.eval(formula, namespace)
        except (ValueError, ZeroDivisionError, TypeError) as exc:
            print(f'[PricingSettings] Помилка формули "{formula}": {exc}. Використано fallback.')
            base_price = metal_area * material_price * 1.15 if metal_area > 0 else weight * material_price * 1.15
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
        is_std = is_standard_size(product_data.get("width", 0), product_data.get("height", 0), product_data.get("length", 0), product_data.get("diameter", 0))
        size_label = "стандарт" if is_std else "нестандарт"
        return PriceBreakdown(
            formula=formula,
            steps=[
                PriceStep("1. Базова ціна (метал)", f"{metal_area:.4f} м² × {material_price:.2f} грн/кг × коеф.", round(base_price, 2)),
                PriceStep("2. Відходи металу", f"× (1 + {waste_pct:.1f}%) = × {waste_mult:.3f}", round(after_waste, 2)),
                PriceStep("3. Зарплата робітників", f"{metal_area:.4f} м² × {rate_per_m2:.2f} грн/м² × (1 + {difficulty:.1f}%)", round(labor_cost, 2)),
                PriceStep("4. Після зарплати", f"{after_waste:.2f} + {labor_cost:.2f}", round(after_labor, 2)),
                PriceStep("5. Амортизація обладнання", f"× (1 + {depr:.2f}%)", round(after_depr, 2)),
                PriceStep("6. Електроенергія", f"{weight:.3f} кг × {elec_rate:.2f} грн/кг", round(elec_cost, 2)),
                PriceStep("7. Процентна націнка", f"× (1 + {markup_pct:.1f}%) — {mat_key} / {PRODUCT_TYPE_LABELS.get(cat_key, cat_key)} / {thickness} мм / {size_label}", round(final_price, 2)),
            ],
            total=round(final_price, 2),
        )

    def calculate_product_price(self, product_data):
        """Ціна виробу (коротка форма) — обгортка над calculate_price_breakdown."""
        return self.calculate_price_breakdown(product_data).total

    def calculate_product_price_detailed(self, product_data):
        """Ціна з покроковим розбиттям — обгортка над calculate_price_breakdown."""
        return self.calculate_price_breakdown(product_data).to_dict()


class SettingsTab:
    """Вкладка налаштувань ціноутворення."""

    def __init__(self, parent: ttk.Notebook):
        self.frame = ttk.Frame(parent)
        self.settings = PricingSettings.get_instance()
        self.theme = get_theme_manager()
        self._build_ui()
        self._refresh_all()

    def _fg(self, key="fg"):
        """Отримати колір з поточної теми."""
        return self.theme.color(key)

    def _build_ui(self):
        # Верхня панель з кнопками
        top = ttk.Frame(self.frame, padding=5)
        top.pack(fill=tk.X)
        ttk.Label(top, text="💰 Налаштування ціноутворення", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(top, text="💾 Зберегти налаштування", command=self._save_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(top, text="🔄 Скинути за замовчуванням", command=self._reset_defaults).pack(side=tk.RIGHT, padx=5)

        # Notebook для під-вкладок
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.metal_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.metal_frame, text="🛠️ Ціни на метал")
        self._build_metal_tab()

        self.costs_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.costs_frame, text="📊 Витрати та амортизація")
        self._build_costs_tab()

        self.labor_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.labor_frame, text="👷 Зарплата")
        self._build_labor_tab()

        self.catalog_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.catalog_frame, text="📦 Каталог продукції")
        self._build_catalog_tab()

        self.params_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.params_frame, text="⚙️ Параметри формул")
        self._build_params_tab()

        self.markup_tab = MarkupMatrixTab(self.notebook, self.settings)
        self.notebook.add(self.markup_tab.frame, text="📐 Націнки по категоріях")

    def _build_metal_tab(self):
        ttk.Label(self.metal_frame, text="Ціни на метал (грн/кг)", font=("Arial", 11, "bold")).pack(pady=5)
        frame = ttk.Frame(self.metal_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        thicknesses = ["0.5", "0.7", "0.9", "1.0", "1.2", "1.5", "2.0"]
        materials = ["оцинкована сталь", "нержавіюча сталь", "алюміній"]
        ttk.Label(frame, text="Матеріал / Товщина", font=("Arial", 9, "bold")).grid(row=0, column=0, padx=5, pady=3)
        for j, th in enumerate(thicknesses):
            ttk.Label(frame, text=f"{th} мм", font=("Arial", 9, "bold")).grid(row=0, column=j + 1, padx=5, pady=3)
        self.metal_entries = {}
        for i, mat in enumerate(materials):
            ttk.Label(frame, text=mat).grid(row=i + 1, column=0, padx=5, pady=3, sticky=tk.W)
            for j, th in enumerate(thicknesses):
                var = tk.StringVar()
                ent = ttk.Entry(frame, textvariable=var, width=10)
                ent.grid(row=i + 1, column=j + 1, padx=3, pady=3)
                self.metal_entries[(mat, th)] = var

    def _build_costs_tab(self):
        left = ttk.LabelFrame(self.costs_frame, text="Постійні витрати", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.cost_vars = {}
        cost_fields = [
            ("electricity_per_kg", "Електроенергія (грн/кг металу):", "2.5"),
            ("rent_per_month", "Оренда (грн/міс):", "15000.0"),
            ("transport_per_project", "Транспорт (грн/проєкт):", "500.0"),
            ("waste_percent", "Відходи металу (%):", "8.0"),
        ]
        for i, (key, label, default) in enumerate(cost_fields):
            ttk.Label(left, text=label).grid(row=i, column=0, sticky=tk.W, pady=3)
            var = tk.StringVar(value=default)
            ttk.Entry(left, textvariable=var, width=12).grid(row=i, column=1, padx=5, pady=3)
            self.cost_vars[key] = var

        right = ttk.LabelFrame(self.costs_frame, text="Амортизація обладнання (%)", padding=10)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.depr_vars = {}
        depr_fields = [
            ("guillotine_percent", "Гільйотина:", "5.0"),
            ("bending_percent", "Листогиб:", "4.0"),
            ("welding_percent", "Зварка:", "3.0"),
            ("plasma_percent", "Плазма:", "6.0"),
        ]
        for i, (key, label, default) in enumerate(depr_fields):
            ttk.Label(right, text=label).grid(row=i, column=0, sticky=tk.W, pady=3)
            var = tk.StringVar(value=default)
            ttk.Entry(right, textvariable=var, width=12).grid(row=i, column=1, padx=5, pady=3)
            self.depr_vars[key] = var

        info_text = """💡 Формула ціни:
(метал × товщина × ціна × коефіцієнт) × (1 + відходи%)
+ зарплата (грн/м² × площа × важкість) + електроенергія × вага
× (1 + середня амортизація%) × (1 + націнка%)"""
        info = ttk.Label(
            self.costs_frame,
            text=info_text,
            foreground=self._fg("fg_muted"),
            justify=tk.LEFT,
            font=("Consolas", 9),
        )
        info.pack(side=tk.BOTTOM, pady=10, padx=10, anchor=tk.W)

    def _build_labor_tab(self):
        top = ttk.Frame(self.labor_frame, padding=5)
        top.pack(fill=tk.X)
        ttk.Label(top, text="👷 Зарплата робітників (грн/м²)", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        ttk.Button(top, text="💾 Зберегти ставки", command=self._save_labor_rates).pack(side=tk.RIGHT, padx=5)

        columns = ("product_type", "rate", "difficulty", "total")
        self.labor_tree = ttk.Treeview(self.labor_frame, columns=columns, show="headings", height=15)
        self.labor_tree.heading("product_type", text="Тип виробу")
        self.labor_tree.heading("rate", text="Ставка, грн/м²")
        self.labor_tree.heading("difficulty", text="Важкість, %")
        self.labor_tree.heading("total", text="Разом, грн/м²")
        self.labor_tree.column("product_type", width=250)
        self.labor_tree.column("rate", width=120, anchor=tk.CENTER)
        self.labor_tree.column("difficulty", width=100, anchor=tk.CENTER)
        self.labor_tree.column("total", width=120, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(self.labor_frame, orient=tk.VERTICAL, command=self.labor_tree.yview)
        self.labor_tree.configure(yscrollcommand=scrollbar.set)
        self.labor_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        self.labor_tree.bind("<Double-1>", lambda e: self._edit_labor_dialog())

        edit_frame = ttk.LabelFrame(self.labor_frame, text="Редагування ставки", padding=10)
        edit_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)

        ttk.Label(edit_frame, text="Тип виробу:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.labor_type_var = tk.StringVar()
        ttk.Entry(edit_frame, textvariable=self.labor_type_var, width=35, state="readonly").grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(edit_frame, text="Ставка (грн/м²):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.labor_rate_var = tk.StringVar(value="120.0")
        ttk.Entry(edit_frame, textvariable=self.labor_rate_var, width=12).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(edit_frame, text="Важкість (%):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.labor_diff_var = tk.StringVar(value="0.0")
        ttk.Entry(edit_frame, textvariable=self.labor_diff_var, width=12).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Button(edit_frame, text="✅ Застосувати", command=self._apply_labor_edit).grid(row=3, column=0, columnspan=2, pady=10)

        help_frame = ttk.LabelFrame(self.labor_frame, text="📖 Як рахується зарплата", padding=10)
        help_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)
        help_text = (
            "Формула розрахунку зарплати у виробі:\n"
            "  Зарплата = metal_area × ставка × (1 + важкість / 100)\n\n"
            "Приклад:\n"
            "  Повітропровід 400×200×1000 мм, площа 1.2 м²\n"
            "  Ставка 120 грн/м², важкість 0%\n"
            "  Зарплата = 1.2 × 120 × 1.0 = 144 грн\n\n"
            "  Трійник, площа 2.5 м²\n"
            "  Ставка 250 грн/м², важкість 25%\n"
            "  Зарплата = 2.5 × 250 × 1.25 = 781.25 грн"
        )
        ttk.Label(help_frame, text=help_text, foreground=self._fg("green"), justify=tk.LEFT, font=("Consolas", 9)).pack(anchor=tk.W)

    def _refresh_labor_tree(self):
        for item in self.labor_tree.get_children():
            self.labor_tree.delete(item)
        catalog_names = {}
        for p in self.settings.products:
            name = p.get("name", "").strip()
            if name:
                catalog_names[name.lower()] = name
        for lower_key, data in self.settings.labor_rates.items():
            display_name = catalog_names.get(lower_key, lower_key)
            rate = data.get("rate_per_m2", 0.0)
            diff = data.get("difficulty_percent", 0.0)
            total = rate * (1 + diff / 100)
            self.labor_tree.insert("", tk.END, values=(display_name, f"{rate:.2f}", f"{diff:.1f}", f"{total:.2f}"))

    def _edit_labor_dialog(self):
        selected = self.labor_tree.selection()
        if not selected:
            return
        idx = self.labor_tree.index(selected[0])
        ptypes = list(self.settings.labor_rates.keys())
        if idx < len(ptypes):
            lower_key = ptypes[idx]
            data = self.settings.labor_rates[lower_key]
            display_name = lower_key
            for p in self.settings.products:
                if p.get("name", "").strip().lower() == lower_key:
                    display_name = p.get("name", "").strip()
                    break
            self.labor_type_var.set(display_name)
            self.labor_rate_var.set(str(data.get("rate_per_m2", 120.0)))
            self.labor_diff_var.set(str(data.get("difficulty_percent", 0.0)))

    def _apply_labor_edit(self):
        ptype = self.labor_type_var.get()
        if not ptype:
            messagebox.showwarning("Увага", "Оберіть тип виробу з таблиці.")
            return
        try:
            rate = float(self.labor_rate_var.get())
            diff = float(self.labor_diff_var.get())
        except ValueError:
            messagebox.showwarning("Увага", "Ставка та важкість мають бути числами.")
            return
        self.settings.labor_rates[ptype.lower().strip()] = {"rate_per_m2": rate, "difficulty_percent": diff}
        self._refresh_labor_tree()

    def _save_labor_rates(self):
        self.settings.save()
        messagebox.showinfo("Успіх", "Ставки зарплати збережено!")

    def _build_catalog_tab(self):
        ctrl = ttk.Frame(self.catalog_frame)
        ctrl.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(ctrl, text="➕ Додати продукцію", command=self._add_product_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="✏️ Редагувати", command=self._edit_product_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="🗑️ Видалити", command=self._delete_product).pack(side=tk.LEFT, padx=2)

        columns = ("name", "formula", "labor", "description")
        self.catalog_tree = ttk.Treeview(self.catalog_frame, columns=columns, show="headings", height=18)
        self.catalog_tree.heading("name", text="Назва виробу")
        self.catalog_tree.heading("formula", text="Формула розрахунку")
        self.catalog_tree.heading("labor", text="Години")
        self.catalog_tree.heading("description", text="Опис")
        self.catalog_tree.column("name", width=200)
        self.catalog_tree.column("formula", width=300)
        self.catalog_tree.column("labor", width=60)
        self.catalog_tree.column("description", width=300)

        scrollbar = ttk.Scrollbar(self.catalog_frame, orient=tk.VERTICAL, command=self.catalog_tree.yview)
        self.catalog_tree.configure(yscrollcommand=scrollbar.set)
        self.catalog_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        self.catalog_tree.bind("<Double-1>", lambda e: self._edit_product_dialog())

    def _build_params_tab(self):
        ctrl = ttk.Frame(self.params_frame)
        ctrl.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(ctrl, text="➕ Додати параметр", command=self._add_param_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="✏️ Редагувати", command=self._edit_param_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="🗑️ Видалити", command=self._delete_param).pack(side=tk.LEFT, padx=2)

        columns = ("name", "value", "description")
        self.params_tree = ttk.Treeview(self.params_frame, columns=columns, show="headings", height=18)
        self.params_tree.heading("name", text="Назва параметра")
        self.params_tree.heading("value", text="Значення")
        self.params_tree.heading("description", text="Опис / використання")
        self.params_tree.column("name", width=200)
        self.params_tree.column("value", width=120)
        self.params_tree.column("description", width=400)

        scrollbar = ttk.Scrollbar(self.params_frame, orient=tk.VERTICAL, command=self.params_tree.yview)
        self.params_tree.configure(yscrollcommand=scrollbar.set)
        self.params_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        self.params_tree.bind("<Double-1>", lambda e: self._edit_param_dialog())

        help_frame = ttk.LabelFrame(self.params_frame, text="📖 Довідка", padding=10)
        help_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)
        help_text = (
            "Кастомні параметри доступні у формулах розрахунку ціни як змінні.\n\n"
            "Приклад використання:\n"
            " • metal_area * material_price * 1.15 + flange_price * 2\n"
            " • metal_area * material_price + coating_price\n"
            " • (width + height) * 2 * material_price * thickness / 1000\n"
            " • length * material_price * 0.5\n"
            " • metal_area * material_price * 1.15 + transport_km * 5\n\n"
            "Стандартні змінні (завжди доступні):\n"
            "  metal_area, metal_area_m2, thickness, material_price,\n"
            "  weight, weight_kg, quantity, bolt_count,\n"
            "  width, height, length"
        )
        ttk.Label(help_frame, text=help_text, foreground=self._fg("green"), justify=tk.LEFT, font=("Consolas", 9)).pack(anchor=tk.W)

    def _add_param_dialog(self):
        self._param_dialog(None)

    def _edit_param_dialog(self):
        selected = self.params_tree.selection()
        if not selected:
            messagebox.showwarning("Увага", "Оберіть параметр для редагування.")
            return
        idx = self.params_tree.index(selected[0])
        self._param_dialog(idx)

    def _param_dialog(self, idx):
        dialog = tk.Toplevel(self.frame)
        dialog.title("Параметр" if idx is None else "Редагувати параметр")
        dialog.geometry("480x380")
        dialog.minsize(450, 350)
        dialog.transient(self.frame)
        dialog.grab_set()

        param_names = list(self.settings.custom_params.keys())
        if idx is not None:
            name = param_names[idx]
            value = self.settings.custom_params[name]
            desc = getattr(self, '_param_descriptions', {}).get(name, "")
        else:
            name = ""
            value = 0.0
            desc = ""

        ttk.Label(dialog, text="Назва параметра:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        name_var = tk.StringVar(value=name)
        ttk.Entry(dialog, textvariable=name_var, width=35).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Значення:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        value_var = tk.StringVar(value=str(value))
        ttk.Entry(dialog, textvariable=value_var, width=15).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(dialog, text="Опис (необов'язково):").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        desc_var = tk.StringVar(value=desc)
        ttk.Entry(dialog, textvariable=desc_var, width=35).grid(row=2, column=1, padx=5, pady=5)

        examples = (
            "Приклади параметрів:\n"
            "  flange_price — ціна одного фланця (грн)\n"
            "  coating_price — вартість покриття (грн/м²)\n"
            "  transport_km — відстань доставки (км)\n"
            "  packing_cost — вартість упаковки (грн)"
        )
        ttk.Label(dialog, text=examples, foreground=self._fg("fg_muted"), justify=tk.LEFT, font=("Consolas", 9)).grid(
            row=3, column=0, columnspan=2, padx=10, pady=10, sticky=tk.W
        )

        def save():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showwarning("Увага", "Назва параметра не може бути порожньою.")
                return
            if not new_name.replace("_", "").isalnum():
                messagebox.showwarning("Увага", "Назва параметра може містити лише латинські літери, цифри та '_' .")
                return
            try:
                new_value = float(value_var.get())
            except ValueError:
                messagebox.showwarning("Увага", "Значення має бути числом.")
                return
            if not hasattr(self, '_param_descriptions'):
                self._param_descriptions = {}
            self._param_descriptions[new_name] = desc_var.get()
            if idx is not None:
                old_name = param_names[idx]
                if old_name != new_name:
                    del self.settings.custom_params[old_name]
            self.settings.custom_params[new_name] = new_value
            self._refresh_params()
            dialog.destroy()

        ttk.Button(dialog, text="Зберегти", command=save).grid(row=4, column=0, columnspan=2, pady=15)

    def _delete_param(self):
        selected = self.params_tree.selection()
        if not selected:
            messagebox.showwarning("Увага", "Оберіть параметр для видалення.")
            return
        if messagebox.askyesno("Підтвердження", "Видалити обраний параметр?"):
            idx = self.params_tree.index(selected[0])
            param_names = list(self.settings.custom_params.keys())
            del self.settings.custom_params[param_names[idx]]
            self._refresh_params()

    def _refresh_params(self):
        for item in self.params_tree.get_children():
            self.params_tree.delete(item)
        descriptions = getattr(self, '_param_descriptions', {})
        for name, value in self.settings.custom_params.items():
            desc = descriptions.get(name, "")
            self.params_tree.insert("", tk.END, values=(name, f"{value:.2f}", desc))

    def _add_product_dialog(self):
        self._product_dialog(None)

    def _edit_product_dialog(self):
        selected = self.catalog_tree.selection()
        if not selected:
            messagebox.showwarning("Увага", "Оберіть продукцію для редагування.")
            return
        idx = self.catalog_tree.index(selected[0])
        self._product_dialog(idx)

    def _product_dialog(self, idx):
        dialog = tk.Toplevel(self.frame)
        dialog.title("Продукція" if idx is None else "Редагувати продукцію")
        dialog.geometry("540x480")
        dialog.minsize(500, 420)
        dialog.transient(self.frame)
        dialog.grab_set()

        product = self.settings.products[idx] if idx is not None else {}

        ttk.Label(dialog, text="Назва виробу:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        name_var = tk.StringVar(value=product.get("name", ""))
        ttk.Entry(dialog, textvariable=name_var, width=40).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Формула розрахунку:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        formula_var = tk.StringVar(value=product.get("formula", "metal_area * thickness * material_price * 1.15"))
        ttk.Entry(dialog, textvariable=formula_var, width=40).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Години роботи:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        labor_var = tk.StringVar(value=str(product.get("labor_hours", 0.15)))
        ttk.Entry(dialog, textvariable=labor_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(dialog, text="Опис:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        desc_var = tk.StringVar(value=product.get("description", ""))
        ttk.Entry(dialog, textvariable=desc_var, width=40).grid(row=3, column=1, padx=5, pady=5)

        param_help = (
            "Доступні змінні у формулі (завжди доступні):\n"
            "  metal_area — площа металу (м²)\n"
            "  thickness — товщина (мм)\n"
            "  material_price — ціна металу (грн/кг)\n"
            "  weight — вага (кг)\n"
            "  quantity — кількість\n"
            "  bolt_count — кількість болтів\n"
            "  width — ширина виробу (мм)\n"
            "  height — висота виробу (мм)\n"
            "  length — довжина виробу (мм)\n\n"
            "Додаткові параметри (автоматично створять поля вводу):\n"
            "  angle — кут згину (°)\n"
            "  radius — радіус дуги (мм)\n"
            "  branch_width / branch_height — відгалуження Ш×В (мм)\n"
            "  branch_length — довжина відгалуження (мм)\n"
            "  branch_offset — відстань від краю (мм)\n"
            "  branch_diameter — Ø відгалуження (мм)\n"
            "  end_width / end_height — кінцеві розміри (мм)\n"
            "  end_diameter — кінцевий Ø (мм)\n"
            "  flange_border / flange_width — ширина полки (мм)\n"
            "  depth — глибина (мм)\n"
            "  border — ширина загину (мм)\n"
            "  segments — кількість сегментів\n"
            "  bolt_count — кількість болтів\n"
            "  bolt_diameter — Ø отвору під болт (мм)\n"
            "  bolt_spacing — крок отворів (мм)\n\n"
            "Кастомні параметри (з вкладки 'Параметри формул'):\n"
            "  " + ", ".join(self.settings.custom_params.keys()) if self.settings.custom_params else "  (немає)"
        )
        ttk.Label(dialog, text=param_help, foreground=self._fg("green"), justify=tk.LEFT).grid(
            row=4, column=0, columnspan=2, padx=10, pady=10, sticky=tk.W
        )

        def save():
            new_product = {
                "name": name_var.get(),
                "formula": formula_var.get(),
                "labor_hours": float(labor_var.get()),
                "description": desc_var.get(),
            }
            if idx is None:
                self.settings.products.append(new_product)
            else:
                self.settings.products[idx] = new_product
            self.settings.sync_labor_rates()
            self.settings.save()
            self._refresh_catalog()
            dialog.destroy()

        ttk.Button(dialog, text="Зберегти", command=save).grid(row=5, column=0, columnspan=2, pady=15)

    def _delete_product(self):
        selected = self.catalog_tree.selection()
        if not selected:
            messagebox.showwarning("Увага", "Оберіть продукцію для видалення.")
            return
        if messagebox.askyesno("Підтвердження", "Видалити обрану продукцію?"):
            idx = self.catalog_tree.index(selected[0])
            removed_name = self.settings.products[idx].get("name", "").strip()
            del self.settings.products[idx]
            lower_name = removed_name.lower()
            if lower_name in self.settings.labor_rates:
                del self.settings.labor_rates[lower_name]
            self.settings.save()
            self._refresh_catalog()

    def _refresh_all(self):
        for (mat, th), var in self.metal_entries.items():
            price = self.settings.material_prices.get(mat, {}).get(th, 0)
            var.set(str(price))
        for key, var in self.cost_vars.items():
            var.set(str(self.settings.overhead.get(key, 0)))
        for key, var in self.depr_vars.items():
            var.set(str(self.settings.depreciation.get(key, 0)))
        self._refresh_catalog()
        self._refresh_params()
        self._refresh_labor_tree()

    def _refresh_catalog(self):
        for item in self.catalog_tree.get_children():
            self.catalog_tree.delete(item)
        for p in self.settings.products:
            self.catalog_tree.insert("", tk.END, values=(p["name"], p["formula"], p.get("labor_hours", 0), p.get("description", "")))
        self.settings.sync_labor_rates()
        self._refresh_labor_tree()

    def _save_settings(self):
        for (mat, th), var in self.metal_entries.items():
            if mat not in self.settings.material_prices:
                self.settings.material_prices[mat] = {}
            with contextlib.suppress(ValueError):
                self.settings.material_prices[mat][th] = float(var.get())
        for key, var in self.cost_vars.items():
            with contextlib.suppress(ValueError):
                self.settings.overhead[key] = float(var.get())
        for key, var in self.depr_vars.items():
            with contextlib.suppress(ValueError):
                self.settings.depreciation[key] = float(var.get())
        self.settings.save()
        messagebox.showinfo("Успіх", "Налаштування збережено!")

    def _reset_defaults(self):
        if messagebox.askyesno("Підтвердження", "Скинути всі налаштування до замовчування?"):
            self.settings.material_prices = DEFAULT_MATERIAL_PRICES.copy()
            self.settings.overhead = DEFAULT_OVERHEAD.copy()
            self.settings.depreciation = DEFAULT_DEPRECIATION.copy()
            self.settings.markup_matrix = build_default_markup_matrix()
            self.settings.products = [p.copy() for p in DEFAULT_PRODUCTS]
            self.settings.custom_params = DEFAULT_CUSTOM_PARAMS.copy()
            self.settings.labor_rates = DEFAULT_LABOR_RATES.copy()
            self._refresh_all()
            self.settings.save()