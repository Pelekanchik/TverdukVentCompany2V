#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))

# 1. Чистимо кеш
for root, dirs, files in os.walk(BASE):
    for d in list(dirs):
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d))
            dirs.remove(d)
print("🗑️  Кеш очищено")

path = os.path.join(BASE, "ventilation_company", "gui", "price_list_tab.py")
with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

# Видаляємо моє криве виправлення з CostEngine (якщо є)
old_bad = '''            # FIX v2.1: перераховуємо через CostEngine (уніфіковано з Виробництвом)
            try:
                from ventilation_company.calculations.cost_engine import CostEngine
                engine = CostEngine(pricing)
                bd = engine.calculate(product_type, width, height, length, thickness, material, quantity=quantity)
                labor = bd.labor_cost / quantity
                cost_price = bd.base_cost / quantity
                overhead_total = (bd.overhead_cost + bd.depreciation_cost + bd.electricity_cost) / quantity
                unit_price = bd.final_price / quantity
                total_price = bd.final_price
            except Exception as e2:
                print(f"[PriceList] CostEngine fallback: {e2}")

            total_price = unit_price * quantity

            # Формуємо розміри з width/height/length'''

if old_bad in txt:
    txt = txt.replace(old_bad, '''            # FIX v2.1: зарплата від surface_area (як у Виробництві), а не від material_area
            # Розраховуємо площу ПОВЕРХНІ готового виробу
            try:
                parts = dimensions.replace("×", "x").replace("X", "x").split("x")
                if len(parts) >= 3:
                    w, h, l = float(parts[0]), float(parts[1]), float(parts[2])
                    area = 2 * (w/1000 + h/1000) * (l/1000)
                elif len(parts) == 2:
                    d, l = float(parts[0]), float(parts[1])
                    area = 3.14159 * (d/1000) * (l/1000)
                else:
                    area = 0
            except (ValueError, IndexError):
                area = 0

            labor_info = pricing.get_labor_rate(product_type)
            rate = labor_info.get("rate_per_m2", 120.0)
            difficulty = labor_info.get("difficulty_percent", 0.0)
            labor = area * rate * (1 + difficulty / 100)

            total_price = unit_price * quantity

            # Формуємо розміри з width/height/length''')
    print("✅ Виправлено: import_from_products() — тепер зарплата від surface_area")
else:
    print("⚠️  Криве виправлення не знайдено (можливо, вже інший формат)")

# 2. Якщо recalculate() ще не виправлений — виправляємо
if "def _estimate_area(self)" not in txt:
    old_recalc = '''    def recalculate(self):
        if self.category == "перепродаж" and self.supplier_price > 0:
            base = self.supplier_price
        else:
            base = self.cost_price + self.labor_cost + self.overhead_cost
        self.unit_price = base * (1 + self.markup_percent / 100)
        self.total_price = self.unit_price * self.quantity'''
    new_recalc = '''    def recalculate(self):
        # FIX v2.1: оновлюємо labor_cost з актуальними ставками + важкість
        from ventilation_company.gui.settings_tab import PricingSettings
        settings = PricingSettings.get_instance()
        if self.category == "власне виробництво":
            labor = settings.get_labor_rate(self.product_type or self.name)
            rate = labor.get("rate_per_m2", 120.0)
            difficulty = labor.get("difficulty_percent", 0.0)
            area = self._estimate_area()
            if area > 0:
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
    if old_recalc in txt:
        txt = txt.replace(old_recalc, new_recalc)
        print("✅ Виправлено: recalculate() + _estimate_area()")
    else:
        print("⚠️  recalculate() — фрагмент не знайдено")

# 3. Якщо _recalculate_salaries() ще не виправлений — виправляємо
if "item.recalculate()  # тепер сама оновлює labor_cost + ціну" not in txt:
    old_sal = '''    def _recalculate_salaries(self):
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
    new_sal = '''    def _recalculate_salaries(self):
        """Перерахувати зарплати для всіх позицій з актуальними ставками."""
        updated = 0
        for item in self.manager.items:
            if item.category != "власне виробництво":
                continue
            # FIX: recalculate() тепер сама оновлює labor_cost + ціну
            item.recalculate()
            updated += 1'''
    if old_sal in txt:
        txt = txt.replace(old_sal, new_sal)
        print("✅ Виправлено: _recalculate_salaries()")
    else:
        print("⚠️  _recalculate_salaries() — фрагмент не знайдено")

with open(path, "w", encoding="utf-8") as f:
    f.write(txt)

# Видаляємо старий прайс
price_json = os.path.join(BASE, "data", "price_list.json")
if os.path.exists(price_json):
    os.remove(price_json)
    print("🗑️  Видалено старий price_list.json")

print("\n" + "=" * 60)
print("✅ ГОТОВО!")
print("=" * 60)
print("\n1. Запустіть:  python main.py")
print("2. Перейдіть у Прайс-лист")
print("3. Натисніть '🔄 Оновити прайс'")
print("\nОчікуваний результат для 400×200×1000:")
print("   Роботи = 172.80 грн (як у Виробництві)")
print("   Собівартість ≈ 834 грн")
print("   Накладні ≈ 100 грн")
print("   Ціна од ≈ 1308 грн (пропорційно зросла)")
print("=" * 60)
input("\nНатисніть Enter...")