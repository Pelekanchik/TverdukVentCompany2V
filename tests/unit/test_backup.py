"""Тести автобекапу (ventilation_company.utils.backup)."""

import json
import subprocess
from pathlib import Path

from ventilation_company.utils import backup


def _pg_url() -> str:
    return "postgresql://u:p@localhost:5432/ventcompany"


def _fake_pg_tool(dump: Path):
    """Імітація pg_dump: створює dump-файл і повертає успішний результат."""

    def _run(args, url):
        dump.write_bytes(b"PGD")
        return subprocess.CompletedProcess(args, 0, "", "")

    return _run


# ── Резолвінг інструментів PostgreSQL ──


def testfind_pg_tool_prefers_path(monkeypatch):
    monkeypatch.setattr(backup.shutil, "which", lambda name: f"/usr/bin/{name}")
    assert backup.find_pg_tool("pg_dump") == "/usr/bin/pg_dump"


def testfind_pg_tool_falls_back_to_program_files(monkeypatch, tmp_path):
    monkeypatch.setattr(backup.shutil, "which", lambda name: None)
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path))
    tool = tmp_path / "PostgreSQL" / "16" / "bin" / "pg_dump.exe"
    tool.parent.mkdir(parents=True)
    tool.write_text("", encoding="utf-8")

    assert backup.find_pg_tool("pg_dump") == str(tool)


def testfind_pg_tool_returns_none_when_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(backup.shutil, "which", lambda name: None)
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path))
    assert backup.find_pg_tool("pg_dump") is None


# ── Створення бекапу ──


def test_create_backup_pg_failure_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(backup, "_database_url", lambda: _pg_url())
    monkeypatch.setattr(
        backup,
        "_run_pg_tool",
        lambda args, url: subprocess.CompletedProcess(args, 1, "", "boom"),
    )
    assert backup.create_backup(backup_dir=str(tmp_path)) is None
    assert list(tmp_path.iterdir()) == []


def test_create_backup_missing_tool_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(backup, "_database_url", lambda: _pg_url())
    monkeypatch.setattr(backup, "find_pg_tool", lambda name: None)
    assert backup.create_backup(backup_dir=str(tmp_path)) is None


def test_create_backup_copies_settings_json(monkeypatch, tmp_path):
    monkeypatch.setattr(backup, "_database_url", lambda: _pg_url())
    dump = tmp_path / "ventcompany_20261008_120000.dump"
    monkeypatch.setattr(
        backup,
        "_run_pg_tool",
        _fake_pg_tool(dump),
    )
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "pricing_settings.json").write_text("{}", encoding="utf-8")
    (data_dir / "business_settings.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(backup, "_settings_data_dir", lambda: data_dir)

    result = backup.create_backup(backup_dir=str(tmp_path))

    assert result is not None
    settings_copies = list(tmp_path.glob("ventcompany_*_settings_*.json"))
    assert len(settings_copies) == 2


# ── Ротація ──


def test_cleanup_rotates_backup_sets_by_stamp(monkeypatch, tmp_path):
    monkeypatch.setattr(backup, "_database_url", lambda: _pg_url())
    # 9 комплектів (dump + 1 json), різні штампи
    for i in range(9):
        stamp = f"2026100{i}_120000"
        (tmp_path / f"ventcompany_{stamp}.dump").write_bytes(b"x")
        (tmp_path / f"ventcompany_{stamp}_settings_pricing_settings.json").write_text(
            "{}", encoding="utf-8"
        )

    deleted = backup.cleanup_old_backups(backup_dir=str(tmp_path), keep=7)

    assert deleted == 4  # 2 комплекти × (dump + json)
    assert len(list(tmp_path.glob("*.dump"))) == 7
    assert len(list(tmp_path.glob("*_settings_*.json"))) == 7


# ── Автобекап при старті ──


def test_auto_backup_never_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(
        backup, "_database_url", lambda: (_ for _ in ()).throw(RuntimeError("no db"))
    )
    assert backup.auto_backup_on_start(backup_dir=str(tmp_path), keep=7) is None


def test_auto_backup_success_rotates(monkeypatch, tmp_path):
    monkeypatch.setattr(backup, "_database_url", lambda: _pg_url())
    monkeypatch.setattr(backup, "_auto_backup_preferences", lambda: (True, 7, str(tmp_path)))
    dump = tmp_path / "ventcompany_20261008_130000.dump"
    monkeypatch.setattr(
        backup,
        "_run_pg_tool",
        _fake_pg_tool(dump),
    )
    monkeypatch.setattr(backup, "_settings_data_dir", lambda: tmp_path / "no_data")

    result = backup.auto_backup_on_start(backup_dir=str(tmp_path), keep=7)

    assert result is not None and result.endswith(".dump")


# ── JSON-серіалізація dump-шляху у списку (регресія формату) ──


def test_backup_paths_are_plain_strings(monkeypatch, tmp_path):
    monkeypatch.setattr(backup, "_database_url", lambda: _pg_url())
    for stamp in ("20261008_120000", "20261009_120000"):
        (tmp_path / f"ventcompany_{stamp}.dump").write_bytes(b"x")

    backups = backup.list_backups(backup_dir=str(tmp_path))

    assert len(backups) == 2
    assert all(isinstance(p, str) for p in backups)
    assert json.dumps(backups)  # серіалізується без помилок


# ── Налаштування автобекапу (app.backup_*) ──


def test_auto_backup_disabled_skips(monkeypatch, tmp_path):
    monkeypatch.setattr(backup, "_auto_backup_preferences", lambda: (False, 7, str(tmp_path)))

    def _boom(*args, **kwargs):
        raise AssertionError("create_backup не повинен викликатися")

    monkeypatch.setattr(backup, "create_backup", _boom)
    assert backup.auto_backup_on_start() is None


def test_auto_backup_uses_preferences(monkeypatch, tmp_path):
    monkeypatch.setattr(backup, "_auto_backup_preferences", lambda: (True, 3, str(tmp_path)))
    dump = tmp_path / "ventcompany_20261008_140000.dump"
    monkeypatch.setattr(backup, "_run_pg_tool", _fake_pg_tool(dump))
    monkeypatch.setattr(backup, "_settings_data_dir", lambda: tmp_path / "no_data")

    result = backup.auto_backup_on_start()

    assert result is not None and result.endswith(".dump")


def test_preferences_defaults_when_db_unavailable(monkeypatch):
    # Імітуємо недоступність репозиторію: ламаємо імпорт всередині
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if "app_settings_repository" in name:
            raise ImportError("no module")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    enabled, keep, path = backup._auto_backup_preferences()
    assert enabled is True
    assert keep == 7
    assert path is None
