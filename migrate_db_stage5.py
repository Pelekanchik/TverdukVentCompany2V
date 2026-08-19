"""Міграція БД Етапу 5: додати blank_area_m2 та material_area_m2 до project_products."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "company.db")

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"База даних не знайдена: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Перевіримо, чи є колонки
    cursor.execute("PRAGMA table_info(project_products)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "blank_area_m2" not in columns:
        cursor.execute("ALTER TABLE project_products ADD COLUMN blank_area_m2 REAL DEFAULT 0")
        print("[OK] Додано колонку blank_area_m2")
    else:
        print("[SKIP] Колонка blank_area_m2 вже існує")
    
    if "material_area_m2" not in columns:
        cursor.execute("ALTER TABLE project_products ADD COLUMN material_area_m2 REAL DEFAULT 0")
        print("[OK] Додано колонку material_area_m2")
    else:
        print("[SKIP] Колонка material_area_m2 вже існує")
    
    conn.commit()
    conn.close()
    print("[DONE] Міграція завершена")

if __name__ == "__main__":
    migrate()
