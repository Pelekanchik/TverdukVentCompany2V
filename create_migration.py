#!/usr/bin/env python3
"""Створити нову міграцію Alembic (автогенерація з моделей)."""

import subprocess
import sys


def main():
    message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "auto"
    cmd = ["alembic", "revision", "--autogenerate", "-m", message]
    print("=" * 50)
    print("🔄 Створення міграції Alembic")
    print("=" * 50)
    print(f"Команда: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
