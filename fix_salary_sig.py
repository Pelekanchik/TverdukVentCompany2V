#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "ventilation_company", "gui", "production_tab.py")

with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

# Змінюємо сигнатуру: product → product=None
# і додаємо fallback: якщо product не передано — беремо selected_product
old = '''    def _calculate_salary(self, product):
        """Розрахувати зарплату для виробу."""
        from ventilation_company.services import SalaryService
        return SalaryService.calculate(
            product_type=product.get("product_type", ""),
            dimensions=product.get("dimensions", ""),
            quantity=product.get("quantity", 1),
            area=product.get("metal_area_m2", 0),
        )'''

new = '''    def _calculate_salary(self, product=None):
        """Розрахувати зарплату для виробу. Якщо product не передано — беремо selected_product."""
        if product is None:
            # Викликано з кнопки "Перерахувати" — беремо вибраний виріб
            product = self.selected_product if hasattr(self, "selected_product") and self.selected_product else None
            if product is None:
                # Якщо нічого не вибрано — беремо перший виріб зі списку
                if self.salary_tree.get_children():
                    item_id = self.salary_tree.get_children()[0]
                    values = self.salary_tree.item(item_id, "values")
                    # values: (name, type, area, rate, difficulty, salary, total)
                    product = {
                        "product_type": values[1] if len(values) > 1 else "",
                        "dimensions": values[0] if len(values) > 0 else "",
                        "quantity": 1,
                        "metal_area_m2": float(values[2]) if len(values) > 2 and values[2] else 0,
                    }
                else:
                    return 0
        
        from ventilation_company.services import SalaryService
        return SalaryService.calculate(
            product_type=product.get("product_type", ""),
            dimensions=product.get("dimensions", ""),
            quantity=product.get("quantity", 1),
            area=product.get("metal_area_m2", 0),
        )'''

if old in txt:
    txt = txt.replace(old, new)
    print("✅ _calculate_salary — виправлено сигнатуру + fallback")
else:
    print("⚠️  Блок не знайдено — можливо, вже інший формат")

with open(path, "w", encoding="utf-8") as f:
    f.write(txt)

print("\nТепер запустіть:  python main.py")
input("\nНатисніть Enter...")