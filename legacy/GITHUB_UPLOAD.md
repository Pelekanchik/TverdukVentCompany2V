# 📤 Інструкція — залити оновлення на GitHub

## 1. Застосуй патч локально

```bash
cd C:\Users\Admin\Desktop\TverdukVentCompany2V
python apply_patch.py
```

Або вручну скопіюй файли:
- `gui_pyside6/program_settings_tab.py` → `ventilation_company/gui_pyside6/`
- `gui_pyside6/__init__.py` → `ventilation_company/gui_pyside6/`
- `auth/permissions.py` → `ventilation_company/auth/`

## 2. Перевір, що main_window.py має settings

Відкрий `ventilation_company/gui_pyside6/main_window.py` і переконайся, що у `self.tabs` є:

```python
"settings": ProgramSettingsTab(current_user=self.user),
```

## 3. Запусти і перевір

```bash
python main_pyside6.py
```

## 4. Коміт і пуш на GitHub

```bash
git add .
git commit -m "feat: додано вкладку Налаштування (PySide6)"
git push origin main
```

## 5. Що змінилося (для опису релізу)

- ✅ Нова вкладка **⚙️ Налаштування** з 6 під-вкладками
- ✅ 🏢 Компанія — реквізити, контакти, підписи, логотип
- ✅ 🗄️ База даних — статус PostgreSQL, тест з'єднання, статистика
- ✅ 🎨 Тема — збереження налаштування оформлення
- ✅ 👥 Користувачі — CRUD користувачів (тільки admin/director)
- ✅ 💾 Бекап — pg_dump/psql, автобекап, відновлення
- ✅ ℹ️ Система — версії, статистика БД, шляхи
- ✅ Пароль у DATABASEURL замасковано
- ✅ Інтеграція з Catppuccin Mocha (через Theme)
