"""Tests for SystemService error handling."""

from ventilation_company.services import system_service as svc


def test_package_version_returns_unknown_for_missing_package():
    assert svc.SystemService.package_version("definitely-not-installed-package-xyz") == "невідомо"


def test_db_stats_returns_error_string_when_db_fails(monkeypatch):
    class BrokenConnection:
        def __enter__(self):
            raise RuntimeError("db down")

        def __exit__(self, exc_type, exc, tb):
            return False

    class BrokenEngine:
        def connect(self):
            return BrokenConnection()

    monkeypatch.setattr(svc, "engine", BrokenEngine())

    assert svc.SystemService.db_stats().startswith("❌ Помилка:")


def test_system_stats_returns_error_string_when_session_fails(monkeypatch):
    def broken_session_local():
        raise RuntimeError("db down")

    monkeypatch.setattr(svc, "SessionLocal", broken_session_local)

    assert svc.SystemService.system_stats().startswith("❌ Помилка:")
