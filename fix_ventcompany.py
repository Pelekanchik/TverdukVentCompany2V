#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VentCompany Salary Fix v2.1
Завантажує оригінальні файли з GitHub, вносить виправлення і зберігає у папку fixed_files/
"""

import os
import re
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIXED_DIR = os.path.join(BASE_DIR, "fixed_files")
os.makedirs(FIXED_DIR, exist_ok=True)

def download(url):
    """Завантажити текст з GitHub."""
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return r.read().decode('utf-8')
    except Exception as e:
        print(f"❌ Помилка завантаження {url}: {e}")
        return None

def save_fixed(subpath, content):
    """Зберегти виправлений файл у fixed_files/."""
    full_path = os.path.join(FIXED_DIR, subpath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ {subpath}")

# ─────────────────────────────────────────────
# 1. cost_engine.py
# ─────────────────────────────────────────────
url = "https://raw.githubusercontent.com/Pelekanchik/TverdukVentCompany2V/main/ventilation_company/calculations/cost_engine.py"
content = download(url)
if content:
    # Замінюємо: blank_area_m2 → surface_area_m2 для зарплати
    content = re.sub(
        r'result\.labor_cost\s*=\s*blank_area_m2\s*\*\s*labor_rate\s*\*\s*\(1\s*\+\s*labor_difficulty\s*/\s*100\)\s*\*\s*quantity',
        'result.labor_cost = surface_area_m2 * labor_rate * (1 + labor_difficulty / 100) * quantity  # FIX v2.1: уніфікація з Виробництвом (surface_area)',
        content
    )
    save_fixed("ventilation_company/calculations/cost_engine.py", content)

# ─────────────────────────────────────────────
# 2. standard_products.py
# ─────────────────────────────────────────────
url = "https://raw.githubusercontent.com/Pelekanchik/TverdukVentCompany2V/main/ventilation_company/standard_products.py"
content = download(url)
if content:
    # Додаємо метод recalculate_price() перед get_cost_breakdown()
    old = '    def get_cost_breakdown(self):'
    new = '''    def recalculate_price(self) -> float:
        """
        Перерахувати ціну з актуальними ставками з pricing_settings.json.
        Використовувати при завантаженні проєкту або зміні налаштувань.
        """
        self.unit_price = Decimal(str(self.calculate_price()))
        self.total_price = self.unit_price * self.quantity
        return float(self.unit_price)

    def get_cost_breakdown(self):'''
    content = content.replace(old, new)
    save_fixed("ventilation_company/standard_products.py", content)

# ─────────────────────────────────────────────
# 3. main_window.py
# ─────────────────────────────────────────────
url = "https://raw.githubusercontent.com/Pelekanchik/TverdukVentCompany2V/main/ventilation_company/gui/main_window.py"
content = download(url)
if content:
    # 3a. Коментар
    content = content.replace(
        "# Перераховуємо зарплати перед автозбереженням",
        "# Перераховуємо ціни та зарплати перед автозбереженням"
    )

    # 3b. _load_project_data — замінити блок перерахунку
    old = '''        # === ПЕРЕРАХУНОК ЦІН ТА ЗАРПЛАТИ при завантаженні ===
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
        # ====================================================='''

    new = '''        # === ПЕРЕРАХУНОК ЦІН ТА ЗАРПЛАТИ при завантаженні ===
        from ventilation_company.standard_products import StandardProduct
        
        for p in products:
            try:
                product_obj = StandardProduct.from_dict(p)
                product_obj.recalculate_price()
                p["unit_price"] = float(product_obj.unit_price)
                p["total_price"] = float(product_obj.total_price)
                breakdown = product_obj.get_cost_breakdown()
                p["salary_per_unit"] = round(breakdown.labor_cost / p.get("quantity", 1), 2)
                p["salary_total"] = round(breakdown.labor_cost, 2)
            except Exception:
                pass
        # ====================================================='''
    content = content.replace(old, new)

    # 3c. _recalculate_current_project
    old = '''        from ventilation_company.gui.settings_tab import PricingSettings
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
                pass'''

    new = '''        from ventilation_company.standard_products import StandardProduct
        
        updated = 0
        for p in products:
            try:
                product_obj = StandardProduct.from_dict(p)
                product_obj.recalculate_price()
                p["unit_price"] = float(product_obj.unit_price)
                p["total_price"] = float(product_obj.total_price)
                breakdown = product_obj.get_cost_breakdown()
                p["salary_per_unit"] = round(breakdown.labor_cost / p.get("quantity", 1), 2)
                p["salary_total"] = round(breakdown.labor_cost, 2)
                updated += 1
            except Exception:
                pass'''
    content = content.replace(old, new)
    save_fixed("ventilation_company/gui/main_window.py", content)

# ─────────────────────────────────────────────
# 4. price_list_tab.py
# ─────────────────────────────────────────────
url = "https://raw.githubusercontent.com/Pelekanchik/TverdukVentCompany2V/main/ventilation_company/gui/price_list_tab.py"
content = download(url)
if content:
    # 4a. PriceItem.recalculate — додати оновлення labor_cost з PricingSettings
    old = '''    def recalculate(self):
        if self.category == "перепродаж" and self.supplier_price > 0:
            base = self.supplier_price
        else:
            base = self.cost_price + self.labor_cost + self.overhead_cost
        self.unit_price = base * (1 + self.markup_percent / 100)
        self.total_price = self.unit_price * self.quantity'''

    new = '''    def recalculate(self):
        # FIX v2.1: оновлюємо labor_cost з актуальними ставками + важкість
        from ventilation_company.gui.settings_tab import PricingSettings
        settings = PricingSettings.get_instance()
        if self.category == "власне виробництво":
            labor = settings.get_labor_rate(self.product_type or self.name)
            rate = labor.get("rate_per_m2", 120.0)
            difficulty = labor.get("difficulty_percent", 0.0)
            area = self._estimate_area()
            self.labor_cost = round(area * rate * (1 + difficulty / 100), 2)
        
        if self.category == "перепродаж" and self.supplier_price > 0:
            base = self.supplier_price
        else:
            base = self.cost_price + self.labor_cost + self.overhead_cost
        self.unit_price = base * (1 + self.markup_percent / 100)
        self.total_price = self.unit_price * self.quantity

    def _estimate_area(self) -> float:
        """Оцінити площу виробу з розмірів (м²) — як у ProductionTab."""
        try:
            parts = self.dimensions.replace("×", "x").replace("X", "x").split("x")
            if len(parts) >= 3:
                w, h, l = float(parts[0]), float(parts[1]), float(parts[2])
                return 2 * (w/1000 + h/1000) * (l/1000)
            elif len(parts) == 2:
                d, l = float(parts[0]), float(parts[1])
                return 3.14159 * (d/1000) * (l/1000)
        except (ValueError, IndexError):
            pass
        return 0.0'''
    content = content.replace(old, new)

    # 4b. PriceListTab._recalculate_salaries — спростити
    old = '''    def _recalculate_salaries(self):
        """Перерахувати зарплати для всіх позицій з актуальними ставками."""
        from ventilation_company.gui.settings_tab import PricingSettings
        settings = PricingSettings.get_instance()
        updated = 0

        for item in self.manager.items:
            if item.category != "власне виробництво":
                continue

            ptype = item.product_type or item.name
            dims = item.dimensions

            # Розпарсити розміри
            try:
                parts = dims.replace("×", "x").replace("X", "x").split("x")
                if len(parts) >= 2:
                    w = float(parts[0])
                    h = float(parts[1]) if len(parts) > 1 else 0
                    l = float(parts[2]) if len(parts) > 2 else 0
                else:
                    w = h = l = 0
            except (ValueError, IndexError):
                w = h = l = 0

            # Приблизна площа
            if "кругл" in ptype.lower():
                area = 3.14159 * w * l / 1_000_000
            else:
                area = 2 * (w + h) * l / 1_000_000

            if area <= 0:
                continue

            labor_info = settings.get_labor_rate(ptype)
            rate = labor_info.get("rate_per_m2", 120.0)
            difficulty = labor_info.get("difficulty_percent", 0.0)
            new_labor = area * rate * (1 + difficulty / 100)

            if abs(new_labor - item.labor_cost) > 0.01:
                item.labor_cost = round(new_labor, 2)
                item.recalculate()
                updated += 1'''

    new = '''    def _recalculate_salaries(self):
        """Перерахувати зарплати для всіх позицій з актуальними ставками."""
        updated = 0
        for item in self.manager.items:
            if item.category != "власне виробництво":
                continue
            item.recalculate()  # тепер сама оновлює labor_cost + ціну
            updated += 1'''
    content = content.replace(old, new)
    save_fixed("ventilation_company/gui/price_list_tab.py", content)

print("\n" + "="*55)
print("ГОТОВО! Виправлені файли у папці: fixed_files/")
print("="*55)
print("\nЩо змінилося:")
print("  1. Зарплата у CostEngine — від surface_area (як у Виробництві)")
print("  2. Ціна виробу оновлюється при зміні ставок/важкості")
print("  3. Прайс-лист тягне актуальні ставки з Налаштувань")
print("\nЩоб застосувати:")
print("  1. Скопіюйте файли з fixed_files/ у відповідні папки проєкту")
print("  2. Перезапустіть програму")
input("\nНатисніть Enter...")