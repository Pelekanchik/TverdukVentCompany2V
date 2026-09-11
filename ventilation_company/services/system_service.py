"""System and DB diagnostics service."""

from __future__ import annotations

import os

from ventilation_company.database.base import Base
from ventilation_company.database.db import (
    SessionLocal,
    check_db_connection,
    engine,
)
from ventilation_company.database.models.calc import CalcSetting
from ventilation_company.database.models.project import Project
from ventilation_company.database.models.user import UserORM


class SystemService:
    """Read-only system/DB diagnostics used by ProgramSettingsTab."""

    @staticmethod
    def test_connection() -> tuple[bool, str]:
        """Return (connected, info_text)."""
        if not check_db_connection():
            return False, ""
        try:
            from sqlalchemy import text

            with engine.connect() as conn:
                version = conn.execute(text("SELECT version()")).scalar()
                return True, str(version)[:150]
        except Exception as exc:
            return True, f"Помилка: {exc}"

    @staticmethod
    def create_tables() -> None:
        Base.metadata.create_all(bind=engine)

    @staticmethod
    def db_stats() -> str:
        try:
            from sqlalchemy import text

            stats = []
            with engine.connect() as conn:
                size_row = conn.execute(
                    text("SELECT pg_size_pretty(pg_database_size(current_database()))")
                ).scalar()
                stats.append(f"📦 Розмір БД: {size_row}")

                tables = conn.execute(
                    text(
                        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
                    )
                ).scalar()
                stats.append(f"📋 Таблиць: {tables}")

                for tbl in [
                    "projects",
                    "users",
                    "project_products",
                    "clients",
                    "calc_calculations",
                ]:
                    try:
                        cnt = conn.execute(text(f"SELECT count(*) FROM {tbl}")).scalar()
                        stats.append(f"   • {tbl}: {cnt} записів")
                    except Exception:
                        pass
            return "\n".join(stats)
        except Exception as exc:
            return f"❌ Помилка: {exc}"

    @staticmethod
    def package_version(pkg: str) -> str:
        try:
            import importlib.metadata

            return importlib.metadata.version(pkg)
        except Exception:
            return "невідомо"

    @staticmethod
    def system_stats() -> str:
        try:
            session = SessionLocal()
            stats = [
                f"📋 Проєктів у БД: {session.query(Project).count()}",
                f"👥 Користувачів: {session.query(UserORM).count()}",
                f"⚙️ Налаштувань: {session.query(CalcSetting).count()}",
            ]
            session.close()

            total_size = 0
            if os.path.exists("data"):
                for dirpath, _dirnames, filenames in os.walk("data"):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        total_size += os.path.getsize(fp)
            stats.append(f"📦 Розмір data/: {total_size / 1024 / 1024:.1f} МБ")

            return "\n".join(stats)
        except Exception as exc:
            return f"❌ Помилка: {exc}"
