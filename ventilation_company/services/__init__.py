"""Сервісний шар — бізнес-логіка, відокремлена від GUI.

Модулі:
 • product_validator — валідація параметрів виробів
 • product_builder — фабрика створення виробів
 • price_calculator — розрахунок цін
"""

from .product_validator import ProductValidator, ValidationError
from .product_builder import ProductBuilder
from .price_calculator import PriceCalculator

__all__ = ["ProductValidator", "ValidationError", "ProductBuilder", "PriceCalculator"]
