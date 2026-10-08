"""Тести хмарного бекапу (ventilation_company.utils.cloud_backup)."""

from pathlib import Path

from ventilation_company.utils import cloud_backup


class _FakeResponse:
    def __init__(self, status: int = 200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


# ── Визначення хмарних тек ──


def test_detect_cloud_folders_finds_existing(monkeypatch, tmp_path):
    (tmp_path / "OneDrive").mkdir()
    (tmp_path / "Dropbox").mkdir()
    monkeypatch.setattr(cloud_backup.Path, "home", classmethod(lambda cls: tmp_path))

    found = cloud_backup.detect_cloud_folders()

    names = {name for name, _path in found}
    assert "OneDrive" in names
    assert "Dropbox" in names


def test_detect_cloud_folders_skips_missing(monkeypatch, tmp_path):
    (tmp_path / "Google Drive").mkdir()
    monkeypatch.setattr(cloud_backup.Path, "home", classmethod(lambda cls: tmp_path))

    found = cloud_backup.detect_cloud_folders()

    assert [name for name, _p in found] == ["Google Drive"]


# ── Telegram ──


def test_send_telegram_document_success(monkeypatch, tmp_path):
    file = tmp_path / "ventcompany_20261008_120000.dump"
    file.write_bytes(b"PGD")
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["timeout"] = timeout
        captured["content_type"] = req.headers.get("Content-type") or req.headers.get(
            "Content-Type"
        )
        return _FakeResponse(200)

    monkeypatch.setattr(cloud_backup.urlrequest, "urlopen", fake_urlopen)

    assert cloud_backup.send_telegram_document("TOKEN", "42", str(file), "підпис") is True
    assert "botTOKEN/sendDocument" in captured["url"]
    assert captured["timeout"] == 60


def test_send_telegram_document_failure_returns_false(monkeypatch, tmp_path):
    file = tmp_path / "b.dump"
    file.write_bytes(b"x")

    def fake_urlopen(req, timeout):
        raise OSError("no network")

    monkeypatch.setattr(cloud_backup.urlrequest, "urlopen", fake_urlopen)

    assert cloud_backup.send_telegram_document("TOKEN", "42", str(file)) is False


def test_send_telegram_document_skips_oversized(monkeypatch, tmp_path):
    file = tmp_path / "big.dump"
    file.write_bytes(b"x" * 1024)
    monkeypatch.setattr(cloud_backup, "TELEGRAM_MAX_BYTES", 10)
    called = []

    def fake_urlopen(req, timeout):
        called.append(req)
        return _FakeResponse(200)

    monkeypatch.setattr(cloud_backup.urlrequest, "urlopen", fake_urlopen)

    assert cloud_backup.send_telegram_document("TOKEN", "42", str(file)) is False
    assert called == []


def test_send_telegram_document_missing_file(monkeypatch):
    called = []

    def fake_urlopen(req, timeout):
        called.append(req)
        return _FakeResponse(200)

    monkeypatch.setattr(cloud_backup.urlrequest, "urlopen", fake_urlopen)

    assert cloud_backup.send_telegram_document("TOKEN", "42", "nope.dump") is False
    assert called == []


# ── Копіювання у хмарні теки ──


def test_copy_to_cloud_folders(monkeypatch, tmp_path):
    cloud = tmp_path / "OneDrive"
    cloud.mkdir()
    monkeypatch.setattr(cloud_backup.Path, "home", classmethod(lambda cls: tmp_path))
    dump = tmp_path / "ventcompany_20261008_120000.dump"
    dump.write_bytes(b"PGD")

    copied = cloud_backup.copy_to_cloud_folders(str(dump))

    assert len(copied) == 1
    dest = Path(copied[0])
    assert dest.parent.name == cloud_backup.CLOUD_SUBFOLDER
    assert dest.read_bytes() == b"PGD"


def test_cleanup_cloud_folders_rotates(monkeypatch, tmp_path):
    cloud = tmp_path / "OneDrive" / cloud_backup.CLOUD_SUBFOLDER
    cloud.mkdir(parents=True)
    for i in range(9):
        (cloud / f"ventcompany_2026100{i}_120000.dump").write_bytes(b"x")
    monkeypatch.setattr(cloud_backup.Path, "home", classmethod(lambda cls: tmp_path))

    deleted = cloud_backup.cleanup_cloud_folders(keep=7)

    assert deleted == 2
    assert len(list(cloud.glob("*.dump"))) == 7


# ── Загальна відправка ──


def test_upload_backup_sends_telegram_only_with_credentials(monkeypatch, tmp_path):
    file = tmp_path / "b.dump"
    file.write_bytes(b"x")
    sent = []
    monkeypatch.setattr(
        cloud_backup,
        "send_telegram_document",
        lambda *a, **kw: sent.append((a, kw)) or True,
    )
    monkeypatch.setattr(cloud_backup, "copy_to_cloud_folders", lambda p: [])
    monkeypatch.setattr(cloud_backup, "build_backup_report", lambda p: str(tmp_path / "звіт.txt"))

    result = cloud_backup.upload_backup(str(file), token="T", chat="C")
    assert result["telegram"] is True
    assert len(sent) == 2  # дамп + звіт
    assert sent[0][0][2] == str(file)
    assert sent[1][0][2].endswith(".txt")

    result = cloud_backup.upload_backup(str(file), token="", chat="")
    assert result["telegram"] is None
    assert len(sent) == 2  # додаткових викликів не було


def test_upload_backup_never_raises(monkeypatch, tmp_path):
    file = tmp_path / "b.dump"
    file.write_bytes(b"x")

    def boom(*a, **kw):
        raise RuntimeError("мережа впала")

    monkeypatch.setattr(cloud_backup, "send_telegram_document", boom)
    monkeypatch.setattr(cloud_backup, "copy_to_cloud_folders", boom)

    result = cloud_backup.upload_backup(str(file), token="T", chat="C")

    assert result["telegram"] is False
    assert result["folders"] == []


# ── Інтеграція з автобекапом ──


def test_auto_backup_triggers_cloud_upload_when_enabled(monkeypatch, tmp_path):
    from ventilation_company.utils import backup

    monkeypatch.setattr(backup, "_database_url", lambda: "postgresql://u:p@h:5432/db")
    monkeypatch.setattr(backup, "_auto_backup_preferences", lambda: (True, 7, str(tmp_path)))
    dump = tmp_path / "ventcompany_20261008_150000.dump"

    import subprocess

    monkeypatch.setattr(
        backup,
        "_run_pg_tool",
        lambda args, url: subprocess.CompletedProcess(args, 0, "", "") or dump.write_bytes(b"PGD"),
    )
    monkeypatch.setattr(backup, "_settings_data_dir", lambda: tmp_path / "no_data")

    uploads = []
    monkeypatch.setattr(backup, "_cloud_upload", lambda path, keep: uploads.append(path))

    result = backup.auto_backup_on_start(backup_dir=str(tmp_path), keep=7)

    assert result is not None
    assert uploads == [result]


def test_cloud_upload_disabled_is_noop(monkeypatch):
    from ventilation_company.utils import backup, cloud_backup

    monkeypatch.setattr(cloud_backup, "cloud_backup_preferences", lambda: (False, "T", "C"))
    assert backup._cloud_upload("some.dump", 7) is None


# ── Звіт до бекапу ──


def test_build_backup_report_survives_broken_db(monkeypatch, tmp_path):
    """Зламана БД не ламає звіт — лишаються дата й розмір дампу."""

    def broken_stats():
        raise RuntimeError("БД недоступна")

    monkeypatch.setattr(cloud_backup, "_collect_backup_stats", broken_stats)
    dump = tmp_path / "ventcompany_20261008_210000.dump"
    dump.write_bytes(b"x" * 2048)

    report = cloud_backup.build_backup_report(str(dump))

    text = Path(report).read_text(encoding="utf-8")
    assert "Дата створення копії" in text
    assert "0,00 МБ" in text or "МБ" in text
    assert "недоступна" in text


def test_build_backup_report_contains_dump_size(monkeypatch, tmp_path):
    monkeypatch.setattr(
        cloud_backup, "_collect_backup_stats", lambda: ["Статистика БД", "Проєктів усього: 5"]
    )
    dump = tmp_path / "ventcompany_20261008_210000.dump"
    dump.write_bytes(b"x" * 5 * 1024 * 1024)  # 5 МБ

    report = cloud_backup.build_backup_report(str(dump))

    text = Path(report).read_text(encoding="utf-8")
    assert "5.00 МБ" in text
    assert "ventcompany_20261008_210000.dump" in text
    assert "Проєктів усього: 5" in text
    # той самий штамп у назві звіту
    assert Path(report).name == "ventcompany_20261008_210000_звіт.txt"


def test_upload_backup_report_failure_keeps_result(monkeypatch, tmp_path):
    """Помилка надсилання звіту не псує успішний результат дампу."""
    file = tmp_path / "b.dump"
    file.write_bytes(b"x")
    sent = []

    def fake_send(token, chat, path, caption=""):
        sent.append(path)
        if path.endswith(".txt"):
            raise RuntimeError("Telegram відмовив")
        return True

    monkeypatch.setattr(cloud_backup, "send_telegram_document", fake_send)
    monkeypatch.setattr(cloud_backup, "copy_to_cloud_folders", lambda p: [])
    monkeypatch.setattr(cloud_backup, "build_backup_report", lambda p: str(tmp_path / "звіт.txt"))

    result = cloud_backup.upload_backup(str(file), token="T", chat="C")

    assert result["telegram"] is True
    assert len(sent) == 2
