"""Візуалізація Gantt-діаграми виробництва через matplotlib."""

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.patches as mpatches
from datetime import datetime, timedelta

from ventilation_company.production_models import (
    OperationStatus,
    OperationType,
    ProductionPlan,
    ScheduledOperation,
)


# Кольори операцій
OP_COLORS = {
    OperationType.CUTTING: "#3498db",      # синій
    OperationType.BENDING: "#f39c12",      # оранжевий
    OperationType.WELDING: "#e74c3c",      # червоний
    OperationType.PAINTING: "#9b59b6",     # фіолетовий
    OperationType.ASSEMBLY: "#2ecc71",     # зелений
    OperationType.PACKING: "#1abc9c",       # бірюзовий
}

# Кольори статусів (обводка)
STATUS_EDGE = {
    OperationStatus.PLANNED: "#333333",
    OperationStatus.IN_PROGRESS: "#0066cc",
    OperationStatus.COMPLETED: "#27ae60",
    OperationStatus.DELAYED: "#cc0000",
    OperationStatus.BLOCKED: "#999999",
}

STATUS_HATCH = {
    OperationStatus.PLANNED: None,
    OperationStatus.IN_PROGRESS: "///",
    OperationStatus.COMPLETED: "xxx",
    OperationStatus.DELAYED: "\\\\\\",
    OperationStatus.BLOCKED: "...",
}


class GanttChart:
    """Gantt-діаграма виробництва."""

    def __init__(self, plan: ProductionPlan, figsize: tuple = (14, 8)):
        self.plan = plan
        self.fig = Figure(figsize=figsize, dpi=100, facecolor="white")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#fafafa")

    def _format_datetime(self, dt: datetime) -> str:
        return dt.strftime("%d.%m %H:%M")

    def _hours_since_start(self, dt: datetime) -> float:
        delta = dt - self.plan.start_date
        return delta.total_seconds() / 3600.0

    def draw(self, show_equipment: bool = True):
        """Намалювати Gantt-діаграму."""
        if not self.plan.operations:
            self.ax.text(0.5, 0.5, "Немає запланованих операцій",
                         transform=self.ax.transAxes, ha="center", fontsize=14, color="#999")
            return

        operations = sorted(self.plan.operations, key=lambda o: (o.product_name, o.start_time))

        y_positions = {}
        y_labels = []
        y = 0

        for op in operations:
            label = f"{op.product_name} — {op.operation_type.value}"
            if show_equipment:
                label += f" [{op.equipment.name}]"
            y_positions[op.id] = y
            y_labels.append(label)
            y += 1

        # Малюємо бари
        for op in operations:
            y_pos = y_positions[op.id]
            start_h = self._hours_since_start(op.start_time)
            duration_h = op.duration_hours

            color = OP_COLORS.get(op.operation_type, "#888888")
            edge = STATUS_EDGE.get(op.status, "#333333")
            hatch = STATUS_HATCH.get(op.status)

            bar = self.ax.barh(
                y_pos,
                duration_h,
                left=start_h,
                height=0.6,
                color=color,
                edgecolor=edge,
                linewidth=1.5,
                hatch=hatch,
                alpha=0.85,
            )

            # Текст всередині бару
            if duration_h > 2:
                self.ax.text(
                    start_h + duration_h / 2,
                    y_pos,
                    f"{op.duration_minutes:.0f} хв",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white",
                    fontweight="bold",
                )

        # Налаштування осей
        self.ax.set_yticks(range(len(y_labels)))
        self.ax.set_yticklabels(y_labels, fontsize=8)
        self.ax.set_xlabel("Години від початку проєкту", fontsize=10)
        self.ax.set_title(
            f"📊 {self.plan.project_name} — Gantt-діаграма виробництва\n"
            f"Початок: {self._format_datetime(self.plan.start_date)}  |  "
            f"Завершення: {self._format_datetime(self.plan.estimated_end)}  |  "
            f"Виконано: {self.plan.completion_percent:.0f}%",
            fontsize=11,
            fontweight="bold",
        )

        # Сітка
        self.ax.grid(True, axis="x", linestyle="--", alpha=0.4)
        self.ax.set_axisbelow(True)

        # Легенда операцій
        op_patches = [
            mpatches.Patch(color=OP_COLORS[ot], label=ot.value)
            for ot in OperationType if ot in OP_COLORS
        ]
        # Легенда статусів
        st_patches = [
            mpatches.Patch(facecolor="white", edgecolor=STATUS_EDGE[s], hatch=STATUS_HATCH[s] or "",
                           label=s.value, linewidth=1.5)
            for s in OperationStatus if s in STATUS_EDGE
        ]

        self.ax.legend(
            handles=op_patches + st_patches,
            loc="upper right",
            fontsize=7,
            ncol=2,
            framealpha=0.9,
        )

        # Вертикальна лінія дедлайну
        if self.plan.deadline:
            dl_h = self._hours_since_start(self.plan.deadline)
            color_dl = "#27ae60" if self.plan.is_on_time else "#cc0000"
            self.ax.axvline(dl_h, color=color_dl, linestyle="--", linewidth=2, alpha=0.7)
            self.ax.text(
                dl_h, len(y_labels) - 0.5, "ДЕДЛАЙН",
                color=color_dl, fontsize=8, fontweight="bold",
                ha="center", va="bottom",
            )

        self.fig.tight_layout()

    def get_canvas(self, master) -> FigureCanvasTkAgg:
        """Отримати FigureCanvasTkAgg для вбудовування в tkinter."""
        return FigureCanvasTkAgg(self.fig, master=master)

    def save(self, filepath: str, dpi: int = 150):
        """Зберегти діаграму в файл."""
        self.fig.savefig(filepath, dpi=dpi, bbox_inches="tight", facecolor="white")


class EquipmentLoadChart:
    """Діаграма завантаження обладнання."""

    def __init__(self, plan: ProductionPlan, figsize: tuple = (10, 5)):
        self.plan = plan
        self.fig = Figure(figsize=figsize, dpi=100, facecolor="white")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#fafafa")

    def draw(self):
        """Намалювати діаграму завантаження обладнання."""
        load = self.plan.get_equipment_load()
        if not load:
            self.ax.text(0.5, 0.5, "Немає даних про завантаження",
                         transform=self.ax.transAxes, ha="center", fontsize=12, color="#999")
            return

        # Розраховуємо загальний робочий час та зайнятий
        total_hours = {}
        used_hours = {}

        for eq_id, intervals in load.items():
            # Знайдемо обладнання
            eq = None
            for op in self.plan.operations:
                if op.equipment.id == eq_id:
                    eq = op.equipment
                    break
            if eq is None:
                continue

            shift_hours = eq.shift_end - eq.shift_start
            # Приблизна кількість днів
            if self.plan.estimated_end:
                days = max(1, (self.plan.estimated_end - self.plan.start_date).days + 1)
            else:
                days = 1
            total = shift_hours * days
            used = sum((end - start).total_seconds() / 3600.0 for start, end in intervals)

            total_hours[eq.name] = total
            used_hours[eq.name] = used

        names = list(total_hours.keys())
        totals = [total_hours[n] for n in names]
        useds = [used_hours[n] for n in names]
        percents = [u / t * 100 if t > 0 else 0 for u, t in zip(useds, totals)]

        x = range(len(names))
        bars = self.ax.bar(x, percents, color="#3498db", edgecolor="#2980b9", linewidth=1.5)

        # Підписи значень
        for i, (bar, pct) in enumerate(zip(bars, percents)):
            self.ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1,
                f"{pct:.1f}%",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )
            # Червоний колір якщо перевантажено (>90%)
            if pct > 90:
                bar.set_color("#e74c3c")
            elif pct > 70:
                bar.set_color("#f39c12")

        self.ax.set_xticks(x)
        self.ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
        self.ax.set_ylabel("Завантаження, %", fontsize=10)
        self.ax.set_title("⚙️ Завантаження обладнання", fontsize=11, fontweight="bold")
        self.ax.set_ylim(0, 110)
        self.ax.axhline(90, color="#cc0000", linestyle="--", linewidth=1, alpha=0.5, label="Перевантаження")
        self.ax.axhline(70, color="#f39c12", linestyle="--", linewidth=1, alpha=0.5, label="Високе")
        self.ax.grid(True, axis="y", linestyle="--", alpha=0.3)
        self.ax.legend(fontsize=8)
        self.fig.tight_layout()

    def get_canvas(self, master) -> FigureCanvasTkAgg:
        return FigureCanvasTkAgg(self.fig, master=master)

    def save(self, filepath: str, dpi: int = 150):
        self.fig.savefig(filepath, dpi=dpi, bbox_inches="tight", facecolor="white")
