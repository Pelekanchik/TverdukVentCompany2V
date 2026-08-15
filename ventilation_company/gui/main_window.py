"""Головне вікно додатку VentCompany — Compact Header Edition."""

import os
import tkinter as tk
from tkinter import messagebox, ttk

from ventilation_company.auth.service import auth
from ventilation_company.auth.permissions import TAB_PERMISSIONS, get_role_label
from ventilation_company.gui.login_window import show_login
from ventilation_company.db_integration import ProjectDatabase, save_project_full
from ventilation_company.gui.cutting_tab import CuttingTab
from ventilation_company.gui.project3d_tab_new import Project3DTabNew
from ventilation_company.gui.products_tab import ProductsTab
from ventilation_company.gui.settings_tab import SettingsTab
from ventilation_company.gui.price_list_tab import PriceListTab
from ventilation_company.gui.metal_prices_tab import MetalPricesTab
from ventilation_company.gui.specification_tab import SpecificationTab
from ventilation_company.gui.production_tab import ProductionTab
from ventilation_company.gui.material_order_tab import MaterialOrderTab
from ventilation_company.gui.aerodynamics_tab import AerodynamicsTab
from ventilation_company.gui.crm_tab import CRMTab
from ventilation_company.gui.dashboard_tab import DashboardTab
from ventilation_company.gui.theme_manager import get_theme_manager


class MainWindow:
    """Головне вікно програми з компактним заголовком."""

    def __init__(self):
        if not show_login():
            return

        self.current_user = auth.current_user

        self.root = tk.Tk()
        self.root.title(
            f"🏭 VentCompany — {self.current_user.full_name} "
            f"({get_role_label(self.current_user.role)})"
        )
        self.root.geometry("1400x900")
        self.root.minsize(1200, 700)

        self.db = ProjectDatabase("data/company.db")
        self.current_project_id = None
        self._auto_save_id = None

        self.theme_mgr = get_theme_manager()
        self.theme_mgr.on_change(self._on_theme_change)
        self.theme_mgr.apply(self.root)

        self._build_compact_header()
        self._build_menu()
        self._build_ui()
        self._update_theme_button()
        self._apply_permissions()
        self._schedule_auto_save()

    def _schedule_auto_save(self):
        if self._auto_save_id:
            self.root.after_cancel(self._auto_save_id)
        self._auto_save_id = self.root.after(300000, self._auto_save)

    def _auto_save(self):
        try:
            products = self._get_products()
            if not products or not self.current_project_id:
                self._schedule_auto_save()
                return
            project_name = self.spec_tab.project_name_var.get() or "auto_save"
            versions_dir = os.path.join("data", "versions", str(self.current_project_id))
            os.makedirs(versions_dir, exist_ok=True)
            self.spec_tab._generate()
            spec = self.spec_tab.get_specification()
            self.cutting_tab._calculate()
            plan = self.cutting_tab.get_plan()
            version_data = {
                "project_id": self.current_project_id,
                "project_name": project_name,
                "saved_at": datetime.now().isoformat(),
                "products": [p.to_dict() if hasattr(p, "to_dict") else p for p in products],
                "specification": spec.to_dict() if spec else None,
                "cutting_plan": plan.to_dict() if plan else None,
            }
            filename = f"{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(versions_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(version_data, f, ensure_ascii=False, indent=2)
            versions = sorted(os.listdir(versions_dir))
            if len(versions) > 50:
                for old_file in versions[:-50]:
                    os.remove(os.path.join(versions_dir, old_file))
            self.status_bar.config(text=f"💾 Автозбережено: {filename}")
        except Exception as e:
            self.status_bar.config(text=f"⚠️ Помилка автозбереження: {e}")
        finally:
            self._schedule_auto_save()

    def _show_version_history(self):
        if not self.current_project_id:
            messagebox.showinfo("Інформація", "Спочатку збережіть проєкт.")
            return
        versions_dir = os.path.join("data", "versions", str(self.current_project_id))
        if not os.path.exists(versions_dir):
            messagebox.showinfo("Історія версій", "Немає збережених версій.")
            return
        versions = sorted(os.listdir(versions_dir), reverse=True)
        if not versions:
            messagebox.showinfo("Історія версій", "Немає збережених версій.")
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("📜 Історія версій")
        dialog.geometry("600x450")
        dialog.transient(self.root)
        ttk.Label(dialog, text=f"Проєкт: {self.spec_tab.project_name_var.get()}",
                  font=("Segoe UI", 11, "bold")).pack(pady=5)
        cols = ("date", "filename")
        tree = ttk.Treeview(dialog, columns=cols, show="headings", height=12)
        tree.heading("date", text="Дата та час")
        tree.heading("filename", text="Файл")
        tree.column("date", width=180)
        tree.column("filename", width=350)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        for v in versions:
            try:
                dt = datetime.strptime(v.split("_")[-1].replace(".json", ""), "%Y%m%d_%H%M%S")
                tree.insert("", tk.END, values=(dt.strftime("%d.%m.%Y %H:%M:%S"), v))
            except Exception:
                tree.insert("", tk.END, values=("—", v))
        def on_restore():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Інформація", "Виберіть версію для відновлення.")
                return
            filename = tree.item(sel[0])["values"][1]
            filepath = os.path.join(versions_dir, filename)
            if not messagebox.askyesno("Підтвердження",
                                       f"Відновити версію \"{filename}\"?\n\nПоточні незбережені зміни будуть втрачені!"):
                return
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                from ventilation_company.models.product import Product
                products = [Product.from_dict(p) for p in data.get("products", [])]
                self._set_products(products)
                self.status_bar.config(text=f"✅ Відновлено версію: {filename}")
                messagebox.showinfo("Успіх", f"Версію \"{filename}\" відновлено!")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося відновити:\n{e}")
        def on_delete():
            sel = tree.selection()
            if not sel:
                return
            filename = tree.item(sel[0])["values"][1]
            if messagebox.askyesno("Підтвердження", f"Видалити версію \"{filename}\"?"):
                os.remove(os.path.join(versions_dir, filename))
                tree.delete(sel[0])
        btn_frm = ttk.Frame(dialog)
        btn_frm.pack(pady=10)
        ttk.Button(btn_frm, text="🔄 Відновити", command=on_restore).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frm, text="🗑️ Видалити", command=on_delete).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frm, text="❌ Закрити", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    # ═══════════════════════════════════════════════════════════
    # КОМПАКТНИЙ ЗАГОЛОВОК (все в один рядок)
    # ═══════════════════════════════════════════════════════════
    def _build_compact_header(self):
        """Один компактний рядок: користувач + проєкт + кнопки."""
        theme = self.theme_mgr.get()
        hdr = tk.Frame(self.root, bg=theme["bg"], padx=8, pady=4)
        hdr.pack(fill=tk.X)

        # Ліва частина — користувач + проєкт
        left = tk.Frame(hdr, bg=theme["bg"])
        left.pack(side=tk.LEFT, fill=tk.Y)

        role_label = get_role_label(self.current_user.role)
        role_color = theme["accent"] if self.current_user.role == "director" else                      theme["accent2"] if self.current_user.role == "engineer" else                      theme["accent3"] if self.current_user.role == "accountant" else                      theme["warning"]

        # Один рядок: 🏭 Ім'я | Посада | 📁 Проєкт
        info_line = tk.Frame(left, bg=theme["bg"])
        info_line.pack(anchor="w")

        tk.Label(info_line, text="🏭", font=("Segoe UI", 11), bg=theme["bg"], fg=theme["accent"]).pack(side=tk.LEFT)
        tk.Label(info_line, text=self.current_user.full_name,
                 font=("Segoe UI", 10, "bold"), bg=theme["bg"], fg=theme["fg"]).pack(side=tk.LEFT, padx=(2, 0))
        tk.Label(info_line, text=f"• {role_label}",
                 font=("Segoe UI", 9), bg=theme["bg"], fg=role_color).pack(side=tk.LEFT, padx=(4, 0))

        tk.Label(info_line, text="|", font=("Segoe UI", 9),
                 bg=theme["bg"], fg=theme["border"]).pack(side=tk.LEFT, padx=6)

        tk.Label(info_line, text="📁", font=("Segoe UI", 9),
                 bg=theme["bg"], fg=theme["fg_muted"]).pack(side=tk.LEFT)
        self.project_label = tk.Label(info_line, text="Новий проєкт",
                                      font=("Segoe UI", 9), bg=theme["bg"], fg=theme["fg_muted"])
        self.project_label.pack(side=tk.LEFT, padx=(2, 0))

        # Права частина — кнопки (компактні)
        right = tk.Frame(hdr, bg=theme["bg"])
        right.pack(side=tk.RIGHT)

        tk.Button(right, text="💾 Зберегти", command=self._save_project,
                  bg=theme["accent"], fg=theme["button_active_fg"],
                  activebackground=theme["accent_soft"],
                  activeforeground=theme["button_active_fg"],
                  relief="flat", cursor="hand2",
                  font=("Segoe UI", 8, "bold"), padx=10, pady=3).pack(side=tk.LEFT, padx=2)

        tk.Button(right, text="📜", command=self._show_version_history,
                  bg=theme["button_bg"], fg=theme["button_fg"],
                  activebackground=theme["button_hover"],
                  activeforeground=theme["button_fg"],
                  relief="flat", cursor="hand2",
                  font=("Segoe UI", 8), padx=6, pady=3).pack(side=tk.LEFT, padx=1)

        tk.Button(right, text="🏗️", command=self._export_3d_project,
                  bg=theme["button_bg"], fg=theme["button_fg"],
                  activebackground=theme["button_hover"],
                  activeforeground=theme["button_fg"],
                  relief="flat", cursor="hand2",
                  font=("Segoe UI", 8), padx=6, pady=3).pack(side=tk.LEFT, padx=1)

        tk.Button(right, text="🌙", command=self._toggle_theme,
                  bg=theme["button_bg"], fg=theme["button_fg"],
                  activebackground=theme["button_hover"],
                  activeforeground=theme["button_fg"],
                  relief="flat", cursor="hand2",
                  font=("Segoe UI", 8), padx=6, pady=3).pack(side=tk.LEFT, padx=1)

        tk.Button(right, text="🚪", command=self._logout,
                  bg=theme["danger"], fg="#ffffff",
                  activebackground="#b91c1c", activeforeground="#ffffff",
                  relief="flat", cursor="hand2",
                  font=("Segoe UI", 8, "bold"), padx=6, pady=3).pack(side=tk.LEFT, padx=2)

    def _logout(self):
        if messagebox.askyesno("Вихід", "Вийти з системи?"):
            auth.logout()
            self.root.destroy()
            import sys
            os.execl(sys.executable, sys.executable, *sys.argv)

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        project_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Проєкт", menu=project_menu)
        project_menu.add_command(label="💾 Зберегти в БД", command=self._save_project)
        project_menu.add_command(label="📂 Відкрити проєкт", command=self._load_project)
        project_menu.add_separator()
        project_menu.add_command(label="🚪 Вихід", command=self.root.quit)
        export_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Експорт", menu=export_menu)
        export_menu.add_command(label="🏗️ Експорт 3D-проєкту", command=self._export_3d_project)
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Довідка", menu=help_menu)
        help_menu.add_command(label="Про програму", command=self._show_about)

    def _build_ui(self):
        theme = self.theme_mgr.get()

        # ── Вкладки ──
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 8))

        self.products_tab = ProductsTab(
            self.notebook, on_products_changed=self._on_products_changed
        )
        self.spec_tab = SpecificationTab(
            self.notebook,
            get_products_callback=self._get_products,
            on_cutting_request=self._open_cutting_for_project,
        )
        self.cutting_tab = CuttingTab(self.notebook, get_products_callback=self._get_products)
        self.project_3d_tab = Project3DTabNew(self.notebook, self)
        self.settings_tab = SettingsTab(self.notebook)
        self.production_tab = ProductionTab(
            self.notebook,
            get_products_callback=self._get_products,
            get_project_info_callback=self._get_project_info,
        )
        self.material_order_tab = MaterialOrderTab(
            self.notebook,
            get_products_callback=self._get_products,
            get_project_info_callback=self._get_project_info,
        )
        self.aerodynamics_tab = AerodynamicsTab(self.notebook)
        self.price_list_tab = PriceListTab(self.notebook, get_products_callback=self._get_products)
        self.crm_tab = CRMTab(self.notebook)
        self.dashboard_tab = DashboardTab(self.notebook)
        self.metal_prices_tab = MetalPricesTab(self.notebook)

        self.notebook.add(self.products_tab.frame, text="📦 Вироби")
        self.notebook.add(self.spec_tab.frame, text="📋 Специфікація")
        self.notebook.add(self.cutting_tab.frame, text="✂️ Розкрій")
        self.notebook.add(self.project_3d_tab, text="🏗️ Проєкти 3D")
        self.notebook.add(self.settings_tab.frame, text="💰 Ціноутворення")
        self.notebook.add(self.production_tab.frame, text="🏭 Виробництво")
        self.notebook.add(self.material_order_tab.frame, text="📦 Матеріали")
        self.notebook.add(self.aerodynamics_tab.frame, text="💨 Аеродинаміка")
        self.notebook.add(self.dashboard_tab.frame, text="📊 Дашборд")
        self.notebook.add(self.price_list_tab.frame, text="🏷️ Прайс-лист")
        self.notebook.add(self.crm_tab.frame, text="👥 CRM")
        self.notebook.add(self.metal_prices_tab.frame, text="🔧 Ціни на метал")

        self.price_list_tab._current_project_id = self.current_project_id

        # ── Статус-бар ──
        self.status_bar = tk.Label(
            self.root, text="Готово", relief=tk.SUNKEN, anchor=tk.W,
            bg=theme["status_bg"], fg=theme["status_fg"],
            font=("Segoe UI", 9), padx=10, pady=3,
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.notebook.select(self.dashboard_tab.frame)

    def _apply_permissions(self):
        for tab_text, required_perms in TAB_PERMISSIONS.items():
            has_access = any(auth.can(p) for p in required_perms)
            if not has_access:
                for idx in range(self.notebook.index("end")):
                    if self.notebook.tab(idx, "text") == tab_text:
                        self.notebook.hide(idx)
                        break

    def _toggle_theme(self):
        self.theme_mgr.toggle()

    def _on_theme_change(self, theme):
        self.theme_mgr.apply(self.root)
        self._update_theme_button()
        if hasattr(self, "dashboard_tab"):
            self.dashboard_tab._refresh_all()
        for tab_name in ["products_tab", "project_3d_tab", "cutting_tab",
                         "price_list_tab", "crm_tab"]:
            if hasattr(self, tab_name):
                tab = getattr(self, tab_name)
                if hasattr(tab, "frame"):
                    self.theme_mgr._update_widget(tab.frame, theme)

    def _update_theme_button(self):
        pass

    def _get_products(self):
        return self.products_tab.get_products_dict()

    def _set_products(self, products):
        self.products_tab.load_products_from_dict(products)

    def _get_project_info(self):
        name = self.spec_tab.project_name_var.get() if hasattr(self, "spec_tab") else "Проєкт"
        return {"name": name, "id": self.current_project_id}

    def _on_products_changed(self):
        self.status_bar.config(text=f"Виробів: {len(self.products_tab.get_library())}")

    def _get_products_for_price(self):
        try:
            return self.products_tab.library.to_dict()
        except Exception:
            return []

    def _save_project(self):
        products = self._get_products()
        if not products:
            messagebox.showwarning("Увага", "Додайте хоча б один виріб.")
            return
        project_name = self.spec_tab.project_name_var.get()
        try:
            self.spec_tab._generate()
            spec = self.spec_tab.get_specification()
            self.cutting_tab._calculate()
            plan = self.cutting_tab.get_plan()
            spec_data = spec.to_dict() if spec else None
            plan_data = plan.to_dict() if plan else None
            result = save_project_full(
                project_name=project_name,
                products=products,
                spec_data=spec_data,
                cutting_plan=plan_data,
                db_path="data/company.db",
            )
            self.current_project_id = result["project_id"]
            self.project_label.config(
                text=f"{project_name} (ID: {self.current_project_id})",
                fg=self.theme_mgr.get()["accent2"],
            )
            self.status_bar.config(
                text=f"✅ Проєкт збережено. ID: {self.current_project_id}",
                fg=self.theme_mgr.get()["status_ok"],
            )
            messagebox.showinfo("Успіх", f"Проєкт збережено!\nID: {self.current_project_id}")
            self.price_list_tab._current_project_id = self.current_project_id
            
            # === ЕТАП 7: Оновлюємо 3D-вкладку ===
            self.project_3d_tab.set_project({
                "products": products,
                "project_id": self.current_project_id,
                "name": project_name,
            })
            # =====================================
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося зберегти:\n{str(e)}")

    def _load_project(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Відкрити проєкт")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Оберіть проєкт:").pack(pady=5)
        listbox = tk.Listbox(dialog, height=15)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        projects = self.db.get_all_projects()
        for p in projects:
            listbox.insert(tk.END, f"[{p['id']}] {p['name']} — {p['created_at']}")
        def on_select():
            sel = listbox.curselection()
            if sel:
                idx = sel[0]
                project_id = projects[idx]["id"]
                self._load_project_data(project_id)
                
                # === ЕТАП 7: Оновлюємо 3D-вкладку ===
                try:
                    products = self._get_products()
                    self.project_3d_tab.set_project({
                        "products": products,
                        "project_id": project_id,
                    })
                except Exception:
                    pass  # якщо ще немає виробів — ігноруємо
                # =====================================
                dialog.destroy()
        ttk.Button(dialog, text="Відкрити", command=on_select).pack(pady=5)

    def _load_project_data(self, project_id: int):
        project = self.db.get_project(project_id)
        if not project:
            messagebox.showerror("Помилка", "Проєкт не знайдено.")
            return
        self.spec_tab.project_name_var.set(project["name"])
        self.project_label.config(text=f"{project['name']} (ID: {project_id})")
        products = self.db.get_project_products(project_id)
        self.products_tab.load_products_from_dict(products)
        self.current_project_id = project_id
        self.price_list_tab._current_project_id = self.current_project_id
        self.status_bar.config(text=f"📂 Завантажено проєкт ID: {project_id}")
        messagebox.showinfo("Успіх", f"Проєкт '{project['name']}' завантажено.")

    def _open_cutting_for_project(self, project_id: int):
        products = self.db.get_project_products(project_id)
        self.notebook.select(self.cutting_tab.frame)
        self.cutting_tab.run_cutting_for_products(products)

    def _export_3d_project(self):
        self.notebook.select(self.project_3d_tab.frame)

    def _show_about(self):
        messagebox.showinfo(
            "Про програму",
            "🏭 VentCompany\n"
            "Система управління вентиляційними проєктами\n\n"
            "Модулі:\n"
            "• Бібліотека стандартних виробів\n"
            "• Автоматичний розкрій металу\n"
            "• Специфікація з експортом\n"
            "• Інтеграція з базою даних\n"
            "• 3D/2D проєкти\n"
            "• Ціноутворення з формулами",
        )

    def run(self):
        self.root.mainloop()


def main():
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
