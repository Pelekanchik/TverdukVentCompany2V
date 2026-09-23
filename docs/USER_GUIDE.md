# VentCompany — User Guide

## 1. Встановлення

### Локальний запуск з source

1. Встановити Python 3.10+.
2. Встановити PostgreSQL.
3. Створити БД `ventcompany`.
4. У корені проєкту створити `.env` на основі `.env.example`:

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
4. Потім можна натиснути **Встановити оновлення зараз** у frozen-збірці.

### Ручне оновлення

1. Завантажте `VentCompany-windows.zip` із Releases.
2. Розпакуйте.
3. Замініть файли застосунку.
4. Збережіть свій `.env`.

---

## 4. Backup / Restore

### Створення backup

У програмі:

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

## 5. CRM

### Клієнти

- додавання;
- редагування;
- видалення;
- пошук;
- фільтр за статусом.

### Історія клієнта

Для обраного клієнта:

```text
📜 Історія
```

Можна вести:

- взаємодії;
- оплати;
- наступні дії.

### Картка клієнта

```text
🪪 Картка
```

Показує:

- контакти;
- статус;
- останні взаємодії;
- останні оплати;
- найближчу дію.

### Dashboard

```text
📊 Dashboard
```

Показує:

- кількість клієнтів;
- активних/потенційних;
- оплати;
- майбутні дії.

---

## 6. Вироби

### CSV export

```text
Вироби → 💾 Експорт CSV
```

### CSV import

```text
Вироби → 📥 Імпорт CSV
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

## 7. Audit Log

```text
Налаштування → Користувачі → 📜 Audit Log
```

Можна фільтрувати за:

- користувачем;
- action;
- entity;
- датою.

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

## 8. Безпека

- Після кількох невдалих login спроб акаунт тимчасово блокується.
- Не коміть `.env`.
- Не коміть `data/`, `logs/`, `documents/`, `dist/`, `build/`, `release/`.

---

## 9. Типові проблеми

### Програма не стартує

Перевірте:

- PostgreSQL запущено;
- `.env` коректний;
- `alembic upgrade head` пройшов успішно;
- у `logs\ventcompany_error.log` немає traceback.

### Немає вікна після login

- перевірте, чи не закритий застосунок вручну;
- відкрийте через `Alt + Tab`.

### Оновлення не з’являється

- перевірте `ventilation_company/version.py`;
- якщо поточна версія = останньому Release, діалог не з’явиться.

---

## 10. Для розробника

Корисні команди:

```bat
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m black --check .
.venv\Scripts\python -m pytest -q
scripts\build_installer.bat
scripts\package_release.bat 1.4.0
```
