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
print("🗑️  Кеш очищено\n")

path = os.path.join(BASE, "ventilation_company", "gui", "price_list_tab.py")
with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

changed = False

# ── 1. PriceItem.recalculate() ──
old = r'    def recalculate\(self\):\n        if self\.category == "перепродаж" and self\.supplier_price > 0:\n            base = self\.supplier_price\n        else:\n            base = self\.cost_price \+ self\.labor_cost \+ self\.overhead_cost\n        self\.unit_price = base \* \(1 \+ self\.markup_percent / 100\)\n        self\.total_price = self\.unit_price \* self\.quantity'
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

if re.search(old, txt):
    txt = re.sub(old, new, txt)
    print("✅ PriceItem.recalculate() — виправлено")
    changed = True
else:
    print("⚠️  PriceItem.recalculate() — НЕ ЗНАЙДЕНО (файл відрізняється від GitHub)")

# ── 2. _recalculate_salaries() ──
old2 = r'    def _recalculate_salaries\(self\):\n        """Перерахувати зарплати для всіх позицій з актуальними ставками\."""\n        from ventilation_company\.gui\.settings_tab import PricingSettings\n        settings = PricingSettings\.get_instance\(\)\n        updated = 0\n\n        for item in self\.manager\.items:\n            if item\.category != "власне виробництво":\n                continue\n\n            ptype = item\.product_type or item\.name\n            dims = item\.dimensions\n\n            # Розпарсити розміри\n            try:\n                parts = dims\.replace\("×", "x"\)\.replace\("X", "x"\)\.split\("x"\)\n                if len\(parts\) >= 2:\n                    w = float\(parts\[0\]\)\n                    h = float\(parts\[1\]\) if len\(parts\) > 1 else 0\n                    l = float\(parts\[2\]\) if len\(parts\) > 2 else 0\n                else:\n                    w = h = l = 0\n            except \(ValueError, IndexError\):\n                w = h = l = 0\n\n            # Приблизна площа\n            if "кругл" in ptype\.lower\(\):\n                area = 3\.14159 \* w \* l / 1_000_000\n            else:\n                area = 2 \* \(w \+ h\) \* l / 1_000_000\n\n            if area <= 0:\n                continue\n\n            labor_info = settings\.get_labor_rate\(ptype\)\n            rate = labor_info\.get\("rate_per_m2", 120\.0\)\n            difficulty = labor_info\.get\("difficulty_percent", 0\.0\)\n            new_labor = area \* rate \* \(1 \+ difficulty / 100\)\n\n            if abs\(new_labor - item\.labor_cost\) > 0\.01:\n                item\.labor_cost = round\(new_labor, 2\)\n                item\.recalculate\(\)\n                updated \+= 1\n'
new2 = '''    def _recalculate_salaries(self):
        """Перерахувати зарплати для всіх позицій з актуальними ставками."""
        updated = 0
        for item in self.manager.items:
            if item.category != "власне виробництво":
                continue
            # FIX: recalculate() тепер сама оновлює labor_cost + ціну
            item.recalculate()
            updated += 1
'''

if re.search(old2, txt):
    txt = re.sub(old2, new2, txt)
    print("✅ _recalculate_salaries() — виправлено")
    changed = True
else:
    print("⚠️  _recalculate_salaries() — НЕ ЗНАЙДЕНО")

# ── 3. import_from_products — додаємо CostEngine ──
old3 = r'            total_price = unit_price \* quantity\n\n            # Формуємо розміри з width/height/length'
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

if re.search(old3, txt):
    txt = re.sub(old3, new3, txt)
    print("✅ import_from_products() — виправлено (CostEngine)")
    changed = True
else:
    print("⚠️  import_from_products() — НЕ ЗНАЙДЕНО")

if changed:
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    print("\n✅ Файл збережено")
else:
    print("\n❌ Нічого не змінено — файл відрізняється від GitHub")
    print("   Відкрийте ventilation_company/gui/price_list_tab.py у VS Code")
    print("   і знайдіть ці 3 фрагменти вручну")

print("\n" + "=" * 60)
print("Тепер запустіть:  python main.py")
print("Потім у Прайс-листі натисніть '🔄 Оновити прайс'")
print("=" * 60)
input("\nНатисніть Enter...")