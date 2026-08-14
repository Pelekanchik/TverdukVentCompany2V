"""Вікно автентифікації (логін / пароль).

Відображається перед головним вікном.
Підтримує Enter для входу.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from ventilation_company.auth.service import auth
from ventilation_company.auth.permissions import get_role_label


class LoginWindow:
    """Вікно входу в систему."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🔐 VentCompany — Вхід в систему")
        self.root.geometry("420x520")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e293b")

        # Центрування
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (420 // 2)
        y = (self.root.winfo_screenheight() // 2) - (520 // 2)
        self.root.geometry(f"+{x}+{y}")

        self._build_ui()
        self.logged_in_user = None

    def _build_ui(self):
        # ── Фрейм картки ──
        card = tk.Frame(self.root, bg="#0f172a", bd=0, highlightthickness=0)
        card.place(relx=0.5, rely=0.5, anchor="center", width=380, height=480)

        # Логотип / іконка
        lbl_icon = tk.Label(
            card,
            text="🏭",
            font=("Segoe UI", 48),
            bg="#0f172a",
            fg="#38bdf8",
        )
        lbl_icon.pack(pady=(30, 5))

        lbl_title = tk.Label(
            card,
            text="VentCompany",
            font=("Segoe UI", 20, "bold"),
            bg="#0f172a",
            fg="#f8fafc",
        )
        lbl_title.pack()

        lbl_sub = tk.Label(
            card,
            text="Система управління вентиляційними проєктами",
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#94a3b8",
        )
        lbl_sub.pack(pady=(0, 25))

        # ── Поле логін ──
        frm_user = tk.Frame(card, bg="#0f172a")
        frm_user.pack(fill=tk.X, padx=35, pady=5)

        tk.Label(
            frm_user, text="👤  Логін", font=("Segoe UI", 10),
            bg="#0f172a", fg="#cbd5e1", anchor="w"
        ).pack(fill=tk.X)

        self.entry_user = tk.Entry(
            frm_user,
            font=("Segoe UI", 12),
            bg="#1e293b",
            fg="#f8fafc",
            insertbackground="#38bdf8",
            relief="flat",
            highlightthickness=1,
            highlightcolor="#38bdf8",
            highlightbackground="#334155",
        )
        self.entry_user.pack(fill=tk.X, pady=(4, 0), ipady=6)
        self.entry_user.focus()

        # ── Поле пароль ──
        frm_pass = tk.Frame(card, bg="#0f172a")
        frm_pass.pack(fill=tk.X, padx=35, pady=12)

        tk.Label(
            frm_pass, text="🔒  Пароль", font=("Segoe UI", 10),
            bg="#0f172a", fg="#cbd5e1", anchor="w"
        ).pack(fill=tk.X)

        self.entry_pass = tk.Entry(
            frm_pass,
            font=("Segoe UI", 12),
            bg="#1e293b",
            fg="#f8fafc",
            insertbackground="#38bdf8",
            relief="flat",
            highlightthickness=1,
            highlightcolor="#38bdf8",
            highlightbackground="#334155",
            show="•",
        )
        self.entry_pass.pack(fill=tk.X, pady=(4, 0), ipady=6)
        self.entry_pass.bind("<Return>", lambda e: self._do_login())
        self.entry_user.bind("<Return>", lambda e: self.entry_pass.focus())

        # ── Кнопка входу ──
        btn_login = tk.Button(
            card,
            text="Увійти в систему",
            font=("Segoe UI", 11, "bold"),
            bg="#0ea5e9",
            fg="white",
            activebackground="#0284c7",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self._do_login,
        )
        btn_login.pack(fill=tk.X, padx=35, pady=(20, 10), ipady=8)

        # ── Статус ──
        self.lbl_status = tk.Label(
            card,
            text="",
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#ef4444",
        )
        self.lbl_status.pack()

        # ── Підказка дефолтних користувачів ──
        hint = tk.Label(
            card,
            text="Дефолтні: admin / engineer / accountant / monter\n(пароль: admin123 / eng123 / acc123 / mon123)",
            font=("Segoe UI", 8),
            bg="#0f172a",
            fg="#475569",
            justify="center",
        )
        hint.pack(side=tk.BOTTOM, pady=15)

    def _do_login(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()

        if not username or not password:
            self.lbl_status.config(text="⚠️  Введіть логін та пароль")
            return

        user = auth.authenticate(username, password)
        if user:
            self.logged_in_user = user
            self.root.destroy()
        else:
            self.lbl_status.config(text="❌  Невірний логін або пароль")
            self.entry_pass.delete(0, tk.END)
            self.entry_pass.focus()

    def run(self) -> bool:
        """Запустити вікно логіну. Повертає True якщо успішно."""
        self.root.mainloop()
        return self.logged_in_user is not None


def show_login() -> bool:
    """Показати вікно входу та ініціалізувати дефолтних користувачів."""
    auth.ensure_default_users()
    win = LoginWindow()
    return win.run()
