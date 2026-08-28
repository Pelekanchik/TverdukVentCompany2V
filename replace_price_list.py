#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))

# 1. Чистимо кеш
for root, dirs, files in os.walk(BASE):
    for d in list(dirs):
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d))
            dirs.remove(d)
print("🗑️  Кеш очищено")

# 2. Видаляємо старий прайс (з неправильними зарплатами)
price_json = os.path.join(BASE, "data", "price_list.json")
if os.path.exists(price_json):
    os.remove(price_json)
    print("🗑️  Видалено старий price_list.json")

# 3. Завантажуємо оригінал price_list_tab.py з GitHub
print("⬇️  Завантаження оригіналу з GitHub...")
url = "https://raw.githubusercontent.com/Pelekanchik/TverdukVentCompany2V/main/ventilation_company/gui/price_list_tab.py"
try:
    with urllib.request.urlopen(url, timeout=15) as r:
        txt = r.read().decode('utf-8')
    print("✅ Завантажено")
except Exception as e:
    print(f"❌ Помилка завантаження: {e}")
    input("\nНатисніть Enter...")
    exit(1)

# 4. Виправлення 1: PriceItem.recalculate()
old1 = '''    def recalculate(self):
        if self.category == "перепродаж" and self.supplier_price > 0:
            base = self.supplier_price
        else:
            base = self.cost_price + self.labor_cost + self.overhead_cost
        self.unit_price = base * (1 + self.markup_percent / 100)
        self.total_price = self.unit_price * self.quantity'''
new1 = '''    def recalculate(self):
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

if old1 in txt:
    txt = txt.replace(old1, new1)
    print("✅ recalculate() — виправлено")
else:
    print("⚠️  recalculate() — фрагмент не знайдено")

# 5. Виправлення 2: _recalculate_salaries()
old2 = '''    def _recalculate_salaries(self):
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
new2 = '''    def _recalculate_salaries(self):
        """Перерахувати зарплати для всіх позицій з актуальними ставками."""
        updated = 0
        for item in self.manager.items:
            if item.category != "власне виробництво":
                continue
            # FIX: recalculate() тепер сама оновлює labor_cost + ціну
            item.recalculate()
            updated += 1'''

if old2 in txt:
    txt = txt.replace(old2, new2)
    print("✅ _recalculate_salaries() — виправлено")
else:
    print("⚠️  _recalculate_salaries() — фрагмент не знайдено")

# 6. Виправлення 3: import_from_products — додаємо CostEngine
old3 = '''            total_price = unit_price * quantity

            # Формуємо розміри з width/height/length'''
new3 = '''            # FIX v2.1: перераховуємо через CostEngine (уніфіковано з Виробництвом)
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

if old3 in txt:
    txt = txt.replace(old3, new3)
    print("✅ import_from_products() — виправлено")
else:
    print("⚠️  import_from_products() — фрагмент не знайдено")

# 7. Зберігаємо
path = os.path.join(BASE, "ventilation_company", "gui", "price_list_tab.py")
with open(path, "w", encoding="utf-8") as f:
    f.write(txt)
print(f"✅ Файл збережено: {path}")

print("\n" + "=" * 60)
print("ГОТОВО! Тепер запустіть:  python main.py")
print("Потім у Прайс-листі натисніть '🔄 Оновити прайс'")
print("=" * 60)
input("\nНатисніть Enter...")