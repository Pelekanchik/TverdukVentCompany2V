"""GitHub release update checker and downloader."""

from __future__ import annotations

import re
from pathlib import Path

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
        asset_url = ""
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if name.endswith(".zip"):
                asset_url = asset.get("browser_download_url", "")
                break
        return {
            "tag": data.get("tag_name", ""),
            "name": data.get("name", ""),
            "url": data.get("html_url", ""),
            "published_at": data.get("published_at", ""),
            "asset_url": asset_url,
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


def download_release_asset(release_info: dict, target_dir: str | Path = "updates") -> str:
    """Download release ZIP into target_dir and return local file path."""
    asset_url = release_info.get("asset_url") or ""
    if not asset_url:
        raise RuntimeError("У релізі не знайдено ZIP-файл оновлення.")

    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    filename = release_info.get("asset_name") or "VentCompany-windows.zip"
    output = target / filename

    with requests.get(asset_url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(output, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return str(output)
