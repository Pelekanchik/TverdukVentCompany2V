"""Утиліти для налаштування діалогових вікон.

Гарантує, що кнопки та контент завжди видно, незалежно від розміру екрана.
"""

import tkinter as tk


def setup_dialog(win: tk.Toplevel, title: str = "", min_w: int = 600, min_h: int = 400):
    """Налаштувати діалогове вікно з адаптивним розміром.

    Args:
        win: Toplevel вікно.
        title: Заголовок (опціонально).
        min_w: Мінімальна ширина.
        min_h: Мінімальна висота.
    """
    if title:
        win.title(title)
    win.minsize(min_w, min_h)
    win.resizable(True, True)
    # Центруємо на екрані
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    # За замовчуванням 80% екрана, але не менше min_w x min_h
    w = max(int(sw * 0.8), min_w)
    h = max(int(sh * 0.8), min_h)
    x = (sw - w) // 2
    y = (sh - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")
