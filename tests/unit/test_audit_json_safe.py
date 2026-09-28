"""Регресійний тест: audit details мають бути JSON-безпечними (datetime/Decimal)."""

from datetime import date, datetime
from decimal import Decimal

from ventilation_company.services.audit_service import _json_safe


def test_json_safe_datetime_and_date():
    out = _json_safe({"created_at": datetime(2026, 9, 28, 7, 30), "day": date(2026, 9, 28)})
    assert out["created_at"] == "2026-09-28T07:30:00"
    assert out["day"] == "2026-09-28"


def test_json_safe_decimal():
    assert _json_safe(Decimal("12.50")) == 12.5


def test_json_safe_nested():
    out = _json_safe({"items": [{"when": datetime(2026, 1, 1)}, ("a", 1)]})
    assert out["items"][0]["when"] == "2026-01-01T00:00:00"
    assert out["items"][1] == ["a", 1]
