# Міграції бази даних VentCompany

## Команди

### Створити нову міграцію (автоматично з моделей)
```bash
python create_migration.py "опис змін"
# або
alembic revision --autogenerate -m "опис змін"
```

### Застосувати міграції
```bash
python apply_migration.py
# або
alembic upgrade head
```

### Відкотити останню міграцію
```bash
alembic downgrade -1
```

### Переглянути історію
```bash
alembic history --verbose
```

### Перевірити поточну версію
```bash
alembic current
```

## Структура

- `migrations/versions/` — файли міграцій
- `migrations/env.py` — конфігурація Alembic
- `alembic.ini` — налаштування підключення

## Примітки

- Початкова міграція (`{revision_id}_initial`) використовує `Base.metadata.create_all()`
  для створення всіх таблиць з поточних ORM-моделей.
- Наступні міграції генеруються автоматично через `--autogenerate`.
- Для SQLite використовується `render_as_batch=True` (див. `env.py`).
