"""Tests for SettingsRepository."""

from __future__ import annotations

from ventilation_company.database.repositories.settings_repo import SettingsRepository


class TestSettingsRepository:
    """CRUD tests for settings."""

    def test_set_and_get_value(self, db_session):
        repo = SettingsRepository(db_session)
        repo.set_value("markup_default", "30")
        assert repo.get_value("markup_default") == "30"

    def test_get_value_default(self, db_session):
        repo = SettingsRepository(db_session)
        assert repo.get_value("nonexistent_key", "fallback") == "fallback"

    def test_get_int(self, db_session):
        repo = SettingsRepository(db_session)
        repo.set_value("workers_count", "5")
        assert repo.get_int("workers_count") == 5
        assert repo.get_int("missing", 10) == 10

    def test_get_float(self, db_session):
        repo = SettingsRepository(db_session)
        repo.set_value("rate_per_hour", "150.5")
        assert repo.get_float("rate_per_hour") == 150.5
        assert repo.get_float("missing", 99.9) == 99.9

    def test_update_existing(self, db_session):
        repo = SettingsRepository(db_session)
        repo.set_value("theme", "dark")
        repo.set_value("theme", "light")
        assert repo.get_value("theme") == "light"

    def test_delete(self, db_session):
        repo = SettingsRepository(db_session)
        repo.set_value("temp", "123")
        assert repo.delete("temp") is True
        assert repo.get_value("temp") is None
        assert repo.delete("temp") is False
