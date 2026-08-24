import os
import shutil

project_dir = os.path.dirname(os.path.abspath(__file__))

deleted_dirs = 0
deleted_files = 0

for root, dirs, files in os.walk(project_dir):
    # Видаляємо папки __pycache__
    for d in dirs:
        if d == "__pycache__":
            pycache_path = os.path.join(root, d)
            try:
                shutil.rmtree(pycache_path)
                print(f"🗑️  Видалено: {pycache_path}")
                deleted_dirs += 1
            except Exception as e:
                print(f"❌ Помилка видалення {pycache_path}: {e}")

    # Видаляємо .pyc файли
    for f in files:
        if f.endswith(".pyc"):
            pyc_path = os.path.join(root, f)
            try:
                os.remove(pyc_path)
                print(f"🗑️  Видалено: {pyc_path}")
                deleted_files += 1
            except Exception as e:
                print(f"❌ Помилка видалення {pyc_path}: {e}")

print(f"\n✅ Готово! Видалено папок: {deleted_dirs}, файлів: {deleted_files}")
print("Тепер можна перезапускати програму.")
