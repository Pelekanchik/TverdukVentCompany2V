"""Менеджер тем (світла / темна) для VentCompany GUI."""

import json
import os
from tkinter import ttk


_THEME_FILE = os.path.join("data", "theme.json")

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
    "notebook_bg": "#f5f5f5",
    "tab_bg": "#e0e0e0",
    "tab_fg": "#333333",
    "border": "#cccccc",
    "status_bg": "#f0f0f0",
    "status_fg": "#333333",
    "chart_bg": "#fafafa",
    "chart_fg": "#333333",
    "chart_grid": "#cccccc",
}

DARK_THEME = {
    "name": "dark",
    "bg": "#1e1e1e",
    "fg": "#ffffff",
    "frame_bg": "#2d2d2d",
    "entry_bg": "#3c3c3c",
    "entry_fg": "#ffffff",
    "select_bg": "#1565C0",
    "select_fg": "#ffffff",
    "button_bg": "#404040",
    "button_fg": "#ffffff",
    "accent": "#4FC3F7",
    "tree_bg": "#2d2d2d",
    "tree_fg": "#ffffff",
    "tree_sel_bg": "#1565C0",
    "tree_sel_fg": "#ffffff",
    "notebook_bg": "#1e1e1e",
    "tab_bg": "#333333",
    "tab_fg": "#ffffff",
    "border": "#666666",
    "status_bg": "#252525",
    "status_fg": "#ffffff",
    "chart_bg": "#1e1e1e",
    "chart_fg": "#ffffff",
    "chart_grid": "#555555",
}


class ThemeManager:
    """Керування темою оформлення."""

    def __init__(self):
        self.current = self._load()
        self._callbacks = []

    def _load(self) -> dict:
        if os.path.exists(_THEME_FILE):
            try:
                with open(_THEME_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    return DARK_THEME if saved.get("name") == "dark" else LIGHT_THEME
            except Exception:
                pass
        return LIGHT_THEME

    def save(self):
        os.makedirs(os.path.dirname(_THEME_FILE), exist_ok=True)
        with open(_THEME_FILE, "w", encoding="utf-8") as f:
            json.dump({"name": self.current["name"]}, f)

    def is_dark(self) -> bool:
        return self.current["name"] == "dark"

    def toggle(self):
        self.current = DARK_THEME if self.current["name"] == "light" else LIGHT_THEME
        self.save()
        self._notify()

    def set_light(self):
        self.current = LIGHT_THEME
        self.save()
        self._notify()

    def set_dark(self):
        self.current = DARK_THEME
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

    def apply(self, root, style: ttk.Style = None):
        """Застосувати поточну тему до всіх віджетів."""
        if style is None:
            style = ttk.Style(root)
        t = self.current

        # ═══ Глобальні налаштування tk (option_add) — для ВСІХ нових віджетів ═══
        root.option_add('*Background', t["bg"])
        root.option_add('*Foreground', t["fg"])
        root.option_add('*Entry.background', t["entry_bg"])
        root.option_add('*Entry.foreground', t["entry_fg"])
        root.option_add('*Entry.insertBackground', t["fg"])
        root.option_add('*Text.background', t["entry_bg"])
        root.option_add('*Text.foreground', t["entry_fg"])
        root.option_add('*Text.insertBackground', t["fg"])
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
        root.option_add('*Button.activeBackground', t["select_bg"])
        root.option_add('*Button.activeForeground', t["select_fg"])
        root.option_add('*Checkbutton.background', t["bg"])
        root.option_add('*Checkbutton.foreground', t["fg"])
        root.option_add('*Checkbutton.selectColor', t["entry_bg"])
        root.option_add('*Radiobutton.background', t["bg"])
        root.option_add('*Radiobutton.foreground', t["fg"])
        root.option_add('*Radiobutton.selectColor', t["entry_bg"])
        root.option_add('*Scale.background', t["bg"])
        root.option_add('*Scale.troughColor', t["button_bg"])
        root.option_add('*Scrollbar.background', t["button_bg"])
        root.option_add('*Scrollbar.troughColor', t["bg"])
        root.option_add('*TCombobox*Listbox.background', t["entry_bg"])
        root.option_add('*TCombobox*Listbox.foreground', t["entry_fg"])

        # ═══ ttk Style ═══
        style.configure(".", background=t["bg"], foreground=t["fg"], fieldbackground=t["entry_bg"])
        style.configure("TFrame", background=t["bg"])
        style.configure("TLabel", background=t["bg"], foreground=t["fg"])
        style.configure("TButton", background=t["button_bg"], foreground=t["button_fg"])
        style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"])
        style.configure("TRadiobutton", background=t["bg"], foreground=t["fg"])
        style.configure("TEntry", fieldbackground=t["entry_bg"], foreground=t["entry_fg"], insertcolor=t["fg"])
        style.configure("TCombobox", fieldbackground=t["entry_bg"], foreground=t["entry_fg"])
        style.map("TCombobox", fieldbackground=[("readonly", t["entry_bg"])],
                  selectbackground=[("readonly", t["select_bg"])])
        style.configure("TSpinbox", fieldbackground=t["entry_bg"], foreground=t["entry_fg"])
        style.configure("TNotebook", background=t["notebook_bg"])
        style.configure("TNotebook.Tab", background=t["tab_bg"], foreground=t["tab_fg"])
        style.map("TNotebook.Tab", background=[("selected", t["select_bg"]), ("active", t["select_bg"])],
                  foreground=[("selected", t["select_fg"]), ("active", t["select_fg"])])
        style.configure("Horizontal.TProgressbar", background=t["accent"])
        style.configure("Vertical.TProgressbar", background=t["accent"])
        style.configure("TScale", background=t["bg"])
        style.configure("TScrollbar", background=t["button_bg"], troughcolor=t["bg"])

        # Treeview
        style.configure("Treeview", background=t["tree_bg"], foreground=t["tree_fg"],
                        fieldbackground=t["tree_bg"])
        style.configure("Treeview.Heading", background=t["button_bg"], foreground=t["button_fg"])
        style.map("Treeview", background=[("selected", t["tree_sel_bg"])],
                  foreground=[("selected", t["tree_sel_fg"])])

        # Labelframe
        style.configure("TLabelframe", background=t["bg"])
        style.configure("TLabelframe.Label", background=t["bg"], foreground=t["fg"])

        # Separator
        style.configure("TSeparator", background=t["border"])

        # PanedWindow
        style.configure("TPanedwindow", background=t["bg"])

        # MenuButton
        style.configure("TMenubutton", background=t["button_bg"], foreground=t["button_fg"])

        # Root фон
        root.configure(background=t["bg"])

        # Оновити всі існуючі віджети
        self._update_widget(root, t)

    def _update_widget(self, widget, t: dict):
        """Рекурсивно оновити кольори tk-віджетів (не ttk)."""
        wtype = widget.winfo_class()
        try:
            if wtype in ("Frame", "Tk", "Toplevel"):
                widget.configure(background=t["bg"])
            elif wtype == "Label":
                widget.configure(background=t["bg"], foreground=t["fg"])
            elif wtype == "Button":
                widget.configure(background=t["button_bg"], foreground=t["button_fg"],
                                 activebackground=t["select_bg"], activeforeground=t["select_fg"])
            elif wtype == "Entry":
                widget.configure(background=t["entry_bg"], foreground=t["entry_fg"],
                                 insertbackground=t["fg"])
            elif wtype == "Text":
                widget.configure(background=t["entry_bg"], foreground=t["entry_fg"],
                                 insertbackground=t["fg"])
            elif wtype == "Listbox":
                widget.configure(background=t["entry_bg"], foreground=t["entry_fg"],
                                 selectbackground=t["select_bg"], selectforeground=t["select_fg"])
            elif wtype == "Menu":
                widget.configure(background=t["bg"], foreground=t["fg"],
                                 activebackground=t["select_bg"], activeforeground=t["select_fg"])
            elif wtype == "Scale":
                widget.configure(background=t["bg"], troughcolor=t["button_bg"])
            elif wtype == "Scrollbar":
                widget.configure(background=t["button_bg"], troughcolor=t["bg"])
            elif wtype == "Canvas":
                widget.configure(background=t["bg"])
            elif wtype == "Labelframe":
                widget.configure(background=t["bg"])
            elif wtype in ("Checkbutton", "Radiobutton"):
                widget.configure(background=t["bg"], foreground=t["fg"],
                                 activebackground=t["bg"], selectcolor=t["entry_bg"])
        except Exception:
            pass

        for child in widget.winfo_children():
            self._update_widget(child, t)

    def get(self) -> dict:
        return self.current


# Глобальний екземпляр
_theme_manager = ThemeManager()


def get_theme_manager() -> ThemeManager:
    return _theme_manager
