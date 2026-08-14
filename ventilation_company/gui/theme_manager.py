"""Менеджер тем для VentCompany GUI — Industrial Orange Edition.

Тема: Industrial Orange
- Темний фон + помаранчевий акцент + сталь
- Покращені стилі: rounded кнопки, hover-ефекти, кольорові KPI, zebra-таблиці
"""

import json
import os
from tkinter import ttk

_THEME_FILE = os.path.join("data", "theme.json")

# ═══════════════════════════════════════════════════════════════
# INDUSTRIAL ORANGE — основна тема
# ═══════════════════════════════════════════════════════════════
INDUSTRIAL_THEME = {
    "name": "industrial",
    # ── Базові ──
    "bg": "#18181b",           # Головний фон
    "fg": "#e4e4e7",           # Основний текст
    "fg_secondary": "#a1a1aa", # Вторинний текст
    "fg_muted": "#71717a",     # Приглушений текст
    # ── Фрейми / картки ──
    "frame_bg": "#27272a",     # Фон карток
    "frame_bg_alt": "#3f3f46", # Альтернативний фон
    "card_bg": "#27272a",
    "card_border": "#3f3f46",
    # ── Поля вводу ──
    "entry_bg": "#3f3f46",
    "entry_fg": "#e4e4e7",
    "entry_border": "#52525b",
    "entry_focus": "#f97316",
    # ── Виділення ──
    "select_bg": "#f97316",
    "select_fg": "#18181b",
    "select_bg_soft": "#7c2d12",  # М'яке виділення
    # ── Кнопки ──
    "button_bg": "#3f3f46",
    "button_fg": "#e4e4e7",
    "button_hover": "#52525b",
    "button_active": "#f97316",
    "button_active_fg": "#18181b",
    # ── Акценти ──
    "accent": "#f97316",       # Помаранчевий
    "accent_soft": "#fb923c",  # Світліший
    "accent_dark": "#c2410c",  # Темніший
    "accent2": "#84cc16",      # Лайм (позитив)
    "accent3": "#06b6d4",      # Бірюзовий (інфо)
    "danger": "#ef4444",       # Червоний (небезпека)
    "warning": "#f59e0b",      # Жовтий (попередження)
    # ── Дерево / таблиці ──
    "tree_bg": "#27272a",
    "tree_fg": "#e4e4e7",
    "tree_sel_bg": "#7c2d12",
    "tree_sel_fg": "#ffffff",
    "tree_alt_bg": "#323238",  # Zebra для парних рядків
    "tree_hover_bg": "#3f3f46",
    # ── Ноутбук / вкладки ──
    "notebook_bg": "#18181b",
    "tab_bg": "#27272a",
    "tab_fg": "#a1a1aa",
    "tab_active_bg": "#f97316",
    "tab_active_fg": "#18181b",
    "tab_hover_bg": "#3f3f46",
    # ── Рамки ──
    "border": "#3f3f46",
    "border_light": "#52525b",
    "separator": "#3f3f46",
    # ── Статус-бар ──
    "status_bg": "#18181b",
    "status_fg": "#a1a1aa",
    "status_ok": "#84cc16",
    "status_warn": "#f59e0b",
    "status_err": "#ef4444",
    # ── Графіки ──
    "chart_bg": "#18181b",
    "chart_fg": "#e4e4e7",
    "chart_grid": "#3f3f46",
    "chart_accent": "#f97316",
    "chart_accent2": "#84cc16",
    "chart_accent3": "#06b6d4",
    "chart_danger": "#ef4444",
    # ── KPI ──
    "kpi_revenue": "#f97316",
    "kpi_projects": "#84cc16",
    "kpi_utilization": "#06b6d4",
    "kpi_overdue": "#ef4444",
    "kpi_clients": "#a78bfa",
    # ── Scrollbar ──
    "scrollbar_bg": "#3f3f46",
    "scrollbar_trough": "#18181b",
    # ── Tooltip ──
    "tooltip_bg": "#3f3f46",
    "tooltip_fg": "#e4e4e7",
    "tooltip_border": "#52525b",
    # ── Жорсткі кольори (для сумісності зі старим кодом) ──
    "gray": "#a1a1aa",
    "green": "#84cc16",
    "blue": "#38bdf8",
}

# ═══════════════════════════════════════════════════════════════
# LIGHT THEME (залишаємо для сумісності)
# ═══════════════════════════════════════════════════════════════
LIGHT_THEME = {
    "name": "light",
    "bg": "#f5f5f5",
    "fg": "#333333",
    "frame_bg": "#ffffff",
    "entry_bg": "#ffffff",
    "entry_fg": "#333333",
    "select_bg": "#2196F3",
    "select_fg": "#ffffff",
    "button_bg": "#e0e0e0",
    "button_fg": "#333333",
    "accent": "#2196F3",
    "tree_bg": "#ffffff",
    "tree_fg": "#333333",
    "tree_sel_bg": "#2196F3",
    "tree_sel_fg": "#ffffff",
    "tree_alt_bg": "#f8f9fa",
    "tree_hover_bg": "#e3f2fd",
    "notebook_bg": "#f5f5f5",
    "tab_bg": "#e0e0e0",
    "tab_fg": "#333333",
    "tab_active_bg": "#2196F3",
    "tab_active_fg": "#ffffff",
    "tab_hover_bg": "#d0d0d0",
    "border": "#cccccc",
    "border_light": "#dddddd",
    "separator": "#cccccc",
    "status_bg": "#f0f0f0",
    "status_fg": "#333333",
    "status_ok": "#4CAF50",
    "status_warn": "#FF9800",
    "status_err": "#F44336",
    "chart_bg": "#fafafa",
    "chart_fg": "#333333",
    "chart_grid": "#cccccc",
    "chart_accent": "#2196F3",
    "chart_accent2": "#4CAF50",
    "chart_accent3": "#FF9800",
    "chart_danger": "#F44336",
    "kpi_revenue": "#2196F3",
    "kpi_projects": "#4CAF50",
    "kpi_utilization": "#FF9800",
    "kpi_overdue": "#F44336",
    "kpi_clients": "#9C27B0",
    "scrollbar_bg": "#e0e0e0",
    "scrollbar_trough": "#f5f5f5",
    "tooltip_bg": "#333333",
    "tooltip_fg": "#ffffff",
    "tooltip_border": "#555555",
    "fg_secondary": "#666666",
    "fg_muted": "#999999",
    "frame_bg_alt": "#f0f0f0",
    "card_bg": "#ffffff",
    "card_border": "#dddddd",
    "entry_border": "#cccccc",
    "entry_focus": "#2196F3",
    "button_hover": "#d0d0d0",
    "button_active": "#2196F3",
    "button_active_fg": "#ffffff",
    "accent_soft": "#64b5f6",
    "accent_dark": "#1565C0",
    "accent2": "#4CAF50",
    "accent3": "#FF9800",
    "danger": "#F44336",
    "warning": "#FF9800",
    "select_bg_soft": "#bbdefb",
    "gray": "#666666",
    "green": "#4CAF50",
    "blue": "#2196F3",
}


class ThemeManager:
    """Керування темою оформлення VentCompany."""

    def __init__(self):
        self.current = self._load()
        self._callbacks = []

    def _load(self) -> dict:
        if os.path.exists(_THEME_FILE):
            try:
                with open(_THEME_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    return INDUSTRIAL_THEME if saved.get("name") == "industrial" else LIGHT_THEME
            except Exception:
                pass
        return INDUSTRIAL_THEME  # За замовчуванням Industrial Orange

    def save(self):
        os.makedirs(os.path.dirname(_THEME_FILE), exist_ok=True)
        with open(_THEME_FILE, "w", encoding="utf-8") as f:
            json.dump({"name": self.current["name"]}, f)

    def is_dark(self) -> bool:
        return self.current["name"] == "industrial"

    def toggle(self):
        self.current = LIGHT_THEME if self.current["name"] == "industrial" else INDUSTRIAL_THEME
        self.save()
        self._notify()

    def set_light(self):
        self.current = LIGHT_THEME
        self.save()
        self._notify()

    def set_industrial(self):
        self.current = INDUSTRIAL_THEME
        self.save()
        self._notify()

    def on_change(self, callback):
        self._callbacks.append(callback)

    def _notify(self):
        for cb in self._callbacks:
            try:
                cb(self.current)
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════
    # ЗАСТОСУВАННЯ ТЕМИ
    # ═══════════════════════════════════════════════════════════
    def apply(self, root, style: ttk.Style = None):
        """Застосувати поточну тему до всіх віджетів."""
        if style is None:
            style = ttk.Style(root)
        t = self.current

        # ═══ КЛЮЧОВЕ: перемикаємо на clam theme (Windows-friendly) ═══
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass  # clam не доступний — використовуємо дефолт
        # ═══════════════════════════════════════════════════════════════

        # ── Глобальні налаштування tk ──
        root.option_add('*Background', t["bg"])
        root.option_add('*Foreground', t["fg"])
        root.option_add('*Entry.background', t["entry_bg"])
        root.option_add('*Entry.foreground', t["entry_fg"])
        root.option_add('*Entry.insertBackground', t["accent"])
        root.option_add('*Text.background', t["entry_bg"])
        root.option_add('*Text.foreground', t["entry_fg"])
        root.option_add('*Text.insertBackground', t["accent"])
        root.option_add('*Listbox.background', t["entry_bg"])
        root.option_add('*Listbox.foreground', t["entry_fg"])
        root.option_add('*Listbox.selectBackground', t["select_bg"])
        root.option_add('*Listbox.selectForeground', t["select_fg"])
        root.option_add('*Menu.background', t["bg"])
        root.option_add('*Menu.foreground', t["fg"])
        root.option_add('*Menu.activeBackground', t["select_bg"])
        root.option_add('*Menu.activeForeground', t["select_fg"])
        root.option_add('*Labelframe.background', t["bg"])
        root.option_add('*Labelframe.foreground', t["fg"])
        root.option_add('*Label.background', t["bg"])
        root.option_add('*Label.foreground', t["fg"])
        root.option_add('*Button.background', t["button_bg"])
        root.option_add('*Button.foreground', t["button_fg"])
        root.option_add('*Button.activeBackground', t["button_active"])
        root.option_add('*Button.activeForeground', t["button_active_fg"])
        root.option_add('*Checkbutton.background', t["bg"])
        root.option_add('*Checkbutton.foreground', t["fg"])
        root.option_add('*Checkbutton.selectColor', t["entry_bg"])
        root.option_add('*Radiobutton.background', t["bg"])
        root.option_add('*Radiobutton.foreground', t["fg"])
        root.option_add('*Radiobutton.selectColor', t["entry_bg"])
        root.option_add('*Scale.background', t["bg"])
        root.option_add('*Scale.troughColor', t["button_bg"])
        root.option_add('*Scrollbar.background', t["scrollbar_bg"])
        root.option_add('*Scrollbar.troughColor', t["scrollbar_trough"])
        root.option_add('*TCombobox*Listbox.background', t["entry_bg"])
        root.option_add('*TCombobox*Listbox.foreground', t["entry_fg"])

        # ── ttk Style — покращені стилі ──
        style.configure(".", background=t["bg"], foreground=t["fg"], fieldbackground=t["entry_bg"])
        style.configure("TFrame", background=t["bg"])
        style.configure("TLabel", background=t["bg"], foreground=t["fg"])

        # Кнопки — rounded, hover
        style.configure("TButton",
            background=t["button_bg"],
            foreground=t["button_fg"],
            font=("Segoe UI", 10),
            padding=(12, 6),
        )
        style.map("TButton",
            background=[("active", t["button_active"]), ("pressed", t["button_active"])],
            foreground=[("active", t["button_active_fg"]), ("pressed", t["button_active_fg"])],
        )

        # Accent кнопка (головна дія)
        style.configure("Accent.TButton",
            background=t["accent"],
            foreground=t["button_active_fg"],
            font=("Segoe UI", 10, "bold"),
            padding=(16, 8),
        )
        style.map("Accent.TButton",
            background=[("active", t["accent_soft"]), ("pressed", t["accent_dark"])],
        )

        # Danger кнопка (видалення)
        style.configure("Danger.TButton",
            background=t["danger"],
            foreground="#ffffff",
            font=("Segoe UI", 10),
            padding=(12, 6),
        )

        # Check / Radio
        style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"])
        style.configure("TRadiobutton", background=t["bg"], foreground=t["fg"])

        # Поля вводу — КЛЮЧОВЕ ВИПРАВЛЕННЯ
        style.configure("TEntry",
            fieldbackground=t["entry_bg"],
            foreground=t["entry_fg"],
            insertcolor=t["accent"],
            padding=(8, 4),
        )
        style.map("TEntry",
            fieldbackground=[("readonly", t["entry_bg"]), ("disabled", t["frame_bg"])],
            foreground=[("readonly", t["entry_fg"]), ("disabled", t["fg_muted"])],
        )

        style.configure("TCombobox",
            fieldbackground=t["entry_bg"],
            foreground=t["entry_fg"],
            padding=(8, 4),
        )
        style.map("TCombobox",
            fieldbackground=[("readonly", t["entry_bg"]), ("disabled", t["frame_bg"])],
            foreground=[("readonly", t["entry_fg"]), ("disabled", t["fg_muted"])],
            selectbackground=[("readonly", t["select_bg"])],
            selectforeground=[("readonly", t["select_fg"])],
        )
        style.configure("TSpinbox",
            fieldbackground=t["entry_bg"],
            foreground=t["entry_fg"],
            padding=(8, 4),
        )
        style.map("TSpinbox",
            fieldbackground=[("readonly", t["entry_bg"]), ("disabled", t["frame_bg"])],
            foreground=[("readonly", t["entry_fg"]), ("disabled", t["fg_muted"])],
        )

        # Ноутбук / вкладки
        style.configure("TNotebook", background=t["notebook_bg"], tabmargins=(2, 5, 2, 0))
        style.configure("TNotebook.Tab",
            background=t["tab_bg"],
            foreground=t["tab_fg"],
            font=("Segoe UI", 10),
            padding=(14, 6),
        )
        style.map("TNotebook.Tab",
            background=[("selected", t["tab_active_bg"]), ("active", t["tab_hover_bg"])],
            foreground=[("selected", t["tab_active_fg"]), ("active", t["fg"])],
            expand=[("selected", (2, 2, 2, 0))],
        )

        # Progressbar
        style.configure("Horizontal.TProgressbar", background=t["accent"], troughcolor=t["button_bg"])
        style.configure("Vertical.TProgressbar", background=t["accent"], troughcolor=t["button_bg"])

        # Scale
        style.configure("TScale", background=t["bg"])

        # Scrollbar
        style.configure("TScrollbar",
            background=t["scrollbar_bg"],
            troughcolor=t["scrollbar_trough"],
            arrowcolor=t["fg"],
        )

        # Treeview — покращений
        style.configure("Treeview",
            background=t["tree_bg"],
            foreground=t["tree_fg"],
            fieldbackground=t["tree_bg"],
            font=("Segoe UI", 10),
            rowheight=28,
        )
        style.configure("Treeview.Heading",
            background=t["button_bg"],
            foreground=t["button_fg"],
            font=("Segoe UI", 10, "bold"),
            padding=(8, 6),
        )
        style.map("Treeview",
            background=[("selected", t["tree_sel_bg"])],
            foreground=[("selected", t["tree_sel_fg"])],
        )

        # Labelframe
        style.configure("TLabelframe", background=t["bg"])
        style.configure("TLabelframe.Label", background=t["bg"], foreground=t["fg"],
                        font=("Segoe UI", 10, "bold"))

        # Separator
        style.configure("TSeparator", background=t["separator"])

        # PanedWindow
        style.configure("TPanedwindow", background=t["bg"])

        # MenuButton
        style.configure("TMenubutton",
            background=t["button_bg"],
            foreground=t["button_fg"],
            padding=(8, 4),
        )

        # Root фон
        root.configure(background=t["bg"])

        # Оновити всі існуючі віджети
        self._update_widget(root, t)

    def _update_widget(self, widget, t: dict):
        """Рекурсивно оновити кольори tk-віджетів."""
        wtype = widget.winfo_class()
        try:
            if wtype in ("Frame", "Tk", "Toplevel"):
                widget.configure(background=t["bg"])
            elif wtype == "Label":
                widget.configure(background=t["bg"], foreground=t["fg"])
            elif wtype == "Button":
                widget.configure(
                    background=t["button_bg"],
                    foreground=t["button_fg"],
                    activebackground=t["button_active"],
                    activeforeground=t["button_active_fg"],
                )
            elif wtype == "Entry":
                widget.configure(
                    background=t["entry_bg"],
                    foreground=t["entry_fg"],
                    insertbackground=t["accent"],
                )
            elif wtype == "Text":
                widget.configure(
                    background=t["entry_bg"],
                    foreground=t["entry_fg"],
                    insertbackground=t["accent"],
                )
            elif wtype == "Listbox":
                widget.configure(
                    background=t["entry_bg"],
                    foreground=t["entry_fg"],
                    selectbackground=t["select_bg"],
                    selectforeground=t["select_fg"],
                )
            elif wtype == "Menu":
                widget.configure(
                    background=t["bg"],
                    foreground=t["fg"],
                    activebackground=t["select_bg"],
                    activeforeground=t["select_fg"],
                )
            elif wtype == "Scale":
                widget.configure(background=t["bg"], troughcolor=t["button_bg"])
            elif wtype == "Scrollbar":
                widget.configure(background=t["scrollbar_bg"], troughcolor=t["scrollbar_trough"])
            elif wtype == "Canvas":
                widget.configure(background=t["bg"])
            elif wtype == "Labelframe":
                widget.configure(background=t["bg"])
            elif wtype in ("Checkbutton", "Radiobutton"):
                widget.configure(
                    background=t["bg"],
                    foreground=t["fg"],
                    activebackground=t["bg"],
                    selectcolor=t["entry_bg"],
                )
        except Exception:
            pass

        for child in widget.winfo_children():
            self._update_widget(child, t)

    def get(self) -> dict:
        return self.current

    def color(self, key: str, default="#888888") -> str:
        """Отримати колір за ключем."""
        return self.current.get(key, default)


# Глобальний екземпляр
_theme_manager = ThemeManager()


def get_theme_manager() -> ThemeManager:
    return _theme_manager
