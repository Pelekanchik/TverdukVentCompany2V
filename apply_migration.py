#!/usr/bin/env python3
"""Застосувати всі міграції Alembic (upgrade to head)."""

import subprocess
import sys


def main():
    cmd = ["alembic", "upgrade", "head"]
    print("=" * 50)
    print("⬆️  Застосування міграцій Alembic")
    print("=" * 50)
    print(f"Команда: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
