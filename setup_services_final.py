#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import urllib.request

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

# =============================================================================
# 1. Сервіси (вже створено, але перевіримо)
# =============================================================================
print("=" * 60)
print("  ЕТАП 1: Сервіси")
print("=" * 60 + "\n")

services_dir = os.path.join(BASE, "ventilation_company", "services")
if not os.path.exists(os.path.join(services_dir, "pricing_service.py")):
    # Якщо ще не створено — створимо (але мали бути створені раніше)
    print("⚠️  Сервіси не знайдено — запустіть спочатку setup_services.py")
    input("Enter...")
    exit(1)
print("✅ Сервіси вже створено")

# =============================================================================
# 2. Завантажуємо оригінал main_window.py і виправляємо
# =============================================================================
print("\n" + "=" * 60)
print("  ЕТАП 2: main_window.py (оригінал з GitHub + виправлення)")
print("=" * 60 + "\n")

url = "https://raw.githubusercontent.com/Pelekanchik/TverdukVentCompany2V/main/ventilation_company/gui/main_window.py"
try:
    with urllib.request.urlopen(url, timeout=15) as r:
        txt = r.read().decode('utf-8')
    print("⬇️  Оригінал завантажено")
except Exception as e:
    print(f"❌ Помилка: {e}")
    input("Enter...")
    exit(1)

# 2a. Додаємо import services
if "from ventilation_company.services import ProjectService" not in txt:
    txt = txt.replace(
        "from ventilation_company.gui.price_list_tab import PriceListTab",
        "from ventilation_company.gui.price_list_tab import PriceListTab\nfrom ventilation_company.services import ProjectService"
    )
    print("✅ Додано import ProjectService")

# 2b. _recalculate_salaries
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
        ProjectService.recalculate_products(products)'''
if old in txt:
    txt = txt.replace(old, new)
    print("✅ _recalculate_salaries → ProjectService")
else:
    print("⚠️  _recalculate_salaries — оригінальний блок не знайдено")

# 2c. _recalculate_current_project
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
        updated = ProjectService.recalculate_products(products)
        self._set_products(products)
        self.status_bar.config(text=f"🔄 Перераховано {updated} виробів")
        messagebox.showinfo("Готово", f"Перераховано {updated} виробів.")'''
if old in txt:
    txt = txt.replace(old, new)
    print("✅ _recalculate_current_project → ProjectService")
else:
    print("⚠️  _recalculate_current_project — оригінальний блок не знайдено")

# 2d. _load_project_data — додаємо перерахунок
old = '''        products = self.db.get_project_products(project_id)
        self.products_tab.load_products_from_dict(products)'''
new = '''        products = self.db.get_project_products(project_id)
        # Перераховуємо ціни з актуальними ставками при завантаженні
        ProjectService.recalculate_products(products)
        self.products_tab.load_products_from_dict(products)'''
if old in txt:
    txt = txt.replace(old, new)
    print("✅ _load_project_data → +ProjectService")
else:
    print("⚠️  _load_project_data — оригінальний блок не знайдено")

# 2e. Видаляємо Прайс-лист (як раніше)
replacements = [
    ('        self.finance_nb.add(self.price_list_tab.frame, text="🏷️ Прайс-лист")\n', ""),
    ('            ("🏷️", "Прайс-лист", self.finance_nb, 1),\n', ""),
    ('            ("🧾", "Документи", self.finance_nb, 2),\n', '            ("🧾", "Документи", self.finance_nb, 1),\n'),
    ("        self.price_list_tab._current_project_id = project_id\n", ""),
    ("        self.price_list_tab._current_project_id = self.current_project_id\n", ""),
    ('                "price_list_tab",\n', ""),
]
for old_r, new_r in replacements:
    if old_r in txt:
        txt = txt.replace(old_r, new_r)

# 2f. Закоментовуємо створення PriceListTab
txt = txt.replace(
    "        self.price_list_tab = PriceListTab(self.finance_nb, self.theme_manager, self.db, self)",
    "        # self.price_list_tab = PriceListTab(...)  # ВИДАЛЕНО"
)

write_file("ventilation_company/gui/main_window.py", txt)

# =============================================================================
# 3. Завантажуємо оригінал production_tab.py і виправляємо
# =============================================================================
print("\n" + "=" * 60)
print("  ЕТАП 3: production_tab.py (оригінал з GitHub + виправлення)")
print("=" * 60 + "\n")

url = "https://raw.githubusercontent.com/Pelekanchik/TverdukVentCompany2V/main/ventilation_company/gui/production_tab.py"
try:
    with urllib.request.urlopen(url, timeout=15) as r:
        txt = r.read().decode('utf-8')
    print("⬇️  Оригінал завантажено")
except Exception as e:
    print(f"❌ Помилка: {e}")
    input("Enter...")
    exit(1)

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

if old in txt:
    txt = txt.replace(old, new)
    print("✅ _calculate_salary → SalaryService")
else:
    print("⚠️  _calculate_salary — оригінальний блок не знайдено")

write_file("ventilation_company/gui/production_tab.py", txt)

# =============================================================================
# 4. Фінал
# =============================================================================
clean_cache()

print("\n" + "=" * 60)
print("✅ ГОТОВО!")
print("=" * 60)
print("\nЗапустіть:  python main.py")
print("=" * 60)
input("\nНатисніть Enter...")