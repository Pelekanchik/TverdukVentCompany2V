"""Утиліти для роботи з грошовими сумами (Decimal).

Використовує Decimal замість float для уникнення помилок округлення:
  float:  0.1 + 0.2 = 0.30000000000000004  ❌
  Decimal: Decimal('0.1') + Decimal('0.2') = Decimal('0.3')  ✅
"""

from decimal import Decimal, ROUND_HALF_UP

# Контекст для всіх грошових операцій
MONEY_CONTEXT = Decimal('0.01')  # точність до копійки


def to_decimal(value, default=Decimal('0')) -> Decimal:
    """Безпечне перетворення в Decimal.

    Приймає: str, int, float, Decimal, None
    Повертає: Decimal
    """
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        # Конвертуємо float через str, щоб уникнути двійкового представлення
        return Decimal(str(value))
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        value = value.strip().replace(',', '.').replace(' ', '')
        if not value:
            return default
        try:
            return Decimal(value)
        except Exception:
            return default
    return default


def money_round(value: Decimal | float | str, places: int = 2) -> Decimal:
    """Округлити до вказаної кількості знаків (за замовчуванням 2 — копійки)."""
    d = to_decimal(value)
    quantize_str = '0.' + '0' * places
    return d.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)


def money_format(value: Decimal | float | str, places: int = 2) -> str:
    """Форматувати для відображення: 1234.5 → '1 234.50'"""
    d = money_round(value, places)
    # Розділяємо тисячі пробілом
    s = str(d)
    if '.' in s:
        int_part, frac_part = s.split('.')
    else:
        int_part, frac_part = s, ''

    # Додаємо пробіли для тисяч
    int_part = f"{int(int_part):,}".replace(',', ' ')

    if places > 0:
        frac_part = (frac_part + '0' * places)[:places]
        return f"{int_part}.{frac_part}"
    return int_part


def money_sum(values: list, places: int = 2) -> Decimal:
    """Сума списку значень з округленням."""
    total = sum(to_decimal(v) for v in values)
    return money_round(total, places)


# Короткі аліаси для зручності
D = to_decimal
R = money_round
F = money_format
