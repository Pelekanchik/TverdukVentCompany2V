"""GitHub release update checker."""

from __future__ import annotations

import re

import requests

from ventilation_company.version import __version__

GITHUB_RELEASES_API = (
    "https://api.github.com/repos/Pelekanchik/TverdukVentCompany2V/releases/latest"
)


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", value or "")
    if not match:
        return (0, 0, 0)
    return (
        int(match.group(1) or 0),
        int(match.group(2) or 0),
        int(match.group(3) or 0),
    )


def is_newer_version(current: str, latest: str) -> bool:
    """Simple semver-like comparison. Accepts tags like v0.1.1."""
    return _version_tuple(latest) > _version_tuple(current)


def get_latest_release(timeout: int = 5) -> dict | None:
    """Return latest GitHub release info or None on any network/API failure."""
    try:
        response = requests.get(GITHUB_RELEASES_API, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return {
            "tag": data.get("tag_name", ""),
            "name": data.get("name", ""),
            "url": data.get("html_url", ""),
            "published_at": data.get("published_at", ""),
        }
    except Exception:
        return None


def check_for_update() -> dict | None:
    """Return latest release only when it is newer than current app version."""
    latest = get_latest_release()
    if not latest:
        return None
    if is_newer_version(__version__, latest.get("tag", "")):
        latest["current_version"] = __version__
        return latest
    return None
