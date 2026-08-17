"""Тести для транзакцій у ProjectDatabase.

Запуск:  pytest tests/test_db_transactions.py -v
"""

import os
import sqlite3
import tempfile

import pytest

from ventilation_company.db_integration import ProjectDatabase, TransactionError, save_project_full


@pytest.fixture
def db():
    """Створити тимчасову БД для кожного тесту."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        path = os.path.join(tmpdir, "test.db")
        database = ProjectDatabase(path)
        yield database
        # Явно закриваємо з'єднання перед cleanup (Windows)
        import gc
        gc.collect()


class TestTransactions:
    """Перевірка атомарності транзакцій."""

    def test_add_product_updates_project_timestamp(self, db):
        """add_product_to_project: виріб додано І проєкт оновлено."""
        pid = db.create_project(name="Тест")
        old_project = db.get_project(pid)
        old_updated = old_project["updated_at"]

        db.add_product_to_project(pid, {
            "name": "Виріб 1", "product_type": "rect_duct",
            "width": 400, "height": 200, "length": 1000,
            "quantity": 2,
        })

        new_project = db.get_project(pid)
        assert new_project["updated_at"] != old_updated
        products = db.get_project_products(pid)
        assert len(products) == 1
        assert products[0]["name"] == "Виріб 1"

    def test_transaction_rollback_on_error(self, db):
        """Якщо друга операція в транзакції падає — перша відкочується."""
        pid = db.create_project(name="Тест Rollback")

        # Симулюємо помилку: передаємо некоректні дані
        # (немає реальної помилки, тому тестуємо через _transaction напряму)
        try:
            with db._transaction() as conn:
                conn.execute("INSERT INTO project_products (project_id, name) VALUES (?, ?)",
                             (pid, "Виріб Rollback"))
                # Симулюємо SQL-помилку
                conn.execute("INSERT INTO nonexistent_table (x) VALUES (1)")
        except TransactionError:
            pass

        # Перевіримо, що перший INSERT відкотився
        products = db.get_project_products(pid)
        assert len(products) == 0

    def test_duplicate_project_atomic(self, db):
        """duplicate_project: або все скопійовано, або нічого."""
        pid = db.create_project(name="Оригінал")
        db.add_product_to_project(pid, {
            "name": "Виріб А", "product_type": "rect_duct",
            "width": 400, "height": 200, "length": 1000, "quantity": 1,
        })
        db.add_product_to_project(pid, {
            "name": "Виріб Б", "product_type": "round_duct",
            "width": 315, "height": 315, "length": 500, "quantity": 3,
        })

        new_id = db.duplicate_project(pid, "Копія")

        original = db.get_project_products(pid)
        copied = db.get_project_products(new_id)

        assert len(copied) == len(original) == 2
        assert copied[0]["name"] == "Виріб А"
        assert copied[1]["name"] == "Виріб Б"
        assert copied[1]["quantity"] == 3

        # Проєкт створено
        new_project = db.get_project(new_id)
        assert new_project["name"] == "Копія"

    def test_delete_project_cascade(self, db):
        """delete_project: видаляє проєкт і всі пов'язані дані."""
        pid = db.create_project(name="На видалення")
        db.add_product_to_project(pid, {"name": "В", "product_type": "rect_duct", "quantity": 1})

        db.delete_project(pid)

        assert db.get_project(pid) is None
        assert db.get_project_products(pid) == []

    def test_save_project_full_atomic(self):
        """save_project_full: або все збережено, або нічого."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            path = os.path.join(tmpdir, "full.db")
            result = save_project_full(
                project_name="Повний проєкт",
                products=[
                    {"name": "В1", "product_type": "rect_duct", "quantity": 2, "width": 400},
                    {"name": "В2", "product_type": "round_duct", "quantity": 1, "width": 315},
                ],
                spec_data={"summary": {"total_items": 2, "total_price": 1500}},
                cutting_plan={"summary": {"sheets_required": 3}, "sheet_width": 1250},
                db_path=path,
            )

            assert result["project_id"] > 0
            assert result["specification_id"] > 0
            assert result["cutting_plan_id"] > 0
            assert result["products_count"] == 2

            # Перевіримо цілісність
            db = ProjectDatabase(path)
            assert db.get_project(result["project_id"]) is not None
            assert len(db.get_project_products(result["project_id"])) == 2
            assert len(db.get_specifications(result["project_id"])) == 1
            assert len(db.get_cutting_plans(result["project_id"])) == 1

    def test_wal_mode_enabled(self, db):
        """WAL-mode увімкнено для кращої продуктивності."""
        with db._get_connection() as conn:
            row = conn.execute("PRAGMA journal_mode").fetchone()
            assert row[0].upper() == "WAL"

    def test_set_material_price_upsert(self, db):
        """set_material_price: INSERT або UPDATE атомарно."""
        id1 = db.set_material_price("оцинкована сталь", 0.7, price_per_kg=580.0)
        id2 = db.set_material_price("оцинкована сталь", 0.7, price_per_kg=600.0)

        assert id1 == id2  # Оновлення, не новий запис
        price = db.get_material_price("оцинкована сталь", 0.7)
        assert price == 600.0

    def test_add_client_project_with_warranty(self, db):
        """add_client_project: проєкт + нагадування про гарантію атомарно."""
        cid = db.add_client(name="Тест Клієнт")
        pid = db.add_client_project(
            client_id=cid,
            project_name="Гарантійний проєкт",
            end_date="2026-12-31",
            warranty_months=24,
        )

        projects = db.get_client_projects(cid)
        assert len(projects) == 1
        assert projects[0]["project_name"] == "Гарантійний проєкт"

        # Нагадування створено автоматично
        reminders = db.get_warranty_reminders(client_id=cid, upcoming_days=9999)
        assert len(reminders) == 1
        assert reminders[0]["project_name"] == "Гарантійний проєкт"

    def test_complete_warranty_reminder(self, db):
        """complete_warranty_reminder: оновлення атомарно."""
        cid = db.add_client(name="Тест")
        rid = db.add_warranty_reminder(
            client_id=cid, project_name="Проєкт",
            reminder_date="2026-12-01", description="Тест",
        )

        db.complete_warranty_reminder(rid, notes="Виконано")

        reminders = db.get_warranty_reminders(client_id=cid, upcoming_days=9999)
        assert len(reminders) == 0  # Виконані не показуються

    def test_concurrent_access_wal(self, db):
        """WAL-mode дозволяє читання під час запису."""
        import threading

        pid = db.create_project(name="Concurrent")
        errors = []
        results = []

        def writer():
            try:
                for i in range(10):
                    db.add_product_to_project(pid, {
                        "name": f"Виріб {i}", "product_type": "rect_duct",
                        "quantity": 1, "width": 100 + i,
                    })
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(10):
                    prods = db.get_project_products(pid)
                    results.append(len(prods))
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=writer)
        t2 = threading.Thread(target=reader)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors, f"Помилки: {errors}"
        assert len(db.get_project_products(pid)) == 10
