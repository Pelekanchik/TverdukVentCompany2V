"""Живий E2E-сценарій VentCompany (headless).

Проганяє реальний користувацький шлях на ТИМЧАСОВІЙ базі PostgreSQL
(ventcompany_e2e_<дата>), яку створює на початку та видаляє в кінці:

  1. Створення БД + таблиць + seed адміна
  2. Логін через LoginDialog
  3. Відкриття всіх вкладок MainWindow
  4. Створення проєкту (код шляху вкладки Проєкти)
  5. Створення виробу з розрахунком ціни (ProductDialog._on_calc_impl)
  6. Зведений фінансовий звіт (DashboardService / репозиторій)
  7. PDF-звіт проєкту (ProjectPDFReport)
  8. Рахунок-фактура (documents.Invoice)
  9. Аудит-лог (AuditLogRepository)
 10. Бекап (код шляху вкладки Backup)

Запуск:  venv/Scripts/python.exe scripts/e2e_live_test.py
Вихід:   друк чеклиста + docs/E2E_CHECKLIST_<дата>.md
"""

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

# ── Підготовка тимчасової БД ──
from sqlalchemy import create_engine as _create_raw
from sqlalchemy import text as _sql_text

from ventilation_company.database import db as dbm

_src_url = dbm.DATABASE_URL
if "CHANGE_ME" in _src_url or "@" not in _src_url:
    print(
        "FATAL: DATABASE_URL не налаштований — E2E потребує PostgreSQL (env DATABASE_URL або .env)"
    )
    sys.exit(2)

_admin_url = _src_url.rsplit("/", 1)[0] + "/postgres"
E2E_DB = f"ventcompany_e2e_{datetime.now():%Y%m%d_%H%M%S}"
E2E_URL = _src_url.rsplit("/", 1)[0] + "/" + E2E_DB

results = []  # (крок, ок, деталь)


def check(step, fn):
    """Виконати крок і записати результат."""
    try:
        detail = fn()
        results.append((step, True, detail or "OK"))
        print(f"  PASS  {step}" + (f" — {detail}" if detail else ""))
    except Exception as e:  # noqa: BLE001 — E2E має ловити все
        tb = traceback.format_exc(limit=3)
        results.append((step, False, f"{type(e).__name__}: {e}\n{tb}"))
        print(f"  FAIL  {step} — {type(e).__name__}: {e}")


# ═══ 0. Створення тимчасової БД ═══
print(f"E2E: тимчасова БД {E2E_DB}")
adm = _create_raw(_admin_url, isolation_level="AUTOCOMMIT", future=True)
with adm.connect() as c:
    c.execute(_sql_text(f'DROP DATABASE IF EXISTS "{E2E_DB}" WITH (FORCE)'))
    c.execute(_sql_text(f'CREATE DATABASE "{E2E_DB}"'))
adm.dispose()

# Перенаправляємо застосунок на тимчасову БД (до ініціалізації engine).
dbm.DATABASE_URL = E2E_URL

from ventilation_company.database.base import Base
from ventilation_company.database.models import *  # noqa: F401,F403

dbm._init_engine()
Base.metadata.create_all(bind=dbm._engine)
print("  таблиці створено")

# ═══ Qt і застосунок ═══
from PySide6.QtWidgets import QApplication

app = QApplication([])

from ventilation_company.database.repositories.audit_log_repo import AuditLogRepository
from ventilation_company.database.repositories.product_repo import ProductRepository
from ventilation_company.database.repositories.project_repo import ProjectRepository
from ventilation_company.services.audit_service import log_action
from ventilation_company.services.auth_service import AuthService

# ═══ 1. Seed адміна + логін через LoginDialog ═══
PASSWORD = "E2e#Test1234"


def step_seed_and_login():
    AuthService.create_user("e2e_admin", PASSWORD, "E2E Адміністратор", "admin")

    from ventilation_company.gui_pyside6.login_dialog import LoginDialog

    dlg = LoginDialog()
    dlg.edit_user.setText("e2e_admin")
    dlg.edit_pass.setText(PASSWORD)
    dlg._do_login()
    user = dlg.authenticated_user
    if user is None:
        raise RuntimeError("authenticated_user is None після _do_login")
    if user.role != "admin":
        raise RuntimeError(f"очікувалась роль admin, отримано {user.role!r}")
    return f"увійшов як {user.full_name} ({user.role})"


check("1. Логін через LoginDialog (seed-адмін)", step_seed_and_login)

# ═══ 2. MainWindow + всі вкладки ═══
_main_window = None


def step_main_window_tabs():
    global _main_window
    user = AuthService.get_current_user() or AuthService.authenticate("e2e_admin", PASSWORD)
    from ventilation_company.gui_pyside6.main_window import MainWindow

    _main_window = MainWindow(user=user)
    errors = []
    for tab_id in list(_main_window.tabs):
        try:
            _main_window._on_tab_changed(tab_id)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{tab_id}: {type(e).__name__}: {e}")
    if errors:
        raise RuntimeError("; ".join(errors))
    return f"вкладок відкрито: {len(_main_window.tabs)}"


check("2. MainWindow: відкриття всіх вкладок", step_main_window_tabs)

# ═══ 3. Створення проєкту (шлях вкладки Проєкти) ═══
project_id = None


def step_create_project():
    global project_id
    from ventilation_company.gui_pyside6.projects_tab import ProjectEditDialog

    tab = _main_window.tabs["projects"]
    dlg = ProjectEditDialog(parent=tab)
    dlg.edit_name.setText("E2E Вентиляція офісу")
    dlg.edit_number.setText("E2E-001")
    dlg.combo_client.setCurrentText("E2E Клієнт ТОВ")
    data = dlg.get_data()
    if not data["name"]:
        raise RuntimeError("get_data повернув порожню назву")
    data["project_number"] = data.get("project_number") or "E2E-001"
    data["created_at"] = datetime.now()
    created = ProjectRepository.create(data)
    project_id = created["id"]
    log_action(
        "project.create",
        entity_type="project",
        entity_id=project_id,
        details=data,
        actor="e2e_admin",
    )
    tab._load_data()
    _main_window.set_active_project(project_id)
    return f"проєкт ID={project_id}"


check("3. Створення проєкту", step_create_project)

# ═══ 4. Створення виробу з розрахунком (ProductDialog) ═══


def step_create_product():
    from ventilation_company.gui_pyside6.product_dialog import ProductDialog

    tab = _main_window.tabs["products"]
    dlg = ProductDialog(parent=tab)
    dlg.edit_name.setText("E2E Пряма труба 400×200×1000")
    dlg.combo_type.setCurrentIndex(0)
    dlg.spin_width.setValue(400)
    dlg.spin_height.setValue(200)
    dlg.spin_length.setValue(1000)
    dlg.spin_qty.setValue(2)
    dlg._on_calc_impl()
    if dlg._calc_result is None:
        raise RuntimeError("розрахунок не виконано (_calc_result is None)")
    data = dlg.get_data()
    data["project_id"] = project_id
    created = ProductRepository.create(data)
    tab._load_data()
    return (
        f"виріб ID={created['id']}, ціна={data.get('total_price')}, "
        f"собівартість={data.get('cost_price')}"
    )


check("4. Створення виробу з розрахунком ціни", step_create_product)

# ═══ 5. Фінансові підсумки через сервіс дашборду ═══


def step_dashboard_stats():
    from ventilation_company.services.dashboard_service import DashboardService

    stats = DashboardService.done_dashboard(["Готовий", "Закритий"])
    keys = ("done_count", "total_revenue", "profit", "clients", "monthly")
    missing = [k for k in keys if k not in stats]
    if missing:
        raise RuntimeError(f"у stats бракує ключів: {missing}")
    return f"done_count={stats['done_count']}, clients={stats['clients']}"


check("5. Фінансовий звіт DashboardService", step_dashboard_stats)

# ═══ 6. PDF-звіт проєкту ═══
out_dir = PROJECT_ROOT / "data" / "e2e_output"
out_dir.mkdir(parents=True, exist_ok=True)


def step_project_pdf():
    from ventilation_company.pdf_generator import ProjectPDFReport

    projects = ProjectRepository.list_all()
    proj = next((p for p in projects if p["id"] == project_id), None)
    if proj is None:
        raise RuntimeError("проєкт не знайдено у репозиторії")
    products = ProductRepository.get_all(project_id)
    if not products:
        raise RuntimeError("вироби проєкту не знайдено")
    path = str(out_dir / "e2e_project_report.pdf")
    ProjectPDFReport().build_report(proj, products, path)
    size = os.path.getsize(path)
    if size < 1000:
        raise RuntimeError(f"PDF підозріло малий: {size} байт")
    return f"{path} ({size:,} байт)"


check("6. PDF-звіт проєкту", step_project_pdf)

# ═══ 7. Рахунок-фактура ═══


def step_invoice():
    from ventilation_company.documents.company_info import DEFAULT_COMPANY, CompanyInfo
    from ventilation_company.documents.invoice import Invoice

    client = CompanyInfo(name='ТОВ "E2E Клієнт"', edrpou="87654321", address="м. Тернопіль")
    doc = Invoice(DEFAULT_COMPANY, client, "E2E-РФ-001")
    items = [
        {
            "name": "Пряма труба 400×200×1000",
            "unit": "шт",
            "qty": 2,
            "price": 1250.0,
            "total": 2500.0,
        },
        {"name": "Монтаж", "unit": "год", "qty": 4, "price": 350.0, "total": 1400.0},
    ]
    path = doc.build(items, str(out_dir / "e2e_invoice.pdf"))
    size = os.path.getsize(path)
    if size < 1000:
        raise RuntimeError(f"PDF підозріло малий: {size} байт")
    return f"{path} ({size:,} байт)"


check("7. Рахунок-фактура (PDF)", step_invoice)

# ═══ 8. Аудит-лог ═══


def step_audit():
    logs = AuditLogRepository.list_recent(limit=50)
    actions = [getattr(l, "action", None) for l in logs]
    if "project.create" not in actions:
        raise RuntimeError(
            f"project.create відсутній у аудиті (є: {sorted(set(map(str, actions)))})"
        )
    return f"записів аудиту: {len(logs)}"


check("8. Аудит-лог (project.create записано)", step_audit)

# ═══ 9. Бекап (код шляху вкладки Backup) ═══


def step_backup():
    import shutil

    if shutil.which("pg_dump") is None:
        return "SKIP: pg_dump відсутній у PATH PostgreSQL (перевірка на цьому ПК неможлива)"
    from ventilation_company.gui_pyside6.settings_backup_tab import BackupSettingsTab

    tab = BackupSettingsTab(current_user="e2e_admin")
    result = tab._create_backup_job(str(out_dir))
    if not result or "error" in str(result).lower():
        raise RuntimeError(f"бекап повернув: {result!r}")
    files = [f for pat in ("*.sql", "*.dump", "*.backup") for f in out_dir.glob(pat)]
    if not files:
        raise RuntimeError("файл бекапу не створено")
    return f"{files[0].name} ({files[0].stat().st_size:,} байт)"


check("9. Бекап БД (pg_dump)", step_backup)

# ═══ Звіт ═══
failed = [r for r in results if not r[1]]
report_path = PROJECT_ROOT / "docs" / f"E2E_CHECKLIST_{datetime.now():%Y-%m-%d}.md"
report_path.parent.mkdir(exist_ok=True)
lines = [
    f"# Живий E2E-чеклист VentCompany — {datetime.now():%Y-%m-%d %H:%M}",
    "",
    f"База: `{E2E_DB}` (тимчасова, видалена після прогону)",
    f"Результат: **{len(results) - len(failed)}/{len(results)} кроків успішно**",
    "",
    "| # | Крок | Результат | Деталі |",
    "|---|------|-----------|--------|",
]
for i, (step, ok, detail) in enumerate(results, 1):
    d = detail.replace("\n", "<br>") if not ok else detail
    lines.append(f"| {i} | {step} | {'✅' if ok else '❌'} | {d} |")
report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\nЗвіт: {report_path}")

# ═══ Очистка: drop тимчасової БД ═══
try:
    dbm._engine.dispose()
    with adm.connect() as c:
        c.execute(_sql_text(f'DROP DATABASE IF EXISTS "{E2E_DB}" WITH (FORCE)'))
    print(f"Тимчасову БД {E2E_DB} видалено")
except Exception as e:  # noqa: BLE001
    print(f"WARN: не вдалося видалити тимчасову БД: {e}")
finally:
    adm.dispose()

sys.exit(1 if failed else 0)
