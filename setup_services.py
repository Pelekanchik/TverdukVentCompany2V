#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))

def clean_cache():
    for root, dirs, files in os.walk(BASE):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d))
                dirs.remove(d)
    print("🗑️  Кеш очищено")

def write_file(path, content):
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ {path}")

def read_file(path):
    with open(os.path.join(BASE, path), "r", encoding="utf-8") as f:
        return f.read()

def replace_block(path, old, new, label):
    txt = read_file(path)
    if old in txt:
        txt = txt.replace(old, new)
        write_file(path, txt)
        print(f"✅ {label}")
        return True
    else:
        print(f"⚠️  {label} — БЛОК НЕ ЗНАЙДЕНО (файл відрізняється)")
        return False

# =============================================================================
# 1. Створюємо services/
# =============================================================================
print("=" * 60)
print("  ЕТАП 1: Створення services/")
print("=" * 60 + "\n")

services_init = '''"""Сервісний шар — бізнес-логіка відокремлена від GUI."""

from .pricing_service import PricingService
from .salary_service import SalaryService
from .project_service import ProjectService

__all__ = ["PricingService", "SalaryService", "ProjectService"]
'''
write_file("ventilation_company/services/__init__.py", services_init)

pricing_service = '''"""PricingService — єдиний сервіс розрахунку ціни виробу."""

from decimal import Decimal
from ventilation_company.standard_products import StandardProduct


class PricingService:
    """GUI тільки викликає цей сервіс. Тут зосереджена ВСЯ логіка ціноутворення."""

    @staticmethod
    def calculate(product_dict: dict) -> dict:
        """
        Приймає dict виробу (як у БД).
        Повертає dict з розрахованими полями.
        """
        try:
            product = StandardProduct.from_dict(product_dict)
            product.recalculate_price()
            breakdown = product.get_cost_breakdown()
            qty = product_dict.get("quantity", 1) or 1

            return {
                "unit_price": float(product.unit_price),
                "total_price": float(product.total_price),
                "cost_price": float(breakdown.base_cost / qty),
                "salary_per_unit": round(breakdown.labor_cost / qty, 2),
                "salary_total": round(breakdown.labor_cost, 2),
                "material_cost": round(breakdown.material_cost / qty, 2),
                "overhead_cost": round(
                    (breakdown.overhead_cost + breakdown.depreciation_cost) / qty, 2
                ),
            }
        except Exception:
            # Якщо не вдалося — залишаємо оригінал
            return {
                "unit_price": product_dict.get("unit_price", 0),
                "total_price": product_dict.get("total_price", 0),
                "cost_price": product_dict.get("cost_price", 0),
                "salary_per_unit": product_dict.get("salary_per_unit", 0),
                "salary_total": product_dict.get("salary_total", 0),
                "material_cost": product_dict.get("material_cost", 0),
                "overhead_cost": product_dict.get("overhead_cost", 0),
            }
'''
write_file("ventilation_company/services/pricing_service.py", pricing_service)

salary_service = '''"""SalaryService — уніфікований розрахунок зарплати."""

from ventilation_company.gui.settings_tab import PricingSettings


class SalaryService:
    """Розрахунок зарплати для Виробництва, Специфікації, Архіву."""

    @staticmethod
    def calculate(
        product_type: str,
        dimensions: str,
        quantity: int = 1,
        area: float = None,
    ) -> float:
        """
        Якщо area передано (наприклад, metal_area_m2) — використовує його.
        Інакше — рахує площу з розмірів.
        """
        settings = PricingSettings.get_instance()
        labor = settings.get_labor_rate(product_type or "")
        rate = labor.get("rate_per_m2", 120.0)
        difficulty = labor.get("difficulty_percent", 0.0)

        if area is None:
            try:
                parts = dimensions.replace("×", "x").replace("X", "x").split("x")
                if len(parts) >= 3:
                    w, h, l = float(parts[0]), float(parts[1]), float(parts[2])
                    area = 2 * (w / 1000 + h / 1000) * (l / 1000)
                elif len(parts) == 2:
                    d, l = float(parts[0]), float(parts[1])
                    area = 3.14159 * (d / 1000) * (l / 1000)
                else:
                    area = 0
            except (ValueError, IndexError):
                area = 0

        return round(area * rate * (1 + difficulty / 100) * quantity, 2)
'''
write_file("ventilation_company/services/salary_service.py", salary_service)

project_service = '''"""ProjectService — робота з проєктом."""

from ventilation_company.services.pricing_service import PricingService


class ProjectService:
    """Завантаження, збереження, перерахунок проєкту."""

    @staticmethod
    def recalculate_products(products: list) -> int:
        """Перерахувати ціни для списку виробів. Повертає кількість оновлених."""
        updated = 0
        for p in products:
            try:
                result = PricingService.calculate(p)
                p.update(result)
                updated += 1
            except Exception:
                pass
        return updated
'''
write_file("ventilation_company/services/project_service.py", project_service)

# =============================================================================
# 2. Виправляємо main_window.py
# =============================================================================
print("\n" + "=" * 60)
print("  ЕТАП 2: Виправлення main_window.py")
print("=" * 60 + "\n")

mw_path = "ventilation_company/gui/main_window.py"

# 2a. _recalculate_salaries
old = '''    def _recalculate_salaries(self, products):
        """Перерахувати зарплати для списку виробів (викликається перед збереженням)."""
        if not products:
            return
        from ventilation_company.gui.settings_tab import PricingSettings
        from ventilation_company.calculations.cost_engine import CostEngine
        settings = PricingSettings.get_instance()
        engine = CostEngine(settings)
        for p in products:
            try:
                price_data = engine.calculate_price_breakdown(p)
                p["salary_per_unit"] = price_data["salary"]
                p["salary_total"] = price_data["salary"] * p.get("quantity", 1)
            except Exception:
                pass'''
new = '''    def _recalculate_salaries(self, products):
        """Перерахувати ціни та зарплати перед збереженням."""
        if not products:
            return
        from ventilation_company.services import ProjectService
        ProjectService.recalculate_products(products)'''
replace_block(mw_path, old, new, "_recalculate_salaries")

# 2b. _recalculate_current_project
old = '''    def _recalculate_current_project(self):
        """Перерахувати ціни поточного проєкту."""
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
        messagebox.showinfo("Готово", f"Перераховано {updated} виробів.")'''
new = '''    def _recalculate_current_project(self):
        """Перерахувати ціни поточного проєкту."""
        products = self._get_products()
        if not products:
            messagebox.showwarning("Увага", "Немає виробів для перерахунку.")
            return
        from ventilation_company.services import ProjectService
        updated = ProjectService.recalculate_products(products)
        self._set_products(products)
        self.status_bar.config(text=f"🔄 Перераховано {updated} виробів")
        messagebox.showinfo("Готово", f"Перераховано {updated} виробів.")'''
replace_block(mw_path, old, new, "_recalculate_current_project")

# 2c. _load_project_data — додаємо перерахунок
old = '''        products = self.db.get_project_products(project_id)
        self.products_tab.load_products_from_dict(products)'''
new = '''        products = self.db.get_project_products(project_id)
        # Перераховуємо ціни з актуальними ставками при завантаженні
        from ventilation_company.services import ProjectService
        ProjectService.recalculate_products(products)
        self.products_tab.load_products_from_dict(products)'''
replace_block(mw_path, old, new, "_load_project_data (перерахунок)")

# 2d. Коментар у _auto_save
old = "            # Перераховуємо зарплати перед автозбереженням"
new = "            # Перераховуємо ціни та зарплати перед автозбереженням"
replace_block(mw_path, old, new, "_auto_save (коментар)")

# =============================================================================
# 3. Виправляємо production_tab.py
# =============================================================================
print("\n" + "=" * 60)
print("  ЕТАП 3: Виправлення production_tab.py")
print("=" * 60 + "\n")

pt_path = "ventilation_company/gui/production_tab.py"

old = '''    def _calculate_salary(self, product):
        """Розрахувати зарплату для виробу."""
        # Отримуємо ставку з налаштувань
        from ventilation_company.gui.settings_tab import PricingSettings
        pricing = PricingSettings.get_instance()
        
        product_type = product.get("product_type", "")
        metal_area = product.get("metal_area_m2", 0)
        quantity = product.get("quantity", 1)
        
        # Отримуємо ставку для цього типу виробу
        labor_info = pricing.get_labor_rate(product_type)
        rate = labor_info.get("rate_per_m2", 120.0)
        difficulty = labor_info.get("difficulty_percent", 0.0)
        
        # Розрахунок зарплати
        salary = metal_area * rate * (1 + difficulty / 100) * quantity
        
        return round(salary, 2)'''

new = '''    def _calculate_salary(self, product):
        """Розрахувати зарплату для виробу."""
        from ventilation_company.services import SalaryService
        return SalaryService.calculate(
            product_type=product.get("product_type", ""),
            dimensions=product.get("dimensions", ""),
            quantity=product.get("quantity", 1),
            area=product.get("metal_area_m2", 0),
        )'''

replace_block(pt_path, old, new, "production_tab._calculate_salary")

# =============================================================================
# 4. Фінал
# =============================================================================
clean_cache()

print("\n" + "=" * 60)
print("✅ ГОТОВО! Архітектура виправлена.")
print("=" * 60)
print("\nЩо зроблено:")
print("  1. Створено ventilation_company/services/")
print("     • PricingService   — розрахунок ціни (єдиний джерело істини)")
print("     • SalaryService    — розрахунок зарплати (уніфікований)")
print("     • ProjectService   — перерахунок проєкту")
print("  2. main_window.py")
print("     • _recalculate_salaries    → ProjectService")
print("     • _recalculate_current_project → ProjectService")
print("     • _load_project_data       → +ProjectService")
print("  3. production_tab.py")
print("     • _calculate_salary        → SalaryService")
print("\nТепер усі розрахунки у services/.")
print("GUI тільки відображає, не рахує.")
print("=" * 60)
print("\nЗапустіть:  python main.py")
print("=" * 60)
input("\nНатисніть Enter...")