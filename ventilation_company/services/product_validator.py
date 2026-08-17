"""Валідація параметрів виробів.

Винесено з products_tab.py для розділення GUI і бізнес-логіки.
"""

from typing import Any


class ValidationError(ValueError):
    """Помилка валідації зі списком проблем."""
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


class ProductValidator:
    """Валідатор параметрів виробу."""

    @staticmethod
    def validate(
        width: Any,
        height: Any,
        length: Any,
        quantity: Any,
        height_visible: bool = True,
        length_visible: bool = True,
    ) -> dict[str, float | int]:
        """Валідувати вхідні параметри виробу.

        Args:
            width: Ширина/діаметр (мм)
            height: Висота (мм)
            length: Довжина (мм)
            quantity: Кількість
            height_visible: Чи видно поле висоти
            length_visible: Чи видно поле довжини

        Returns:
            Словник з валідованими значеннями

        Raises:
            ValidationError: Якщо є помилки валідації
        """
        errors: list[str] = []

        def _parse_float(value: Any, name: str, allow_zero: bool = False) -> float:
            try:
                v = float(str(value).replace(",", "."))
                if v < 0:
                    errors.append(f"'{name}' не може бути від'ємним")
                    return 0.0
                if not allow_zero and v == 0:
                    errors.append(f"'{name}' має бути більше 0")
                    return 0.0
                return v
            except (ValueError, TypeError):
                errors.append(f"'{name}' має бути числом")
                return 0.0

        def _parse_int(value: Any, name: str) -> int:
            try:
                v = int(float(str(value).replace(",", ".")))
                if v < 0:
                    errors.append(f"'{name}' не може бути від'ємним")
                    return 0
                if v == 0:
                    errors.append(f"'{name}' має бути більше 0")
                    return 0
                return v
            except (ValueError, TypeError):
                errors.append(f"'{name}' має бути цілим числом")
                return 0

        w = _parse_float(width, "Ширина/Діаметр")
        h = _parse_float(height, "Висота") if height_visible else w
        l = _parse_float(length, "Довжина", allow_zero=True) if length_visible else 0.0
        qty = _parse_int(quantity, "Кількість")

        if errors:
            raise ValidationError(errors)

        return {"width": w, "height": h, "length": l, "quantity": qty}
