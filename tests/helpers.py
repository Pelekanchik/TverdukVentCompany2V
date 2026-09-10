# Test-only ProjectDatabase replacement.
# This is intentionally small and lives only under tests/. It replaces the
# legacy production db_integration module for test fixtures.

from __future__ import annotations

import sqlite3
from decimal import Decimal


class ProjectDatabase:
    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                salary_total REAL DEFAULT 0
            )
            """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT,
                product_type TEXT,
                quantity REAL DEFAULT 1,
                metal_area_m2 REAL DEFAULT 0,
                salary_per_unit REAL DEFAULT 0
            )
            """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS standard_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                product_type TEXT,
                width REAL,
                height REAL,
                length REAL,
                thickness REAL,
                material TEXT
            )
            """)
        self.conn.commit()

    def create_project(self, name: str) -> int:
        cur = self.conn.cursor()
        cur.execute("INSERT INTO projects(name) VALUES (?)", (name,))
        self.conn.commit()
        return int(cur.lastrowid)

    def get_project(self, project_id: int):
        row = self.conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            return None
        return dict(row)

    def update_project(self, project_id: int, **kwargs) -> None:
        fields = []
        values = []
        for key in ("name", "salary_total"):
            if key in kwargs:
                value = kwargs[key]
                if isinstance(value, Decimal):
                    value = float(value)
                fields.append(f"{key} = ?")
                values.append(value)
        if not fields:
            return
        values.append(project_id)
        self.conn.execute(f"UPDATE projects SET {', '.join(fields)} WHERE id = ?", values)
        self.conn.commit()

    def delete_project(self, project_id: int) -> None:
        self.conn.execute("DELETE FROM products WHERE project_id = ?", (project_id,))
        self.conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.conn.commit()

    def add_product_to_project(self, project_id: int, product: dict) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO products(project_id, name, product_type, quantity, metal_area_m2, salary_per_unit)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                product.get("name") or product.get("product_type") or "product",
                product.get("product_type"),
                product.get("quantity", 1),
                float(product.get("metal_area_m2") or 0),
                float(product.get("salary_per_unit") or 0),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get_project_products(self, project_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM products WHERE project_id = ? ORDER BY id",
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_product(self, product_id: int) -> None:
        self.conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        self.conn.commit()

    def add_standard_product(
        self,
        name: str,
        product_type: str,
        width: float,
        height: float,
        length: float,
        thickness: float,
        material: str,
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO standard_products(name, product_type, width, height, length, thickness, material)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, product_type, width, height, length, thickness, material),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get_standard_products(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM standard_products ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.conn.close()
