#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VentCompany v2.1 — Виправлення зарплати та ціноутворення"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def fix_cost_engine():
    path = os.path.join(BASE_DIR, "ventilation_company", "calculations", "cost_engine.py")
    if not os.path.exists(path):
        print("[SKIP] cost_engine.py не знайдено")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    old = "        result.labor_cost = blank_area_m2 * labor_rate * (1 + labor_difficulty / 100) * quantity"
    new = ("        # ВИПРАВЛЕННЯ v2.1: уніфікація зарплати з вкладкою \"Виробництво\"\n"
           "        # Тепер зарплата рахується від surface_area (площа готового виробу),\n"
           "        # а не від blank_area (площа заготовки). Це усуває розбіжності\n"
           "        # між CostEngine, ProductionTab та PricingSettings.\n"
           "        result.labor_cost = surface_area_m2 * labor_rate * (1 + labor_difficulty / 100) * quantity")
    if old not in content:
        print("[SKIP] cost_engine.py: рядок не знайдено (можливо, вже виправлено)")
        return False
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[OK]  cost_engine.py — зарплата тепер від surface_area_m2")
    return True

def fix_standard_products():
    path = os.path.join(BASE_DIR, "ventilation_company", "standard_products.py")
    if not os.path.exists(path):
        print("[SKIP] standard_products.py не знайдено")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    old = '    def get_cost_breakdown(self):\n        """Отримати детальний розбив собівартості (CostBreakdown)."""'
    new = ('    def recalculate_price(self) -> float:\n'
           '        """Перерахувати ціну з актуальними ставками з pricing_settings.json.\n\n'
           '        Використовувати при завантаженні проєкту або зміні налаштувань\n'
           '        цін/зарплат, щоб ціна виробу завжди відповідала поточним ставкам.\n'
           '        """\n'
           '        self.unit_price = Decimal(str(self.calculate_price()))\n'
           '        self.total_price = self.unit_price * self.quantity\n'
           '        return float(self.unit_price)\n\n'
           '    def get_cost_breakdown(self):\n'
           '        """Отримати детальний розбив собівартості (CostBreakdown)."""')
    if old not in content:
        print("[SKIP] standard_products.py: рядок не знайдено (можливо, вже виправлено)")
        return False
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[OK]  standard_products.py — додано recalculate_price()")
    return True

def fix_main_window():
    path = os.path.join(BASE_DIR, "ventilation_company", "gui", "main_window.py")
    if not os.path.exists(path):
        print("[SKIP] main_window.py не знайдено")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace(
        "            # Перераховуємо зарплати перед автозбереженням",
        "            # Перераховуємо ціни та зарплати перед автозбереженням"
    )
    old_load = ('        # === ПЕРЕРАХУНОК ЦІН ТА ЗАРПЛАТИ при завантаженні ===\n'
                '        from ventilation_company.gui.settings_tab import PricingSettings\n'
                '        from ventilation_company.calculations.cost_engine import CostEngine\n'
                '        settings = PricingSettings.get_instance()\n'
                '        engine = CostEngine(settings)\n        \n'
                '        for p in products:\n'
                '            # Перераховуємо ціну з актуальними ставками\n'
                '            try:\n'
                '                price_data = engine.calculate_price_breakdown(p)\n'
                '                p["unit_price"] = price_data["price_with_vat"]\n'
                '                p["total_price"] = p["unit_price"] * p.get("quantity", 1)\n'
                '                p["cost_price"] = price_data["cost_price"]\n'
                '                p["salary_per_unit"] = price_data["salary"]\n'
                '                p["salary_total"] = p["salary_per_unit"] * p.get("quantity", 1)\n'
                '            except Exception:\n'
                '                pass  # якщо не вдалося перерахувати — залишаємо старі значення\n'
                '        # =====================================================')
    new_load = ('        # === ПЕРЕРАХУНОК ЦІН ТА ЗАРПЛАТИ при завантаженні ===\n'
                '        from ventilation_company.standard_products import StandardProduct\n        \n'
                '        for p in products:\n'
                '            try:\n'
                '                # Перестворюємо виріб і перераховуємо ціну з актуальними ставками\n'
                '                product_obj = StandardProduct.from_dict(p)\n'
                '                product_obj.recalculate_price()\n                \n'
                '                p["unit_price"] = float(product_obj.unit_price)\n'
                '                p["total_price"] = float(product_obj.total_price)\n                \n'
                '                # Зарплата з CostEngine (тепер уніфікована з surface_area)\n'
                '                breakdown = product_obj.get_cost_breakdown()\n'
                '                p["salary_per_unit"] = round(breakdown.labor_cost / p.get("quantity", 1), 2)\n'
                '                p["salary_total"] = round(breakdown.labor_cost, 2)\n'
                '            except Exception:\n'
                '                pass  # якщо не вдалося перерахувати — залишаємо старі значення\n'
                '        # =====================================================')
    if old_load in content:
        content = content.replace(old_load, new_load)
    else:
        print("[WARN] main_window.py: блок _load_project_data не знайдено")
    old_recalc = ('        from ventilation_company.gui.settings_tab import PricingSettings\n'
                  '        from ventilation_company.calculations.cost_engine import CostEngine\n'
                  '        settings = PricingSettings.get_instance()\n'
                  '        engine = CostEngine(settings)\n        \n'
                  '        updated = 0\n'
                  '        for p in products:\n'
                  '            try:\n'
                  '                price_data = engine.calculate_price_breakdown(p)\n'
                  '                p["unit_price"] = price_data["price_with_vat"]\n'
                  '                p["total_price"] = p["unit_price"] * p.get("quantity", 1)\n'
                  '                updated += 1\n'
                  '            except Exception:\n'
                  '                pass')
    new_recalc = ('        from ventilation_company.standard_products import StandardProduct\n        \n'
                  '        updated = 0\n'
                  '        for p in products:\n'
                  '            try:\n'
                  '                product_obj = StandardProduct.from_dict(p)\n'
                  '                product_obj.recalculate_price()\n                \n'
                  '                p["unit_price"] = float(product_obj.unit_price)\n'
                  '                p["total_price"] = float(product_obj.total_price)\n                \n'
                  '                breakdown = product_obj.get_cost_breakdown()\n'
                  '                p["salary_per_unit"] = round(breakdown.labor_cost / p.get("quantity", 1), 2)\n'
                  '                p["salary_total"] = round(breakdown.labor_cost, 2)\n'
                  '                updated += 1\n'
                  '            except Exception:\n'
                  '                pass')
    if old_recalc in content:
        content = content.replace(old_recalc, new_recalc)
    else:
        print("[WARN] main_window.py: блок _recalculate_current_project не знайдено")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[OK]  main_window.py — виправлено завантаження та перерахунок")
    return True

def fix_price_list_tab():
    path = os.path.join(BASE_DIR, "ventilation_company", "gui", "price_list_tab.py")
    if not os.path.exists(path):
        print("[SKIP] price_list_tab.py не знайдено")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    old_recalc = ('    def recalculate(self):\n'
                  '        if self.category == "перепродаж" and self.supplier_price > 0:\n'
                  '            base = self.supplier_price\n'
                  '        else:\n'
                  '            base = self.cost_price + self.labor_cost + self.overhead_cost\n'
                  '        self.unit_price = base * (1 + self.markup_percent / 100)\n'
                  '        self.total_price = self.unit_price * self.quantity')
    new_recalc = ('    def recalculate(self):\n'
                  '        # ВИПРАВЛЕННЯ v2.1: отримати актуальні ставки зарплати з PricingSettings\n'
                  '        # і перерахувати labor_cost + кінцеву ціну при кожному виклику.\n'
                  '        from ventilation_company.gui.settings_tab import PricingSettings\n'
                  '        settings = PricingSettings.get_instance()\n        \n'
                  '        if self.category == "власне виробництво":\n'
                  '            # Перерахувати labor_cost з актуальними ставками\n'
                  '            labor = settings.get_labor_rate(self.product_type or self.name)\n'
                  '            rate = labor.get("rate_per_m2", 120.0)\n'
                  '            difficulty = labor.get("difficulty_percent", 0.0)\n'
                  '            area = self._estimate_area()\n'
                  '            self.labor_cost = round(area * rate * (1 + difficulty / 100), 2)\n        \n'
                  '        if self.category == "перепродаж" and self.supplier_price > 0:\n'
                  '            base = self.supplier_price\n'
                  '        else:\n'
                  '            base = self.cost_price + self.labor_cost + self.overhead_cost\n'
                  '        self.unit_price = base * (1 + self.markup_percent / 100)\n'
                  '        self.total_price = self.unit_price * self.quantity\n\n'
                  '    def _estimate_area(self) -> float:\n'
                  '        """Оцінити площу виробу з розмірів (м²) — як у ProductionTab."""\n'
                  '        try:\n'
                  '            parts = self.dimensions.replace("×", "x").replace("X", "x").split("x")\n'
                  '            if len(parts) >= 3:\n'
                  '                w, h, l = float(parts[0]), float(parts[1]), float(parts[2])\n'
                  '                return 2 * (w/1000 + h/1000) * (l/1000)\n'
                  '            elif len(parts) == 2:\n'
                  '                d, l = float(parts[0]), float(parts[1])\n'
                  '                return 3.14159 * (d/1000) * (l/1000)\n'
                  '        except (ValueError, IndexError):\n'
                  '            pass\n'
                  '        return 0.0')
    if old_recalc in content:
        content = content.replace(old_recalc, new_recalc)
    else:
        print("[WARN] price_list_tab.py: метод recalculate не знайдено")
    old_method = ('    def _recalculate_salaries(self):\n'
                  '        """Перерахувати зарплати для всіх позицій з актуальними ставками."""\n'
                  '        from ventilation_company.gui.settings_tab import PricingSettings\n'
                  '        settings = PricingSettings.get_instance()\n'
                  '        updated = 0\n\n'
                  '        for item in self.manager.items:\n'
                  '            if item.category != "власне виробництво":\n'
                  '                continue\n\n'
                  '            ptype = item.product_type or item.name\n'
                  '            dims = item.dimensions\n\n'
                  '            # Розпарсити розміри\n'
                  '            try:\n'
                  '                parts = dims.replace("×", "x").replace("X", "x").split("x")\n'
                  '                if len(parts) >= 2:\n'
                  '                    w = float(parts[0])\n'
                  '                    h = float(parts[1]) if len(parts) > 1 else 0\n'
                  '                    l = float(parts[2]) if len(parts) > 2 else 0\n'
                  '                else:\n'
                  '                    w = h = l = 0\n'
                  '            except (ValueError, IndexError):\n'
                  '                w = h = l = 0\n\n'
                  '            # Приблизна площа\n'
                  '            if "кругл" in ptype.lower():\n'
                  '                area = 3.14159 * w * l / 1_000_000\n'
                  '            else:\n'
                  '                area = 2 * (w + h) * l / 1_000_000\n\n'
                  '            if area <= 0:\n'
                  '                continue\n\n'
                  '            labor_info = settings.get_labor_rate(ptype)\n'
                  '            rate = labor_info.get("rate_per_m2", 120.0)\n'
                  '            difficulty = labor_info.get("difficulty_percent", 0.0)\n'
                  '            new_labor = area * rate * (1 + difficulty / 100)\n\n'
                  '            if abs(new_labor - item.labor_cost) > 0.01:\n'
                  '                item.labor_cost = round(new_labor, 2)\n'
                  '                item.recalculate()\n'
                  '                updated += 1')
    new_method = ('    def _recalculate_salaries(self):\n'
                  '        """Перерахувати зарплати для всіх позицій з актуальними ставками."""\n'
                  '        updated = 0\n\n'
                  '        for item in self.manager.items:\n'
                  '            if item.category != "власне виробництво":\n'
                  '                continue\n'
                  '            # ВИПРАВЛЕННЯ: recalculate() тепер сама перераховує labor_cost\n'
                  '            # з актуальними ставками і оновлює кінцеву ціну\n'
                  '            item.recalculate()\n'
                  '            updated += 1')
    if old_method in content:
        content = content.replace(old_method, new_method)
    else:
        print("[WARN] price_list_tab.py: метод _recalculate_salaries не знайдено")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[OK]  price_list_tab.py — ціна прайсу тепер жива")
    return True

if __name__ == "__main__":
    print("=" * 55)
    print("  VentCompany v2.1 — Виправлення зарплати")
    print("=" * 55 + "\n")
    results = [fix_cost_engine(), fix_standard_products(), fix_main_window(), fix_price_list_tab()]
    print("\n" + "=" * 55)
    if all(results):
        print("  ✅ Усі виправлення застосовано!")
        print("\n  Що змінилося:")
        print("   1. Зарплата у CostEngine — від surface_area (уніфіковано)")
        print("   2. Додано recalculate_price() — жива ціна виробу")
        print("   3. При завантаженні проєкту — автоперерахунок цін")
        print("   4. Прайс-лист — оновлюється при зміні ставок")
    else:
        print("  ⚠️  Деякі файли пропущено (можливо, вже виправлені)")
    print("\n  💡 Перезапустіть програму.")
    print("=" * 55)
    input("\nНатисніть Enter...")