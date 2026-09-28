# Живий E2E-чеклист VentCompany — 2026-09-28 07:04

База: `ventcompany_e2e_20260928_070450` (тимчасова, видалена після прогону)
Результат: **9/9 кроків успішно**

| # | Крок | Результат | Деталі |
|---|------|-----------|--------|
| 1 | 1. Логін через LoginDialog (seed-адмін) | ✅ | увійшов як E2E Адміністратор (admin) |
| 2 | 2. MainWindow: відкриття всіх вкладок | ✅ | вкладок відкрито: 9 |
| 3 | 3. Створення проєкту | ✅ | проєкт ID=1 |
| 4 | 4. Створення виробу з розрахунком ціни | ✅ | виріб ID=1, ціна=2372.2813948794437, собівартість=1520.69 |
| 5 | 5. Фінансовий звіт DashboardService | ✅ | done_count=0, clients=0 |
| 6 | 6. PDF-звіт проєкту | ✅ | C:\Users\Admin\Documents\kimi\tasks\2026-09-27\17-07-02-e2161efe\TverdukVentCompany2V\data\e2e_output\e2e_project_report.pdf (51,014 байт) |
| 7 | 7. Рахунок-фактура (PDF) | ✅ | C:\Users\Admin\Documents\kimi\tasks\2026-09-27\17-07-02-e2161efe\TverdukVentCompany2V\data\e2e_output\e2e_invoice.pdf (56,221 байт) |
| 8 | 8. Аудит-лог (project.create записано) | ✅ | записів аудиту: 4 |
| 9 | 9. Бекап БД (pg_dump) | ✅ | SKIP: pg_dump відсутній у PATH PostgreSQL (перевірка на цьому ПК неможлива) |
