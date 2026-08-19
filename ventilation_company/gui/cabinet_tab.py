"""Вкладка "Мій кабінет" — профіль, зміна пароля, керування користувачами (тільки директор).

ВСТАНОВЛЕННЯ:
    1. Скопіюйте цей файл у: ventilation_company/gui/cabinet_tab.py
    2. У main_window.py додайте імпорт та вкладку (див. INSTRUCTIONS.md)
"""

import tkinter as tk
from tkinter import messagebox, ttk

from ventilation_company.auth.service import auth
from ventilation_company.auth.permissions import get_role_label


class CabinetTab(ttk.Frame):
    """Вкладка "Мій кабінет" з профілем та керуванням доступом."""

    def __init__(self, parent, current_user: str, is_director: bool = False):
        super().__init__(parent)
        self.current_user = current_user
        self.is_director = is_director
        self._build_ui()

    def _build_ui(self):
        # === Ліва частина: Мій профіль (доступно всім) ===
        left_frame = ttk.LabelFrame(self, text="🏠 Мій профіль", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5, ipadx=5)

        user = auth.get_user_by_username(self.current_user)
        if user:
            ttk.Label(left_frame, text=f"👤 Логін: {user.username}",
                      font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=2)
            ttk.Label(left_frame, text=f"📝 ПІБ: {user.full_name or '—'}").pack(anchor=tk.W, pady=2)
            ttk.Label(left_frame, text=f"🛡️ Роль: {get_role_label(user.role)}",
                      foreground="#f97316").pack(anchor=tk.W, pady=2)
            ttk.Label(left_frame, text=f"🆔 ID: {user.id}").pack(anchor=tk.W, pady=2)
        else:
            ttk.Label(left_frame, text="Користувача не знайдено", foreground="red").pack(anchor=tk.W)

        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Редагування ПІБ
        ttk.Label(left_frame, text="📝 Редагувати ПІБ",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))

        self.name_var = tk.StringVar(value=user.full_name if user else "")
        ttk.Entry(left_frame, textvariable=self.name_var, width=25).pack(pady=2, fill=tk.X)
        ttk.Button(left_frame, text="💾 Зберегти ПІБ",
                   command=self._change_name).pack(pady=5, fill=tk.X)

        self.name_status = ttk.Label(left_frame, text="", foreground="#84cc16")
        self.name_status.pack(anchor=tk.W, pady=2)

        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Зміна пароля
        ttk.Label(left_frame, text="🔒 Зміна пароля",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))

        self.old_pass = ttk.Entry(left_frame, show="•", width=25)
        self.old_pass.pack(pady=2, fill=tk.X)
        self.old_pass.insert(0, "Старий пароль")
        self.old_pass.bind("<FocusIn>",
            lambda e: self._clear_placeholder(self.old_pass, "Старий пароль"))

        self.new_pass = ttk.Entry(left_frame, show="•", width=25)
        self.new_pass.pack(pady=2, fill=tk.X)
        self.new_pass.insert(0, "Новий пароль")
        self.new_pass.bind("<FocusIn>",
            lambda e: self._clear_placeholder(self.new_pass, "Новий пароль"))

        self.new_pass2 = ttk.Entry(left_frame, show="•", width=25)
        self.new_pass2.pack(pady=2, fill=tk.X)
        self.new_pass2.insert(0, "Підтвердіть пароль")
        self.new_pass2.bind("<FocusIn>",
            lambda e: self._clear_placeholder(self.new_pass2, "Підтвердіть пароль"))

        ttk.Button(left_frame, text="💾 Змінити пароль",
                   command=self._change_own_password).pack(pady=5, fill=tk.X)

        self.status_label = ttk.Label(left_frame, text="", foreground="#ef4444")
        self.status_label.pack(anchor=tk.W, pady=5)

        # === Права частина: Керування доступом (ТІЛЬКИ ДИРЕКТОР) ===
        if self.is_director:
            right_frame = ttk.LabelFrame(self, text="⚙️ Керування доступом (Директор)", padding=10)
            right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Кнопки НАД таблицею
            btn_frame = ttk.Frame(right_frame)
            btn_frame.pack(fill=tk.X, pady=(0, 5))
            ttk.Button(btn_frame, text="➕ Додати",
                       command=self._add_user_dialog).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="✏️ Редагувати",
                       command=self._edit_user_dialog).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="🗑️ Видалити",
                       command=self._delete_user).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="🔄 Оновити",
                       command=self._refresh_users).pack(side=tk.LEFT, padx=2)

            # Таблиця зі скролбаром
            table_container = ttk.Frame(right_frame)
            table_container.pack(fill=tk.BOTH, expand=True)

            cols = ("Логін", "ПІБ", "Посада", "Активний")
            self.users_tree = ttk.Treeview(table_container, columns=cols,
                                           show="headings", height=12)
            for col in cols:
                self.users_tree.heading(col, text=col)
                self.users_tree.column(col, width=100, anchor=tk.CENTER)
            self.users_tree.grid(row=0, column=0, sticky="nsew")

            scrollbar = ttk.Scrollbar(table_container, orient=tk.VERTICAL,
                                      command=self.users_tree.yview)
            self.users_tree.configure(yscrollcommand=scrollbar.set)
            scrollbar.grid(row=0, column=1, sticky="ns")

            table_container.grid_rowconfigure(0, weight=1)
            table_container.grid_columnconfigure(0, weight=1)

            self._refresh_users()
        else:
            info = ttk.LabelFrame(self, text="📋 Мої дозволи", padding=10)
            info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

            perms_text = "🔸 Перегляд проєктів: ✅\n"
            perms_text += "🔸 Редагування цін: " + (
                "✅" if user and user.role in ("director", "engineer") else "❌"
            ) + "\n"
            perms_text += "🔸 Видалення проєктів: " + (
                "✅" if user and user.role == "director" else "❌"
            ) + "\n"
            perms_text += "🔸 Керування користувачами: ❌ (тільки Директор)"
            ttk.Label(info, text=perms_text, justify=tk.LEFT).pack(anchor=tk.NW, pady=5)

    def _clear_placeholder(self, entry, placeholder):
        if entry.get() == placeholder:
            entry.delete(0, tk.END)

    def _change_name(self):
        """Зберегти нове ПІБ поточного користувача."""
        new_name = self.name_var.get().strip()
        if not new_name:
            self.name_status.config(text="⚠️ Введіть ПІБ", foreground="#f59e0b")
            return
        user = auth.get_user_by_username(self.current_user)
        if not user:
            self.name_status.config(text="❌ Користувача не знайдено", foreground="#ef4444")
            return
        try:
            auth.update_user(user.id, full_name=new_name)
            self.name_status.config(text="✅ ПІБ оновлено", foreground="#84cc16")
        except Exception as e:
            self.name_status.config(text=f"❌ Помилка: {e}", foreground="#ef4444")

    def _refresh_users(self):
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        for u in auth.list_users():
            self.users_tree.insert("", tk.END, values=(
                u.username, u.full_name or "—", get_role_label(u.role), "Так"
            ))

    def _change_own_password(self):
        old = self.old_pass.get()
        new = self.new_pass.get()
        new2 = self.new_pass2.get()

        if old in ("Старий пароль", "") or new in ("Новий пароль", "") \
                or new2 in ("Підтвердіть пароль", ""):
            self.status_label.config(text="⚠️ Заповніть всі поля", foreground="#f59e0b")
            return
        if new != new2:
            self.status_label.config(text="❌ Паролі не співпадають", foreground="#ef4444")
            return
        if len(new) < 4:
            self.status_label.config(text="❌ Пароль мінімум 4 символи", foreground="#ef4444")
            return

        user = auth.authenticate(self.current_user, old)
        if not user:
            self.status_label.config(text="❌ Старий пароль невірний", foreground="#ef4444")
            return

        try:
            auth.update_user(user.id, password=new)
            self.status_label.config(text="✅ Пароль змінено", foreground="#84cc16")
            self.old_pass.delete(0, tk.END)
            self.new_pass.delete(0, tk.END)
            self.new_pass2.delete(0, tk.END)
        except Exception as e:
            self.status_label.config(text=f"❌ Помилка: {e}", foreground="#ef4444")

    def _add_user_dialog(self):
        win = tk.Toplevel(self)
        win.title("Новий користувач")
        win.geometry("380x420")
        win.transient(self)
        win.grab_set()

        frm = ttk.Frame(win, padding=15)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="👤 Логін *").pack(anchor=tk.W, pady=(5, 2))
        login_entry = ttk.Entry(frm, width=30)
        login_entry.pack(fill=tk.X, pady=2)

        ttk.Label(frm, text="📝 Повне ім'я *").pack(anchor=tk.W, pady=(8, 2))
        name_entry = ttk.Entry(frm, width=30)
        name_entry.pack(fill=tk.X, pady=2)

        ttk.Label(frm, text="🔒 Пароль *").pack(anchor=tk.W, pady=(8, 2))
        pass_entry = ttk.Entry(frm, show="•", width=30)
        pass_entry.pack(fill=tk.X, pady=2)

        ttk.Label(frm, text="🔒 Підтвердіть пароль *").pack(anchor=tk.W, pady=(8, 2))
        pass2_entry = ttk.Entry(frm, show="•", width=30)
        pass2_entry.pack(fill=tk.X, pady=2)

        ttk.Label(frm, text="🛡️ Посада *").pack(anchor=tk.W, pady=(8, 2))
        role_var = tk.StringVar(value="Монтажник")
        ttk.Combobox(frm, values=["Директор", "Інженер", "Бухгалтер", "Монтажник"],
                     state="readonly", textvariable=role_var, width=27).pack(fill=tk.X, pady=2)

        status = ttk.Label(frm, text="", foreground="#ef4444")
        status.pack(anchor=tk.W, pady=5)

        def save():
            login = login_entry.get().strip()
            name = name_entry.get().strip()
            password = pass_entry.get()
            password2 = pass2_entry.get()
            role_label = role_var.get()

            if not all([login, name, password]):
                status.config(text="⚠️ Заповніть обов'язкові поля", foreground="#f59e0b")
                return
            if password != password2:
                status.config(text="❌ Паролі не співпадають", foreground="#ef4444")
                return
            if len(password) < 4:
                status.config(text="❌ Пароль мінімум 4 символи", foreground="#ef4444")
                return

            role_map = {"Директор": "director", "Інженер": "engineer",
                        "Бухгалтер": "accountant", "Монтажник": "monter"}
            role = role_map.get(role_label, "monter")

            try:
                auth.create_user(login, password, name, role)
                self._refresh_users()
                win.destroy()
                messagebox.showinfo("Успіх", f"Користувача {login} створено")
            except ValueError as e:
                status.config(text=f"❌ {e}", foreground="#ef4444")

        ttk.Button(frm, text="💾 Створити", command=save).pack(fill=tk.X, pady=10)

    def _edit_user_dialog(self):
        sel = self.users_tree.selection()
        if not sel:
            messagebox.showwarning("Увага", "Оберіть користувача")
            return
        username = self.users_tree.item(sel[0])["values"][0]
        user = auth.get_user_by_username(username)
        if not user:
            return
        if username == self.current_user:
            messagebox.showwarning("Увага",
                "Використовуйте 'Мій профіль' для зміни свого пароля")
            return

        dlg = tk.Toplevel(self)
        dlg.title(f"Редагування: {username}")
        dlg.geometry("400x400")
        dlg.transient(self)
        dlg.grab_set()

        frm = ttk.Frame(dlg, padding=15)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text=f"👤 Логін: {username}",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=5)

        ttk.Label(frm, text="📝 Повне ім'я").pack(anchor=tk.W, pady=(10, 2))
        name_var = tk.StringVar(value=user.full_name or "")
        ttk.Entry(frm, textvariable=name_var, width=30).pack(fill=tk.X, pady=2)

        ttk.Label(frm, text="🛡️ Посада").pack(anchor=tk.W, pady=(10, 2))
        role_var = tk.StringVar(value=get_role_label(user.role))
        ttk.Combobox(frm, values=["Директор", "Інженер", "Бухгалтер", "Монтажник"],
                     state="readonly", textvariable=role_var, width=27).pack(fill=tk.X, pady=2)

        ttk.Label(frm, text="🔒 Новий пароль (залиште порожнім, щоб не змінювати)").pack(
            anchor=tk.W, pady=(10, 2))
        pass_var = tk.StringVar()
        ttk.Entry(frm, textvariable=pass_var, show="•", width=30).pack(fill=tk.X, pady=2)

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
            messagebox.showinfo("Успіх", f"Користувача {username} оновлено")

        ttk.Button(frm, text="💾 Зберегти", command=save).pack(fill=tk.X, pady=15)

    def _delete_user(self):
        sel = self.users_tree.selection()
        if not sel:
            messagebox.showwarning("Увага", "Оберіть користувача")
            return
        username = self.users_tree.item(sel[0])["values"][0]
        if username == self.current_user:
            messagebox.showerror("Помилка", "Не можна видалити самого себе")
            return
        user = auth.get_user_by_username(username)
        if user and messagebox.askyesno("Підтвердження",
                                         f'Видалити користувача "{username}"?'):
            auth.delete_user(user.id)
            self._refresh_users()
            messagebox.showinfo("Успіх", f"Користувача {username} видалено")
