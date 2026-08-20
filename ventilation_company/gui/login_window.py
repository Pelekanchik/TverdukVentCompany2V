"""Вікно автентифікації (логін / пароль / реєстрація).

ПАТЧ v2.1:
 • Прибрано вкладку "👥 Користувачі" — тепер вона у вкладці "Мій кабінет"
 • Додано property user_role для передачі ролі у головне вікно
 • Видалено хардкод-підказку з паролями
 • Додано діалог першого запуску з показом випадкового пароля admin
"""

import tkinter as tk
from tkinter import messagebox, ttk

from ventilation_company.auth.service import auth
from ventilation_company.auth.password_policy import validate_password
from ventilation_company.auth.permissions import get_role_label


class LoginWindow:
    """Вікно входу в систему з реєстрацією."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🔐 VentCompany — Вхід в систему")
        self.root.geometry("460x520")
        self.root.resizable(True, True)
        self.root.minsize(420, 450)
        self.root.configure(bg="#18181b")

        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (460 // 2)
        y = (self.root.winfo_screenheight() // 2) - (520 // 2)
        self.root.geometry(f"+{x}+{y}")

        self.logged_in_user = None
        self._build_ui()

    @property
    def user_role(self):
        """Роль увійшовшого користувача (для main_window)."""
        return self.logged_in_user.role if self.logged_in_user else None

    def _build_ui(self):
        card = tk.Frame(self.root, bg="#18181b", bd=0, highlightthickness=0)
        card.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        lbl_icon = tk.Label(card, text="🏭", font=("Segoe UI", 42), bg="#18181b", fg="#f97316")
        lbl_icon.pack(pady=(10, 2))

        lbl_title = tk.Label(card, text="VentCompany", font=("Segoe UI", 20, "bold"),
                             bg="#18181b", fg="#e4e4e7")
        lbl_title.pack()

        lbl_sub = tk.Label(card, text="Система управління вентиляційними проєктами",
                           font=("Segoe UI", 9), bg="#18181b", fg="#71717a")
        lbl_sub.pack(pady=(0, 10))

        # ── Тільки 2 таби: Вхід / Реєстрація ──
        self.tabs = ttk.Notebook(card)
        self.tabs.pack(fill=tk.BOTH, expand=True, pady=5)

        self.tab_login = tk.Frame(self.tabs, bg="#18181b")
        self.tabs.add(self.tab_login, text=" 🔐 Вхід ")
        self._build_login_tab(self.tab_login)

        self.tab_register = tk.Frame(self.tabs, bg="#18181b")
        self.tabs.add(self.tab_register, text=" 📝 Реєстрація ")
        self._build_register_tab(self.tab_register)

        self.lbl_status = tk.Label(card, text="", font=("Segoe UI", 9),
                                   bg="#18181b", fg="#ef4444")
        self.lbl_status.pack(pady=(5, 0))

        # Підказка без паролів — тільки загальна інформація
        hint = tk.Label(card,
                        text="Якщо ви вперше запускаєте програму,\n"
                             "з'явиться вікно з тимчасовим паролем адміністратора.",
                        font=("Segoe UI", 8), bg="#18181b", fg="#52525b", justify="center")
        hint.pack(side=tk.BOTTOM, pady=5)

    def _styled_entry(self, parent, show=None, width=32):
        ent = tk.Entry(parent, font=("Segoe UI", 11),
                       bg="#3f3f46", fg="#e4e4e7",
                       insertbackground="#f97316",
                       relief="flat", highlightthickness=1,
                       highlightcolor="#f97316", highlightbackground="#52525b",
                       show=show, width=width)
        return ent

    def _styled_label(self, parent, text):
        return tk.Label(parent, text=text, font=("Segoe UI", 10),
                        bg="#18181b", fg="#a1a1aa", anchor="w")

    def _styled_btn(self, parent, text, command, bg="#f97316", fg="#18181b"):
        return tk.Button(parent, text=text, font=("Segoe UI", 11, "bold"),
                         bg=bg, fg=fg, activebackground="#fb923c",
                         activeforeground="#18181b", relief="flat",
                         cursor="hand2", command=command, padx=20, pady=8)

    def _build_login_tab(self, parent):
        frm = tk.Frame(parent, bg="#18181b", padx=25, pady=15)
        frm.pack(fill=tk.BOTH, expand=True)

        self._styled_label(frm, "👤 Логін").pack(fill=tk.X, pady=(15, 2))
        self.entry_user = self._styled_entry(frm)
        self.entry_user.pack(fill=tk.X, ipady=5)
        self.entry_user.focus()

        self._styled_label(frm, "🔒 Пароль").pack(fill=tk.X, pady=(12, 2))
        self.entry_pass = self._styled_entry(frm, show="•")
        self.entry_pass.pack(fill=tk.X, ipady=5)

        self.entry_pass.bind("<Return>", lambda e: self._do_login())
        self.entry_user.bind("<Return>", lambda e: self.entry_pass.focus())

        self._styled_btn(frm, "Увійти в систему", self._do_login).pack(
            fill=tk.X, pady=(25, 5))

    def _build_register_tab(self, parent):
        frm = tk.Frame(parent, bg="#18181b", padx=25, pady=10)
        frm.pack(fill=tk.BOTH, expand=True)

        self._styled_label(frm, "👤 Логін *").pack(fill=tk.X, pady=(8, 2))
        self.reg_user = self._styled_entry(frm)
        self.reg_user.pack(fill=tk.X, ipady=4)

        self._styled_label(frm, "📝 Повне ім'я *").pack(fill=tk.X, pady=(8, 2))
        self.reg_name = self._styled_entry(frm)
        self.reg_name.pack(fill=tk.X, ipady=4)

        self._styled_label(frm, "🔒 Пароль *").pack(fill=tk.X, pady=(8, 2))
        self.reg_pass = self._styled_entry(frm, show="•")
        self.reg_pass.pack(fill=tk.X, ipady=4)

        self._styled_label(frm, "🔒 Підтвердіть пароль *").pack(fill=tk.X, pady=(8, 2))
        self.reg_pass2 = self._styled_entry(frm, show="•")
        self.reg_pass2.pack(fill=tk.X, ipady=4)

        self._styled_label(frm, "🛡️ Посада *").pack(fill=tk.X, pady=(8, 2))
        self.reg_role = ttk.Combobox(frm, values=[
            "Директор", "Інженер", "Бухгалтер", "Монтажник"
        ], state="readonly", font=("Segoe UI", 10))
        self.reg_role.set("Монтажник")
        self.reg_role.pack(fill=tk.X, pady=(2, 0))

        self._styled_btn(frm, "Зареєструватися", self._do_register).pack(
            fill=tk.X, pady=(18, 5))

    def _do_login(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        if not username or not password:
            self.lbl_status.config(text="⚠️ Введіть логін та пароль", fg="#f59e0b")
            return
        user = auth.authenticate(username, password)
        if user:
            self.logged_in_user = user
            # Якщо це був перший вхід — видаляємо файл з тимчасовими даними
            auth.clear_setup_credentials()
            self.root.destroy()
        else:
            self.lbl_status.config(text="❌ Невірний логін або пароль", fg="#ef4444")
            self.entry_pass.delete(0, tk.END)
            self.entry_pass.focus()

    def _do_register(self):
        username = self.reg_user.get().strip()
        full_name = self.reg_name.get().strip()
        password = self.reg_pass.get().strip()
        password2 = self.reg_pass2.get().strip()
        role_label = self.reg_role.get()

        if not all([username, full_name, password]):
            self.lbl_status.config(text="⚠️ Заповніть всі обов'язкові поля", fg="#f59e0b")
            return
        if password != password2:
            self.lbl_status.config(text="❌ Паролі не співпадають", fg="#ef4444")
            return
        if len(password) < 4:
            self.lbl_status.config(text="❌ Пароль мінімум 4 символи", fg="#ef4444")
            return

        role_map = {"Директор": "director", "Інженер": "engineer",
                    "Бухгалтер": "accountant", "Монтажник": "monter"}
        role = role_map.get(role_label, "monter")

        try:
            auth.create_user(username, password, full_name, role)
            self.lbl_status.config(text=f"✅ Користувача {username} створено", fg="#84cc16")
            self.reg_user.delete(0, tk.END)
            self.reg_name.delete(0, tk.END)
            self.reg_pass.delete(0, tk.END)
            self.reg_pass2.delete(0, tk.END)
            self.tabs.select(self.tab_login)
            self.entry_user.insert(0, username)
            self.entry_pass.focus()
        except ValueError as e:
            self.lbl_status.config(text=f"❌ {e}", fg="#ef4444")

    def run(self) -> bool:
        self.root.mainloop()
        return self.logged_in_user is not None


def _show_first_run_dialog(parent):
    """Показати модальне вікно з тимчасовим паролем адміністратора."""
    creds = auth.get_setup_credentials()
    if not creds:
        return

    dialog = tk.Toplevel(parent)
    dialog.title("🔐 Перший запуск — облікові дані адміністратора")
    dialog.geometry("480x280")
    dialog.minsize(400, 300)
    dialog.configure(bg="#18181b")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

    # Центрування
    dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (480 // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (280 // 2)
    dialog.geometry(f"+{x}+{y}")
    dialog.minsize(400, 300)
    dialog.resizable(True, True)

    tk.Label(dialog, text="🏭 VentCompany", font=("Segoe UI", 18, "bold"),
             bg="#18181b", fg="#f97316").pack(pady=(15, 5))

    tk.Label(dialog, text="Створено обліковий запис адміністратора",
             font=("Segoe UI", 11), bg="#18181b", fg="#e4e4e7").pack()

    tk.Label(dialog, text="Збережіть ці дані — їх більше не буде показано!",
             font=("Segoe UI", 9, "bold"), bg="#18181b", fg="#ef4444").pack(pady=(10, 5))

    # Логін
    frm_user = tk.Frame(dialog, bg="#18181b")
    frm_user.pack(fill=tk.X, padx=30, pady=3)
    tk.Label(frm_user, text="Логін:", font=("Segoe UI", 10), bg="#18181b",
             fg="#a1a1aa", width=10, anchor="w").pack(side=tk.LEFT)
    lbl_user = tk.Label(frm_user, text=creds["username"], font=("Consolas", 11, "bold"),
                        bg="#27272a", fg="#84cc16", padx=10, pady=3)
    lbl_user.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Пароль
    frm_pass = tk.Frame(dialog, bg="#18181b")
    frm_pass.pack(fill=tk.X, padx=30, pady=3)
    tk.Label(frm_pass, text="Пароль:", font=("Segoe UI", 10), bg="#18181b",
             fg="#a1a1aa", width=10, anchor="w").pack(side=tk.LEFT)
    lbl_pass = tk.Label(frm_pass, text=creds["password"], font=("Consolas", 11, "bold"),
                        bg="#27272a", fg="#f97316", padx=10, pady=3)
    lbl_pass.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _copy_and_close():
        parent.clipboard_clear()
        parent.clipboard_append(creds["password"])
        parent.update()
        dialog.destroy()

    tk.Button(dialog, text="📋 Копіювати пароль і закрити",
              font=("Segoe UI", 10, "bold"), bg="#f97316", fg="#18181b",
              activebackground="#fb923c", relief="flat", cursor="hand2",
              command=_copy_and_close).pack(pady=(20, 5), ipadx=10, ipady=5)

    tk.Label(dialog, text="Рекомендується одразу змінити пароль у вкладці «Мій кабінет»",
             font=("Segoe UI", 8), bg="#18181b", fg="#52525b").pack(pady=(5, 10))

    parent.wait_window(dialog)


def show_login() -> bool:
    """Показати вікно входу. При першому запуску — створити admin і показати пароль."""
    auth.ensure_default_users()
    win = LoginWindow()

    # Якщо є тимчасові облікові дані — показуємо діалог ПЕРЕД головним вікном
    if auth.has_setup_credentials():
        win.root.update()
        win.root.after(100, lambda: _show_first_run_dialog(win.root))

    return win.run()