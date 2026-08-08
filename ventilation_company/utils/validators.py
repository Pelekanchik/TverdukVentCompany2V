"""
Модуль валідації даних
"""

import re
from datetime import datetime


def validate_project_number(value):
    pattern = r"^PR-\d{4}-\d{2}$"
    if not re.match(pattern, value):
        return False, "Nomer proektu maie buty u formati PR-XXXX-YY"
    return True, "OK"


def validate_positive_number(value, field_name="Znachennia"):
    try:
        num = float(value)
        if num <= 0:
            return False, f"{field_name} maie buty bilshym za 0"
        return True, "OK"
    except ValueError:
        return False, f"{field_name} maie buty chyslom"


def validate_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_date(date_str, fmt="%Y-%m-%d"):
    try:
        datetime.strptime(date_str, fmt)
        return True
    except ValueError:
        return False


def sanitize_filename(filename):
    return re.sub(r"[<>:\"/\\|?*]", "_", filename)
