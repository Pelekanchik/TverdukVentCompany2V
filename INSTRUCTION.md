# 🐘 VentCompany — Інструкція по запуску з PostgreSQL

## 1. Швидкий старт (Docker)

```bash
# 1. Запусти PostgreSQL
docker-compose up -d

# 2. Зачекай 10 секунд, поки БД підніметься

# 3. Запусти програму
python main.py
```

## 2. Ручний старт (якщо PostgreSQL вже встановлено)

### 2.1. Створи базу даних

```sql
CREATE DATABASE ventcompany;
CREATE USER vent WITH PASSWORD 'vent123';
GRANT ALL PRIVILEGES ON DATABASE ventcompany TO vent;
```

### 2.2. Налаштуй `.env`

```env
DATABASE_URL=postgresql://ТВІЙ_КОРИСТУВАЧ:ТВІЙ_ПАРОЛЬ@localhost:5432/ventcompany
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_FULL_NAME=Адміністратор
```

### 2.3. Встанови залежності

```bash
pip install -r requirements.txt
```

### 2.4. Запусти setup

```bash
python setup_postgres.py
```

Це створить:
- `.env`
- `alembic.ini`
- `migrations/env.py`
- `migrations/README`
- `migrations/versions/001_initial.py`

### 2.5. Перевір Alembic

```bash
# Має показати: 001 (head)
alembic current

# Має показати історію
alembic history --verbose
```

### 2.6. Запусти програму

```bash
python main.py
```

## 3. Як створити нову міграцію

Коли зміниш моделі (додав колонку, таблицю):

```bash
# Автоматично згенерувати міграцію
alembic revision --autogenerate -m "додав поле email до клієнтів"

# Застосувати
alembic upgrade head
```

## 4. Типові помилки

### "Can't locate revision identified by 'head'"

**Причина:** папка `migrations/versions/` порожня.

**Рішення:**
```bash
alembic revision -m "initial"
alembic upgrade head
```

### "connection refused"

**Причина:** PostgreSQL не запущено.

**Рішення:**
```bash
# Windows — Services → postgresql-x64-16 → Start
# Або через Docker:
docker-compose up -d
```

### "alembic: command not found"

**Причина:** alembic не встановлено в поточному venv.

**Рішення:**
```bash
pip install alembic
# Або викликай через Python:
python -m alembic upgrade head
```

## 5. Структура файлів (що замінити)

| Файл | Дія |
|------|-----|
| `main.py` | Замінити повністю |
| `setup_postgres.py` | Замінити повністю |
| `migrations/README` | Створити (якщо немає) |
| `migrations/versions/001_initial.py` | Створити (якщо немає) |
| `docker-compose.yml` | Створити (опціонально) |
| `.env` | Перевірити/оновити |

## 6. Чек-лист перед запуском

- [ ] PostgreSQL запущено і доступний
- [ ] База `ventcompany` створена
- [ ] `.env` налаштований з правильним `DATABASE_URL`
- [ ] `migrations/versions/001_initial.py` існує
- [ ] `alembic current` показує `001`
- [ ] `pip install -r requirements.txt` виконано
