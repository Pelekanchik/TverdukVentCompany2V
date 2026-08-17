"""Вкладка CRM — картки клієнтів, історія, платежі, нагадування."""

import os
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, simpledialog, ttk

from ventilation_company.db_integration import ProjectDatabase


class CRMTab:
    """Вкладка CRM з картками клієнтів."""

    def __init__(self, parent: ttk.Notebook):
        self.frame = ttk.Frame(parent)
        self.db = ProjectDatabase()
        self._selected_client_id: int | None = None
        self._build_ui()
        self._refresh_client_list()
        self._check_upcoming_reminders()

    def _build_ui(self):
        # ── Toolbar ──
        tbar = ttk.Frame(self.frame, padding=5)
        tbar.pack(fill=tk.X)

        ttk.Label(tbar, text="👥 CRM", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        ttk.Separator(tbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Button(tbar, text="➕ Новий клієнт", command=self._add_client_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(tbar, text="✏️ Редагувати", command=self._edit_client_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(tbar, text="❌ Видалити", command=self._delete_client).pack(side=tk.LEFT, padx=2)
        ttk.Separator(tbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Label(tbar, text="🔍 Пошук:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._refresh_client_list())
        ttk.Entry(tbar, textvariable=self.search_var, width=20).pack(side=tk.LEFT, padx=2)

        ttk.Separator(tbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(tbar, text="🔔 Нагадування", command=self._show_reminders).pack(side=tk.LEFT, padx=2)

        # ── Основна область: ліворуч список, праворуч деталі ──
        paned = ttk.PanedWindow(self.frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Ліва панель — список клієнтів
        left = ttk.Frame(paned, width=280)
        paned.add(left, weight=1)

        ttk.Label(left, text="Клієнти", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 3))
        cols = ("name", "phone", "balance")
        self.client_tree = ttk.Treeview(left, columns=cols, show="headings", height=20)
        self.client_tree.heading("name", text="Ім'я / Фірма")
        self.client_tree.heading("phone", text="Телефон")
        self.client_tree.heading("balance", text="Баланс")
        self.client_tree.column("name", width=140)
        self.client_tree.column("phone", width=90)
        self.client_tree.column("balance", width=70)
        self.client_tree.pack(fill=tk.BOTH, expand=True)
        self.client_tree.bind("<<TreeviewSelect>>", self._on_client_select)

        # Права панель — деталі клієнта
        right = ttk.Notebook(paned)
        paned.add(right, weight=3)

        # ── Вкладка "Картка" ──
        self.card_frame = ttk.Frame(right, padding=10)
        right.add(self.card_frame, text="📝 Картка")
        self._build_card_tab()

        # ── Вкладка "Взаємодії" ──
        self.inter_frame = ttk.Frame(right, padding=10)
        right.add(self.inter_frame, text="📞 Взаємодії")
        self._build_interactions_tab()

        # ── Вкладка "Платежі" ──
        self.pay_frame = ttk.Frame(right, padding=10)
        right.add(self.pay_frame, text="💰 Платежі")
        self._build_payments_tab()

        # ── Вкладка "Проєкти" ──
        self.proj_frame = ttk.Frame(right, padding=10)
        right.add(self.proj_frame, text="📋 Проєкти")
        self._build_projects_tab()

        # ── Вкладка "Гарантія" ──
        self.warr_frame = ttk.Frame(right, padding=10)
        right.add(self.warr_frame, text="🛡️ Гарантія")
        self._build_warranty_tab()

        # Статус
        self.status = ttk.Label(self.frame, text="Готово", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    # ═══════════════════════════════════════════════════════════════════
    # КАРТКА КЛІЄНТА
    # ═══════════════════════════════════════════════════════════════════

    def _build_card_tab(self):
        self.card_labels: dict[str, ttk.Label] = {}
        fields = [
            ("name", "Назва / Фірма:"),
            ("contact_person", "Контактна особа:"),
            ("phone", "Телефон:"),
            ("email", "Email:"),
            ("address", "Адреса:"),
            ("company_type", "Форма:"),
            ("edrpou", "ЄДРПОУ:"),
            ("notes", "Примітки:"),
        ]
        for key, label in fields:
            frm = ttk.Frame(self.card_frame)
            frm.pack(fill=tk.X, pady=2)
            ttk.Label(frm, text=label, width=16, anchor=tk.E).pack(side=tk.LEFT)
            lbl = ttk.Label(frm, text="—", font=("Arial", 9, "bold"))
            lbl.pack(side=tk.LEFT, padx=5)
            self.card_labels[key] = lbl

    # ═══════════════════════════════════════════════════════════════════
    # ВЗАЄМОДІЇ
    # ═══════════════════════════════════════════════════════════════════

    def _build_interactions_tab(self):
        tbar = ttk.Frame(self.inter_frame)
        tbar.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(tbar, text="➕ Додати дзвінок/зустріч", command=self._add_interaction_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(tbar, text="🗑️ Видалити", command=self._delete_interaction).pack(side=tk.LEFT, padx=2)

        cols = ("date", "type", "subject", "result", "next")
        self.inter_tree = ttk.Treeview(self.inter_frame, columns=cols, show="headings", height=12)
        self.inter_tree.heading("date", text="Дата")
        self.inter_tree.heading("type", text="Тип")
        self.inter_tree.heading("subject", text="Тема")
        self.inter_tree.heading("result", text="Результат")
        self.inter_tree.heading("next", text="Наступна дія")
        for c in cols:
            self.inter_tree.column(c, width=100)
        self.inter_tree.column("subject", width=200)
        self.inter_tree.pack(fill=tk.BOTH, expand=True)

    # ═══════════════════════════════════════════════════════════════════
    # ПЛАТЕЖІ
    # ═══════════════════════════════════════════════════════════════════

    def _build_payments_tab(self):
        tbar = ttk.Frame(self.pay_frame)
        tbar.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(tbar, text="➕ Додати платіж", command=self._add_payment_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(tbar, text="🗑️ Видалити", command=self._delete_payment).pack(side=tk.LEFT, padx=2)

        cols = ("date", "type", "amount", "purpose", "project")
        self.pay_tree = ttk.Treeview(self.pay_frame, columns=cols, show="headings", height=12)
        self.pay_tree.heading("date", text="Дата")
        self.pay_tree.heading("type", text="Тип")
        self.pay_tree.heading("amount", text="Сума")
        self.pay_tree.heading("purpose", text="Призначення")
        self.pay_tree.heading("project", text="Проєкт")
        for c in cols:
            self.pay_tree.column(c, width=100)
        self.pay_tree.column("purpose", width=200)
        self.pay_tree.pack(fill=tk.BOTH, expand=True)

        self.balance_label = ttk.Label(self.pay_frame, text="Баланс: 0.00 грн", font=("Arial", 11, "bold"))
        self.balance_label.pack(anchor=tk.W, pady=5)

    # ═══════════════════════════════════════════════════════════════════
    # ПРОЄКТИ
    # ═══════════════════════════════════════════════════════════════════

    def _build_projects_tab(self):
        tbar = ttk.Frame(self.proj_frame)
        tbar.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(tbar, text="➕ Додати проєкт", command=self._add_project_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(tbar, text="🔄 Змінити статус", command=self._change_project_status).pack(side=tk.LEFT, padx=2)

        cols = ("name", "number", "start", "end", "status", "amount")
        self.proj_tree = ttk.Treeview(self.proj_frame, columns=cols, show="headings", height=12)
        self.proj_tree.heading("name", text="Назва")
        self.proj_tree.heading("number", text="№")
        self.proj_tree.heading("start", text="Початок")
        self.proj_tree.heading("end", text="Завершення")
        self.proj_tree.heading("status", text="Статус")
        self.proj_tree.heading("amount", text="Сума")
        for c in cols:
            self.proj_tree.column(c, width=90)
        self.proj_tree.column("name", width=180)
        self.proj_tree.pack(fill=tk.BOTH, expand=True)

    # ═══════════════════════════════════════════════════════════════════
    # ГАРАНТІЯ
    # ═══════════════════════════════════════════════════════════════════

    def _build_warranty_tab(self):
        tbar = ttk.Frame(self.warr_frame)
        tbar.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(tbar, text="✅ Виконано", command=self._complete_reminder).pack(side=tk.LEFT, padx=2)

        cols = ("date", "project", "description", "completed")
        self.warr_tree = ttk.Treeview(self.warr_frame, columns=cols, show="headings", height=12)
        self.warr_tree.heading("date", text="Дата нагадування")
        self.warr_tree.heading("project", text="Проєкт")
        self.warr_tree.heading("description", text="Опис")
        self.warr_tree.heading("completed", text="Виконано")
        for c in cols:
            self.warr_tree.column(c, width=120)
        self.warr_tree.column("description", width=300)
        self.warr_tree.pack(fill=tk.BOTH, expand=True)

    # ═══════════════════════════════════════════════════════════════════
    # ОНОВЛЕННЯ ДАНИХ
    # ═══════════════════════════════════════════════════════════════════

    def _refresh_client_list(self):
        search = self.search_var.get().strip()
        clients = self.db.get_all_clients(search=search)
        self.client_tree.delete(*self.client_tree.get_children())
        for c in clients:
            balance = self.db.get_client_balance(c["id"])
            self.client_tree.insert("", tk.END, iid=str(c["id"]),
                                    values=(c["name"], c.get("phone", ""), f"{balance:,.2f}"))

    def _on_client_select(self, event=None):
        sel = self.client_tree.selection()
        if not sel:
            return
        self._selected_client_id = int(sel[0])
        self._load_client_card()
        self._load_interactions()
        self._load_payments()
        self._load_projects()
        self._load_warranty()

    def _load_client_card(self):
        client = self.db.get_client(self._selected_client_id)
        if not client:
            return
        for key, lbl in self.card_labels.items():
            val = client.get(key, "") or "—"
            lbl.config(text=str(val))
        self.status.config(text=f"Вибрано: {client.get('name', '')}")

    def _load_interactions(self):
        self.inter_tree.delete(*self.inter_tree.get_children())
        rows = self.db.get_client_interactions(self._selected_client_id)
        for r in rows:
            self.inter_tree.insert("", tk.END, iid=str(r["id"]), values=(
                r.get("date", "")[:10],
                r.get("interaction_type", ""),
                r.get("subject", "") or "—",
                r.get("result", "") or "—",
                r.get("next_action", "") or "—",
            ))

    def _load_payments(self):
        self.pay_tree.delete(*self.pay_tree.get_children())
        rows = self.db.get_client_payments(self._selected_client_id)
        for r in rows:
            self.pay_tree.insert("", tk.END, iid=str(r["id"]), values=(
                r.get("date", "")[:10],
                r.get("payment_type", ""),
                f"{r.get('amount', 0):,.2f} {r.get('currency', 'UAH')}",
                r.get("purpose", "") or "—",
                r.get("project_name", "") or "—",
            ))
        balance = self.db.get_client_balance(self._selected_client_id)
        self.balance_label.config(text=f"Баланс: {balance:,.2f} грн")

    def _load_projects(self):
        self.proj_tree.delete(*self.proj_tree.get_children())
        rows = self.db.get_client_projects(self._selected_client_id)
        for r in rows:
            self.proj_tree.insert("", tk.END, iid=str(r["id"]), values=(
                r.get("project_name", ""),
                r.get("project_number", "") or "—",
                (r.get("start_date").strftime("%Y-%m-%d") if r.get("start_date") else "—"),
                (r.get("end_date").strftime("%Y-%m-%d") if r.get("end_date") else "—"),
                r.get("status", ""),
                f"{r.get('total_amount', 0):,.2f}",
            ))

    def _load_warranty(self):
        self.warr_tree.delete(*self.warr_tree.get_children())
        rows = self.db.get_warranty_reminders(self._selected_client_id, upcoming_days=3650)
        for r in rows:
            self.warr_tree.insert("", tk.END, iid=str(r["id"]), values=(
                (r.get("reminder_date").strftime("%Y-%m-%d") if r.get("reminder_date") else ""),
                r.get("project_name", ""),
                r.get("description", "") or "—",
                "✅ Так" if r.get("is_completed") else "❌ Ні",
            ))

    # ═══════════════════════════════════════════════════════════════════
    # ДІАЛОГИ
    # ═══════════════════════════════════════════════════════════════════

    def _add_client_dialog(self):
        dialog = tk.Toplevel(self.frame)
        dialog.title("➕ Новий клієнт")
        dialog.geometry("400x400")
        dialog.transient(self.frame)
        dialog.grab_set()

        fields = {}
        params = [
            ("name", "Назва / Фірма *", ""),
            ("contact_person", "Контактна особа", ""),
            ("phone", "Телефон", ""),
            ("email", "Email", ""),
            ("address", "Адреса", ""),
            ("company_type", "Форма (ФОП/ТОВ/ПП)", ""),
            ("edrpou", "ЄДРПОУ", ""),
            ("notes", "Примітки", ""),
        ]
        for key, label, default in params:
            frm = ttk.Frame(dialog)
            frm.pack(fill=tk.X, padx=10, pady=2)
            ttk.Label(frm, text=label + ":", width=18).pack(side=tk.LEFT)
            var = tk.StringVar(value=default)
            ttk.Entry(frm, textvariable=var, width=30).pack(side=tk.LEFT)
            fields[key] = var

        def on_ok():
            name = fields["name"].get().strip()
            if not name:
                messagebox.showwarning("Увага", "Вкажіть назву клієнта")
                return
            self.db.add_client(
                name=name,
                contact=fields["contact_person"].get(),
                phone=fields["phone"].get(),
                email=fields["email"].get(),
                address=fields["address"].get(),
                company_type=fields["company_type"].get(),
                edrpou=fields["edrpou"].get(),
                notes=fields["notes"].get(),
            )
            self._refresh_client_list()
            dialog.destroy()
            self.status.config(text=f"✅ Клієнта \"{name}\" додано")

        ttk.Button(dialog, text="✅ Додати", command=on_ok).pack(pady=15)

    def _edit_client_dialog(self):
        if self._selected_client_id is None:
            messagebox.showinfo("Інформація", "Виберіть клієнта зі списку")
            return
        client = self.db.get_client(self._selected_client_id)
        if not client:
            return

        dialog = tk.Toplevel(self.frame)
        dialog.title("✏️ Редагувати клієнта")
        dialog.geometry("400x400")
        dialog.transient(self.frame)
        dialog.grab_set()

        fields = {}
        params = [
            ("name", "Назва / Фірма", client.get("name", "")),
            ("contact_person", "Контактна особа", client.get("contact_person", "")),
            ("phone", "Телефон", client.get("phone", "")),
            ("email", "Email", client.get("email", "")),
            ("address", "Адреса", client.get("address", "")),
            ("company_type", "Форма", client.get("company_type", "")),
            ("edrpou", "ЄДРПОУ", client.get("edrpou", "")),
            ("notes", "Примітки", client.get("notes", "")),
        ]
        for key, label, default in params:
            frm = ttk.Frame(dialog)
            frm.pack(fill=tk.X, padx=10, pady=2)
            ttk.Label(frm, text=label + ":", width=18).pack(side=tk.LEFT)
            var = tk.StringVar(value=default or "")
            ttk.Entry(frm, textvariable=var, width=30).pack(side=tk.LEFT)
            fields[key] = var

        def on_ok():
            self.db.update_client(
                self._selected_client_id,
                name=fields["name"].get(),
                contact_person=fields["contact_person"].get(),
                phone=fields["phone"].get(),
                email=fields["email"].get(),
                address=fields["address"].get(),
                company_type=fields["company_type"].get(),
                edrpou=fields["edrpou"].get(),
                notes=fields["notes"].get(),
            )
            self._refresh_client_list()
            self._load_client_card()
            dialog.destroy()
            self.status.config(text="✅ Клієнта оновлено")

        ttk.Button(dialog, text="💾 Зберегти", command=on_ok).pack(pady=15)

    def _delete_client(self):
        if self._selected_client_id is None:
            messagebox.showinfo("Інформація", "Виберіть клієнта")
            return
        client = self.db.get_client(self._selected_client_id)
        if not client:
            return
        if messagebox.askyesno("Підтвердження", f"Видалити клієнта \"{client['name']}\"?\n\nВсі дані (платежі, проєкти, взаємодії) будуть видалені!"):
            self.db.delete_client(self._selected_client_id)
            self._selected_client_id = None
            self._refresh_client_list()
            self.status.config(text="🗑️ Клієнта видалено")

    def _add_interaction_dialog(self):
        if self._selected_client_id is None:
            messagebox.showinfo("Інформація", "Виберіть клієнта")
            return
        dialog = tk.Toplevel(self.frame)
        dialog.title("📞 Нова взаємодія")
        dialog.geometry("400x350")
        dialog.transient(self.frame)
        dialog.grab_set()

        ttk.Label(dialog, text="Тип:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        type_var = tk.StringVar(value="дзвінок")
        ttk.Combobox(dialog, textvariable=type_var, values=["дзвінок", "зустріч", "лист", "email", "замітка"], state="readonly", width=20).pack(anchor=tk.W, padx=10)

        ttk.Label(dialog, text="Тема:").pack(anchor=tk.W, padx=10, pady=(5, 0))
        subj_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=subj_var, width=40).pack(anchor=tk.W, padx=10)

        ttk.Label(dialog, text="Опис:").pack(anchor=tk.W, padx=10, pady=(5, 0))
        desc_text = tk.Text(dialog, width=40, height=4, wrap=tk.WORD)
        desc_text.pack(anchor=tk.W, padx=10)

        ttk.Label(dialog, text="Результат:").pack(anchor=tk.W, padx=10, pady=(5, 0))
        res_var = tk.StringVar(value="у процесі")
        ttk.Combobox(dialog, textvariable=res_var, values=["позитив", "негатив", "у процесі"], state="readonly", width=20).pack(anchor=tk.W, padx=10)

        ttk.Label(dialog, text="Наступна дія:").pack(anchor=tk.W, padx=10, pady=(5, 0))
        next_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=next_var, width=40).pack(anchor=tk.W, padx=10)

        def on_ok():
            self.db.add_interaction(
                client_id=self._selected_client_id,
                interaction_type=type_var.get(),
                subject=subj_var.get(),
                description=desc_text.get("1.0", tk.END).strip(),
                result=res_var.get(),
                next_action=next_var.get(),
            )
            self._load_interactions()
            dialog.destroy()
            self.status.config(text="✅ Взаємодію додано")

        ttk.Button(dialog, text="✅ Додати", command=on_ok).pack(pady=10)

    def _delete_interaction(self):
        sel = self.inter_tree.selection()
        if not sel:
            messagebox.showinfo("Інформація", "Виберіть взаємодію")
            return
        if messagebox.askyesno("Підтвердження", "Видалити вибрану взаємодію?"):
            self.db.delete_interaction(int(sel[0]))
            self._load_interactions()
            self.status.config(text="🗑️ Взаємодію видалено")

    def _add_payment_dialog(self):
        if self._selected_client_id is None:
            messagebox.showinfo("Інформація", "Виберіть клієнта")
            return
        dialog = tk.Toplevel(self.frame)
        dialog.title("💰 Новий платіж")
        dialog.geometry("350x300")
        dialog.transient(self.frame)
        dialog.grab_set()

        ttk.Label(dialog, text="Тип:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        type_var = tk.StringVar(value="вхідний")
        ttk.Combobox(dialog, textvariable=type_var, values=["вхідний", "вихідний"], state="readonly", width=15).pack(anchor=tk.W, padx=10)

        ttk.Label(dialog, text="Сума (грн):").pack(anchor=tk.W, padx=10, pady=(5, 0))
        amt_var = tk.DoubleVar(value=0)
        ttk.Spinbox(dialog, from_=0, to=9999999, increment=100, textvariable=amt_var, width=15).pack(anchor=tk.W, padx=10)

        ttk.Label(dialog, text="Призначення:").pack(anchor=tk.W, padx=10, pady=(5, 0))
        purp_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=purp_var, width=35).pack(anchor=tk.W, padx=10)

        ttk.Label(dialog, text="Проєкт:").pack(anchor=tk.W, padx=10, pady=(5, 0))
        proj_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=proj_var, width=35).pack(anchor=tk.W, padx=10)

        def on_ok():
            self.db.add_payment(
                client_id=self._selected_client_id,
                amount=amt_var.get(),
                payment_type=type_var.get(),
                purpose=purp_var.get(),
                project_name=proj_var.get(),
            )
            self._load_payments()
            self._refresh_client_list()  # оновити баланс
            dialog.destroy()
            self.status.config(text="✅ Платіж додано")

        ttk.Button(dialog, text="✅ Додати", command=on_ok).pack(pady=10)

    def _delete_payment(self):
        sel = self.pay_tree.selection()
        if not sel:
            messagebox.showinfo("Інформація", "Виберіть платіж")
            return
        if messagebox.askyesno("Підтвердження", "Видалити вибраний платіж?"):
            self.db.delete_payment(int(sel[0]))
            self._load_payments()
            self._refresh_client_list()
            self.status.config(text="🗑️ Платіж видалено")

    def _add_project_dialog(self):
        if self._selected_client_id is None:
            messagebox.showinfo("Інформація", "Виберіть клієнта")
            return
        dialog = tk.Toplevel(self.frame)
        dialog.title("📋 Новий проєкт")
        dialog.geometry("400x350")
        dialog.transient(self.frame)
        dialog.grab_set()

        ttk.Label(dialog, text="Назва проєкту *:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=40).pack(anchor=tk.W, padx=10)

        ttk.Label(dialog, text="Номер:").pack(anchor=tk.W, padx=10, pady=(5, 0))
        num_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=num_var, width=40).pack(anchor=tk.W, padx=10)

        ttk.Label(dialog, text="Дата початку (РРРР-ММ-ДД):").pack(anchor=tk.W, padx=10, pady=(5, 0))
        start_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(dialog, textvariable=start_var, width=15).pack(anchor=tk.W, padx=10)

        ttk.Label(dialog, text="Дата завершення (РРРР-ММ-ДД):").pack(anchor=tk.W, padx=10, pady=(5, 0))
        end_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=end_var, width=15).pack(anchor=tk.W, padx=10)

        ttk.Label(dialog, text="Сума (грн):").pack(anchor=tk.W, padx=10, pady=(5, 0))
        amt_var = tk.DoubleVar(value=0)
        ttk.Spinbox(dialog, from_=0, to=9999999, increment=1000, textvariable=amt_var, width=15).pack(anchor=tk.W, padx=10)

        ttk.Label(dialog, text="Гарантія (міс):").pack(anchor=tk.W, padx=10, pady=(5, 0))
        warr_var = tk.IntVar(value=24)
        ttk.Spinbox(dialog, from_=0, to=120, increment=1, textvariable=warr_var, width=10).pack(anchor=tk.W, padx=10)

        def on_ok():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Увага", "Вкажіть назву проєкту")
                return
            self.db.add_client_project(
                client_id=self._selected_client_id,
                project_name=name,
                project_number=num_var.get(),
                start_date=start_var.get(),
                end_date=end_var.get() or None,
                total_amount=amt_var.get(),
                warranty_months=warr_var.get(),
            )
            self._load_projects()
            self._load_warranty()
            dialog.destroy()
            self.status.config(text=f"✅ Проєкт \"{name}\" додано")

        ttk.Button(dialog, text="✅ Додати", command=on_ok).pack(pady=10)

    def _change_project_status(self):
        sel = self.proj_tree.selection()
        if not sel:
            messagebox.showinfo("Інформація", "Виберіть проєкт")
            return
        statuses = ["в роботі", "завершено", "гарантія", "закрито"]
        dialog = tk.Toplevel(self.frame)
        dialog.title("🔄 Змінити статус")
        dialog.geometry("250x150")
        dialog.transient(self.frame)
        dialog.grab_set()
        ttk.Label(dialog, text="Новий статус:").pack(pady=5)
        status_var = tk.StringVar()
        ttk.Combobox(dialog, textvariable=status_var, values=statuses, state="readonly", width=15).pack(pady=5)
        def on_ok():
            self.db.update_client_project_status(int(sel[0]), status_var.get())
            self._load_projects()
            dialog.destroy()
        ttk.Button(dialog, text="✅ Змінити", command=on_ok).pack(pady=10)

    def _complete_reminder(self):
        sel = self.warr_tree.selection()
        if not sel:
            messagebox.showinfo("Інформація", "Виберіть нагадування")
            return
        notes = simpledialog.askstring("Примітки", "Результат виконання:", parent=self.frame)
        self.db.complete_warranty_reminder(int(sel[0]), notes or "")
        self._load_warranty()
        self.status.config(text="✅ Нагадування виконано")

    def _show_reminders(self):
        """Показати всі майбутні нагадування."""
        dialog = tk.Toplevel(self.frame)
        dialog.title("🔔 Нагадування про гарантію")
        dialog.geometry("600x400")
        dialog.transient(self.frame)

        cols = ("date", "client", "project", "description")
        tree = ttk.Treeview(dialog, columns=cols, show="headings", height=15)
        tree.heading("date", text="Дата")
        tree.heading("client", text="Клієнт")
        tree.heading("project", text="Проєкт")
        tree.heading("description", text="Опис")
        tree.column("date", width=100)
        tree.column("client", width=150)
        tree.column("project", width=150)
        tree.column("description", width=250)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        rows = self.db.get_warranty_reminders(upcoming_days=365)
        for r in rows:
            tree.insert("", tk.END, values=(
                (r.get("reminder_date").strftime("%Y-%m-%d") if r.get("reminder_date") else ""),
                r.get("client_name", ""),
                r.get("project_name", ""),
                r.get("description", "") or "—",
            ))

        ttk.Button(dialog, text="OK", command=dialog.destroy).pack(pady=5)

    def _check_upcoming_reminders(self):
        """Перевірити нагадування при старті."""
        try:
            rows = self.db.get_warranty_reminders(upcoming_days=7)
            if rows:
                msg = f"⚠️ {len(rows)} нагадувань на найближчий тиждень:\n"
                for r in rows[:5]:
                    msg += f"\n• {r.get('client_name', '')} — {r.get('project_name', '')} ({r.get('reminder_date', '')[:10]})"
                if len(rows) > 5:
                    msg += f"\n... та ще {len(rows) - 5}"
                messagebox.showinfo("🔔 Нагадування", msg)
        except Exception:
            pass
