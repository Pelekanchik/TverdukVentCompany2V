"""Tests for update version comparison."""

from ventilation_company.services.update_service import is_newer_version
from ventilation_company.version import __version__


def test_current_version_exists():
    assert __version__
    assert isinstance(__version__, str)


def test_newer_patch_version():
    assert is_newer_version("0.1.0", "v0.1.1")


def test_newer_minor_version():
    assert is_newer_version("0.1.0", "0.2.0")


def test_same_version_is_not_newer():
    assert not is_newer_version("0.1.0", "v0.1.0")


def test_older_version_is_not_newer():
    assert not is_newer_version("0.2.0", "v0.1.9")


def test_invalid_latest_is_not_newer():
    assert not is_newer_version("0.1.0", "latest")
