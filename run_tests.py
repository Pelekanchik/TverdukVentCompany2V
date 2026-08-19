#!/usr/bin/env python3
"""
RUN_TESTS.PY — Запуск глобальних тестів VentilationCompany2V
===========================================================

Використання:
    python run_tests.py          — запуск усіх тестів
    python run_tests.py -v       — докладний вивід
    python run_tests.py --global — тільки test_global.py

Перед першим запуском (якщо з'являються дивні помилки):
    1. Видаліть кеш:  rmdir /s /q __pycache__  (Windows)
                     rm -rf __pycache__        (Linux/Mac)
    2. Видаліть .pyc:  del /s *.pyc           (Windows)
                      find . -name "*.pyc" -delete  (Linux/Mac)

Залежності:
    pip install pytest sqlalchemy
"""

import subprocess
import sys
import os


def print_header(text: str):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def main():
    args = sys.argv[1:]

    # Визначаємо, які тести запускати
    if "--global" in args:
        test_path = "tests/test_global.py"
        args.remove("--global")
    elif "--all" in args:
        test_path = "tests/"
        args.remove("--all")
    else:
        test_path = "tests/"  # за замовчуванням усі тести

    # Базова команда pytest
    cmd = [sys.executable, "-m", "pytest", test_path, "--tb=short"]

    # Додаємо -v якщо не передано
    if "-v" in args or "--verbose" in args:
        cmd.append("-v")
        if "--verbose" in args:
            args.remove("--verbose")
        if "-v" in args:
            args.remove("-v")

    # Додаємо решту аргументів
    cmd.extend(args)

    print_header("ЗАПУСК ТЕСТІВ VentilationCompany2V")
    print(f"Команда: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))

    print_header("РЕЗУЛЬТАТ")
    if result.returncode == 0:
        print("✅ УСІ ТЕСТИ ПРОЙДЕНІ")
    else:
        print(f"❌ ТЕСТИ НЕ ПРОЙДЕНІ (код виходу: {result.returncode})")
        print("\nПідказки:")
        print("  • Якщо помилки імпорту — спробуйте очистити кеш:")
        print("      python -c \"import pathlib, shutil; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]\"")
        print("  • Якщо pytest не знайдено — встановіть:")
        print("      pip install pytest sqlalchemy")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
