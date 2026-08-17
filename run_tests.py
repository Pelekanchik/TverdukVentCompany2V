#!/usr/bin/env python3
"""
Запуск всіх тестів VentCompany v2.1

Використання:
    python run_tests.py              → запуск усіх тестів
    python run_tests.py -v           → детальний вивід
    python run_tests.py -k pricing   → тільки тести зі словом "pricing"
    python run_tests.py --cov        → з покриттям коду (потрібен pytest-cov)
"""

import subprocess
import sys


def main():
    args = ["pytest", "tests/", "-v", "--tb=short"]

    # Додаємо додаткові аргументи з командного рядка
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])

    print("=" * 60)
    print("🧪 Запуск тестів VentCompany v2.1")
    print("=" * 60)
    print(f"Команда: {' '.join(args)}\n")

    result = subprocess.run(args)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
