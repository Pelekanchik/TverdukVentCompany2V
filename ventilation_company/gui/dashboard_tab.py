"""Дашборд для директора — графіки та KPI."""

import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ventilation_company.db_integration import ProjectDatabase


class DashboardTab:
    """Вкладка дашборду з графіками для директора."""

    def __init__(self, parent: ttk.Notebook):
        self.frame = ttk.Frame(parent)
        self.db = ProjectDatabase()
        self._build_ui()
        self._refresh_all()

    def _build_ui(self):
        # Toolbar
        tbar = ttk.Frame(self.frame, padding=5)
        tbar.pack(fill=tk.X)

        ttk.Label(tbar, text="📊 Дашборд", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        ttk.Separator(tbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(tbar, text="🔄 Оновити", command=self._refresh_all).pack(side=tk.LEFT, padx=2)

        # KPI картки (верхній ряд)
        self.kpi_frame = ttk.Frame(self.frame, padding=10)
        self.kpi_frame.pack(fill=tk.X)

        self.kpi_labels = {}
        kpi_names = [
            ("total_revenue", "💰 Виручка", "0 грн"),
            ("avg_check", "Середній чек", "0 грн"),
            ("active_projects", "🏗️ Активні проєкти", "0"),
            ("overdue_projects", "⏰ Прострочено", "0"),
            ("total_clients", "👥 Клієнтів", "0"),
        ]
        for key, title, default in kpi_names:
            frm = ttk.LabelFrame(self.kpi_frame, text=title, padding=10)
            frm.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
            lbl = ttk.Label(frm, text=default, font=("Arial", 16, "bold"))
            lbl.pack()
            self.kpi_labels[key] = lbl

        # Графіки
        self.fig = plt.Figure(figsize=(14, 8), dpi=90, facecolor="#fafafa")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Статус
        self.status = ttk.Label(self.frame, text="Готово", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def _refresh_all(self):
        self.fig.clear()
        self._update_kpi()
        self._draw_profit_chart()
        self._draw_workload_chart()
        self._draw_top_clients_chart()
        self._draw_status_chart()
        self._draw_monthly_revenue_chart()
        self.fig.tight_layout(pad=3.0)
        self.canvas.draw()
        self.status.config(text=f"Оновлено: {datetime.now().strftime('%H:%M:%S')}")

    def _update_kpi(self):
        stats = self.db.get_dashboard_stats()
        self.kpi_labels["total_revenue"].config(text=f"{stats.get('total_revenue', 0):,.0f} грн")
        self.kpi_labels["avg_check"].config(text=f"{stats.get('avg_check', 0):,.0f} грн")
        self.kpi_labels["active_projects"].config(text=str(stats.get('active_projects', 0)))
        self.kpi_labels["overdue_projects"].config(text=str(stats.get('overdue_projects', 0)))
        self.kpi_labels["total_clients"].config(text=str(stats.get('total_clients', 0)))

    def _draw_profit_chart(self):
        """Прибуток по місяцях (останні 12 міс)."""
        data = self.db.get_monthly_revenue(months=12)
        ax = self.fig.add_subplot(2, 3, 1)
        if data:
            months = [d["month"] for d in data]
            amounts = [d["amount"] for d in data]
            ax.bar(months, amounts, color="#2196F3", edgecolor="white", linewidth=0.5)
            ax.set_title("Виручка по місяцях", fontsize=10, fontweight="bold")
            ax.set_ylabel("грн", fontsize=8)
            ax.tick_params(axis="x", rotation=45, labelsize=7)
            ax.tick_params(axis="y", labelsize=7)
            ax.grid(axis="y", alpha=0.3)
        else:
            ax.text(0.5, 0.5, "Немає даних", ha="center", va="center", transform=ax.transAxes)
            ax.set_title("Виручка по місяцях", fontsize=10)
        ax.set_axisbelow(True)

    def _draw_workload_chart(self):
        """Завантаження цеху: проєкти в роботі vs завершено."""
        data = self.db.get_project_status_counts()
        ax = self.fig.add_subplot(2, 3, 2)
        if data:
            labels = list(data.keys())
            values = list(data.values())
            colors = ["#4CAF50", "#FF9800", "#F44336", "#9E9E9E"]
            ax.pie(values, labels=labels, autopct="%1.0f%%", colors=colors[:len(labels)],
                   textprops={"fontsize": 8}, startangle=90)
            ax.set_title("Завантаження цеху", fontsize=10, fontweight="bold")
        else:
            ax.text(0.5, 0.5, "Немає даних", ha="center", va="center", transform=ax.transAxes)
            ax.set_title("Завантаження цеху", fontsize=10)

    def _draw_top_clients_chart(self):
        """ТОП-5 клієнтів за виручкою."""
        data = self.db.get_top_clients(limit=5)
        ax = self.fig.add_subplot(2, 3, 3)
        if data:
            names = [d["name"][:15] for d in data]
            amounts = [d["total"] for d in data]
            ax.barh(names, amounts, color="#673AB7", edgecolor="white", linewidth=0.5)
            ax.set_title("ТОП-5 клієнтів", fontsize=10, fontweight="bold")
            ax.set_xlabel("грн", fontsize=8)
            ax.tick_params(axis="both", labelsize=7)
            ax.invert_yaxis()
            ax.grid(axis="x", alpha=0.3)
        else:
            ax.text(0.5, 0.5, "Немає даних", ha="center", va="center", transform=ax.transAxes)
            ax.set_title("ТОП-5 клієнтів", fontsize=10)
        ax.set_axisbelow(True)

    def _draw_status_chart(self):
        """Динаміка статусів проєктів по місяцях."""
        data = self.db.get_monthly_project_status(months=6)
        ax = self.fig.add_subplot(2, 3, 4)
        if data:
            months = [d["month"] for d in data]
            active = [d.get("active", 0) for d in data]
            completed = [d.get("completed", 0) for d in data]
            x = range(len(months))
            width = 0.35
            ax.bar([i - width/2 for i in x], active, width, label="В роботі", color="#FF9800")
            ax.bar([i + width/2 for i in x], completed, width, label="Завершено", color="#4CAF50")
            ax.set_xticks(x)
            ax.set_xticklabels(months, rotation=45, fontsize=7)
            ax.set_title("Динаміка проєктів", fontsize=10, fontweight="bold")
            ax.legend(fontsize=7)
            ax.tick_params(axis="y", labelsize=7)
            ax.grid(axis="y", alpha=0.3)
        else:
            ax.text(0.5, 0.5, "Немає даних", ha="center", va="center", transform=ax.transAxes)
            ax.set_title("Динаміка проєктів", fontsize=10)
        ax.set_axisbelow(True)

    def _draw_monthly_revenue_chart(self):
        """Середній чек по місяцях."""
        data = self.db.get_monthly_avg_check(months=12)
        ax = self.fig.add_subplot(2, 3, 5)
        if data:
            months = [d["month"] for d in data]
            avg = [d["avg"] for d in data]
            ax.plot(months, avg, marker="o", color="#E91E63", linewidth=2, markersize=4)
            ax.fill_between(months, avg, alpha=0.2, color="#E91E63")
            ax.set_title("Середній чек", fontsize=10, fontweight="bold")
            ax.set_ylabel("грн", fontsize=8)
            ax.tick_params(axis="x", rotation=45, labelsize=7)
            ax.tick_params(axis="y", labelsize=7)
            ax.grid(alpha=0.3)
        else:
            ax.text(0.5, 0.5, "Немає даних", ha="center", va="center", transform=ax.transAxes)
            ax.set_title("Середній чек", fontsize=10)
        ax.set_axisbelow(True)

    def _draw_overdue_chart(self):
        """Прострочені проєкти (порожній слот — можна прибрати або залишити)."""
        # Використовуємо як додатковий графік або залишаємо порожнім
        ax = self.fig.add_subplot(2, 3, 6)
        overdue = self.db.get_overdue_projects()
        if overdue:
            names = [p["project_name"][:20] for p in overdue[:5]]
            days = [(datetime.now() - datetime.fromisoformat(p["end_date"])).days for p in overdue[:5]]
            ax.barh(names, days, color="#F44336", edgecolor="white", linewidth=0.5)
            ax.set_title("Прострочення (дні)", fontsize=10, fontweight="bold")
            ax.set_xlabel("днів", fontsize=8)
            ax.tick_params(axis="both", labelsize=7)
            ax.invert_yaxis()
            ax.grid(axis="x", alpha=0.3)
        else:
            ax.text(0.5, 0.5, "Немає прострочень", ha="center", va="center", transform=ax.transAxes)
            ax.set_title("Прострочення", fontsize=10)
        ax.set_axisbelow(True)
