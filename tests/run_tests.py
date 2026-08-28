#!/usr/bin/env python3
"""Запуск тестів VentCompany."""

import subprocess
import sys

def main():
    print("🧪 Запуск тестів VentCompany...")
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"])
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
