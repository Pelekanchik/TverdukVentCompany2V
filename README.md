# 🏭 VentCompany v2.7.0

**Система управління вентиляційними проєктами**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![PySide6](https://img.shields.io/badge/PySide6-6.6%2B-green)](https://wiki.qt.io/Qt_for_Python)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-blue)](https://postgresql.org)
[![CI](https://github.com/Pelekanchik/TverdukVentCompany2V/actions/workflows/ci.yml/badge.svg)](https://github.com/Pelekanchik/TverdukVentCompany2V/actions)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Опис

VentCompany — desktop-додаток для автоматизації роботи вентиляційної компанії. Програма дозволяє:

- 🏗️ Вести проєкти вентиляції: вироби, специфікації, розкрій листового металу
- 💰 Розраховувати собівартість, ціни, ПДВ та прибуток
- 📊 Вести CRM: клієнти, взаємодії, проєкти клієнтів, гарантійні нагадування
- 📄 Генерувати документи проєкту (кошториси, специфікації, рахунки)
- 🏭 Контролювати виробництво: вироби, матеріали, роботи, витрати
- ⚙️ Налаштовувати реквізити компанії, тему, бізнес-параметри, бекапи

---

## 🖥️ Технології

| Компонент | Технологія |
|-----------|------------|
| GUI | PySide6 (Qt6), QSS-теми (Catppuccin Mocha / Light) |
| База даних | PostgreSQL 14+ (прод), фейки/SQLite у тестах |
| ORM | SQLAlchemy 2.0 |
| Міграції | Alembic (`migrations/`, поточна head — `008`) |
| Аутентифікація | bcrypt, політика паролів, rate limiting, audit log |
| Експорт | pandas, openpyxl, reportlab, fpdf2, matplotlib |
| 3D / геометрія | Власні модулі `project3d/`, `freecad_geometry.py` (опційно VTK/pyvista) |

Повний перелік залежностей — у `requirements.txt`; опційні (3D, AutoCAD, вебв'ю) — у `requirements-optional.txt`.

---

## 🚀 Встановлення

### 1. Клонування та середовище

```bash
git clone https://github.com/Pelekanchik/TverdukVentCompany2V.git
cd TverdukVentCompany2V
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
```

### 2. Налаштування PostgreSQL

Найпростіший шлях — Docker:

```bash
docker-compose up -d
```

Або власний сервер: створи БД `ventcompany`, потім файл `.env` у корені проєкту:

```env
DATABASE_URL=postgresql://КОРИСТУВАЧ:ПАРОЛЬ@localhost:5432/ventcompany
```

Детальніша інструкція — у [INSTRUCTION.md](INSTRUCTION.md).

### 3. Запуск

```bash
python main_pyside6.py
```

Точка входу автоматично застосовує Alembic-міграції та відкриє вікно логіну.

---

## 🎨 Інтерфейс

Бічна панель навігації:

- **РОБОТА** — 📊 Дашборд · 📁 Проєкти · 🔧 Вироби · 📋 Специфікація · ✂️ Розкрій
- **ФІНАНСИ** — 💰 Ціноутворення · 📄 Документи
- **АНАЛІТИКА** — 👥 CRM · ⚙️ Налаштування
- Вихід

Користувачів та ручку — у [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

---

## 👥 Ролі користувачів

Матриця дозволів — `ventilation_company/auth/permissions.py`.

| Роль | Доступ (скорочено) |
|------|---------------------|
| **Адміністратор** | Повний доступ + керування користувачами |
| **Директор** | Повний доступ |
| **Менеджер** | Проєкти, CRM, специфікації, вироби, прайси |
| **Інженер** | Проєкти, специфікації, виробництво, вироби, перегляд налаштувань |
| **Майстер** | Проєкти (перегляд), специфікації, виробництво |
| **Бухгалтер** | Проєкти, CRM, прайси |
| **Монтажник** | Проєкти, специфікації, виробництво (перегляд) |
| **Перегляд** | Тільки читання |

---

## ⚙️ Вкладка «Налаштування»

- 🏢 **Компанія** — реквізити, контакти, підписи, логотип
- 🗄️ **База даних** — статус PostgreSQL, тест з'єднання, статистика
- 🎨 **Тема** — оформлення (Catppuccin Mocha / Light)
- 💼 **Бізнес** — ПДВ, ціни на комплектуючі та ізоляцію, посади/ставки (тільки admin/director)
- 👥 **Користувачі** — CRUD користувачів (тільки admin/director)
- 💾 **Бекап** — pg_dump/psql, автобекап, відновлення
- ℹ️ **Система** — версії, статистика БД, шляхи

Бізнес-параметри (ПДВ, комплектуючі, посади, ціни фланців) зберігаються у `data/business_settings.json` (сервіс `services/business_settings.py`); ціни матеріалів — у `data/pricing_settings.json`.

---

## 🗄️ База даних

PostgreSQL, 32 таблиці (перевірено запитом до БД):

| Домен | Таблиці |
|-------|---------|
| Користувачі та аудит | `users`, `audit_logs` |
| Проєкти | `projects`, `project_products`, `project_components`, `project_materials`, `project_works`, `project_expenses`, `project_documents`, `payments` |
| Клієнти (CRM) | `clients`, `interactions`, `client_projects`, `warranty_reminders` |
| Вироби та каталоги | `product_types`, `product_subtypes`, `subtype_materials`, `size_ranges`, `product_items`, `standard_products_library`, `works_catalog` |
| Розрахунки | `calculations`, `calc_calculations`, `calc_items`, `calc_templates` |
| Матеріали та ціноутворення | `calc_materials`, `material_prices`, `calc_settings` |
| Виробництво | `overhead_items`, `employees`, `specifications`, `cutting_plans` |

Підключення — ліниве: engine створюється при першому зверненні (`database/db.py`, аксесори `get_session_local()` / `get_engine()`), а не на імпорті модуля. Неналаштований `DATABASE_URL` дає зрозумілу помилку з інструкцією.

---

## 🛠️ Розробка

### Структура проєкту

```
TverdukVentCompany2V/
├── main_pyside6.py                 # Точка входу (міграції → GUI)
├── requirements.txt                # Основні залежності
├── requirements-dev.txt            # pytest, ruff, black
├── requirements-optional.txt       # Опційні (3D, AutoCAD, вебв'ю)
├── pyproject.toml                  # Конфіг ruff/black
├── .github/workflows/ci.yml        # CI: ruff + black + pytest
├── migrations/                     # Alembic-міграції (head: 008)
├── data/                           # Локальні дані (business_settings.json, бекапи)
├── ventilation_company/
│   ├── auth/                       # Автентифікація, ролі, дозволи
│   ├── database/
│   │   ├── db.py                   # Ліниве підключення, пул з'єднань
│   │   ├── models/                 # ORM-моделі (12 модулів)
│   │   └── repositories/           # Репозиторії (get_db / ліниві синглтони)
│   ├── services/                   # Бізнес-логіка (17 сервісів)
│   ├── gui_pyside6/                # PySide6 GUI (~30 модулів)
│   ├── project3d/                  # 3D-геометрія, конвертери, прев'ю
│   └── utils/                      # Бекапи, допоміжні функції
└── tests/                          # 95 тестів (unit + integration)
```

### Якості гейт

```bash
ruff check .        # лінтер
black --check .     # форматування
pytest -q           # тести (PostgreSQL не потрібен — фейки/патчі)
```

Усі три перевірки гоняються в CI на Python 3.13 (windows-latest) при кожному пуші в `main`.

---

## 📄 Ліцензія

MIT License © Pelekanchik

---

## 📞 Контакти

- **Автор:** Pelekanchik
- **Репозиторій:** https://github.com/Pelekanchik/TverdukVentCompany2V
