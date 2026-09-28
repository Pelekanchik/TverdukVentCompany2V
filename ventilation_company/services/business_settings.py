"""Бізнес-налаштування: ПДВ, комплектуючі, додаткові матеріали, посади/ставки.

Єдине джерело правди для бізнес-констант, які раніше були захардкоджені
у ventilation_company/config.py. Патерн зберігання — як у PricingSettings:
singleton, JSON-файл у DATA_DIR, атомарний запис, reload за mtime.

Ціни листового металу тут НЕ зберігаються — вони живуть у PricingSettings
(material_prices за матеріалом і товщиною).
"""

from __future__ import annotations

import json
import os
import threading

from ventilation_company.paths import DATA_DIR

SETTINGS_FILE = str(DATA_DIR / "business_settings.json")

DEFAULT_VAT_RATE = 20.0

# Комплектуючі (вентилятори, фільтри, клапани тощо) — ключ: назва з _ замість пробілів.
DEFAULT_COMPONENTS = {
    "вентилятор_осьовий": {"ціна": 3500, "одиниця": "шт"},
    "вентилятор_радіальний": {"ціна": 8500, "одиниця": "шт"},
    "вентилятор_канальний": {"ціна": 4200, "одиниця": "шт"},
    "фільтр_грубої_очистки": {"ціна": 1200, "одиниця": "шт"},
    "фільтр_тонкої_очистки": {"ціна": 2800, "одиниця": "шт"},
    "клапан_вогнезатримуючий": {"ціна": 5600, "одиниця": "шт"},
    "гнучка_вставка": {"ціна": 850, "одиниця": "шт"},
    "решітка_вентиляційна": {"ціна": 450, "одиниця": "шт"},
    "дифузор": {"ціна": 680, "одиниця": "шт"},
    "шумоглушник": {"ціна": 3200, "одиниця": "шт"},
    "калорифер": {"ціна": 15000, "одиниця": "шт"},
    "рекуператор": {"ціна": 28000, "одиниця": "шт"},
}

# Додаткові матеріали, яких немає в PricingSettings (ізоляція тощо).
DEFAULT_EXTRA_MATERIALS = {
    "ізоляція_мінвата": {"ціна_за_м2": 180, "одиниця": "м2"},
    "ізоляція_каучук": {"ціна_за_м2": 250, "одиниця": "м2"},
}

# Посади та ставки зарплати (грн/міс + премія, %).
DEFAULT_POSITIONS = {
    "директор": {"ставка": 45000, "премія_%": 20},
    "головний_інженер": {"ставка": 38000, "премія_%": 15},
    "інженер_проектувальник": {"ставка": 28000, "премія_%": 10},
    "технолог": {"ставка": 25000, "премія_%": 10},
    "зварник": {"ставка": 22000, "премія_%": 15},
    "монтажник": {"ставка": 20000, "премія_%": 12},
    "електрик": {"ставка": 21000, "премія_%": 10},
    "комірник": {"ставка": 16000, "премія_%": 5},
    "бухгалтер": {"ставка": 22000, "премія_%": 8},
    "менеджер_з_продажу": {"ставка": 18000, "премія_%": 25},
    "водій": {"ставка": 15000, "премія_%": 5},
}

# Ціни фланців за профілем, грн/шт.
DEFAULT_FLANGE_PRICES = {
    "P30": {"ціна": 150.0},
    "P40": {"ціна": 200.0},
}


class BusinessSettings:
    """Менеджер бізнес-налаштувань (Singleton, файлове блокування)."""

    _instance: BusinessSettings | None = None
    _lock = threading.Lock()
    # Встановлюється в __new__; анотація тут — для mypy.
    _initialized: bool

    def __new__(cls, filepath: str = SETTINGS_FILE) -> BusinessSettings:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls, filepath: str = SETTINGS_FILE) -> BusinessSettings:
        """Отримати єдиний екземпляр налаштувань."""
        return cls(filepath)

    def __init__(self, filepath: str = SETTINGS_FILE):
        if self._initialized:
            return
        self._initialized = True

        self.filepath = filepath
        self._file_lock = threading.Lock()
        self._last_modified: float = 0.0

        self.vat_rate: float = DEFAULT_VAT_RATE
        self.components: dict = {}
        self.extra_materials: dict = {}
        self.positions: dict = {}
        self.flange_prices: dict = {}

        self.load()

    # ── Файлові операції з блокуванням ──

    def _atomic_write(self, data: dict) -> None:
        """Атомарний запис: спочатку у тимчасовий файл, потім replace."""
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
        self.vat_rate = float(data.get("vat_rate", DEFAULT_VAT_RATE))
        self.components = data.get("components", json.loads(json.dumps(DEFAULT_COMPONENTS)))
        self.extra_materials = data.get(
            "extra_materials", json.loads(json.dumps(DEFAULT_EXTRA_MATERIALS))
        )
        self.positions = data.get("positions", json.loads(json.dumps(DEFAULT_POSITIONS)))
        self.flange_prices = data.get(
            "flange_prices", json.loads(json.dumps(DEFAULT_FLANGE_PRICES))
        )
        if not data:
            self.save()

    def save(self) -> None:
        """Зберегти налаштування атомарно."""
        data = {
            "vat_rate": self.vat_rate,
            "components": self.components,
            "extra_materials": self.extra_materials,
            "positions": self.positions,
            "flange_prices": self.flange_prices,
        }
        with self._file_lock:
            self._atomic_write(data)

    # ── Зручні геттери ──

    def get_vat_rate(self) -> float:
        """Поточна ставка ПДВ, %."""
        self.reload()
        return self.vat_rate

    def get_component(self, key: str) -> dict:
        """Ціна та одиниця комплектуючого; порожній dict, якщо невідомо."""
        self.reload()
        return self.components.get(key, {})

    def get_extra_material_price(self, key: str, default: float = 0.0) -> float:
        """Ціна за м² додаткового матеріалу (ізоляція тощо)."""
        self.reload()
        return self.extra_materials.get(key, {}).get("ціна_за_м2", default)

    def get_position(self, name: str) -> dict:
        """Ставка та премія посади; нульові значення, якщо невідомо."""
        self.reload()
        return self.positions.get(name, {"ставка": 0, "премія_%": 0})

    def get_flange_price(self, profile: str, default: float = 150.0) -> float:
        """Ціна фланця за профілем (P30/P40), грн/шт."""
        self.reload()
        raw = self.flange_prices.get(profile, {})
        if isinstance(raw, dict):
            return float(raw.get("ціна", default))
        return float(raw) if raw else default
