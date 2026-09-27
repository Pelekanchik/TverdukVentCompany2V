# План модернізації VentCompany

Дата аудиту: 2026-09-27. Версія коду: 2.7.0 (git HEAD `9761ac4`).

## Стан на момент аудиту (перевірено на ноутбуці)

| Перевірка | Результат |
|---|---|
| Python | 3.13.13 (venv створено в проєкті) |
| Залежності | встановлено з `requirements.txt`, конфліктів немає |
| PostgreSQL 16 | служба запущена, БД `ventcompany` на міграції `008 (head)` |
| Тести | **71/71 passed** (2.66 с) |
| Старт GUI | headless-smoke: LoginDialog + MainWindow (admin) будуються без помилок |
| Дані в БД | 2 проєкти, 1 клієнт, 0 виробів — система у ранньому використанні |
| Синтаксис | `compileall` по всьому пакету — чисто |

## Підтверджені проблеми (з першого огляду + аудиту)

1. **Сміття в репозиторії**: файли-«привиди» `tyle: enable ruff UP rules"` і `tyle: enable ruff bugbear rules"` (обрізані назви комітів, всередині — дифи), `ventcompany_salary_fix.patch`, бінарник `updates/VentCompany-windows.zip`, `spec_*.xlsx`, демо-CSV у `exports/`.
2. **Мертві точки входу**: `main.py`, `run_gui.py`, `launch_gui.py` (останні два ідентичні), `demo_stage3.py`, `demo_stage4.py`, `create_tables.py`, `add_user.py` (напівдублі функціоналу).
3. **`legacy/`** (~21 000 рядків старого GUI) — не підтримується, але залишається в репозиторії; наразі ісключений з ruff/black, що маскує розклад.
4. **Хардкод бізнес-даних** у `ventilation_company/config.py`: ціни на метал/компоненти, ставки зарплат (`MIN_WAGE = 8000` — явно застаріло), дублюються з `ventilation_company/data/*.json`.
5. **Розсинхрон залежностей**: `requirements.txt` ≠ `pyproject.toml`; дубль драйверів `psycopg2-binary` + `psycopg[binary]`; важкі опційні пакети (`pyautocad`, `pywebview`, 3D) у core-залежностях.
6. **Side-effect на імпорті**: `database/db.py` створює engine при імпорті; дефолтний `DATABASE_URL` — заглушка `CHANGE_ME`.
7. **Файл-опечатка**: `ventilation_company/database/models/__init___.py` (двійне підкреслення) поруч із `__init__.py`.
8. **Невідповідність документації**: README описує таблиці `production_orders`, `specifications` — у реальній схемі їх немає (перевірено запитом).
9. Дублювання шарів моделей: `ventilation_company/models/` поруч із `ventilation_company/database/models/`.

## Фаза 1 — Гігієна репозиторія ✅ (виконано 2026-09-27, коміт `21656f2`)

- Видалити сміттєві файли з кореня; `exports/*.csv` — у `.gitignore` (залишити як приклади через `products_template.csv`).
- Звести запуск до однієї точки входу: лишити `main_pyside6.py` (він уже робить міграції → `launch_gui`), решту лаунчерів і демо — видалити.
- Вирішити долю `legacy/`: запропонувати винести в окремий архівний репозиторій або гілку `archive/legacy`, з основної гілки — видалити.
- Видалити `__init___.py`-опечатку після перевірки, що він не імпортується.
- Синхронізувати `requirements.txt` ↔ `pyproject.toml`: лишити один драйвер (`psycopg[binary]`), винести `pyautocad`/`pywebview`/3D у `requirements-optional.txt` з graceful-degradation у коді.
- Оновити `.gitignore` (`venv/`, `data/`, `*.zip` у `updates/`, `__pycache__`).

## Фаза 2 — Конфігурація і бізнес-дані ✅ (виконано 2026-09-27)

Зроблено:
- Новий сервіс `services/business_settings.py` (патерн PricingSettings): ПДВ, комплектуючі,
  додаткові матеріали (ізоляція), посади/ставки → `data/business_settings.json`, атомарний запис.
- Листовий метал у `material_order.py` тепер береться з `PricingSettings.material_prices`
  (замість плоского хардкоду; невідомий матеріал → ціна 0, як і раніше).
- `pricing.py` — ПДВ з BusinessSettings; `salary_calculator.py` — посади з BusinessSettings.
- `config.py` скорочено з 83 до ~30 рядків: лише шляхи + VENTILATION_TYPES.
- Видалено мертві константи без споживачів: MARKUP_PERCENTAGE, OVERHEAD_PERCENTAGE,
  MIN_WAGE, WORKING_HOURS_PER_MONTH, WORKS.
- Додано `tests/unit/test_business_settings.py` (+8 тестів), усього 79/79 зелених, ruff чисто.

Не зроблено (наступний крок): редактор цих налаштувань у GUI (зараз файл можна правити руками).

## Фаза 3 — Архітектура і стійкість (2–4 дні)

- Завершити винесення довгих операцій у `gui_pyside6/workers.py` (QThread), аудит великих вкладок (`project_card_dialog.py` 899 р., `product_dialog.py` 860 р.).
- Консолідація моделей: один каталог `database/models/`, перехідники — прибрати.
- CI (GitHub Actions): `ruff check`, `pytest` на SQLite-фікстурах, збірка PyInstaller-артефакту.
- Типізація: підняти coverage mypy на сервісному шарі поступово.

## Фаза 4 — Документація і релізна гігієна (1 день)

- README: реальна схема БД, одна інструкція запуску, актуальні ролі.
- `docs/USER_GUIDE.md` — звірити з реальними вкладками.
- Changelog на основі історії комітів.

## Порядок виконання та критерії

Кожна фаза — окремий коміт/PR, після кожної: `pytest` зелений + smoke-старт GUI. Фази 1–2 не змінюють поведінку програми (рефакторинг + дані), безпечні для робочої БД; фаза 3 зачіпає GUI — зміни застосовувати ітераційно з твоїм тестуванням вручну.

## Ризики

- Видалення `legacy/` незворотне — перед тим зробити тег `v2.7.0-pre-cleanup`.
- Перенесення цін/ставок у БД вимагає міграції початкових значень (009_seed_settings).
- PySide6 у venv — 6.11.2, програма цільована на ≥6.5: сумісність підтверджено smoke-тестом, але повне тестування GUI — вручну.
