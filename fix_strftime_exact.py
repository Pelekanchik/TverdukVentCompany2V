#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "ventilation_company", "db_integration.py")

with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

# 1. get_monthly_revenue
old1 = '''    def get_monthly_revenue(self, months: int = 12) -> list[dict]:
        """Виручка по місяцях."""
        since = (datetime.now() - timedelta(days=months * 31)).strftime("%Y-%m")
        with self._session_scope() as session:
            rows = (
                session.query(
                    func.strftime("%Y-%m", ClientProject.end_date).label("month"),
                    func.sum(ClientProject.total_amount).label("amount"),
                )
                .filter(
                    ClientProject.end_date.isnot(None),
                    ClientProject.end_date >= since + "-01",
                )
                .group_by("month")
                .order_by("month")
                .all()
            )
            return [{"month": r.month, "amount": float(r.amount or 0)} for r in rows]'''

new1 = '''    def get_monthly_revenue(self, months: int = 12) -> list[dict]:
        """Виручка по місяцях."""
        since = datetime.now() - timedelta(days=months * 31)
        with self._session_scope() as session:
            rows = (
                session.query(
                    func.to_char(ClientProject.end_date, 'YYYY-MM').label("month"),
                    func.sum(ClientProject.total_amount).label("amount"),
                )
                .filter(
                    ClientProject.end_date.isnot(None),
                    ClientProject.end_date >= since,
                )
                .group_by("month")
                .order_by("month")
                .all()
            )
            return [{"month": r.month, "amount": float(r.amount or 0)} for r in rows]'''

if old1 in txt:
    txt = txt.replace(old1, new1)
    print("✅ get_monthly_revenue — strftime → to_char")
else:
    print("⚠️  get_monthly_revenue — блок не знайдено")

# 2. get_monthly_project_status
old2 = '''    def get_monthly_project_status(self, months: int = 6) -> list[dict]:
        """Кількість проєктів по місяцях за статусами."""
        since = datetime.now() - timedelta(days=months * 31)
        with self._session_scope() as session:
            rows = (
                session.query(
                    func.strftime("%Y-%m", ClientProject.start_date).label("month"),
                    func.sum(
                        case((ClientProject.status == "в роботі", 1), else_=0)
                    ).label("active"),
                    func.sum(
                        case(
                            (ClientProject.status.in_(["завершено", "гарантія", "закрито"]), 1),
                            else_=0,
                        )
                    ).label("completed"),
                )
                .filter(
                    ClientProject.start_date.isnot(None),
                    ClientProject.start_date >= since,
                )
                .group_by("month")
                .order_by("month")
                .all()
            )
            return [
                {"month": r.month, "active": int(r.active or 0), "completed": int(r.completed or 0)}
                for r in rows
            ]'''

new2 = '''    def get_monthly_project_status(self, months: int = 6) -> list[dict]:
        """Кількість проєктів по місяцях за статусами."""
        since = datetime.now() - timedelta(days=months * 31)
        with self._session_scope() as session:
            rows = (
                session.query(
                    func.to_char(ClientProject.start_date, 'YYYY-MM').label("month"),
                    func.sum(
                        case((ClientProject.status == "в роботі", 1), else_=0)
                    ).label("active"),
                    func.sum(
                        case(
                            (ClientProject.status.in_(["завершено", "гарантія", "закрито"]), 1),
                            else_=0,
                        )
                    ).label("completed"),
                )
                .filter(
                    ClientProject.start_date.isnot(None),
                    ClientProject.start_date >= since,
                )
                .group_by("month")
                .order_by("month")
                .all()
            )
            return [
                {"month": r.month, "active": int(r.active or 0), "completed": int(r.completed or 0)}
                for r in rows
            ]'''

if old2 in txt:
    txt = txt.replace(old2, new2)
    print("✅ get_monthly_project_status — strftime → to_char")
else:
    print("⚠️  get_monthly_project_status — блок не знайдено")

# 3. get_monthly_avg_check
old3 = '''    def get_monthly_avg_check(self, months: int = 12) -> list[dict]:
        """Середній чек по місяцях."""
        since = (datetime.now() - timedelta(days=months * 31)).strftime("%Y-%m")
        with self._session_scope() as session:
            rows = (
                session.query(
                    func.strftime("%Y-%m", ClientProject.end_date).label("month"),
                    func.avg(ClientProject.total_amount).label("avg"),
                )
                .filter(
                    ClientProject.end_date.isnot(None),
                    ClientProject.end_date >= since + "-01",
                    ClientProject.total_amount > 0,
                )
                .group_by("month")
                .order_by("month")
                .all()
            )
            return [{"month": r.month, "avg": float(r.avg or 0)} for r in rows]'''

new3 = '''    def get_monthly_avg_check(self, months: int = 12) -> list[dict]:
        """Середній чек по місяцях."""
        since = datetime.now() - timedelta(days=months * 31)
        with self._session_scope() as session:
            rows = (
                session.query(
                    func.to_char(ClientProject.end_date, 'YYYY-MM').label("month"),
                    func.avg(ClientProject.total_amount).label("avg"),
                )
                .filter(
                    ClientProject.end_date.isnot(None),
                    ClientProject.end_date >= since,
                    ClientProject.total_amount > 0,
                )
                .group_by("month")
                .order_by("month")
                .all()
            )
            return [{"month": r.month, "avg": float(r.avg or 0)} for r in rows]'''

if old3 in txt:
    txt = txt.replace(old3, new3)
    print("✅ get_monthly_avg_check — strftime → to_char")
else:
    print("⚠️  get_monthly_avg_check — блок не знайдено")

with open(path, "w", encoding="utf-8") as f:
    f.write(txt)

print("\nТепер запустіть:  python main.py")
input("\nНатисніть Enter...")