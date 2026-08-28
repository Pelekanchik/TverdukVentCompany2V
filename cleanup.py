#!/usr/bin/env python3
"""Видаляє всі тимчасові файли фіксів."""

import os

files = [
    "convert_json_to_sqlite.py", "patch_ventcompany.py",
    "fix_preset.py", "fix_preset2.py", "fix_preset3.py",
    "fix_preset_final.py", "fix_preset_import.py",
    "fix_import_final.py", "fix_import_correct.py",
    "fix_syntax.py", "debug_preset.py", "debug_all.py",
    "show_on_ok.py", "show_double_click.py",
    "show_preset_methods.py", "show_import.py",
    "list_methods.py", "patch_products_tab_real.py",
    "patch_price_list.py", "recalculate_salaries.py",
    "recalculate_all_salaries.py", "check_salaries.py",
    "sync_salaries.py", "patch_freecad_cmd.py",
    "patch_freecad_final.py", "patch_freecad_workbench.py",
]

removed = 0
for f in files:
    if os.path.exists(f):
        os.remove(f)
        print(f"🗑️  {f}")
        removed += 1

for root, dirs, files in os.walk("."):
    for f in files:
        if f.endswith(".backup"):
            os.remove(os.path.join(root, f))
            print(f"🗑️  {f}")
            removed += 1

print(f"\n✅ Видалено {removed} файлів")