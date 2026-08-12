# 🏭 VentCompany v2.0 — Система управління вентиляційною виробничою фірмою

Комплексна система управління проєктами, розрахунків собівартості, ціноутворення, розкрою металу та 3D-моделювання для виробничої фірми з вентиляційних систем.

---

## 📋 Зміст

- [Огляд](#-огляд)
- [Функціонал](#-функціонал)
- [Встановлення](#-встановлення)
- [Запуск](#-запуск)
- [Структура проєкту](#-структура-проєкту)
- [Технологічний стек](#-технологічний-стек)
- [Модулі](#-модулі)
- [Тестування](#-тестування)
- [Ліцензія](#-ліцензія)

---

## 🔭 Огляд

**VentCompany** — це desktop-додаток з графічним інтерфейсом (tkinter), який охоплює повний цикл роботи вентиляційної виробничої фірми:

1. **Каталог виробів** — створення та редагування повітропроводів, фасонних виробів, фланців, заглушок, гнучких вставок
2. **Розрахунок собівартості** — автоматичний підрахунок вартості матеріалів, робіт, накладних витрат та амортизації
3. **Ціноутворення** — гнучка матриця націнок (стандартні/нестандартні розміри), ПДВ 20%
4. **Розкрій металу** — оптимізація розкладки деталей на стандартних листах (Bottom-Left + Guillotine)
5. **3D-моделювання** — інтеграція з FreeCAD + вбудований перегляд через matplotlib
6. **Документообіг** — генерація PDF, Excel, CSV звітів; специфікації; прайс-листи
7. **Управління проєктами** — SQLite БД з архівуванням та фінансовою аналітикою
8. **Зарплатний калькулятор** — розрахунок ФОП з податками (ПДФО 18%, ВЗ 1.5%, ЄСВ 22%)

---

## ✨ Функціонал

### 📦 Вироби
- **Круглі вироби**: труби, відводи, трійники, переходи, фланці, заглушки
- **Прямокутні вироби**: труби, відводи, трійники, переходи, фланці, заглушки
- **Гнучкі вставки**
- Матеріали: оцинкована сталь, нержавіюча сталь, алюміній
- Товщини: 0.5, 0.7, 0.9, 1.0, 1.2, 1.5, 2.0 мм
- Кастомні формули розрахунку для кожного типу виробу
- Експорт у FreeCAD (FCStd, STEP, STL, OBJ, IGES)

### 💰 Ціноутворення
- **Матриця націнок**: різні націнки для стандартних/нестандартних розмірів
- **Накладні витрати**: електроенергія, оренда, транспорт, відходи (8%)
- **Амортизація обладнання**: гільйотина (5%), гнуття (4%), зварка (3%), плазма (6%)
- **ПДВ**: 20%
- **Два прайси**: внутрішній (повний) та для замовника (публічний)
- Експорт прайс-листів: PDF, Excel, CSV, HTML

### ✂️ Розкрій металу
- Алгоритми: **Bottom-Left heuristic** та **Guillotine cutting**
- Стандартні листи: 1250×2500, 1000×2000, 1500×3000, 1250×3000 мм
- Припуски на різ (2 мм) та згин (3 мм)
- Візуалізація плану розкрою
- Мінімізація відходів

### 🏗️ 3D-моделювання (FreeCAD)
- Автопошук FreeCAD (Windows/Linux/Mac)
- Експорт у формати: FCStd, STEP, STL, OBJ, IGES
- Вбудований 3D-перегляд через **matplotlib** (без FreeCAD)
- Кольорове кодування за типом виробу
- Пакетний експорт

### 📋 Специфікація та документи
- Автоматичне формування специфікацій з групуванням
- Генерація PDF-звітів (fpdf2 з підтримкою кирилиці)
- Експорт у Excel (openpyxl)
- Архів проєктів з фінансовою аналітикою

### 🗄️ База даних (SQLite + SQLAlchemy ORM)
- **Проєкти**: номер, назва, клієнт, адреса, тип вентиляції, витрата повітря, тиск
- **Компоненти, матеріали, роботи** — прив'язані до проєкту
- **Розрахунки**: собівартість, націнка, ПДВ, кінцева ціна, прибуток
- **Співробітники**: посада, ставка, премія, фактична зарплата
- **Каталог робіт**: прайс робіт з одиницями виміру
- **Калькулятор виробів**: типи, підтипи, діапазони розмірів, формули

---

## 🚀 Встановлення

### Вимоги
- Python **≥ 3.10**
- (Опціонально) FreeCAD для 3D-експорту

### Клонування та встановлення

```bash
git clone https://github.com/Pelekanchik/TverdukVentCompany2V.git
cd TverdukVentCompany2V
pip install -r requirements.txt
```

### Залежності

| Пакет | Версія | Призначення |
|-------|--------|-------------|
| `openpyxl` | ≥3.1.0 | Excel-експорт |
| `reportlab` | ≥4.0.0 | PDF-звіти (додатково) |
| `matplotlib` | ≥3.7.0 | 3D-перегляд, графіки |
| `python-dateutil` | ≥2.8.0 | Робота з датами |
| `pywebview` | ≥4.4 | Web-віджети |
| `sqlalchemy` | ≥2.0 | ORM для SQLite |
| `alembic` | ≥1.13 | Міграції БД |
| `fpdf2` | ≥2.7.0 | PDF-звіти з Unicode |

---

## ▶️ Запуск

### GUI режим (за замовчуванням)
```bash
python main.py
# або
python run_gui.py
```

### Консольний режим
```bash
python main.py --cli
# або
python main.py -c
```

### Консольні команди (pyproject.toml)
```bash
vent-firm      # CLI
vent-firm-gui  # GUI
```

---

## 📁 Структура проєкту

```
TverdukVentCompany2V/
├── main.py                          # Точка входу (GUI/CLI)
├── run_gui.py                       # Альтернативний запуск GUI
├── pyproject.toml                   # Конфігурація пакету
├── requirements.txt                 # Залежності Python
├── LICENSE                          # Ліцензія MIT
├── README.md                        # Цей файл
│
├── data/                            # 📂 Дані
│   ├── company.db                   # SQLite база даних
│   ├── price_list.json              # Прайс-лист (позиції)
│   └── pricing_settings.json        # Налаштування цін і націнок
│
├── tests/                           # 🧪 Модульні тести (pytest)
│   ├── conftest.py                  # Фікстури pytest
│   ├── test_auto_specification.py   # Тести специфікацій
│   ├── test_db_integration.py       # Тести БД
│   ├── test_metal_cutting.py        # Тести розкрою
│   ├── test_models_product.py       # Тести моделі Product
│   ├── test_models_project.py       # Тести моделі Project
│   ├── test_pricing.py              # Тести PricingEngine
│   ├── test_salary_calculator.py    # Тести зарплатного калькулятора
│   ├── test_standard_products.py    # Тести стандартних виробів
│   ├── test_utils_helpers.py        # Тести helpers
│   ├── test_utils_validators.py     # Тести validators
│   └── test_repositories/
│       └── test_overhead_repo.py    # Тести OverheadRepository
│
├── debug_export.py                  # 🔧 Дебаг-скрипт FreeCAD
├── test_price.py                    # 🔧 Тестовий скрипт ціноутворення
│
└── ventilation_company/             # 📦 Основний пакет
    ├── __init__.py
    ├── config.py                    # Конфігурація: матеріали, компоненти, роботи, посади
    ├── standard_products.py         # Класи виробів (круглі/прямокутні)
    ├── auto_specification.py        # Автоматична специфікація
    ├── metal_cutting.py             # Розкрій листового металу
    ├── freecad_models.py            # Інтеграція з FreeCAD
    ├── freecad_preview.py           # 3D-перегляд через matplotlib
    ├── freecad_macro.py             # FreeCAD macro для 3D-моделей
    ├── freecad_geometry.py          # Pure-Python 3D геометрія
    ├── pdf_generator.py             # Генератор PDF-звітів
    ├── db_integration.py            # Розширена інтеграція з SQLite
    │
    ├── calculations/                # 💰 Модуль розрахунків
    │   ├── __init__.py
    │   ├── pricing.py               # PricingEngine (собівартість + націнка)
    │   └── salary_calculator.py     # SalaryCalculator (ФОП + податки)
    │
    ├── database/                    # 🗄️ ORM SQLAlchemy
    │   ├── __init__.py
    │   ├── db.py                    # Підключення до SQLite, сесії
    │   ├── base.py                  # Базовий клас DeclarativeBase
    │   ├── context.py               # DatabaseContext (єдиний контекст БД)
    │   ├── models/                  # ORM-моделі
    │   │   ├── __init__.py
    │   │   ├── project.py           # Project, ProjectComponent, ProjectMaterial, ProjectWork
    │   │   ├── product.py           # ProductType, ProductSubtype, SizeRange
    │   │   ├── calculation.py       # Calculation (розрахунки проєкту)
    │   │   ├── employee.py          # Employee (співробітники)
    │   │   ├── work_catalog.py      # WorkCatalog (каталог робіт)
    │   │   └── calc.py              # CalcMaterial, CalcCalculation, CalcItem, OverheadItem
    │   └── repositories/            # Репозиторії (CRUD)
    │       ├── __init__.py
    │       ├── product_repo.py      # ProductRepository
    │       ├── material_repo.py     # MaterialRepository
    │       ├── overhead_repo.py     # OverheadRepository
    │       ├── settings_repo.py     # SettingsRepository
    │       ├── calc_repo.py         # CalculationRepository
    │       └── template_repo.py     # TemplateRepo
    │
    ├── gui/                         # 🖥️ Графічний інтерфейс (tkinter)
    │   ├── __init__.py
    │   ├── main_window.py           # Головне вікно з вкладками
    │   ├── products_tab.py          # Вкладка "Вироби" (каталог + конструктор)
    │   ├── specification_tab.py     # Вкладка "Специфікація" + архів проєктів
    │   ├── cutting_tab.py           # Вкладка "Розкрій металу"
    │   ├── freecad_tab.py           # Вкладка "FreeCAD 3D"
    │   ├── price_list_tab.py        # Вкладка "Прайс-лист"
    │   ├── metal_prices_tab.py      # Вкладка "Ціни на метал"
    │   ├── settings_tab.py          # Вкладка "Ціноутворення" (налаштування)
    │   └── markup_matrix_tab.py     # Вкладка "Націнки по категоріях"
    │
    ├── models/                      # 📐 Pydantic/датакласи моделі
    │   ├── __init__.py
    │   ├── product.py               # Product, PriceHistoryEntry
    │   └── project.py               # Project, generate_project_number
    │
    └── utils/                       # 🛠️ Утиліти
        ├── __init__.py
        ├── helpers.py               # Допоміжні функції
        └── validators.py            # Валідація даних
```

---

## 🛠️ Технологічний стек

| Шар | Технологія |
|-----|------------|
| **GUI** | tkinter + ttk |
| **База даних** | SQLite + SQLAlchemy 2.0 (ORM) |
| **Міграції** | Alembic |
| **PDF** | fpdf2 (Unicode/кирилиця) |
| **Excel** | openpyxl |
| **3D-візуалізація** | matplotlib (TkAgg backend) |
| **3D-CAD** | FreeCAD (опціонально) |
| **Тестування** | pytest |
| **Форматування** | black, isort, ruff |

---

## 📦 Модулі

### `standard_products.py`
Базові класи виробів вентиляції:
- `StandardProduct` — базовий клас
- `RoundDuct`, `RectDuct` — круглі/прямокутні труби
- `RoundElbow`, `RectElbow` — відводи
- `RoundTee`, `RectTee` — трійники
- `RoundTransition`, `RectTransition` — переходи
- `RoundFlange`, `RectFlange` — фланці
- `RoundCap`, `RectCap` — заглушки
- `FlexibleConnector` — гнучка вставка
- `ProductLibrary` — бібліотека виробів

### `metal_cutting.py`
Алгоритми розкрою:
- `Detail` — деталь з припусками
- `Sheet` — лист металу
- `PlacedDetail` — розміщена деталь
- `CuttingPlan` — план розкрою
- `MetalCutter` — основний клас розкрою
- `calculate_sheet_cutting()` — розрахунок розкрою
- `estimate_metal_needed()` — оцінка потреби в металі

### `pricing.py`
Ціноутворення:
- `PricingEngine` — розрахунок ціни (cost-plus, competitive, value-based)
- Методи: `cost_plus_pricing()`, `competitive_pricing()`, `value_based_pricing()`

### `salary_calculator.py`
Зарплатний калькулятор:
- `SalaryCalculator` — розрахунок ФОП
- Податки: ПДФО 18%, ВЗ 1.5%, ЄСВ 22%
- Премії за посадами

### `auto_specification.py`
Специфікації:
- `SpecItem` — рядок специфікації
- `Specification` — повна специфікація
- `SpecBuilder` — побудовник специфікацій
- Експорт: JSON, CSV, TXT, HTML

### `pdf_generator.py`
PDF-звіти:
- `ProjectPDFReport` — звіт по проєкту
- Автопошук шрифтів з підтримкою кирилиці (Windows/Linux)

---

## 🧪 Тестування

```bash
# Запуск усіх тестів
pytest

# З детальним виводом
pytest -v

# З покриттям
pytest --cov=ventilation_company
```

### Перелік тестів

| Файл | Що тестується |
|------|---------------|
| `test_auto_specification.py` | SpecItem, SpecBuilder, merge_specifications |
| `test_db_integration.py` | ProjectDatabase, CRUD операції |
| `test_metal_cutting.py` | Detail, Sheet, MetalCutter, CuttingPlan |
| `test_models_product.py` | Product, PriceHistoryEntry |
| `test_models_project.py` | Project, generate_project_number, validate_project_number |
| `test_pricing.py` | PricingEngine (cost-plus, competitive, value-based) |
| `test_salary_calculator.py` | SalaryCalculator (ФОП, податки, премії) |
| `test_standard_products.py` | Всі класи виробів (RoundDuct, RectElbow тощо) |
| `test_utils_helpers.py` | helpers (форматування, розрахунок площ) |
| `test_utils_validators.py` | validators (валідація даних) |
| `test_overhead_repo.py` | OverheadRepository (CRUD накладних витрат) |

---

## ⚙️ Конфігурація

### Налаштування цін (`data/pricing_settings.json`)

```json
{
  "material_prices": {
    "оцинкована сталь": {
      "0.5": 260.0, "0.7": 380.0, "1.0": 750.0, ...
    },
    "нержавіюча сталь": { ... },
    "алюміній": { ... }
  },
  "overhead": {
    "electricity_per_kg": 2.5,
    "rent_per_month": 15000.0,
    "transport_per_project": 500.0,
    "waste_percent": 8.0
  },
  "depreciation": {
    "guillotine_percent": 5.0,
    "bending_percent": 4.0,
    "welding_percent": 3.0,
    "plasma_percent": 6.0
  },
  "markup_percent": 30.0,
  "markup_matrix": { ... }
}
```

### Константи (`config.py`)

| Константа | Значення | Опис |
|-----------|----------|------|
| `MARKUP_PERCENTAGE` | 30% | Базова націнка |
| `VAT_RATE` | 20% | ПДВ |
| `OVERHEAD_PERCENTAGE` | 15% | Накладні витрати |
| `MIN_WAGE` | 8000 грн | Мінімальна зарплата |
| `WORKING_HOURS_PER_MONTH` | 168 | Робочих годин на місяць |

---

## 📝 Ліцензія

MIT License — див. файл [LICENSE](LICENSE).

---

## 👨‍💻 Автор

**Pelekanchik** — [GitHub](https://github.com/Pelekanchik)

---

> 💡 **Підказка**: Для роботи з 3D-моделями встановіть [FreeCAD](https://www.freecad.org/) (версія 0.21+). Без FreeCAD доступний вбудований 3D-перегляд через matplotlib.
