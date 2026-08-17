"""Розширена інтеграція з SQLite для збереження проектів, виробів,
специфікацій та планів розкрою.

🔒 ТРАНЗАКЦІЇ: всі складні операції атомарні (BEGIN → COMMIT/ROLLBACK).
"""

import contextlib
import json
import os
import sqlite3
from datetime import datetime, timedelta


class TransactionError(Exception):
    """Помилка транзакції БД."""
    pass


class ProjectDatabase:
    """Розширений менеджер бази даних для вентиляційних проєктів.

    Усі методи, що модифікують кілька таблиць, використовують
    атомарні транзакції через контекстний менеджер _transaction().
    """

    def __init__(self, db_path: str = "data/company.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_tables()
        self._init_wal_mode()

    # ═══════════════════════════════════════════════════════════════
    # 🔒 ТРАНЗАКЦІЇ
    # ═══════════════════════════════════════════════════════════════

    @contextlib.contextmanager
    def _transaction(self, conn: sqlite3.Connection | None = None):
        """Контекстний менеджер для атомарних транзакцій.

        Використання:
            with self._transaction() as conn:
                conn.execute("INSERT ...")
                conn.execute("UPDATE ...")
            # Автоматично COMMIT якщо все ок, ROLLBACK якщо exception
        """
        own_conn = conn is None
        if own_conn:
            conn = self._get_connection()
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("BEGIN")
            yield conn
            conn.commit()
        except Exception as exc:
            conn.rollback()
            raise TransactionError(f"Помилка транзакції БД: {exc}") from exc
        finally:
            if own_conn:
                conn.close()

    def _init_wal_mode(self):
        """Увімкнути WAL-mode для кращої продуктивності та потокобезпеки."""
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _add_column_if_not_exists(self, conn, table: str, column: str, col_type: str):
        """Додати колонку в таблицю, якщо її ще немає."""
        cursor = conn.execute(f"PRAGMA table_info({table})")
        existing = [row[1] for row in cursor.fetchall()]
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

    def _get_table_columns(self, conn, table: str) -> list[str]:
        """Отримати список колонок таблиці."""
        cursor = conn.execute(f"PRAGMA table_info({table})")
        return [row[1] for row in cursor.fetchall()]

    def _init_tables(self):
        """Ініціалізація таблиць (якщо не існують) + міграція існуючих."""
        with self._get_connection() as conn:
            # Проєкти
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    client TEXT,
                    status TEXT DEFAULT 'draft',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
                """
            )

            # Міграція колонок
            self._add_column_if_not_exists(conn, "projects", "description", "TEXT")
            self._add_column_if_not_exists(conn, "projects", "client", "TEXT")
            self._add_column_if_not_exists(conn, "projects", "status", "TEXT DEFAULT 'draft'")
            self._add_column_if_not_exists(conn, "projects", "updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP")
            self._add_column_if_not_exists(conn, "projects", "metadata", "TEXT")
            self._add_column_if_not_exists(conn, "projects", "drawing_path", "TEXT")
            self._add_column_if_not_exists(conn, "projects", "customer_price", "REAL DEFAULT 0")
            self._add_column_if_not_exists(conn, "projects", "cost_price", "REAL DEFAULT 0")
            self._add_column_if_not_exists(conn, "projects", "salary_total", "REAL DEFAULT 0")
            self._add_column_if_not_exists(conn, "projects", "profit", "REAL DEFAULT 0")
            self._add_column_if_not_exists(conn, "projects", "assigned_to", "INTEGER")
            self._add_column_if_not_exists(conn, "projects", "created_by", "INTEGER")

            # Вироби в проєкті
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    product_type TEXT,
                    width REAL,
                    height REAL,
                    length REAL,
                    thickness REAL,
                    material TEXT,
                    quantity INTEGER DEFAULT 1,
                    metal_area_m2 REAL,
                    weight_kg REAL,
                    unit_price REAL DEFAULT 0,
                    total_price REAL DEFAULT 0,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
                """
            )

            # Специфікації
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS specifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT,
                    format TEXT DEFAULT 'json',
                    content TEXT NOT NULL,
                    total_items INTEGER,
                    total_quantity INTEGER,
                    total_weight_kg REAL,
                    total_area_m2 REAL,
                    total_price REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
                """
            )

            # Плани розкрою
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cutting_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT,
                    sheet_width REAL,
                    sheet_height REAL,
                    thickness REAL,
                    material TEXT,
                    sheets_required INTEGER,
                    utilization_percent REAL,
                    waste_percent REAL,
                    plan_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
                """
            )

            # Бібліотека стандартних виробів
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS standard_products_library (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    product_type TEXT NOT NULL,
                    width REAL,
                    height REAL,
                    length REAL,
                    thickness REAL,
                    material TEXT,
                    default_quantity INTEGER DEFAULT 1,
                    parameters TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Ціни на матеріали
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS material_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material TEXT NOT NULL,
                    thickness REAL,
                    price_per_kg REAL,
                    price_per_m2 REAL,
                    currency TEXT DEFAULT 'UAH',
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(material, thickness)
                )
                """
            )

            # Клієнти
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    contact_person TEXT,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    company_type TEXT,
                    edrpou TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Взаємодії
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    date TEXT DEFAULT CURRENT_TIMESTAMP,
                    interaction_type TEXT DEFAULT 'дзвінок',
                    subject TEXT,
                    description TEXT,
                    result TEXT,
                    next_action TEXT,
                    next_action_date TEXT,
                    created_by TEXT,
                    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
                )
                """
            )

            # Платежі
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    date TEXT DEFAULT CURRENT_TIMESTAMP,
                    amount REAL DEFAULT 0,
                    currency TEXT DEFAULT 'UAH',
                    payment_type TEXT DEFAULT 'вхідний',
                    purpose TEXT,
                    project_name TEXT,
                    notes TEXT,
                    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
                )
                """
            )

            # Проєкти клієнта
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS client_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    project_name TEXT NOT NULL,
                    project_number TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    status TEXT DEFAULT 'в роботі',
                    total_amount REAL DEFAULT 0,
                    warranty_months INTEGER DEFAULT 24,
                    description TEXT,
                    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
                )
                """
            )

            # Користувачі
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'monter',
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_login TEXT
                )
                """
            )

            # Нагадування про гарантію
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS warranty_reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    client_project_id INTEGER,
                    project_name TEXT NOT NULL,
                    reminder_date TEXT NOT NULL,
                    description TEXT,
                    is_completed INTEGER DEFAULT 0,
                    completed_at TEXT,
                    notes TEXT,
                    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
                )
                """
            )

    # ═══════════════════════════════════════════════════════════════
    # ПРОЄКТИ
    # ═══════════════════════════════════════════════════════════════

    def create_project(
        self,
        name: str,
        description: str = "",
        client: str = "",
        metadata: dict | None = None,
        **extra_fields,
    ) -> int:
        """Створити новий проєкт."""
        with self._get_connection() as conn:
            cursor = conn.execute("PRAGMA table_info(projects)")
            col_info = {
                row[1]: {"type": row[2], "notnull": row[3], "default": row[4]}
                for row in cursor.fetchall()
            }

            data = {"name": name}
            if "description" in col_info:
                data["description"] = description
            if "client" in col_info:
                data["client"] = client
            if "metadata" in col_info:
                data["metadata"] = json.dumps(metadata) if metadata else None
            if "status" in col_info:
                data["status"] = "draft"
            if "created_at" in col_info:
                data["created_at"] = datetime.now().isoformat()
            if "updated_at" in col_info:
                data["updated_at"] = datetime.now().isoformat()

            for key, value in extra_fields.items():
                if key in col_info and key not in data:
                    data[key] = value

            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            defaults = {
                "project_number": f"PRJ-{timestamp}",
                "total_area": 0.0, "total_cost": 0.0,
                "total_weight": 0.0, "profit": 0.0, "markup": 0.0,
                "client_name": "", "client_phone": "", "client_email": "",
                "address": "", "notes": "", "author": "", "manager": "",
                "drawing_path": "", "customer_price": 0.0,
                "cost_price": 0.0, "salary_total": 0.0,
            }

            for col_name, info in col_info.items():
                if col_name not in data and info["notnull"] == 1 and info["default"] is None:
                    col_type = info["type"].upper()
                    if col_name in defaults:
                        data[col_name] = defaults[col_name]
                    elif any(t in col_type for t in ["INT", "REAL", "FLOAT", "NUM"]):
                        data[col_name] = 0
                    elif any(t in col_type for t in ["TEXT", "CHAR", "VARCHAR"]):
                        data[col_name] = ""
                    elif any(t in col_type for t in ["DATE", "TIME"]):
                        data[col_name] = datetime.now().isoformat()
                    else:
                        data[col_name] = ""

            cols = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            cursor = conn.execute(
                f"INSERT INTO projects ({cols}) VALUES ({placeholders})",
                tuple(data.values()),
            )
            conn.commit()
            return cursor.lastrowid

    def get_project(self, project_id: int) -> dict | None:
        """Отримати проєкт за ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_all_projects(self, status: str | None = None) -> list[dict]:
        """Отримати всі проєкти (або за статусом)."""
        with self._get_connection() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM projects ORDER BY updated_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def list_projects(self, status: str | None = None) -> list[dict]:
        """Alias для get_all_projects."""
        return self.get_all_projects(status)

    def update_project(self, project_id: int, **kwargs) -> bool:
        """Оновити проєкт."""
        with self._get_connection() as conn:
            columns = self._get_table_columns(conn, "projects")
            allowed = {
                "name", "description", "client", "status", "metadata",
                "drawing_path", "customer_price", "cost_price",
                "salary_total", "profit",
            }
            updates = {
                k: v for k, v in kwargs.items() if k in allowed and k in columns
            }
            if not updates:
                return False

            if "updated_at" in columns:
                updates["updated_at"] = datetime.now().isoformat()
            if "metadata" in updates and isinstance(updates["metadata"], dict):
                updates["metadata"] = json.dumps(updates["metadata"])

            fields = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [project_id]

            conn.execute(f"UPDATE projects SET {fields} WHERE id = ?", values)
            conn.commit()
            return True

    def delete_project(self, project_id: int) -> bool:
        """Видалити проєкт (каскадне видалення виробів, специфікацій тощо)."""
        with self._transaction() as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        return True

    def duplicate_project(self, project_id: int, new_name: str | None = None) -> int:
        """Дублювати проєкт з усіма виробами (АТОМАРНО)."""
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Проєкт {project_id} не знайдено")

        with self._transaction() as conn:
            # 1. Створюємо новий проєкт
            new_id = self._create_project_in_conn(
                conn,
                name=new_name or f"{project['name']} (копія)",
                description=project.get("description", ""),
                client=project.get("client", ""),
                metadata=json.loads(project["metadata"]) if project.get("metadata") else None,
            )

            # 2. Копіюємо всі вироби
            products = self._get_project_products_in_conn(conn, project_id)
            for p in products:
                self._add_product_to_project_in_conn(conn, new_id, {
                    "name": p["name"],
                    "product_type": p["product_type"],
                    "width": p["width"],
                    "height": p["height"],
                    "length": p["length"],
                    "thickness": p["thickness"],
                    "material": p["material"],
                    "quantity": p["quantity"],
                    "metal_area_m2": p["metal_area_m2"],
                    "weight_kg": p["weight_kg"],
                    "notes": p["notes"],
                })

            # 3. Оновлюємо updated_at нового проєкту
            conn.execute(
                "UPDATE projects SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), new_id),
            )

        return new_id

    # ── Хелпери для транзакцій (працюють з існуючим conn) ──

    def _create_project_in_conn(
        self, conn: sqlite3.Connection, name: str,
        description: str = "", client: str = "",
        metadata: dict | None = None,
    ) -> int:
        """Створити проєкт у межах транзакції."""
        cursor = conn.execute(
            """INSERT INTO projects (name, description, client, status, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, description, client, "draft",
             datetime.now().isoformat(), datetime.now().isoformat(),
             json.dumps(metadata) if metadata else None),
        )
        return cursor.lastrowid

    def _get_project_products_in_conn(
        self, conn: sqlite3.Connection, project_id: int
    ) -> list[dict]:
        """Отримати вироби проєкту у межах транзакції."""
        rows = conn.execute(
            "SELECT * FROM project_products WHERE project_id = ? ORDER BY id",
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def _add_product_to_project_in_conn(
        self, conn: sqlite3.Connection, project_id: int, product: dict
    ) -> int:
        """Додати виріб у межах транзакції."""
        cursor = conn.execute(
            """INSERT INTO project_products
            (project_id, name, product_type, width, height, length,
             thickness, material, quantity, metal_area_m2, weight_kg,
             unit_price, total_price, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                project_id,
                product.get("name", ""),
                product.get("product_type", ""),
                product.get("width", 0),
                product.get("height", 0),
                product.get("length", 0),
                product.get("thickness", 0.7),
                product.get("material", "оцинкована сталь"),
                product.get("quantity", 1),
                product.get("metal_area_m2", 0),
                product.get("weight_kg", 0),
                product.get("unit_price", 0),
                product.get("total_price", 0),
                product.get("notes", ""),
            ),
        )
        return cursor.lastrowid

    # ═══════════════════════════════════════════════════════════════
    # ВИРОБИ В ПРОЄКТІ
    # ═══════════════════════════════════════════════════════════════

    def add_product_to_project(self, project_id: int, product: dict) -> int:
        """Додати виріб до проєкту (АТОМАРНО: виріб + оновлення проєкту)."""
        with self._transaction() as conn:
            product_id = self._add_product_to_project_in_conn(conn, project_id, product)
            conn.execute(
                "UPDATE projects SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), project_id),
            )
        return product_id

    def get_project_products(self, project_id: int) -> list[dict]:
        """Отримати всі вироби проєкту."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM project_products WHERE project_id = ? ORDER BY id",
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def update_product(self, product_id: int, **kwargs) -> bool:
        """Оновити виріб."""
        allowed = {
            "name", "product_type", "width", "height", "length",
            "thickness", "material", "quantity", "metal_area_m2",
            "weight_kg", "notes",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        fields = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [product_id]

        with self._get_connection() as conn:
            conn.execute(f"UPDATE project_products SET {fields} WHERE id = ?", values)
            conn.commit()
            return True

    def delete_product(self, product_id: int) -> bool:
        """Видалити виріб."""
        with self._transaction() as conn:
            conn.execute("DELETE FROM project_products WHERE id = ?", (product_id,))
        return True

    def get_project_summary(self, project_id: int) -> dict:
        """Отримати зведення по проєкту."""
        with self._get_connection() as conn:
            row = conn.execute(
                """SELECT
                COUNT(*) as total_items,
                SUM(quantity) as total_quantity,
                SUM(weight_kg * quantity) as total_weight,
                SUM(metal_area_m2 * quantity) as total_area
                FROM project_products WHERE project_id = ?""",
                (project_id,),
            ).fetchone()
            return dict(row) if row else {}

    # ═══════════════════════════════════════════════════════════════
    # СПЕЦИФІКАЦІЇ
    # ═══════════════════════════════════════════════════════════════

    def save_specification(
        self,
        project_id: int,
        spec_data: dict,
        name: str = "Специфікація",
        format: str = "json",
    ) -> int:
        """Зберегти специфікацію проєкту."""
        content = (
            spec_data
            if isinstance(spec_data, str)
            else json.dumps(spec_data, ensure_ascii=False)
        )
        summary = spec_data.get("summary", {}) if isinstance(spec_data, dict) else {}

        with self._transaction() as conn:
            cursor = conn.execute(
                """INSERT INTO specifications
                (project_id, name, format, content, total_items, total_quantity,
                 total_weight_kg, total_area_m2, total_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_id, name, format, content,
                    summary.get("total_items", 0),
                    summary.get("total_quantity", 0),
                    summary.get("total_weight_kg", 0),
                    summary.get("total_area_m2", 0),
                    summary.get("total_price", 0),
                ),
            )
        return cursor.lastrowid

    def get_specifications(self, project_id: int) -> list[dict]:
        """Отримати всі специфікації проєкту."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM specifications WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_specification(self, spec_id: int) -> dict | None:
        """Отримати специфікацію за ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM specifications WHERE id = ?", (spec_id,)
            ).fetchone()
            if row:
                data = dict(row)
                if data.get("format") == "json" and data.get("content"):
                    try:
                        data["parsed_content"] = json.loads(data["content"])
                    except Exception:
                        pass
                return data
            return None

    # ═══════════════════════════════════════════════════════════════
    # ПЛАНИ РОЗКРОЮ
    # ═══════════════════════════════════════════════════════════════

    def save_cutting_plan(
        self, project_id: int, plan: dict, name: str = "План розкрою"
    ) -> int:
        """Зберегти план розкрою."""
        summary = plan.get("summary", {})

        with self._transaction() as conn:
            cursor = conn.execute(
                """INSERT INTO cutting_plans
                (project_id, name, sheet_width, sheet_height, thickness, material,
                 sheets_required, utilization_percent, waste_percent, plan_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_id, name,
                    plan.get("sheet_width", 1250),
                    plan.get("sheet_height", 2500),
                    plan.get("thickness", 0.7),
                    plan.get("material", "оцинкована сталь"),
                    summary.get("sheets_required", 0),
                    summary.get("utilization_percent", 0),
                    summary.get("waste_percent", 0),
                    json.dumps(plan, ensure_ascii=False),
                ),
            )
        return cursor.lastrowid

    def get_cutting_plans(self, project_id: int) -> list[dict]:
        """Отримати плани розкрою проєкту."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM cutting_plans WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
            result = []
            for r in rows:
                data = dict(r)
                if data.get("plan_data"):
                    try:
                        data["parsed_plan"] = json.loads(data["plan_data"])
                    except Exception:
                        pass
                result.append(data)
            return result

    # ═══════════════════════════════════════════════════════════════
    # БІБЛІОТЕКА СТАНДАРТНИХ ВИРОБІВ
    # ═══════════════════════════════════════════════════════════════

    def add_standard_product(
        self,
        name: str,
        product_type: str,
        width: float,
        height: float,
        length: float,
        thickness: float,
        material: str,
        parameters: dict | None = None,
    ) -> int:
        """Додати виріб у бібліотеку стандартних виробів."""
        with self._transaction() as conn:
            cursor = conn.execute(
                """INSERT INTO standard_products_library
                (name, product_type, width, height, length, thickness, material, parameters)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    name, product_type, width, height, length, thickness, material,
                    json.dumps(parameters) if parameters else None,
                ),
            )
        return cursor.lastrowid

    def get_standard_products(
        self, product_type: str | None = None, active_only: bool = True
    ) -> list[dict]:
        """Отримати стандартні вироби з бібліотеки."""
        with self._get_connection() as conn:
            query = "SELECT * FROM standard_products_library WHERE 1=1"
            params = []
            if active_only:
                query += " AND is_active = 1"
            if product_type:
                query += " AND product_type = ?"
                params.append(product_type)
            query += " ORDER BY product_type, name"

            rows = conn.execute(query, params).fetchall()
            result = []
            for r in rows:
                data = dict(r)
                if data.get("parameters"):
                    try:
                        data["parsed_parameters"] = json.loads(data["parameters"])
                    except Exception:
                        pass
                result.append(data)
            return result

    def update_standard_product(self, product_id: int, **kwargs) -> bool:
        """Оновити стандартний виріб."""
        allowed = {
            "name", "product_type", "width", "height", "length",
            "thickness", "material", "default_quantity", "parameters", "is_active",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        if "parameters" in updates and isinstance(updates["parameters"], dict):
            updates["parameters"] = json.dumps(updates["parameters"])

        fields = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [product_id]

        with self._transaction() as conn:
            conn.execute(
                f"UPDATE standard_products_library SET {fields} WHERE id = ?", values
            )
        return True

    # ═══════════════════════════════════════════════════════════════
    # ЦІНИ НА МАТЕРІАЛИ
    # ═══════════════════════════════════════════════════════════════

    def set_material_price(
        self,
        material: str,
        thickness: float,
        price_per_kg: float | None = None,
        price_per_m2: float | None = None,
    ) -> int:
        """Встановити/оновити ціну матеріалу (АТОМАРНО)."""
        with self._transaction() as conn:
            existing = conn.execute(
                "SELECT id FROM material_prices WHERE material = ? AND thickness = ?",
                (material, thickness),
            ).fetchone()

            if existing:
                updates = []
                values = []
                if price_per_kg is not None:
                    updates.append("price_per_kg = ?")
                    values.append(price_per_kg)
                if price_per_m2 is not None:
                    updates.append("price_per_m2 = ?")
                    values.append(price_per_m2)
                if updates:
                    updates.append("updated_at = CURRENT_TIMESTAMP")
                    values.extend([existing["id"]])
                    conn.execute(
                        f"UPDATE material_prices SET {', '.join(updates)} WHERE id = ?",
                        values,
                    )
                return existing["id"]
            else:
                cursor = conn.execute(
                    """INSERT INTO material_prices (material, thickness, price_per_kg, price_per_m2)
                    VALUES (?, ?, ?, ?)""",
                    (material, thickness, price_per_kg, price_per_m2),
                )
                return cursor.lastrowid

    def get_material_prices(self) -> list[dict]:
        """Отримати всі ціни на матеріали."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM material_prices ORDER BY material, thickness"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_material_price(self, material: str, thickness: float) -> float | None:
        """Отримати ціну за кг для конкретного матеріалу."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT price_per_kg FROM material_prices WHERE material = ? AND thickness = ?",
                (material, thickness),
            ).fetchone()
            return row["price_per_kg"] if row else None

    # ═══════════════════════════════════════════════════════════════
    # КЛІЄНТИ
    # ═══════════════════════════════════════════════════════════════

    def add_client(
        self, name: str, contact: str = "", phone: str = "",
        email: str = "", address: str = "", company_type: str = "",
        edrpou: str = "", notes: str = "",
    ) -> int:
        """Додати клієнта (АТОМАРНО)."""
        with self._transaction() as conn:
            cur = conn.execute(
                """INSERT INTO clients (name, contact_person, phone, email, address,
                company_type, edrpou, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, contact, phone, email, address, company_type, edrpou, notes,
                 datetime.now().isoformat(), datetime.now().isoformat()),
            )
        return cur.lastrowid

    def update_client(self, client_id: int, **kwargs) -> bool:
        """Оновити клієнта."""
        allowed = {"name", "contact_person", "phone", "email", "address",
                   "company_type", "edrpou", "notes"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return False
        fields["updated_at"] = datetime.now().isoformat()
        sets = ", ".join(f"{k} = ?" for k in fields)

        with self._transaction() as conn:
            conn.execute(f"UPDATE clients SET {sets} WHERE id = ?",
                         (*fields.values(), client_id))
        return True

    def get_client(self, client_id: int) -> dict | None:
        """Отримати клієнта за ID."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
            return dict(row) if row else None

    def get_all_clients(self, search: str = "") -> list[dict]:
        """Отримати всіх клієнтів."""
        with self._get_connection() as conn:
            if search:
                like = f"%{search}%"
                rows = conn.execute(
                    """SELECT * FROM clients WHERE name LIKE ? OR phone LIKE ? OR email LIKE ?
                    ORDER BY name""", (like, like, like)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
            return [dict(r) for r in rows]

    def delete_client(self, client_id: int) -> bool:
        """Видалити клієнта (каскадне видалення)."""
        with self._transaction() as conn:
            conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        return True

    # ═══════════════════════════════════════════════════════════════
    # ВЗАЄМОДІЇ
    # ═══════════════════════════════════════════════════════════════

    def add_interaction(
        self, client_id: int, interaction_type: str = "дзвінок",
        subject: str = "", description: str = "", result: str = "",
        next_action: str = "", next_action_date: str = "",
        created_by: str = "",
    ) -> int:
        """Додати взаємодію (АТОМАРНО)."""
        with self._transaction() as conn:
            cur = conn.execute(
                """INSERT INTO interactions (client_id, date, interaction_type, subject,
                description, result, next_action, next_action_date, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (client_id, datetime.now().isoformat(), interaction_type, subject,
                 description, result, next_action, next_action_date, created_by),
            )
        return cur.lastrowid

    def get_client_interactions(self, client_id: int) -> list[dict]:
        """Отримати взаємодії клієнта."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM interactions WHERE client_id = ? ORDER BY date DESC",
                (client_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_interaction(self, interaction_id: int) -> bool:
        """Видалити взаємодію."""
        with self._transaction() as conn:
            conn.execute("DELETE FROM interactions WHERE id = ?", (interaction_id,))
        return True

    # ═══════════════════════════════════════════════════════════════
    # ПЛАТЕЖІ
    # ═══════════════════════════════════════════════════════════════

    def add_payment(
        self, client_id: int, amount: float, currency: str = "UAH",
        payment_type: str = "вхідний", purpose: str = "",
        project_name: str = "", notes: str = "",
    ) -> int:
        """Додати платіж (АТОМАРНО)."""
        with self._transaction() as conn:
            cur = conn.execute(
                """INSERT INTO payments (client_id, date, amount, currency, payment_type,
                purpose, project_name, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (client_id, datetime.now().isoformat(), amount, currency, payment_type,
                 purpose, project_name, notes),
            )
        return cur.lastrowid

    def get_client_payments(self, client_id: int) -> list[dict]:
        """Отримати платежі клієнта."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM payments WHERE client_id = ? ORDER BY date DESC",
                (client_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_client_balance(self, client_id: int) -> float:
        """Отримати баланс клієнта."""
        with self._get_connection() as conn:
            row = conn.execute(
                """SELECT SUM(CASE WHEN payment_type = 'вхідний' THEN amount ELSE -amount END) as balance
                FROM payments WHERE client_id = ?""", (client_id,)
            ).fetchone()
            return float(row["balance"] or 0.0)

    # ═══════════════════════════════════════════════════════════════
    # ПРОЄКТИ КЛІЄНТА
    # ═══════════════════════════════════════════════════════════════

    def add_client_project(
        self, client_id: int, project_name: str,
        project_number: str = "", start_date: str = "",
        end_date: str = "", status: str = "в роботі",
        total_amount: float = 0, warranty_months: int = 24,
        description: str = "",
    ) -> int:
        """Додати проєкт клієнта (АТОМАРНО: проєкт + нагадування про гарантію)."""
        with self._transaction() as conn:
            cur = conn.execute(
                """INSERT INTO client_projects (client_id, project_name, project_number,
                start_date, end_date, status, total_amount, warranty_months, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (client_id, project_name, project_number, start_date, end_date,
                 status, total_amount, warranty_months, description),
            )
            project_id = cur.lastrowid

            # Автоматично створюємо нагадування про гарантію
            if end_date and warranty_months > 0:
                try:
                    end_dt = datetime.fromisoformat(end_date)
                    reminder_dt = end_dt + timedelta(days=warranty_months * 30)
                    conn.execute(
                        """INSERT INTO warranty_reminders
                        (client_id, client_project_id, project_name, reminder_date,
                         description, is_completed, notes)
                        VALUES (?, ?, ?, ?, ?, 0, ?)""",
                        (client_id, project_id, project_name, reminder_dt.isoformat(),
                         f"Гарантійне обслуговування проєкту \"{project_name}\" (завершено {end_date})",
                         ""),
                    )
                except Exception:
                    pass
        return project_id

    def get_client_projects(self, client_id: int) -> list[dict]:
        """Отримати проєкти клієнта."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM client_projects WHERE client_id = ? ORDER BY start_date DESC",
                (client_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def update_client_project_status(self, project_id: int, status: str) -> bool:
        """Оновити статус проєкту клієнта."""
        with self._transaction() as conn:
            conn.execute(
                "UPDATE client_projects SET status = ? WHERE id = ?",
                (status, project_id),
            )
        return True

    # ═══════════════════════════════════════════════════════════════
    # НАГАДУВАННЯ ПРО ГАРАНТІЮ
    # ═══════════════════════════════════════════════════════════════

    def add_warranty_reminder(
        self, client_id: int, project_name: str,
        reminder_date: str, description: str = "",
        client_project_id: int = None, notes: str = "",
    ) -> int:
        """Додати нагадування про гарантію (АТОМАРНО)."""
        with self._transaction() as conn:
            cur = conn.execute(
                """INSERT INTO warranty_reminders (client_id, client_project_id, project_name,
                reminder_date, description, is_completed, notes)
                VALUES (?, ?, ?, ?, ?, 0, ?)""",
                (client_id, client_project_id, project_name, reminder_date, description, notes),
            )
        return cur.lastrowid

    def get_warranty_reminders(
        self, client_id: int = None, upcoming_days: int = 30
    ) -> list[dict]:
        """Отримати нагадування про гарантію."""
        with self._get_connection() as conn:
            future = (datetime.now() + timedelta(days=upcoming_days)).isoformat()
            now = datetime.now().isoformat()
            if client_id:
                rows = conn.execute(
                    """SELECT wr.*, c.name as client_name FROM warranty_reminders wr
                    JOIN clients c ON wr.client_id = c.id
                    WHERE wr.client_id = ? AND wr.reminder_date <= ? AND wr.reminder_date >= ?
                    AND wr.is_completed = 0
                    ORDER BY wr.reminder_date ASC""",
                    (client_id, future, now),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT wr.*, c.name as client_name FROM warranty_reminders wr
                    JOIN clients c ON wr.client_id = c.id
                    WHERE wr.reminder_date <= ? AND wr.reminder_date >= ?
                    AND wr.is_completed = 0
                    ORDER BY wr.reminder_date ASC""",
                    (future, now),
                ).fetchall()
            return [dict(r) for r in rows]

    def complete_warranty_reminder(self, reminder_id: int, notes: str = "") -> bool:
        """Відмітити нагадування як виконане."""
        with self._transaction() as conn:
            conn.execute(
                """UPDATE warranty_reminders SET is_completed = 1, completed_at = ?, notes = ?
                WHERE id = ?""",
                (datetime.now().isoformat(), notes, reminder_id),
            )
        return True

    # ═══════════════════════════════════════════════════════════════
    # ДАШБОРД — СТАТИСТИКА
    # ═══════════════════════════════════════════════════════════════

    def get_dashboard_stats(self) -> dict:
        """KPI для дашборду."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT SUM(total_amount) as total FROM client_projects WHERE status IN ('завершено', 'гарантія', 'закрито')"
            ).fetchone()
            total_revenue = float(row["total"] or 0)

            row = conn.execute(
                "SELECT AVG(total_amount) as avg FROM client_projects WHERE total_amount > 0"
            ).fetchone()
            avg_check = float(row["avg"] or 0)

            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM client_projects WHERE status = 'в роботі'"
            ).fetchone()
            active_projects = int(row["cnt"] or 0)

            now = datetime.now().isoformat()
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM client_projects WHERE end_date < ? AND status != 'закрито'",
                (now,),
            ).fetchone()
            overdue_projects = int(row["cnt"] or 0)

            row = conn.execute("SELECT COUNT(*) as cnt FROM clients").fetchone()
            total_clients = int(row["cnt"] or 0)

            return {
                "total_revenue": total_revenue,
                "avg_check": avg_check,
                "active_projects": active_projects,
                "overdue_projects": overdue_projects,
                "total_clients": total_clients,
            }

    def get_monthly_revenue(self, months: int = 12) -> list[dict]:
        """Виручка по місяцях."""
        with self._get_connection() as conn:
            since = (datetime.now() - timedelta(days=months * 31)).strftime("%Y-%m")
            rows = conn.execute(
                """SELECT strftime('%Y-%m', end_date) as month, SUM(total_amount) as amount
                FROM client_projects
                WHERE end_date IS NOT NULL AND end_date >= ?
                GROUP BY month
                ORDER BY month""",
                (since + "-01",),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_project_status_counts(self) -> dict:
        """Кількість проєктів за статусами."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM client_projects GROUP BY status"
            ).fetchall()
            return {r["status"]: r["cnt"] for r in rows}

    def get_top_clients(self, limit: int = 5) -> list[dict]:
        """ТОП клієнтів за сумою замовлень."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT c.name, SUM(cp.total_amount) as total
                FROM clients c
                JOIN client_projects cp ON c.id = cp.client_id
                GROUP BY c.id
                ORDER BY total DESC
                LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_monthly_project_status(self, months: int = 6) -> list[dict]:
        """Кількість проєктів по місяцях за статусами."""
        with self._get_connection() as conn:
            since = (datetime.now() - timedelta(days=months * 31)).strftime("%Y-%m")
            rows = conn.execute(
                """SELECT strftime('%Y-%m', start_date) as month,
                SUM(CASE WHEN status = 'в роботі' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN status IN ('завершено', 'гарантія', 'закрито') THEN 1 ELSE 0 END) as completed
                FROM client_projects
                WHERE start_date IS NOT NULL AND start_date >= ?
                GROUP BY month
                ORDER BY month""",
                (since + "-01",),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_monthly_avg_check(self, months: int = 12) -> list[dict]:
        """Середній чек по місяцях."""
        with self._get_connection() as conn:
            since = (datetime.now() - timedelta(days=months * 31)).strftime("%Y-%m")
            rows = conn.execute(
                """SELECT strftime('%Y-%m', end_date) as month, AVG(total_amount) as avg
                FROM client_projects
                WHERE end_date IS NOT NULL AND end_date >= ? AND total_amount > 0
                GROUP BY month
                ORDER BY month""",
                (since + "-01",),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_overdue_projects(self) -> list[dict]:
        """Прострочені проєкти."""
        with self._get_connection() as conn:
            now = datetime.now().isoformat()
            rows = conn.execute(
                """SELECT * FROM client_projects
                WHERE end_date < ? AND status != 'закрито'
                ORDER BY end_date ASC""",
                (now,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_material_usage_report(self) -> list[dict]:
        """Звіт по використанню матеріалів."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT
                material, thickness,
                SUM(quantity) as total_quantity,
                SUM(weight_kg * quantity) as total_weight,
                SUM(metal_area_m2 * quantity) as total_area,
                COUNT(DISTINCT project_id) as projects_count
                FROM project_products
                GROUP BY material, thickness
                ORDER BY total_weight DESC"""
            ).fetchall()
            return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════
# ФАБРИКА
# ═══════════════════════════════════════════════════════════════════

def get_db(db_path: str = "data/company.db") -> ProjectDatabase:
    """Швидке отримання екземпляру БД."""
    return ProjectDatabase(db_path)


# ═══════════════════════════════════════════════════════════════════
# ІНТЕГРАЦІЯ
# ═══════════════════════════════════════════════════════════════════

def save_project_full(
    project_name: str,
    products: list[dict],
    spec_data: dict | None = None,
    cutting_plan: dict | None = None,
    db_path: str = "data/company.db",
) -> dict:
    """Зберегти повний проєкт (вироби + специфікація + розкрій) АТОМАРНО."""
    db = ProjectDatabase(db_path)

    with db._transaction() as conn:
        project_id = db._create_project_in_conn(conn, name=project_name)

        for p in products:
            db._add_product_to_project_in_conn(conn, project_id, p)

        spec_id = None
        if spec_data:
            content = json.dumps(spec_data, ensure_ascii=False)
            summary = spec_data.get("summary", {})
            cursor = conn.execute(
                """INSERT INTO specifications
                (project_id, name, format, content, total_items, total_quantity,
                 total_weight_kg, total_area_m2, total_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_id, "Специфікація", "json", content,
                    summary.get("total_items", 0),
                    summary.get("total_quantity", 0),
                    summary.get("total_weight_kg", 0),
                    summary.get("total_area_m2", 0),
                    summary.get("total_price", 0),
                ),
            )
            spec_id = cursor.lastrowid

        plan_id = None
        if cutting_plan:
            summary = cutting_plan.get("summary", {})
            cursor = conn.execute(
                """INSERT INTO cutting_plans
                (project_id, name, sheet_width, sheet_height, thickness, material,
                 sheets_required, utilization_percent, waste_percent, plan_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_id, "План розкрою",
                    cutting_plan.get("sheet_width", 1250),
                    cutting_plan.get("sheet_height", 2500),
                    cutting_plan.get("thickness", 0.7),
                    cutting_plan.get("material", "оцинкована сталь"),
                    summary.get("sheets_required", 0),
                    summary.get("utilization_percent", 0),
                    summary.get("waste_percent", 0),
                    json.dumps(cutting_plan, ensure_ascii=False),
                ),
            )
            plan_id = cursor.lastrowid

    return {
        "project_id": project_id,
        "specification_id": spec_id,
        "cutting_plan_id": plan_id,
        "products_count": len(products),
    }
