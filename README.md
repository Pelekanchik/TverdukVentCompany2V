# 🏭 VentCompany v2.0

**Система управління вентиляційними проєктами**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![PySide6](https://img.shields.io/badge/PySide6-6.5%2B-green)](https://wiki.qt.io/Qt_for_Python)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-blue)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Опис

VentCompany — це desktop-додаток для автоматизації роботи вентиляційної компанії. Програма дозволяє:

- 🏗️ Проєктувати вентиляційні системи (3D-моделі, специфікації, розкрій)
- 💰 Розраховувати собівартість, ціни та прибуток
- 📊 Вести CRM, керувати клієнтами та замовленнями
- 🏭 Контролювати виробництво та відвантаження
- 📄 Генерувати документи (кошториси, рахунки, накладні)
- ⚙️ Налаштовувати реквізити компанії, тему, бекапи

---

## 🖥️ Технології

| Компонент | Технологія |
|-----------|------------|
| GUI | PySide6 (Qt6) |
| Тема | Catppuccin Mocha (темна) / Light (світла) |
| База даних | PostgreSQL 14+ (основна) / SQLite (резерв) |
| ORM | SQLAlchemy 2.0 |
| Міграції | Alembic |
| 3D | PyVista / VTK |
| Експорт | pandas, openpyxl, reportlab |

---

## 🚀 Встановлення

### 1. Клонування репозиторію

```bash
git clone https://github.com/Pelekanchik/TverdukVentCompany2V.git
cd TverdukVentCompany2V
```

### 2. Віртуальне середовище

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Залежності

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
PySide6>=6.5.0
SQLAlchemy>=2.0.0
psycopg[binary]>=3.1.0
alembic>=1.12.0
pandas>=2.0.0
openpyxl>=3.1.0
reportlab>=4.0.0
pyvista>=0.42.0
vtk>=9.3.0
```

### 4. Налаштування PostgreSQL

Створи файл `.env` у корені проєкту:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/ventcompany
```

Або відредагуй `ventilation_company/config.py`.

### 5. Запуск

```bash
python main_pyside6.py
```

---

## 🎨 Структура інтерфейсу

```
┌─────────────────────────────────────────────┐
│  VentCompany — Адміністратор (director)     │
├──────────┬──────────────────────────────────┤
│          │  📊 Дашборд                      │
│  🏭      │  📁 Проєкти                      │
│ Vent     │  🛠️ Вироби                       │
│ Company  │  📋 Специфікація                 │
│          │  ✂️ Розкрій                      │
├──────────┤  💰 Ціноутворення                │
│  РОБОТА  │  📝 Документи                    │
│  📊      ├──────────────────────────────────┤
│  Дашборд │  💨 Аеродинаміка                 │
│  📁      │  📦 Матеріали                    │
│  Проєкти │  🏭 Виробництво                  │
│  🛠️      ├──────────────────────────────────┤
│  Вироби  │  📊 Аналітика                    │
│  📋      │  👥 CRM                          │
│  Специф. │                                  │
│  ✂️      ├──────────────────────────────────┤
│  Розкрій │  ⚙️ Налаштування                 │
│          │  👤 Кабінет                      │
│  ФІНАНСИ │  🚪 Вихід                        │
│  💰      │                                  │
│  Ціни    └──────────────────────────────────┘
│  📝      
│  Докум.  
├──────────┤
│  АНАЛІТ. │
│  📊 CRM  │
├──────────┤
│  ⚙️ Нал. │
│  👤 Каб. │
│  🚪 Вих. │
└──────────┘
```

---

## 👥 Ролі користувачів

| Роль | Доступ |
|------|--------|
| **Адміністратор** | Повний доступ + керування користувачами |
| **Директор** | Повний доступ |
| **Менеджер** | Проєкти, клієнти, ціни, прайси, CRM |
| **Інженер** | Розкрій, специфікації, 3D-моделі, розрахунки |
| **Майстер** | Виробництво, статуси, відвантаження |
| **Бухгалтер** | Собівартість, прибуток, звіти, зарплати |
| **Перегляд** | Тільки читання |

---

## ⚙️ Вкладка "Налаштування"

Нова вкладка з 6 під-вкладками:

- 🏢 **Компанія** — реквізити, контакти, підписи, логотип
- 🗄️ **База даних** — статус PostgreSQL, тест з'єднання, статистика, `create_all`
- 🎨 **Тема** — збереження налаштування оформлення (Catppuccin Mocha / Light)
- 👥 **Користувачі** — CRUD користувачів (тільки admin/director)
- 💾 **Бекап** — pg_dump/psql, автобекап, відновлення, очищення старих
- ℹ️ **Система** — версії, статистика БД, шляхи

---

## 🗄️ База даних

### PostgreSQL (основна)

```
postgresql://user:password@localhost:5432/ventcompany
```

### Таблиці

- `users` — користувачі
- `projects` — проєкти
- `project_products` — вироби проєкту
- `clients` — клієнти (CRM)
- `calc_settings` — налаштування програми (key-value)
- `calc_calculations` — розрахунки
- `metal_prices` — ціни на метал
- `specifications` — специфікації
- `cutting_patterns` — розкрій
- `production_orders` — виробничі замовлення

---

## 🛠️ Розробка

### Структура проєкту

```
TverdukVentCompany2V/
├── main_pyside6.py                 # Точка входу
├── requirements.txt
├── .env                            # Налаштування БД
├── data/                           # Локальні дані, бекапи
├── ventilation_company/
│   ├── __init__.py
│   ├── config.py                   # Конфігурація
│   ├── database/
│   │   ├── db.py                   # Підключення до БД
│   │   ├── base.py                 # Base SQLAlchemy
│   │   ├── models/                 # ORM-моделі
│   │   │   ├── user.py
│   │   │   ├── project.py
│   │   │   ├── calc.py
│   │   │   └── ...
│   │   └── repositories/           # Репозиторії
│   ├── auth/
│   │   ├── service.py              # Сервіс авторизації
│   │   └── permissions.py          # Ролі та дозволи
│   ├── services/
│   │   └── auth_service.py         # AuthUser, сесії
│   ├── gui_pyside6/                # PySide6 GUI
│   │   ├── __init__.py
│   │   ├── main_window.py          # Головне вікно
│   │   ├── sidebar.py              # Бічна панель
│   │   ├── login_dialog.py         # Вікно логіну
│   │   ├── theme.py                # Catppuccin Mocha QSS
│   │   ├── program_settings_tab.py # ⚙️ Налаштування
│   │   ├── dashboard_tab.py
│   │   ├── projects_tab.py
│   │   ├── products_tab.py
│   │   ├── specification_tab.py
│   │   ├── cutting_tab.py
│   │   ├── pricing_tab.py
│   │   ├── documents_tab.py
│   │   ├── crm_tab.py
│   │   └── cabinet_tab.py
│   ├── utils/
│   │   └── backup.py               # Резервне копіювання
│   └── alembic/                    # Міграції
└── tests/
```

---

## 📄 Ліцензія

MIT License © Pelekanchik

---

## 📞 Контакти

- **Автор:** Pelekanchik
- **Репозиторій:** https://github.com/Pelekanchik/TverdukVentCompany2V
