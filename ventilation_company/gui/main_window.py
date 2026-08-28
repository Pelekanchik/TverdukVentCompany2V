"""Головне вікно додатку VentCompany — Compact Header Edition."""

import json
import os
import sys
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from ventilation_company.gui.cabinet_tab import CabinetTab
from ventilation_company.auth.service import auth
from ventilation_company.auth.permissions import TAB_PERMISSIONS, get_role_label
from ventilation_company.gui.login_window import show_login
from ventilation_company.db_integration import ProjectDatabase, save_project_full
from ventilation_company.gui.cutting_tab import CuttingTab
from ventilation_company.gui.project_3d_tab import Project3DTab
from ventilation_company.gui.products_tab import ProductsTab
from ventilation_company.gui.documents_tab import DocumentsTab
from ventilation_company.gui.settings_tab import SettingsTab
from ventilation_company.gui.price_list_tab import PriceListTab
from ventilation_company.gui.specification_tab import SpecificationTab
from ventilation_company.gui.production_tab import ProductionTab
from ventilation_company.gui.material_order_tab import MaterialOrderTab
from ventilation_company.gui.metal_prices_tab import MetalPricesTab
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
        self.is_director = (self.current_user.role == "director")

        self.root = tk.Tk()
        self.root.title(
            f"🏭 VentCompany — {self.current_user.full_name} "
            f"({get_role_label(self.current_user.role)})"
        )
        self.root.geometry("1400x900")
        self.root.resizable(True, True)
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
        """Автозбереження тепер у SQLite БД замість JSON-файлів."""
        try:
            products = self._get_products()
            # Перераховуємо зарплати перед автозбереженням
            self._recalculate_salaries(products)
            if not products or not self.current_project_id:
                self._schedule_auto_save()
                return

            project_name = self.spec_tab.project_name_var.get() or "auto_save"

            # Оновлюємо назву проєкту
            self.db.update_project(
                self.current_project_id,
                name=project_name,
                updated_at=datetime.now(),
            )
            # Перезаписуємо вироби в БД
            old_products = self.db.get_project_products(self.current_project_id)
            for p in old_products:
                self.db.delete_product(p["id"])
            for p in products:
                self.db.add_product_to_project(self.current_project_id, p)

            self.status_bar.config(
                text=f"💾 Автозбережено в БД: проєкт ID {self.current_project_id}"
            )
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
        dialog.minsize(400, 300)
        dialog.resizable(True, True)
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
        """Мінімальний рядок: користувач + проєкт (без кнопок)."""
        theme = self.theme_mgr.get()
        hdr = tk.Frame(self.root, bg=theme["bg"], padx=8, pady=2, height=28)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        role_label = get_role_label(self.current_user.role)
        role_color = theme["accent"] if self.current_user.role == "director" else theme["accent2"] if self.current_user.role == "engineer" else theme["accent3"] if self.current_user.role == "accountant" else theme["warning"]

        tk.Label(hdr, text=f"🏭 {self.current_user.full_name} • {role_label}",
                 font=("Segoe UI", 9), bg=theme["bg"], fg=theme["fg"]).pack(side=tk.LEFT)
        tk.Label(hdr, text="|", font=("Segoe UI", 9),
                 bg=theme["bg"], fg=theme["border"]).pack(side=tk.LEFT, padx=6)
        self.project_label = tk.Label(hdr, text="📁 Новий проєкт",
                                      font=("Segoe UI", 9), bg=theme["bg"], fg=theme["fg_muted"])
        self.project_label.pack(side=tk.LEFT)

    def _logout(self):
        if messagebox.askyesno("Вихід", "Вийти з системи?"):
            auth.logout()
            self.root.destroy()
            os.execl(sys.executable, sys.executable, *sys.argv)

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        project_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Проєкт", menu=project_menu)
        project_menu.add_command(label="💾 Зберегти в БД", command=self._save_project)
        project_menu.add_command(label="📂 Відкрити проєкт", command=self._load_project)
        project_menu.add_command(label="🔄 Перерахувати ціни", command=self._recalculate_current_project)
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

        # ── Головний контейнер: сайдбар + контент ──
        main_frame = tk.Frame(self.root, bg=theme["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ── Сайдбар ──
        self.sidebar = tk.Frame(main_frame, bg=theme["sidebar_bg"], width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Логотип / заголовок сайдбару
        tk.Label(self.sidebar, text="🏭 VentCompany", font=("Segoe UI", 13, "bold"),
                 bg=theme["sidebar_bg"], fg=theme["accent"]).pack(pady=(10, 5), padx=10, anchor="w")

        # Роздільник
        tk.Frame(self.sidebar, bg=theme["border"], height=1).pack(fill=tk.X, padx=10, pady=5)

        # Структура меню: (категорія, [(emoji, назва, notebook, tab_index or widget), ...])
        self._sidebar_items = []
        self._active_sub_btn = None

        def _cat(text, items):
            """Додати розділ-категорію з підпунктами."""
            cat_btn = tk.Button(
                self.sidebar, text=text, font=("Segoe UI", 10, "bold"),
                bg=theme["sidebar_bg"], fg=theme["sidebar_fg"],
                activebackground=theme["sidebar_hover"], activeforeground=theme["sidebar_fg"],
                relief="flat", anchor="w", padx=10, pady=5, cursor="hand2"
            )
            cat_btn.pack(fill=tk.X, padx=5, pady=(5, 0))
            sub_frame = tk.Frame(self.sidebar, bg=theme["sidebar_bg"])
            sub_frame.pack(fill=tk.X, padx=5)
            for emoji, label, target_nb, target_idx in items:
                sub = tk.Button(
                    sub_frame, text=f"  {emoji} {label}", font=("Segoe UI", 9),
                    bg=theme["sidebar_bg"], fg=theme["sidebar_fg"],
                    activebackground=theme["sidebar_hover"], activeforeground=theme["sidebar_fg"],
                    relief="flat", anchor="w", padx=25, pady=3, cursor="hand2",
                    command=lambda nb=target_nb, idx=target_idx, btn=None: self._show_tab(nb, idx, btn)
                )
                sub.pack(fill=tk.X)
                self._sidebar_items.append((sub, target_nb, target_idx))
            return sub_frame

        # ── КОНТЕНТ-ФРЕЙМИ ──
        self.content_frame = tk.Frame(main_frame, bg=theme["bg"])
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 1. ПРОЄКТ
        self.project_frame = ttk.Frame(self.content_frame)
        # Приховуємо вкладки під-ноутбуків — навігація тільки через сайдбар
        style = ttk.Style()
        style.layout("HiddenTab.TNotebook.Tab", [])
        style.configure("HiddenTab.TNotebook", tabmargins=0)

        self.project_nb = ttk.Notebook(self.project_frame, style="HiddenTab.TNotebook")
        self.project_nb.pack(fill=tk.BOTH, expand=True)

        self.products_tab = ProductsTab(self.project_nb, on_products_changed=self._on_products_changed)
        self.project_nb.add(self.products_tab.frame, text="🔧 Вироби")

        self.spec_tab = SpecificationTab(self.project_nb, get_products_callback=self._get_products)
        self.project_nb.add(self.spec_tab.frame, text="📋 Специфікація")

        self.cutting_tab = CuttingTab(self.project_nb, get_products_callback=self._get_products, get_standard_products_callback=self._get_standard_products)
        self.project_nb.add(self.cutting_tab.frame, text="✂️ Розкрій")

        self.project_3d_tab = Project3DTab(self.project_nb, get_products_callback=self.products_tab.get_products_data)
        self.project_nb.add(self.project_3d_tab.frame, text="🧊 3D")

        # 2. ФІНАНСИ
        self.finance_frame = ttk.Frame(self.content_frame)
        self.finance_nb = ttk.Notebook(self.finance_frame, style="HiddenTab.TNotebook")
        self.finance_nb.pack(fill=tk.BOTH, expand=True)

        self.settings_tab = SettingsTab(self.finance_nb)
        self.finance_nb.add(self.settings_tab.frame, text="💰 Ціноутворення")

        self.price_list_tab = PriceListTab(self.finance_nb, get_products_callback=self._get_products)
        self.finance_nb.add(self.price_list_tab.frame, text="🏷️ Прайс-лист")

        self.documents_tab = DocumentsTab(self.finance_nb)
        self.finance_nb.add(self.documents_tab.frame, text="📄 Документи")

        # 3. ВИРОБНИЦТВО
        self.prod_frame = ttk.Frame(self.content_frame)
        self.prod_nb = ttk.Notebook(self.prod_frame, style="HiddenTab.TNotebook")
        self.prod_nb.pack(fill=tk.BOTH, expand=True)

        self.production_tab = ProductionTab(self.prod_nb, get_products_callback=self.products_tab.get_products_data)
        self.prod_nb.add(self.production_tab.frame, text="🏭 Виробництво")

        self.material_order_tab = MaterialOrderTab(self.prod_nb, get_products_callback=self.products_tab.get_products_data)
        self.prod_nb.add(self.material_order_tab.frame, text="📦 Матеріали")

        self.aerodynamics_tab = AerodynamicsTab(self.prod_nb)
        self.prod_nb.add(self.aerodynamics_tab.frame, text="💨 Аеродинаміка")

        # 4. АНАЛІТИКА
        self.analytics_frame = ttk.Frame(self.content_frame)
        self.analytics_nb = ttk.Notebook(self.analytics_frame, style="HiddenTab.TNotebook")
        self.analytics_nb.pack(fill=tk.BOTH, expand=True)

        self.dashboard_tab = DashboardTab(self.analytics_nb)
        self.analytics_nb.add(self.dashboard_tab.frame, text="📊 Дашборд")

        self.crm_tab = CRMTab(self.analytics_nb)
        self.analytics_nb.add(self.crm_tab.frame, text="👥 CRM")

        # 5. КАБІНЕТ
        self.cabinet_frame = ttk.Frame(self.content_frame)
        self.cabinet_tab = CabinetTab(
            self.cabinet_frame,
            current_user=self.current_user.username,
            is_director=self.is_director,
        )
        self.cabinet_tab.pack(fill=tk.BOTH, expand=True)

        # Зберігаємо всі верхні фрейми для перемикання
        self._main_frames = {
            "project": self.project_frame,
            "finance": self.finance_frame,
            "prod": self.prod_frame,
            "analytics": self.analytics_frame,
            "cabinet": self.cabinet_frame,
        }

        # ── Будуємо сайдбар (після створення фреймів, щоб lambda працювали) ──
        self._project_subs = _cat("📋 Проєкт", [
            ("🔧", "Вироби", self.project_nb, 0),
            ("📋", "Специфікація", self.project_nb, 1),
            ("✂️", "Розкрій", self.project_nb, 2),
            ("🧊", "3D", self.project_nb, 3),
        ])
        self._finance_subs = _cat("💰 Фінанси", [
            ("💰", "Ціноутворення", self.finance_nb, 0),
            ("🏷️", "Прайс-лист", self.finance_nb, 1),
            ("📄", "Документи", self.finance_nb, 2),
        ])
        self._prod_subs = _cat("🏭 Виробництво", [
            ("🏭", "Виробництво", self.prod_nb, 0),
            ("📦", "Матеріали", self.prod_nb, 1),
            ("💨", "Аеродинаміка", self.prod_nb, 2),
        ])
        self._analytics_subs = _cat("📊 Аналітика", [
            ("📊", "Дашборд", self.analytics_nb, 0),
            ("👥", "CRM", self.analytics_nb, 1),
        ])

        # Кабінет — без підпунктів
        cabinet_btn = tk.Button(
            self.sidebar, text="👤 Кабінет", font=("Segoe UI", 10, "bold"),
            bg=theme["sidebar_bg"], fg=theme["sidebar_fg"],
            activebackground=theme["sidebar_hover"], activeforeground=theme["sidebar_fg"],
            relief="flat", anchor="w", padx=10, pady=5, cursor="hand2",
            command=lambda: self._show_main_frame("cabinet", None, None)
        )
        cabinet_btn.pack(fill=tk.X, padx=5, pady=(5, 0))

        # ── Статус-бар ──
        self.status_bar = tk.Label(
            self.root, text="Готово", relief=tk.SUNKEN, anchor=tk.W,
            bg=theme["status_bg"], fg=theme["status_fg"],
            font=("Segoe UI", 9), padx=10, pady=2,
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # Показуємо перший пункт за замовчуванням
        self._show_tab(self.project_nb, 0, None)

    def _show_main_frame(self, frame_key, notebook, tab_idx):
        """Показати головний фрейм і приховати інші."""
        for key, frm in self._main_frames.items():
            if key == frame_key:
                frm.pack(fill=tk.BOTH, expand=True)
            else:
                frm.pack_forget()
        if notebook is not None and tab_idx is not None:
            notebook.select(tab_idx)
        # Оновлюємо підсвічування сайдбару
        theme = self.theme_mgr.get()
        for btn, nb, idx in self._sidebar_items:
            if nb is notebook and idx == tab_idx:
                btn.config(bg=theme["sidebar_active"], fg=theme["sidebar_active_fg"])
            else:
                btn.config(bg=theme["sidebar_bg"], fg=theme["sidebar_fg"])

    def _show_tab(self, notebook, tab_idx, btn):
        """Визначити який головний фрейм відкривати і показати вкладку."""
        if notebook is self.project_nb:
            self._show_main_frame("project", notebook, tab_idx)
        elif notebook is self.finance_nb:
            self._show_main_frame("finance", notebook, tab_idx)
        elif notebook is self.prod_nb:
            self._show_main_frame("prod", notebook, tab_idx)
        elif notebook is self.analytics_nb:
            self._show_main_frame("analytics", notebook, tab_idx)
        else:
            self._show_main_frame("cabinet", notebook, tab_idx)

    def _apply_permissions(self):
        for tab_text, required_perms in TAB_PERMISSIONS.items():
            has_access = any(auth.can(p) for p in required_perms)
            if not has_access:
                # Ховаємо відповідні пункти сайдбару
                _map = {
                    "📋 Проєкт": [self._project_subs],
                    "💰 Фінанси": [self._finance_subs],
                    "🏭 Виробництво": [self._prod_subs],
                    "📊 Аналітика": [self._analytics_subs],
                    "👤 Кабінет": [],
                }
                for widget in _map.get(tab_text, []):
                    widget.pack_forget()

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

    def _get_standard_products(self):
        return self.products_tab.get_standard_products()

    def _set_products(self, products):
        self.products_tab.load_products_from_dict(products)

    def _get_project_info(self):
        name = self.spec_tab.project_name_var.get() if hasattr(self, "spec_tab") else "Проєкт"
        return {"name": name, "id": self.current_project_id}

    def _on_products_changed(self):
        self.status_bar.config(text=f"Виробів: {len(self.products_tab.get_library())}")

    def _on_materials_changed(self):
        """Обробник зміни матеріалів."""
        pass

    def _get_products_for_price(self):
        try:
            return self.products_tab.library.to_dict()
        except Exception:
            return []

    def _recalculate_salaries(self, products):
        """Перерахувати зарплату для всіх виробів з актуальними ставками."""
        from ventilation_company.gui.settings_tab import PricingSettings
        settings = PricingSettings.get_instance()
        for p in products:
            ptype = p.get("product_type", "")
            metal_area = p.get("metal_area_m2", 0) or p.get("surface_area", 0)
            qty = p.get("quantity", 1)
            if metal_area and ptype:
                labor = settings.get_labor_rate(ptype)
                rate = labor.get("rate_per_m2", 120.0)
                difficulty = labor.get("difficulty_percent", 0.0)
                salary = metal_area * rate * (1 + difficulty / 100)
                p["salary_per_unit"] = round(salary, 2)
                p["salary_total"] = round(salary * qty, 2)

    def _save_project(self):
        """Зберегти проєкт: оновлює існуючий або створює новий."""
        products = self._get_products()
        # Перераховуємо зарплати перед збереженням
        self._recalculate_salaries(products)
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

            if self.current_project_id:
                # ── ОНОВЛЕННЯ існуючого проєкту ──
                self.db.update_project(
                    self.current_project_id,
                    name=project_name,
                    updated_at=datetime.now(),
                )
                # Видаляємо старі вироби проєкту
                old_products = self.db.get_project_products(self.current_project_id)
                for p in old_products:
                    self.db.delete_product(p["id"])
                # Додаємо актуальні вироби
                for p in products:
                    self.db.add_product_to_project(self.current_project_id, p)
                project_id = self.current_project_id
            else:
                # ── СТВОРЕННЯ нового проєкту ──
                result = save_project_full(
                    project_name=project_name,
                    products=products,
                    spec_data=spec_data,
                    cutting_plan=plan_data,
                    db_path="data/company.db",
                )
                project_id = result["project_id"]
                self.current_project_id = project_id

            self.project_label.config(
                text=f"{project_name} (ID: {project_id})",
                fg=self.theme_mgr.get()["accent2"],
            )
            self.status_bar.config(
                text=f"✅ Проєкт збережено. ID: {project_id}",
                fg=self.theme_mgr.get()["status_ok"],
            )
            messagebox.showinfo("Успіх", f"Проєкт збережено!\nID: {project_id}")
            self.price_list_tab._current_project_id = project_id

            self.project_3d_tab.set_project({
                "products": products,
                "project_id": project_id,
                "name": project_name,
            })
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося зберегти:\n{str(e)}")

    def _load_project(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Відкрити проєкт")
        dialog.geometry("500x400")
        dialog.minsize(400, 300)
        dialog.resizable(True, True)
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
        
        # === ПЕРЕРАХУНОК ЦІН ТА ЗАРПЛАТИ при завантаженні ===
        from ventilation_company.gui.settings_tab import PricingSettings
        from ventilation_company.calculations.cost_engine import CostEngine
        settings = PricingSettings.get_instance()
        engine = CostEngine(settings)
        
        for p in products:
            # Перераховуємо ціну з актуальними ставками
            try:
                price_data = engine.calculate_price_breakdown(p)
                p["unit_price"] = price_data["price_with_vat"]
                p["total_price"] = p["unit_price"] * p.get("quantity", 1)
                p["cost_price"] = price_data["cost_price"]
                p["salary_per_unit"] = price_data["salary"]
                p["salary_total"] = p["salary_per_unit"] * p.get("quantity", 1)
            except Exception:
                pass  # якщо не вдалося перерахувати — залишаємо старі значення
        # =====================================================
        
        self.products_tab.load_products_from_dict(products)
        self.current_project_id = project_id
        self.price_list_tab._current_project_id = self.current_project_id
        self.status_bar.config(text=f"📂 Завантажено проєкт ID: {project_id}")
        messagebox.showinfo("Успіх", f"Проєкт '{project['name']}' завантажено.")

    def _recalculate_current_project(self):
        """Перерахувати ціни поточного проєкту з актуальними ставками."""
        products = self._get_products()
        if not products:
            messagebox.showwarning("Увага", "Немає виробів для перерахунку.")
            return
        
        from ventilation_company.gui.settings_tab import PricingSettings
        from ventilation_company.calculations.cost_engine import CostEngine
        settings = PricingSettings.get_instance()
        engine = CostEngine(settings)
        
        updated = 0
        for p in products:
            try:
                price_data = engine.calculate_price_breakdown(p)
                p["unit_price"] = price_data["price_with_vat"]
                p["total_price"] = p["unit_price"] * p.get("quantity", 1)
                updated += 1
            except Exception:
                pass
        
        self._set_products(products)
        self.status_bar.config(text=f"🔄 Перераховано {updated} виробів")
        messagebox.showinfo("Готово", f"Перераховано {updated} виробів з актуальними ставками.")

    def _open_cutting_for_project(self, project_id: int):
        products = self.db.get_project_products(project_id)
        self._show_tab(self.project_nb, 2, None)
        self.cutting_tab.run_cutting_for_products(products)

    def _export_3d_project(self):
        self._show_tab(self.project_nb, 3, None)

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
