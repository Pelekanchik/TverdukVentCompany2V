# VentCompany — User Guide

## 1. Встановлення

### Локальний запуск з source

1. Встановити Python 3.10+.
2. Встановити PostgreSQL.
3. Створити БД `ventcompany`.
4. Створити `.env` на основі `.env.example`:

```env
DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/ventcompany
ADMIN_USERNAME=admin
ADMIN_PASSWORD=
```

5. Створити venv і встановити залежності:

```bat
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
```

6. Запустити міграції:

```bat
.venv\Scripts\python -m alembic upgrade head
```

7. Запустити застосунок:

```bat
scripts\run_app.bat
```

---

## 2. Перший запуск

- Відкриється вікно логіна.
- Якщо `ADMIN_PASSWORD=` у `.env` порожній, пароль admin генерується автоматично.
- Згенерований пароль може бути збережений локально в:

```text
data\.setup_credentials.json
```

- Після першого входу цей файл бажано видалити.

---

## 3. Оновлення програми

### Автоматичне оновлення

Якщо доступна нова версія:

1. З’явиться діалог оновлення.
2. Натисніть **Завантажити**.
3. Після завантаження натисніть **Розпакувати**.
4. У frozen-збірці можна натиснути **Встановити оновлення зараз**.

Програма:

- завантажить ZIP;
- перевірить його;
- розпакує;
- створить backup;
- замінить файли;
- запустить нову версію.

### Ручне оновлення

1. Завантажте `VentCompany-windows.zip` із Releases.
2. Розпакуйте.
3. Замініть файли застосунку.
4. Збережіть свій `.env`.

---

## 4. Backup / Restore

### Створення backup

```text
Налаштування → Бекап → Створити бекап зараз
```

Для PostgreSQL backup створюється через `pg_dump`.

### Restore

1. Оберіть backup.
2. Натисніть **Відновити**.
3. Підтвердіть дію.
4. Перезапустіть програму.

⚠️ Restore може перезаписати поточні дані.

---

## 5. Проєкти

### Основні можливості

- створення проєкту;
- редагування;
- видалення;
- пошук;
- картка проєкту;
- документи по проєкту;
- audit подій `project.*`.

Видалення проєкту також видаляє пов’язані вироби та документи.

---

## 6. Вироби

### Додавання / редагування

- додавання виробу;
- редагування;
- видалення;
- копіювання;
- розрахунок ціни;
- попередження про дублікати.

### CSV export

```text
Вироби → 💾 Експорт CSV
```

### CSV import

```text
Вироби → 📥 Імпорт CSV
```

### Шаблон CSV

```text
Вироби → 📄 Шаблон CSV
```

Підтримувані колонки:

- `name`
- `product_type`
- `width`
- `height`
- `length`
- `thickness`
- `material`
- `quantity`
- `cost_price`
- `unit_price`
- `total_price`
- `discounted_price`
- `notes`

---

## 7. CRM

### Клієнти

- додавання;
- редагування;
- видалення;
- пошук;
- фільтр за статусом;
- попередження про дублікати.

### Картка клієнта

```text
🪪 Картка
```

У картці можна редагувати:

- назву;
- контактну особу;
- телефон;
- email;
- адресу;
- статус;
- нотатки.

### Історія клієнта

```text
📜 Історія
```

Можна вести:

- взаємодії;
- оплати;
- наступні дії;
- додавати, редагувати, видаляти записи.

### CRM Dashboard

```text
📊 Dashboard
```

Показує:

- кількість клієнтів;
- активних/потенційних;
- взаємодії;
- оплати;
- майбутні дії.

Експорт CSV включає:

- `clients.csv`
- `interactions.csv`
- `payments.csv`
- `upcoming_actions.csv`

---

## 8. Audit Log

```text
Налаштування → Користувачі → 📜 Audit Log
```

Фільтри:

- користувач;
- action;
- entity;
- дата.

Корисні action:

- `auth.login`
- `auth.login_failed`
- `user.create`
- `user.update`
- `user.delete`
- `project.create`
- `project.update`
- `project.delete`
- `product.create`
- `product.update`
- `product.delete`
- `document.create`
- `document.delete`
- `backup.create`
- `backup.restore`

---

## 9. Безпека

- після кількох невдалих login спроб акаунт тимчасово блокується;
- не коміть `.env`;
- не коміть `data/`, `logs/`, `documents/`, `dist/`, `build/`, `release/`.

---

## 10. Типові проблеми

### Програма не стартує

Перевірте:

- PostgreSQL запущено;
- `.env` коректний;
- `alembic upgrade head` пройшов успішно;
- у `logs\ventcompany_error.log` немає traceback.

### Оновлення не з’являється

- перевірте `ventilation_company/version.py`;
- якщо поточна версія = останньому Release, діалог не з’явиться.

### Audit Log не відкривається

- перевірте `logs\ventcompany_error.log`;
- переконайтеся, що застосовано останні repository fixes.

---

## 11. Для розробника

```bat
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m black --check .
.venv\Scripts\python -m pytest -q
scripts\build_installer.bat
scripts\package_release.bat 1.9.0
```
