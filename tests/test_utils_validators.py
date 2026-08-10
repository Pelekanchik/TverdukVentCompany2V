"""Тести для модуля validators."""

import pytest

from ventilation_company.utils.validators import (
    sanitize_filename,
    validate_date,
    validate_email,
    validate_positive_number,
    validate_project_number,
)


class TestValidateProjectNumber:
    """Тести валідації номера проєкту (regex)."""

    def test_valid_format(self):
        result = validate_project_number("PR-2024-01")
        assert result[0] is True
        assert result[1] == "OK"

    def test_invalid_format_no_dash(self):
        result = validate_project_number("PR202401")
        assert result[0] is False

    def test_invalid_format_short_year(self):
        result = validate_project_number("PR-2024-1")
        assert result[0] is False

    def test_empty_string(self):
        result = validate_project_number("")
        assert result[0] is False


class TestValidatePositiveNumber:
    """Тести валідації позитивних чисел."""

    def test_positive_integer(self):
        result = validate_positive_number(100, "Кількість")
        assert result[0] is True
        assert result[1] == "OK"

    def test_positive_float(self):
        result = validate_positive_number(150.5, "Ціна")
        assert result[0] is True

    def test_zero(self):
        result = validate_positive_number(0, "Кількість")
        assert result[0] is False
        assert "bilshym" in result[1].lower() or "більшим" in result[1].lower()

    def test_negative(self):
        result = validate_positive_number(-10, "Ціна")
        assert result[0] is False

    def test_string_not_number(self):
        result = validate_positive_number("abc", "Поле")
        assert result[0] is False
        assert "chyslom" in result[1].lower() or "числом" in result[1].lower()


class TestValidateEmail:
    """Тести валідації email."""

    def test_valid_email(self):
        assert validate_email("test@example.com") is True

    def test_valid_email_with_dots(self):
        assert validate_email("user.name@company.co.uk") is True

    def test_invalid_no_at(self):
        assert validate_email("testexample.com") is False

    def test_invalid_no_domain(self):
        assert validate_email("test@") is False

    def test_invalid_no_local(self):
        assert validate_email("@example.com") is False

    def test_invalid_spaces(self):
        assert validate_email("test @example.com") is False


class TestValidateDate:
    """Тести валідації дати."""

    def test_valid_date(self):
        assert validate_date("2026-08-10") is True

    def test_valid_date_custom_format(self):
        assert validate_date("10.08.2026", fmt="%d.%m.%Y") is True

    def test_invalid_date(self):
        assert validate_date("2026-13-45") is False

    def test_invalid_format(self):
        assert validate_date("10-08-2026") is False

    def test_empty_string(self):
        assert validate_date("") is False


class TestSanitizeFilename:
    """Тести очищення імені файлу."""

    def test_remove_invalid_chars(self):
        result = sanitize_filename("file<name>:test|?*.txt")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result

    def test_replacement_with_underscore(self):
        result = sanitize_filename("file:name.txt")
        assert "_" in result
        assert ":" not in result

    def test_valid_filename_unchanged(self):
        result = sanitize_filename("valid_filename.txt")
        assert result == "valid_filename.txt"
