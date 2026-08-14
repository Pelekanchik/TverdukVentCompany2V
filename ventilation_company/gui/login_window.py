"""Вікно автентифікації (логін / пароль / реєстрація / редагування).

Відображається перед головним вікном.
Підтримує Enter для входу.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from ventilation_company.auth.service import auth
from ventilation_company.auth.permissions import get_role_label, Role


class LoginWindow:
    """Вікно входу в систему з реєстрацією та редагуванням профілю."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🔐 VentCompany — Вхід в систему")
        self.root.geometry("460x680")
        self.root.resizable(True, True)
        self.root.minsize(420, 600)
        self.root.configure(bg="#18181b")

        # Центрування
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (460 // 2)
        y = (self.root.winfo_screenheight() // 2) - (680 // 2)
        self.root.geometry(f"+{x}+{y}")

        self.logged_in_user = None
        self._build_ui()

    def _build_ui(self):
        # ── Фрейм картки ──
        card = tk.Frame(self.root, bg="#18181b", bd=0, highlightthickness=0)
        card.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Логотип
        lbl_icon = tk.Label(card, text="🏭", font=("Segoe UI", 42), bg="#18181b", fg="#f97316")
        lbl_icon.pack(pady=(10, 2))

        lbl_title = tk.Label(card, text="VentCompany", font=("Segoe UI", 20, "bold"),
                             bg="#18181b", fg="#e4e4e7")
        lbl_title.pack()

        lbl_sub = tk.Label(card, text="Система управління вентиляційними проєктами",
                           font=("Segoe UI", 9), bg="#18181b", fg="#71717a")
        lbl_sub.pack(pady=(0, 10))

        # ── Таби: Вхід / Реєстрація / Користувачі ──
        self.tabs = ttk.Notebook(card)
        self.tabs.pack(fill=tk.BOTH, expand=True, pady=5)

        # === ВКЛАДКА ВХІД ===
        self.tab_login = tk.Frame(self.tabs, bg="#18181b")
        self.tabs.add(self.tab_login, text="  🔐 Вхід  ")
        self._build_login_tab(self.tab_login)

        # === ВКЛАДКА РЕЄСТРАЦІЯ ===
        self.tab_register = tk.Frame(self.tabs, bg="#18181b")
        self.tabs.add(self.tab_register, text="  📝 Реєстрація  ")
        self._build_register_tab(self.tab_register)

        # === ВКЛАДКА КОРИСТУВАЧІ ===
        self.tab_users = tk.Frame(self.tabs, bg="#18181b")
        self.tabs.add(self.tab_users, text="  👥 Користувачі  ")
        self._build_users_tab(self.tab_users)

        # ── Статус ──
        self.lbl_status = tk.Label(card, text="", font=("Segoe UI", 9),
                                   bg="#18181b", fg="#ef4444")
        self.lbl_status.pack(pady=(5, 0))

        # ── Підказка ──
        hint = tk.Label(card,
            text="Дефолтні: admin/admin123 | engineer/eng123\n"
                 "accountant/acc123 | monter/mon123",
            font=("Segoe UI", 8), bg="#18181b", fg="#52525b", justify="center")
        hint.pack(side=tk.BOTTOM, pady=5)

    def _styled_entry(self, parent, show=None, width=32):
        """Створити стильне поле вводу."""
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

        self._styled_label(frm, "👤  Логін").pack(fill=tk.X, pady=(15, 2))
        self.entry_user = self._styled_entry(frm)
        self.entry_user.pack(fill=tk.X, ipady=5)
        self.entry_user.focus()

        self._styled_label(frm, "🔒  Пароль").pack(fill=tk.X, pady=(12, 2))
        self.entry_pass = self._styled_entry(frm, show="•")
        self.entry_pass.pack(fill=tk.X, ipady=5)

        self.entry_pass.bind("<Return>", lambda e: self._do_login())
        self.entry_user.bind("<Return>", lambda e: self.entry_pass.focus())

        self._styled_btn(frm, "Увійти в систему", self._do_login).pack(
            fill=tk.X, pady=(25, 5))

    def _build_register_tab(self, parent):
        frm = tk.Frame(parent, bg="#18181b", padx=25, pady=10)
        frm.pack(fill=tk.BOTH, expand=True)

        self._styled_label(frm, "👤  Логін *").pack(fill=tk.X, pady=(8, 2))
        self.reg_user = self._styled_entry(frm)
        self.reg_user.pack(fill=tk.X, ipady=4)

        self._styled_label(frm, "📝  Повне ім'я *").pack(fill=tk.X, pady=(8, 2))
        self.reg_name = self._styled_entry(frm)
        self.reg_name.pack(fill=tk.X, ipady=4)

        self._styled_label(frm, "🔒  Пароль *").pack(fill=tk.X, pady=(8, 2))
        self.reg_pass = self._styled_entry(frm, show="•")
        self.reg_pass.pack(fill=tk.X, ipady=4)

        self._styled_label(frm, "🔒  Підтвердіть пароль *").pack(fill=tk.X, pady=(8, 2))
        self.reg_pass2 = self._styled_entry(frm, show="•")
        self.reg_pass2.pack(fill=tk.X, ipady=4)

        self._styled_label(frm, "🛡️  Посада *").pack(fill=tk.X, pady=(8, 2))
        self.reg_role = ttk.Combobox(frm, values=[
            "Директор", "Інженер", "Бухгалтер", "Монтажник"
        ], state="readonly", font=("Segoe UI", 10))
        self.reg_role.set("Монтажник")
        self.reg_role.pack(fill=tk.X, pady=(2, 0))

        self._styled_btn(frm, "Зареєструватися", self._do_register).pack(
            fill=tk.X, pady=(18, 5))

    def _build_users_tab(self, parent):
        frm = tk.Frame(parent, bg="#18181b", padx=15, pady=5)
        frm.pack(fill=tk.BOTH, expand=True)

        cols = ("user", "name", "role")
        self.users_tree = ttk.Treeview(frm, columns=cols, show="headings", height=10)
        self.users_tree.heading("user", text="Логін")
        self.users_tree.heading("name", text="Ім'я")
        self.users_tree.heading("role", text="Посада")
        self.users_tree.column("user", width=100)
        self.users_tree.column("name", width=130)
        self.users_tree.column("role", width=100)
        self.users_tree.pack(fill=tk.BOTH, expand=True, pady=(5, 5))

        btn_frm = tk.Frame(frm, bg="#18181b")
        btn_frm.pack(fill=tk.X, pady=5)
        tk.Button(btn_frm, text="✏️ Редагувати", font=("Segoe UI", 9),
                  bg="#3f3f46", fg="#e4e4e7", relief="flat", cursor="hand2",
                  command=self._edit_user_dialog).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frm, text="🗑️ Видалити", font=("Segoe UI", 9),
                  bg="#ef4444", fg="#ffffff", relief="flat", cursor="hand2",
                  command=self._delete_user).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frm, text="🔄 Оновити", font=("Segoe UI", 9),
                  bg="#3f3f46", fg="#e4e4e7", relief="flat", cursor="hand2",
                  command=self._refresh_users).pack(side=tk.LEFT, padx=2)

        self._refresh_users()

    def _refresh_users(self):
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        for u in auth.list_users():
            self.users_tree.insert("", tk.END, values=(
                u.username, u.full_name, get_role_label(u.role)
            ))

    def _edit_user_dialog(self):
        sel = self.users_tree.selection()
        if not sel:
            self.lbl_status.config(text="⚠️ Оберіть користувача", fg="#f59e0b")
            return
        username = self.users_tree.item(sel[0])["values"][0]
        user = auth.get_user_by_username(username)
        if not user:
            return

        dlg = tk.Toplevel(self.root)
        dlg.title(f"Редагування: {username}")
        dlg.geometry("400x400")
        dlg.minsize(380, 350)
        dlg.configure(bg="#18181b")
        dlg.transient(self.root)
        dlg.grab_set()

        frm = tk.Frame(dlg, bg="#18181b", padx=20, pady=15)
        frm.pack(fill=tk.BOTH, expand=True)

        tk.Label(frm, text="👤 Логін", font=("Segoe UI", 9), bg="#18181b", fg="#a1a1aa").pack(anchor="w", pady=(5, 2))
        tk.Label(frm, text=username, font=("Segoe UI", 11, "bold"), bg="#18181b", fg="#e4e4e7").pack(anchor="w")

        tk.Label(frm, text="📝 Повне ім'я", font=("Segoe UI", 9), bg="#18181b", fg="#a1a1aa").pack(anchor="w", pady=(10, 2))
        name_var = tk.StringVar(value=user.full_name)
        tk.Entry(frm, textvariable=name_var, font=("Segoe UI", 11),
                 bg="#3f3f46", fg="#e4e4e7", insertbackground="#f97316",
                 relief="flat", highlightthickness=1, highlightcolor="#f97316",
                 highlightbackground="#52525b").pack(fill=tk.X, ipady=4)

        tk.Label(frm, text="🛡️ Посада", font=("Segoe UI", 9), bg="#18181b", fg="#a1a1aa").pack(anchor="w", pady=(10, 2))
        role_var = tk.StringVar(value=get_role_label(user.role))
        role_combo = ttk.Combobox(frm, values=["Директор", "Інженер", "Бухгалтер", "Монтажник"],
                                   state="readonly", textvariable=role_var, font=("Segoe UI", 10))
        role_combo.pack(fill=tk.X)

        tk.Label(frm, text="🔒 Новий пароль (залиште порожнім, щоб не змінювати)",
                 font=("Segoe UI", 9), bg="#18181b", fg="#a1a1aa").pack(anchor="w", pady=(10, 2))
        pass_var = tk.StringVar()
        tk.Entry(frm, textvariable=pass_var, font=("Segoe UI", 11), show="•",
                 bg="#3f3f46", fg="#e4e4e7", insertbackground="#f97316",
                 relief="flat", highlightthickness=1, highlightcolor="#f97316",
                 highlightbackground="#52525b").pack(fill=tk.X, ipady=4)

        def save():
            role_map = {"Директор": "director", "Інженер": "engineer",
                        "Бухгалтер": "accountant", "Монтажник": "monter"}
            new_role = role_map.get(role_var.get(), user.role)
            kwargs = {"full_name": name_var.get(), "role": new_role}
            if pass_var.get():
                kwargs["password"] = pass_var.get()
            auth.update_user(user.id, **kwargs)
            self._refresh_users()
            dlg.destroy()
            self.lbl_status.config(text="✅ Користувача оновлено", fg="#84cc16")

        tk.Button(frm, text="💾 Зберегти", font=("Segoe UI", 10, "bold"),
                  bg="#f97316", fg="#18181b", relief="flat", cursor="hand2",
                  command=save).pack(fill=tk.X, pady=(20, 5))

    def _delete_user(self):
        sel = self.users_tree.selection()
        if not sel:
            self.lbl_status.config(text="⚠️ Оберіть користувача", fg="#f59e0b")
            return
        username = self.users_tree.item(sel[0])["values"][0]
        if username == "admin":
            self.lbl_status.config(text="❌ Неможливо видалити admin", fg="#ef4444")
            return
        user = auth.get_user_by_username(username)
        if user and messagebox.askyesno("Підтвердження", f'Видалити користувача "{username}"?'):
            auth.delete_user(user.id)
            self._refresh_users()
            self.lbl_status.config(text=f"✅ {username} видалено", fg="#84cc16")

    def _do_login(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        if not username or not password:
            self.lbl_status.config(text="⚠️ Введіть логін та пароль", fg="#f59e0b")
            return
        user = auth.authenticate(username, password)
        if user:
            self.logged_in_user = user
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
            self._refresh_users()
            self.tabs.select(self.tab_login)
            self.entry_user.insert(0, username)
            self.entry_pass.focus()
        except ValueError as e:
            self.lbl_status.config(text=f"❌ {e}", fg="#ef4444")

    def run(self) -> bool:
        self.root.mainloop()
        return self.logged_in_user is not None


def show_login() -> bool:
    """Показати вікно входу та ініціалізувати дефолтних користувачів."""
    auth.ensure_default_users()
    win = LoginWindow()
    return win.run()
