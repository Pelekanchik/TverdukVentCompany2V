#!/usr/bin/env python3
"""Діагностика: чому немає кнопки 📚."""

import os
import sys
import py_compile

ROOT = r"C:\Users\Admin\Desktop\TverdukVentCompany2V"
os.chdir(ROOT)
sys.path.insert(0, ROOT)

print("=" * 60)
print("🔍 ДІАГНОСТИКА products_tab.py")
print("=" * 60)

# 1. Який файл насправді завантажується?
print("\n📁 1. Шлях до завантаженого модуля:")
try:
    import ventilation_company.gui.products_tab as pt
    print(f"   {pt.__file__}")
except Exception as e:
    print(f"   ❌ Помилка імпорту: {e}")
    sys.exit(1)

# 2. Перевірка синтаксису
print("\n📝 2. Перевірка синтаксису:")
filepath = pt.__file__
try:
    py_compile.compile(filepath, doraise=True)
    print("   ✅ Синтаксис ОК")
except py_compile.PyCompileError as e:
    print(f"   ❌ СИНТАКСИЧНА ПОМИЛКА: {e}")
    print("   → Віднови файл з .backup і повідом мене")

# 3. Чи є новий метод?
print("\n🔧 3. Перевірка методів:")
has_method = hasattr(pt.ProductsTab, "_save_selected_to_library")
print(f"   _save_selected_to_library: {'✅ Є' if has_method else '❌ НЕМАЄ'}")

# 4. Чи є кнопка в коді?
print("\n📚 4. Перевірка кнопки в файлі:")
with open(filepath, "r", encoding="utf-8") as f:
    code = f.read()
has_button = "📚" in code and "_save_selected_to_library" in code
print(f"   Кнопка 'В бібліотеку': {'✅ Є в коді' if has_button else '❌ НЕМАЄ в коді'}")

# 5. Кеш
print("\n💾 5. Кеш Python (__pycache__):")
pycache = os.path.join(os.path.dirname(filepath), "__pycache__")
if os.path.exists(pycache):
    files = os.listdir(pycache)
    print(f"   Знайдено {len(files)} файлів у {pycache}")
    for f in files:
        if "products_tab" in f:
            print(f"   → {f}")
else:
    print("   Кешу немає")

print("\n" + "=" * 60)
if not has_method:
    print("❌ Проблема: метод не завантажується.")
    print("   → Видали __pycache__ і перезапусти програму")
elif not has_button:
    print("❌ Проблема: патч не застосувався до файлу.")
    print("   → Віднови з .backup і запусти patch_ventcompany.py знову")
else:
    print("✅ Код в порядку! Спробуй:")
    print("   1. Закрити VentCompany повністю")
    print("   2. Видалити папку __pycache__ в ventilation_company/gui/")
    print("   3. Запустити python main.py знову")
print("=" * 60)