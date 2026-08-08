"""
Допоміжні функції
"""

import json
import os
from datetime import datetime


def generate_project_number():
    year = datetime.now().year % 100
    return f"PR-{1:04d}-{year:02d}"


def format_currency(amount):
    return f"{amount:,.2f} hrn"


def format_date(date_obj=None, fmt="%d.%m.%Y"):
    if date_obj is None:
        date_obj = datetime.now()
    return date_obj.strftime(fmt)


def save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(filepath):
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def calculate_area(length, width):
    return length * width


def calculate_duct_area(diameter, length):
    import math

    perimeter = math.pi * diameter
    return perimeter * length


def calculate_rect_duct_area(width, height, length):
    perimeter = 2 * (width + height)
    return perimeter * length
