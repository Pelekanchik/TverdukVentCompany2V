#!/usr/bin/env python3
"""
ПАТЧ: Ціна виробу тепер розраховується від АКТУАЛЬНОЇ зарплати (як у Виробництві),
а не від збереженої в БД.
"""

import os

def patch_file(filepath, old_method, new_method):
    if not os.path.exists(filepath):
        print(f"❌ Не знайдено: {filepath}")
        return False
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    if old_method not in content:
        print(f"⚠️ Не знайдено старий метод у {filepath}")
        return False
    
    content = content.replace(old_method, new_method)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✅ {filepath} пропатчено")
    return True


# 1. Патчим pricing.py
pricing_path = "ventilation_company/calculations/pricing.py"
old_pricing = '''    def _labor_cost(self, p):
        return p.get("salary_per_unit", 0) * p.get("quantity", 1)'''

new_pricing = '''    def _labor_cost(self, p):
        """Розрахунок зарплати 'на льоту' з актуальними ставками."""
        ptype = p.get("product_type", "")
        metal_area = p.get("metal_area_m2", 0)
        qty = p.get("quantity", 1)
        
        labor_info = self.settings.get_labor_rate(ptype)
        rate = labor_info.get("rate_per_m2", 120.0)
        difficulty = labor_info.get("difficulty_percent", 0.0)
        salary_per_unit = metal_area * rate * (1 + difficulty / 100)
        
        # Синхронізуємо зарплату в продукті
        p["salary_per_unit"] = salary_per_unit
        
        return salary_per_unit * qty'''

patch_file(pricing_path, old_pricing, new_pricing)


# 2. Патчим cost_engine.py
cost_path = "ventilation_company/calculations/cost_engine.py"
old_cost = '''    def _labor_cost(self, product):
        return product.get("salary_per_unit", 0) * product.get("quantity", 1)'''

new_cost = '''    def _labor_cost(self, product):
        """Розрахунок зарплати 'на льоту' з актуальними ставками."""
        ptype = product.get("product_type", "")
        metal_area = product.get("metal_area_m2", 0)
        qty = product.get("quantity", 1)
        
        labor_info = self.settings.get_labor_rate(ptype)
        rate = labor_info.get("rate_per_m2", 120.0)
        difficulty = labor_info.get("difficulty_percent", 0.0)
        salary_per_unit = metal_area * rate * (1 + difficulty / 100)
        
        # Синхронізуємо зарплату в продукті
        product["salary_per_unit"] = salary_per_unit
        
        return salary_per_unit * qty'''

patch_file(cost_path, old_cost, new_cost)

print("\n" + "=" * 60)
print("🎉 Готово! Тепер ціна виробу розраховується від актуальної зарплати.")
print("   Запусти: python sync_all.py")
print("   Перезапусти VentCompany")
print("=" * 60)