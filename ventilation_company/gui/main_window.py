"""Головне вікно додатку VentCompany з усіма вкладками.
Об'єднує: Вироби, Специфікацію, Розкрій, Проєкти (БД), Проєкти 3D/Креслення, Ціноутворення.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from ventilation_company.db_integration import ProjectDatabase, save_project_full
from ventilation_company.gui.cutting_tab import CuttingTab
from ventilation_company.gui.project_3d_tab import Project3DTab  # НОВЕ
from ventilation_company.gui.products_tab import ProductsTab
from ventilation_company.gui.settings_tab import SettingsTab
from ventilation_company.gui.price_list_tab import PriceListTab
from ventilation_company.gui.metal_prices_tab import MetalPricesTab
from ventilation_company.gui.specification_tab import SpecificationTab
from ventilation_company.gui.production_tab import ProductionTab
from ventilation_company.gui.material_order_tab import MaterialOrderTab


class MainWindow:
    """Головне вікно програми."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🏭 VentCompany — Вентиляційні системи")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 700)

        self.db = ProjectDatabase("data/company.db")
        self.current_project_id = None

        self._build_menu()
        self._build_ui()

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
        top_frame = ttk.Frame(self.root, padding=5)
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="📁 Проєкт:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.project_label = ttk.Label(
            top_frame, text="Новий проєкт (не збережено)", foreground="#666"
        )
        self.project_label.pack(side=tk.LEFT, padx=5)

        ttk.Button(top_frame, text="💾 Зберегти проєкт", command=self._save_project).pack(
            side=tk.RIGHT, padx=5
        )
        ttk.Button(top_frame, text="🏗️ 3D Проєкт", command=self._export_3d_project).pack(
            side=tk.RIGHT, padx=5
        )

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.products_tab = ProductsTab(
            self.notebook, on_products_changed=self._on_products_changed
        )
        self.spec_tab = SpecificationTab(self.notebook,get_products_callback=self._get_products,on_cutting_request=self._open_cutting_for_project,)
        self.cutting_tab = CuttingTab(self.notebook, get_products_callback=self._get_products)
        self.project_3d_tab = Project3DTab(self.notebook, get_products_callback=self._get_products)  # НОВЕ
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
        self.notebook.add(self.products_tab.frame, text="📦 Вироби")
        self.notebook.add(self.spec_tab.frame, text="📋 Специфікація")
        self.notebook.add(self.cutting_tab.frame, text="✂️ Розкрій")
        self.notebook.add(self.project_3d_tab.frame, text="🏗️ Проєкти 3D")  # НОВЕ
        self.notebook.add(self.settings_tab.frame, text="💰 Ціноутворення")
        self.notebook.add(self.production_tab.frame, text="🏭 Виробництво")
        self.notebook.add(self.material_order_tab.frame, text="📦 Матеріали")

        # Прайс-лист
        self.price_list_tab = PriceListTab(self.notebook, get_products_callback=self._get_products)
        self.notebook.add(self.price_list_tab.frame, text="🏷️ Прайс-лист")

        # ═══ ВИПРАВЛЕННЯ: прив'язка project_id до прайс-листа ═══
        self.price_list_tab._current_project_id = self.current_project_id

        # Ціни на метал
        self.metal_prices_tab = MetalPricesTab(self.notebook)
        self.notebook.add(self.metal_prices_tab.frame, text="🔧 Ціни на метал")

        self.status_bar = ttk.Label(self.root, text="Готово", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _get_products(self):
        return self.products_tab.get_products_dict()

    def _get_project_info(self):
        """Повернути інформацію про поточний проєкт."""
        name = self.spec_tab.project_name_var.get() if hasattr(self, "spec_tab") else "Проєкт"
        return {
            "name": name,
            "id": self.current_project_id,
        }

    def _on_products_changed(self):
        self.status_bar.config(text=f"Виробів: {len(self.products_tab.get_library())}")
        # self.project_3d_tab._refresh_list()  # TODO: оновити 3D-перегляд при зміні виробів

    def _get_products_for_price(self):
        """Повернути список виробів для синхронізації з прайсом."""
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
                text=f"{project_name} (ID: {self.current_project_id})", foreground="green"
            )
            self.status_bar.config(text=f"✅ Проєкт збережено. ID: {self.current_project_id}")
            messagebox.showinfo("Успіх", f"Проєкт збережено!\nID: {self.current_project_id}")

            # ═══ ВИПРАВЛЕННЯ: оновлюємо project_id у прайс-листі ═══
            self.price_list_tab._current_project_id = self.current_project_id

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
                dialog.destroy()

        ttk.Button(dialog, text="Відкрити", command=on_select).pack(pady=5)

    def _load_project_data(self, project_id: int):
        """Завантажити дані проєкту з БД — ВИПРАВЛЕНО: тепер підтягуються вироби."""
        project = self.db.get_project(project_id)
        if not project:
            messagebox.showerror("Помилка", "Проєкт не знайдено.")
            return

        self.spec_tab.project_name_var.set(project["name"])
        self.project_label.config(text=f"{project['name']} (ID: {project_id})")

        # === ВИПРАВЛЕННЯ: завантажуємо вироби з БД ===
        products = self.db.get_project_products(project_id)
        self.products_tab.load_products_from_dict(products)
        # =============================================

        # self.project_3d_tab._refresh_list()  # TODO: оновити 3D-перегляд при зміні виробів

        self.current_project_id = project_id

        # ═══ ВИПРАВЛЕННЯ: оновлюємо project_id у прайс-листі ═══
        self.price_list_tab._current_project_id = self.current_project_id

        self.status_bar.config(text=f"📂 Завантажено проєкт ID: {project_id}")
        messagebox.showinfo("Успіх", f"Проєкт '{project['name']}' завантажено.")

    def _open_cutting_for_project(self, project_id: int):
        """Відкрити розкрій для проєкту з архіву (контекстне меню)."""
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
            "• 3D/2D проєкти з імпортом/експортом (Revit, AutoCAD, Solidworks, FreeCAD)\n"
            "• Ціноутворення з формулами",
        )

    def run(self):
        self.root.mainloop()


def main():
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
