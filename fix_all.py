#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import re

BASE = os.path.dirname(os.path.abspath(__file__))

def clean_pycache():
    count = 0
    for root, dirs, files in os.walk(BASE):
        for d in list(dirs):
            if d == "__pycache__":
                path = os.path.join(root, d)
                shutil.rmtree(path)
                print(f"🗑️  {path}")
                count += 1
                dirs.remove(d)
        for f in files:
            if f.endswith(".pyc"):
                os.remove(os.path.join(root, f))
                count += 1
    print(f"✅ Очищено {count} кеш-елементів\n")

def read(path):
    with open(os.path.join(BASE, path), "r", encoding="utf-8") as f:
        return f.read()

def write(path, text):
    with open(os.path.join(BASE, path), "w", encoding="utf-8") as f:
        f.write(text)
    print(f"✅ {path}")

print("=" * 60)
print("  VentCompany — Повне виправлення + очищення кешу")
print("=" * 60 + "\n")

# 1. Чистимо кеш
clean_pycache()

# 2. cost_engine.py — зарплата від surface_area
txt = read("ventilation_company/calculations/cost_engine.py")
if "blank_area_m2 * labor_rate" in txt:
    txt = re.sub(
        r'result\.labor_cost\s*=\s*blank_area_m2\s*\*\s*labor_rate\s*\*\s*\(1\s*\+\s*labor_difficulty\s*/\s*100\)\s*\*\s*quantity',
        'result.labor_cost = surface_area_m2 * labor_rate * (1 + labor_difficulty / 100) * quantity  # FIX: уніфікація з Виробництвом',
        txt
    )
    write("ventilation_company/calculations/cost_engine.py", txt)
else:
    print("[OK] cost_engine.py — вже виправлено")

# 3. standard_products.py — додаємо recalculate_price
txt = read("ventilation_company/standard_products.py")
if "def recalculate_price(self)" not in txt:
    old = '    def get_cost_breakdown(self):'
    new = '''    def recalculate_price(self) -> float:
        """Перерахувати ціну з актуальними ставками."""
        self.unit_price = Decimal(str(self.calculate_price()))
        self.total_price = self.unit_price * self.quantity
        return float(self.unit_price)

    def get_cost_breakdown(self):'''
    txt = txt.replace(old, new)
    write("ventilation_company/standard_products.py", txt)
else:
    print("[OK] standard_products.py — вже виправлено")

# 4. main_window.py
txt = read("ventilation_company/gui/main_window.py")
changed = False
if "Перераховуємо зарплати перед автозбереженням" in txt:
    txt = txt.replace("Перераховуємо зарплати перед автозбереженням",
                      "Перераховуємо ціни та зарплати перед автозбереженням")
    changed = True
if "engine.calculate_price_breakdown(p)" in txt:
    txt = txt.replace(
        "from ventilation_company.gui.settings_tab import PricingSettings\n        from ventilation_company.calculations.cost_engine import CostEngine\n        settings = PricingSettings.get_instance()\n        engine = CostEngine(settings)",
        "from ventilation_company.standard_products import StandardProduct"
    )
    txt = txt.replace(
        "price_data = engine.calculate_price_breakdown(p)\n                p[\"unit_price\"] = price_data[\"price_with_vat\"]\n                p[\"total_price\"] = p[\"unit_price\"] * p.get(\"quantity\", 1)\n                p[\"cost_price\"] = price_data[\"cost_price\"]\n                p[\"salary_per_unit\"] = price_data[\"salary\"]\n                p[\"salary_total\"] = p[\"salary_per_unit\"] * p.get(\"quantity\", 1)",
        "product_obj = StandardProduct.from_dict(p)\n                product_obj.recalculate_price()\n                p[\"unit_price\"] = float(product_obj.unit_price)\n                p[\"total_price\"] = float(product_obj.total_price)\n                breakdown = product_obj.get_cost_breakdown()\n                p[\"salary_per_unit\"] = round(breakdown.labor_cost / p.get(\"quantity\", 1), 2)\n                p[\"salary_total\"] = round(breakdown.labor_cost, 2)"
    )
    txt = txt.replace(
        "price_data = engine.calculate_price_breakdown(p)\n                p[\"unit_price\"] = price_data[\"price_with_vat\"]\n                p[\"total_price\"] = p[\"unit_price\"] * p.get(\"quantity\", 1)\n                updated += 1",
        "product_obj = StandardProduct.from_dict(p)\n                product_obj.recalculate_price()\n                p[\"unit_price\"] = float(product_obj.unit_price)\n                p[\"total_price\"] = float(product_obj.total_price)\n                breakdown = product_obj.get_cost_breakdown()\n                p[\"salary_per_unit\"] = round(breakdown.labor_cost / p.get(\"quantity\", 1), 2)\n                p[\"salary_total\"] = round(breakdown.labor_cost, 2)\n                updated += 1"
    )
    changed = True
if changed:
    write("ventilation_company/gui/main_window.py", txt)
else:
    print("[OK] main_window.py — вже виправлено")

# 5. price_list_tab.py
txt = read("ventilation_company/gui/price_list_tab.py")
changed = False
if "def _estimate_area(self)" not in txt:
    old = '''    def recalculate(self):
        if self.category == "перепродаж" and self.supplier_price > 0:
            base = self.supplier_price
        else:
            base = self.cost_price + self.labor_cost + self.overhead_cost
        self.unit_price = base * (1 + self.markup_percent / 100)
        self.total_price = self.unit_price * self.quantity'''
    new = '''    def recalculate(self):
        # FIX: оновлюємо labor_cost з актуальними ставками + важкість
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
    if old in txt:
        txt = txt.replace(old, new)
        changed = True

if "item.recalculate()" not in txt:
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
    if old in txt:
        txt = txt.replace(old, new)
        changed = True

if changed:
    write("ventilation_company/gui/price_list_tab.py", txt)
else:
    print("[OK] price_list_tab.py — вже виправлено")

# 6. db_integration.py — виправляємо NameError
txt = read("ventilation_company/db_integration.py")
if "product_data" in txt:
    txt = txt.replace("product_data", "product")
    write("ventilation_company/db_integration.py", txt)
else:
    print("[OK] db_integration.py — вже виправлено")

# 7. specification_tab.py — правильний розрахунок зарплати для архіву
txt = read("ventilation_company/gui/specification_tab.py")
changed = False

if "pricing = PricingSettings()" in txt:
    txt = txt.replace("pricing = PricingSettings()", "pricing = PricingSettings.get_instance()")
    changed = True

# Виправляємо розрахунок зарплати: замінюємо labor = full_cost * 0.10 на розрахунок зі ставок
old_labor = "labor = full_cost * 0.10"
new_labor = '''# FIX: зарплата з актуальних ставок, а не 10% від ціни
                    ptype = p.get("product_type", "")
                    metal_area = p.get("metal_area_m2", 0) or p.get("surface_area", 0)
                    if metal_area and ptype:
                        labor_info = pricing.get_labor_rate(ptype)
                        rate = labor_info.get("rate_per_m2", 120.0)
                        difficulty = labor_info.get("difficulty_percent", 0.0)
                        labor = metal_area * rate * (1 + difficulty / 100)
                    else:
                        labor = full_cost * 0.10'''
if old_labor in txt:
    txt = txt.replace(old_labor, new_labor)
    changed = True

if changed:
    write("ventilation_company/gui/specification_tab.py", txt)
else:
    print("[OK] specification_tab.py — вже виправлено")

print("\n" + "=" * 60)
print("✅ ГОТОВО! Кеш очищено, всі файли виправлено.")
print("=" * 60)
print("\nТепер запустіть:  python main.py")
print("\nПісля запуску:")
print("  1. Натисніть '👷 Перерахувати зарплати' у Прайс-листі")
print("  2. Перевірте, що зарплата у Прайсі = зарплаті у Виробництві")
print("=" * 60)
input("\nНатисніть Enter...")