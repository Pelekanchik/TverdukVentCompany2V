"""Політика паролів та хешування bcrypt для VentCompany.

Вимоги до паролю:
  • Мінімум 8 символів
  • Хоча б 1 велика літера (A-Z)
  • Хоча б 1 мала літера (a-z)
  • Хоча б 1 цифра (0-9)
  • Хоча б 1 спецсимвол (!@#$%^&*()_+-=[]{}|;:,.<>?)

Хешування:
  • bcrypt з salt (автоматично)
  • work factor = 12 (рекомендовано OWASP)
"""

import re
from typing import NamedTuple

import bcrypt


class PasswordValidationResult(NamedTuple):
    """Результат валідації паролю."""
    valid: bool
    errors: list[str]
    strength: str  # "weak" | "medium" | "strong"


# ── Валідація паролю ──────────────────────────────────────────

MIN_LENGTH = 8
SPECIAL_CHARS = r"!@#$%^&*()_+-=[]{}|;:,.<>?"


def validate_password(password: str) -> PasswordValidationResult:
    """Перевірити пароль на відповідність політиці.

    Повертає (valid, [errors], strength).
    """
    errors = []

    if len(password) < MIN_LENGTH:
        errors.append(f"Мінімум {MIN_LENGTH} символів")

    if not re.search(r"[A-Z]", password):
        errors.append("Хоча б 1 велика літера (A-Z)")

    if not re.search(r"[a-z]", password):
        errors.append("Хоча б 1 мала літера (a-z)")

    if not re.search(r"\d", password):
        errors.append("Хоча б 1 цифра (0-9)")

    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password):
        errors.append("Хоча б 1 спецсимвол (!@#$...)")

    # Оцінка сили
    strength = _calculate_strength(password)

    return PasswordValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        strength=strength,
    )


def _calculate_strength(password: str) -> str:
    """Оцінити силу паролю: weak / medium / strong."""
    score = 0
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"[a-z]", password):
        score += 1
    if re.search(r"\d", password):
        score += 1
    if re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password):
        score += 1

    if score <= 2:
        return "weak"
    elif score <= 4:
        return "medium"
    else:
        return "strong"


# ── Хешування bcrypt ─────────────────────────────────────────

BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """Хешувати пароль через bcrypt.

    Повертає рядок для зберігання в БД.
    """
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Перевірити пароль проти bcrypt-хешу.

    Повертає True, якщо пароль правильний.
    """
    try:
        pwd_bytes = password.encode("utf-8")
        hash_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False
