"""Tests for in-memory login rate limiting."""

from datetime import datetime, timedelta

from ventilation_company.auth.service import AuthService


def _clean_state():
    AuthService._login_attempts.clear()
    AuthService._login_lockouts.clear()


def test_lockout_after_five_failed_attempts():
    _clean_state()
    svc = AuthService()
    now = datetime(2026, 1, 1, 12, 0, 0)

    for i in range(5):
        svc._record_failed_attempt("user1", now=now + timedelta(seconds=i))

    assert svc._is_locked("user1", now=now + timedelta(seconds=20))


def test_lockout_expires():
    _clean_state()
    svc = AuthService()
    now = datetime(2026, 1, 1, 12, 0, 0)

    for i in range(5):
        svc._record_failed_attempt("user2", now=now + timedelta(seconds=i))

    assert not svc._is_locked("user2", now=now + timedelta(seconds=605))
    assert "user2" not in AuthService._login_lockouts


def test_clear_attempts_removes_lockout():
    _clean_state()
    svc = AuthService()
    now = datetime(2026, 1, 1, 12, 0, 0)

    for i in range(5):
        svc._record_failed_attempt("user3", now=now + timedelta(seconds=i))

    assert svc._is_locked("user3", now=now + timedelta(seconds=20))
    svc._clear_failed_attempts("user3")
    assert not svc._is_locked("user3", now=now + timedelta(seconds=20))
