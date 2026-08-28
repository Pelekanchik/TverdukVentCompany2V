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

# 2. Видаляємо старий прайс (з неправильними зарплатами)
price_json = os.path.join(BASE, "data", "price_list.json")
if os.path.exists(price_json):
    os.remove(price_json)
    print("🗑️  Видалено старий price_list.json (були неправильні зарплати)")

# 3. Виправляємо price_list_tab.py жорстко — через regex
path = os.path.join(BASE, "ventilation_company", "gui", "price_list_tab.py")
with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

if "def _estimate_area(self)" not in txt:
    print("⚠️  price_list_tab.py — ще не виправлено. Виправляю...")
    
    # Замінюємо recalculate() — шукаємо від "def recalculate(self):" до наступного методу
    pattern = r'(    def recalculate\(self\):)(.*?)(?=    def [a-zA-Z_])'
    match = re.search(pattern, txt, re.DOTALL)
    if match:
        new_recalc = '''    def recalculate(self):
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
        return 0.0

'''
        txt = txt[:match.start()] + new_recalc + txt[match.end():]
        print("   ✅ recalculate() + _estimate_area() додано")
    else:
        print("   ❌ Не знайдено recalculate() — перевірте файл вручну")

    # Замінюємо _recalculate_salaries()
    pattern2 = r'(    def _recalculate_salaries\(self\):)(.*?)(?=    def [a-zA-Z_])'
    match2 = re.search(pattern2, txt, re.DOTALL)
    if match2:
        new_method = '''    def _recalculate_salaries(self):
        """Перерахувати зарплати для всіх позицій з актуальними ставками."""
        updated = 0
        for item in self.manager.items:
            if item.category != "власне виробництво":
                continue
            item.recalculate()  # тепер сама оновлює labor_cost + ціну
            updated += 1

'''
        txt = txt[:match2.start()] + new_method + txt[match2.end():]
        print("   ✅ _recalculate_salaries() спрощено")
    else:
        print("   ❌ Не знайдено _recalculate_salaries()")

    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
else:
    print("[OK] price_list_tab.py — вже виправлено")

print("\n" + "=" * 55)
print("✅ ГОТОВО!")
print("=" * 55)
print("\nЩО РОБИТИ ДАЛІ:")
print("1. Запустіть:  python main.py")
print("2. Перейдіть у Прайс-лист")
print("3. Натисніть '🔄 Оновити прайс' (праворуч вгорі)")
print("   Це заново імпортує вироби з правильними зарплатами")
print("\nПісля цього Роботи у прайсі мають дорівнювати")
print("Зарплаті у Виробництві (наприклад, 172.80 грн)")
print("=" * 55)
input("\nНатисніть Enter...")