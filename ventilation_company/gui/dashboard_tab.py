"""Дашборд для директора — графіки та KPI (Industrial Orange Edition)."""

import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ventilation_company.db_integration import ProjectDatabase
from ventilation_company.gui.theme_manager import get_theme_manager


class DashboardTab:
    """Вкладка дашборду з покращеними графіками та KPI."""

    def __init__(self, parent: ttk.Notebook):
        self.frame = ttk.Frame(parent)
        self.db = ProjectDatabase()
        self._build_ui()
        self._refresh_all()

    def _build_ui(self):
        theme = get_theme_manager().get()

        # ── Toolbar ──
        tbar = tk.Frame(self.frame, bg=theme["bg"])
        tbar.pack(fill=tk.X, padx=10, pady=(10, 0))

        tk.Label(tbar, text="📊 Дашборд", font=("Segoe UI", 16, "bold"),
                 bg=theme["bg"], fg=theme["fg"]).pack(side=tk.LEFT, padx=5)
        ttk.Separator(tbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(tbar, text="🔄 Оновити", command=self._refresh_all).pack(side=tk.LEFT, padx=2)

        # ── KPI картки (верхній ряд) ──
        self.kpi_frame = tk.Frame(self.frame, bg=theme["bg"])
        self.kpi_frame.pack(fill=tk.X, padx=10, pady=10)

        self.kpi_data = [
            ("total_revenue", "💰 Виручка", "0 грн", theme["kpi_revenue"]),
            ("avg_check", "📈 Середній чек", "0 грн", theme["kpi_projects"]),
            ("active_projects", "🏗️ Активні проєкти", "0", theme["kpi_utilization"]),
            ("overdue_projects", "⏰ Прострочено", "0", theme["kpi_overdue"]),
            ("total_clients", "👥 Клієнтів", "0", theme["kpi_clients"]),
        ]

        self.kpi_labels = {}
        self.kpi_frames = {}

        for key, title, default, color in self.kpi_data:
            frm = tk.Frame(
                self.kpi_frame,
                bg=theme["frame_bg"],
                highlightbackground=color,
                highlightthickness=2,
                padx=14,
                pady=14,
            )
            frm.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

            # Іконка + заголовок
            hdr = tk.Label(frm, text=title, font=("Segoe UI", 10, "bold"),
                           bg=theme["frame_bg"], fg=theme["fg_secondary"])
            hdr.pack(anchor="w")

            # Значення
            lbl = tk.Label(frm, text=default, font=("Segoe UI", 22, "bold"),
                           bg=theme["frame_bg"], fg=color)
            lbl.pack(anchor="w", pady=(4, 0))

            # Індикатор-лінія
            line = tk.Frame(frm, bg=color, height=3)
            line.pack(fill=tk.X, pady=(8, 0))

            self.kpi_labels[key] = lbl
            self.kpi_frames[key] = frm

        # ── Графіки ──
        self.fig = plt.Figure(figsize=(14, 8), dpi=90, facecolor=theme["chart_bg"])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().configure(bg=theme["chart_bg"])
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ── Статус ──
        self.status = tk.Label(
            self.frame, text="Готово", relief=tk.SUNKEN, anchor=tk.W,
            bg=theme["status_bg"], fg=theme["status_fg"],
            font=("Segoe UI", 9),
        )
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def _refresh_all(self):
        theme = get_theme_manager().get()
        self.fig.clear()
        self.fig.set_facecolor(theme["chart_bg"])
        self.canvas.get_tk_widget().configure(bg=theme["chart_bg"])

        # Оновити KPI кольори
        for key, frm in self.kpi_frames.items():
            color = next(c for k, _, _, c in self.kpi_data if k == key)
            frm.configure(bg=theme["frame_bg"], highlightbackground=color)
            for child in frm.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=theme["frame_bg"])
                elif isinstance(child, tk.Frame):
                    child.configure(bg=color)

        self._update_kpi()
        self._draw_profit_chart()
        self._draw_workload_chart()
        self._draw_top_clients_chart()
        self._draw_status_chart()
        self._draw_monthly_revenue_chart()
        self._draw_overdue_chart()
        self.fig.tight_layout(pad=3.0)
        self.canvas.draw()
        self.status.config(
            text=f"Оновлено: {datetime.now().strftime('%H:%M:%S')}",
            bg=theme["status_bg"], fg=theme["status_fg"],
        )

    def _update_kpi(self):
        stats = self.db.get_dashboard_stats()
        theme = get_theme_manager().get()

        self.kpi_labels["total_revenue"].config(
            text=f"{stats.get('total_revenue', 0):,.0f} грн",
            fg=theme["kpi_revenue"],
        )
        self.kpi_labels["avg_check"].config(
            text=f"{stats.get('avg_check', 0):,.0f} грн",
            fg=theme["kpi_projects"],
        )
        self.kpi_labels["active_projects"].config(
            text=str(stats.get('active_projects', 0)),
            fg=theme["kpi_utilization"],
        )
        self.kpi_labels["overdue_projects"].config(
            text=str(stats.get('overdue_projects', 0)),
            fg=theme["kpi_overdue"],
        )
        self.kpi_labels["total_clients"].config(
            text=str(stats.get('total_clients', 0)),
            fg=theme["kpi_clients"],
        )

    def _theme_axes(self, ax):
        """Застосувати поточну тему до осей matplotlib."""
        theme = get_theme_manager().get()
        ax.set_facecolor(theme["chart_bg"])
        ax.tick_params(colors=theme["chart_fg"], labelsize=8)
        ax.xaxis.label.set_color(theme["chart_fg"])
        ax.yaxis.label.set_color(theme["chart_fg"])
        ax.title.set_color(theme["chart_fg"])
        for spine in ax.spines.values():
            spine.set_color(theme["chart_grid"])
        ax.grid(color=theme["chart_grid"], alpha=0.25, linestyle="--", linewidth=0.5)
        ax.set_axisbelow(True)

    def _draw_profit_chart(self):
        data = self.db.get_monthly_revenue(months=12)
        theme = get_theme_manager().get()
        ax = self.fig.add_subplot(2, 3, 1)
        self._theme_axes(ax)
        if data:
            months = [d["month"] for d in data]
            amounts = [d["amount"] for d in data]
            bars = ax.bar(months, amounts,
                          color=theme["chart_accent"],
                          edgecolor=theme["chart_grid"],
                          linewidth=0.5,
                          alpha=0.9)
            # Градієнт-ефект для останнього стовпчика
            if bars:
                bars[-1].set_color(theme["accent_soft"])
            ax.set_title("Виручка по місяцях", fontsize=10, fontweight="bold", pad=10)
            ax.set_ylabel("грн", fontsize=8)
            ax.tick_params(axis="x", rotation=45, labelsize=7)
        else:
            ax.text(0.5, 0.5, "Немає даних", ha="center", va="center",
                    transform=ax.transAxes, color=theme["chart_fg"], fontsize=10)
            ax.set_title("Виручка по місяцях", fontsize=10)

    def _draw_workload_chart(self):
        data = self.db.get_project_status_counts()
        theme = get_theme_manager().get()
        ax = self.fig.add_subplot(2, 3, 2)
        if data:
            labels = list(data.keys())
            values = list(data.values())
            colors = [theme["chart_accent"], theme["chart_accent2"],
                      theme["chart_danger"], theme["chart_accent3"]]
            wedges, texts, autotexts = ax.pie(
                values, labels=labels, autopct="%1.0f%%",
                colors=colors[:len(labels)],
                textprops={"fontsize": 8, "color": theme["chart_fg"]},
                startangle=90,
                wedgeprops={"edgecolor": theme["chart_bg"], "linewidth": 2},
            )
            for autotext in autotexts:
                autotext.set_fontweight("bold")
                autotext.set_fontsize(9)
            ax.set_title("Завантаження цеху", fontsize=10, fontweight="bold",
                         color=theme["chart_fg"], pad=10)
        else:
            ax.text(0.5, 0.5, "Немає даних", ha="center", va="center",
                    transform=ax.transAxes, color=theme["chart_fg"], fontsize=10)
            ax.set_title("Завантаження цеху", fontsize=10, color=theme["chart_fg"])

    def _draw_top_clients_chart(self):
        data = self.db.get_top_clients(limit=5)
        theme = get_theme_manager().get()
        ax = self.fig.add_subplot(2, 3, 3)
        self._theme_axes(ax)
        if data:
            names = [d["name"][:15] for d in data]
            amounts = [d["total"] for d in data]
            bars = ax.barh(names, amounts,
                           color=theme["chart_accent3"],
                           edgecolor=theme["chart_grid"],
                           linewidth=0.5,
                           alpha=0.85)
            # Значення на кінцях стовпчиків
            for bar, val in zip(bars, amounts):
                ax.text(val + max(amounts) * 0.02, bar.get_y() + bar.get_height() / 2,
                        f"{val:,.0f}", va="center", fontsize=8,
                        color=theme["chart_fg"])
            ax.set_title("ТОП-5 клієнтів", fontsize=10, fontweight="bold", pad=10)
            ax.set_xlabel("грн", fontsize=8)
            ax.invert_yaxis()
            ax.tick_params(axis="both", labelsize=7)
        else:
            ax.text(0.5, 0.5, "Немає даних", ha="center", va="center",
                    transform=ax.transAxes, color=theme["chart_fg"], fontsize=10)
            ax.set_title("ТОП-5 клієнтів", fontsize=10)

    def _draw_status_chart(self):
        data = self.db.get_monthly_project_status(months=6)
        theme = get_theme_manager().get()
        ax = self.fig.add_subplot(2, 3, 4)
        self._theme_axes(ax)
        if data:
            months = [d["month"] for d in data]
            active = [d.get("active", 0) for d in data]
            completed = [d.get("completed", 0) for d in data]
            x = range(len(months))
            width = 0.35
            ax.bar([i - width / 2 for i in x], active, width,
                   label="В роботі", color=theme["chart_accent"], alpha=0.9)
            ax.bar([i + width / 2 for i in x], completed, width,
                   label="Завершено", color=theme["chart_accent2"], alpha=0.9)
            ax.set_xticks(x)
            ax.set_xticklabels(months, rotation=45, fontsize=7)
            ax.set_title("Динаміка проєктів", fontsize=10, fontweight="bold", pad=10)
            ax.legend(fontsize=8, labelcolor=theme["chart_fg"],
                      facecolor=theme["chart_bg"], edgecolor=theme["chart_grid"])
            ax.tick_params(axis="y", labelsize=7)
        else:
            ax.text(0.5, 0.5, "Немає даних", ha="center", va="center",
                    transform=ax.transAxes, color=theme["chart_fg"], fontsize=10)
            ax.set_title("Динаміка проєктів", fontsize=10)

    def _draw_monthly_revenue_chart(self):
        data = self.db.get_monthly_avg_check(months=12)
        theme = get_theme_manager().get()
        ax = self.fig.add_subplot(2, 3, 5)
        self._theme_axes(ax)
        if data:
            months = [d["month"] for d in data]
            avg = [d["avg"] for d in data]
            ax.plot(months, avg, marker="o", color=theme["chart_accent2"],
                    linewidth=2.5, markersize=5, markerfacecolor=theme["chart_bg"],
                    markeredgecolor=theme["chart_accent2"], markeredgewidth=2)
            ax.fill_between(months, avg, alpha=0.15, color=theme["chart_accent2"])
            ax.set_title("Середній чек", fontsize=10, fontweight="bold", pad=10)
            ax.set_ylabel("грн", fontsize=8)
            ax.tick_params(axis="x", rotation=45, labelsize=7)
            ax.tick_params(axis="y", labelsize=7)
        else:
            ax.text(0.5, 0.5, "Немає даних", ha="center", va="center",
                    transform=ax.transAxes, color=theme["chart_fg"], fontsize=10)
            ax.set_title("Середній чек", fontsize=10)

    def _draw_overdue_chart(self):
        ax = self.fig.add_subplot(2, 3, 6)
        theme = get_theme_manager().get()
        self._theme_axes(ax)
        overdue = self.db.get_overdue_projects()
        if overdue:
            names = [p["project_name"][:20] for p in overdue[:5]]
            days = [(datetime.now() - datetime.fromisoformat(p["end_date"])).days
                    for p in overdue[:5]]
            bars = ax.barh(names, days,
                           color=theme["chart_danger"],
                           edgecolor=theme["chart_grid"],
                           linewidth=0.5,
                           alpha=0.85)
            for bar, val in zip(bars, days):
                ax.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                        f"{val} дн", va="center", fontsize=8,
                        color=theme["chart_fg"])
            ax.set_title("Прострочення (дні)", fontsize=10, fontweight="bold", pad=10)
            ax.set_xlabel("днів", fontsize=8)
            ax.invert_yaxis()
            ax.tick_params(axis="both", labelsize=7)
        else:
            ax.text(0.5, 0.5, "Немає прострочень ✓", ha="center", va="center",
                    transform=ax.transAxes, color=theme["chart_accent2"], fontsize=10)
            ax.set_title("Прострочення", fontsize=10)
