TverdukVentCompany2V/
├── main.py                    # Точка входу (GUI/CLI перемикач)
├── run_gui.py                 # Альтернативний запуск GUI
├── pyproject.toml             # Конфігурація пакету (PEP 621)
├── requirements.txt           # Залежності
│
├── ventilation_company/       # 📦 Основний пакет
│   ├── config.py              # Константи: ціни, матеріали, посади, ПДВ
│   ├── auto_specification.py  # Автоматична специфікація (dataclasses, експорт)
│   ├── metal_cutting.py       # Розкрій листового металу
│   ├── freecad_models.py      # Інтеграція з FreeCAD (3D моделі)
│   ├── standard_products.py   # Стандартні вироби
│   ├── price_list_tab.py      # Логіка прайс-листа
│   ├── db_integration.py      # Інтеграція з БД (ProjectDatabase)
│   │
│   ├── database/              # 🗄️ Шар даних (SQLAlchemy ORM)
│   │   ├── db.py              # Engine + Session (SQLite)
│   │   ├── base.py            # DeclarativeBase
│   │   ├── models/            # ORM-моделі
│   │   │   ├── project.py
│   │   │   ├── product.py
│   │   │   ├── calculation.py
│   │   │   ├── employee.py
│   │   │   ├── work_catalog.py
│   │   │   └── calc.py
│   │   └── repositories/      # Repository Pattern
│   │       ├── product_repo.py
│   │       ├── material_repo.py
│   │       ├── calc_repo.py
│   │       ├── settings_repo.py
│   │       ├── overhead_repo.py
│   │       └── template_repo.py
│   │
│   ├── models/                # 🧠 Domain Models (чисті класи)
│   │   ├── project.py         # Клас Project (валідація, компоненти)
│   │   └── product.py         # Клас Product (історія цін, властивості)
│   │
│   ├── calculations/          # 💰 Розрахунки
│   │   ├── pricing.py         # PricingEngine (3 методи ціноутворення)
│   │   └── salary_calculator.py
│   │
│   ├── gui/                   # 🎨 Інтерфейс (tkinter)
│   │   ├── main_window.py     # Головне вікно (1400×900, вкладки)
│   │   ├── products_tab.py    # Вкладка виробів
│   │   ├── specification_tab.py
│   │   ├── cutting_tab.py     # Вкладка розкрою
│   │   ├── freecad_tab.py     # Вкладка FreeCAD
│   │   └── settings_tab.py    # Налаштування
│   │
│   └── utils/                 # 🛠️ Утиліти
│       ├── validators.py
│       └── helpers.py
│
├── tests/                     # 🧪 Тести (pytest)
│   ├── test_project.py
│   ├── test_calculations.py
│   └── test_repositories/
│
├── data/                      # 📂 База даних SQLite
│   ├── company.db
│   └── pricing_settings.json
│
└── ventilation_price_list.json # 📋 JSON прайс-лист