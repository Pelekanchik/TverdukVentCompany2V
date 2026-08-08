"""
Репозиторій для роботи з шаблонами розрахунків
"""

import json
import sqlite3

from ventilation_company.database import get_calc_db


class TemplateRepo:
    """CRUD для calc_templates"""

    @staticmethod
    def get_all() -> list[sqlite3.Row]:
        db = get_calc_db()
        rows = db.execute("SELECT * FROM calc_templates ORDER BY name").fetchall()
        db.close()
        return rows

    @staticmethod
    def get_by_id(template_id: int) -> sqlite3.Row | None:
        db = get_calc_db()
        row = db.execute("SELECT * FROM calc_templates WHERE id=?", (template_id,)).fetchone()
        db.close()
        return row

    @staticmethod
    def add(name: str, description: str = "", items_data: list[dict] = None) -> int:
        db = get_calc_db()
        from datetime import datetime

        now = datetime.now().isoformat()
        cursor = db.execute(
            """INSERT INTO calc_templates
               (name, description, items_data, created_at)
               VALUES (?, ?, ?, ?)""",
            (name, description, json.dumps(items_data or []), now),
        )
        db.commit()
        last_id = cursor.lastrowid
        db.close()
        return last_id

    @staticmethod
    def update(template_id: int, **kwargs) -> None:
        db = get_calc_db()
        allowed = {"name", "description", "items_data"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            db.close()
            return
        if "items_data" in fields:
            fields["items_data"] = json.dumps(fields["items_data"])
        set_clause = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values()) + [template_id]
        db.execute(f"UPDATE calc_templates SET {set_clause} WHERE id=?", values)
        db.commit()
        db.close()

    @staticmethod
    def delete(template_id: int) -> None:
        db = get_calc_db()
        db.execute("DELETE FROM calc_templates WHERE id=?", (template_id,))
        db.commit()
        db.close()
