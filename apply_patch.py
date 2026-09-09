"""Скрипт для застосування патчу "Налаштування" до VentCompany.

Запуск:
    python apply_patch.py

Що робить:
  1. Перевіряє наявність program_settings_tab.py
  2. Перевіряє main_window.py — додає "settings" у tabs, якщо немає
  3. Перевіряє permissions.py — додає view_program_settings, якщо немає
"""

import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))


def patch_main_window():
    """Додати ProgramSettingsTab у main_window.py, якщо ще немає."""
    path = os.path.join(BASE, "ventilation_company", "gui_pyside6", "main_window.py")
    if not os.path.exists(path):
        print("❌ main_window.py не знайдено")
        return False

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "ProgramSettingsTab" in content:
        print("✅ main_window.py вже містить ProgramSettingsTab")
        return True

    # Додаємо імпорт
    if (
        "from ventilation_company.gui_pyside6.program_settings_tab import ProgramSettingsTab"
        not in content
    ):
        # Знайдемо перший імпорт gui_pyside6 і вставимо після нього
        lines = content.split("\n")
        import_idx = -1
        for i, line in enumerate(lines):
            if "gui_pyside6" in line and line.strip().startswith("from"):
                import_idx = i
        if import_idx >= 0:
            lines.insert(
                import_idx + 1,
                "from ventilation_company.gui_pyside6.program_settings_tab import ProgramSettingsTab",
            )
        else:
            # Вставимо після останнього from
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip().startswith("from "):
                    lines.insert(
                        i + 1,
                        "from ventilation_company.gui_pyside6.program_settings_tab import ProgramSettingsTab",
                    )
                    break

    # Додаємо "settings" у tabs
    if '"settings":' not in content and "'settings':" not in content:
        # Шукаємо рядок з "crm": CRMTab()
        for i, line in enumerate(lines):
            if '"crm":' in line or "'crm':" in line:
                indent = len(line) - len(line.lstrip())
                new_line = " " * indent + '"settings": ProgramSettingsTab(current_user=self.user),'
                lines.insert(i + 1, new_line)
                break

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("✅ main_window.py оновлено")
    return True


def patch_permissions():
    """Додати view_program_settings у permissions.py, якщо ще немає."""
    path = os.path.join(BASE, "ventilation_company", "auth", "permissions.py")
    if not os.path.exists(path):
        print("❌ permissions.py не знайдено — скопіюй його з архіву вручну")
        return False

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "view_program_settings" in content:
        print("✅ permissions.py вже містить view_program_settings")
        return True

    print("⚠️ permissions.py не містить view_program_settings")
    print("   Скопіюй permissions.py з цього архіву вручну:")
    print("   ventilation_company/auth/permissions.py")
    return False


def copy_files():
    """Скопіювати нові файли."""
    files = [
        (
            "gui_pyside6/program_settings_tab.py",
            "ventilation_company/gui_pyside6/program_settings_tab.py",
        ),
        ("gui_pyside6/__init__.py", "ventilation_company/gui_pyside6/__init__.py"),
    ]
    for src_rel, dst_rel in files:
        src = os.path.join(BASE, src_rel)
        dst = os.path.join(BASE, dst_rel)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"✅ Скопійовано: {dst_rel}")
        else:
            print(f"❌ Не знайдено: {src_rel}")


if __name__ == "__main__":
    print("🔧 Застосування патчу VentCompany — Налаштування\n")
    copy_files()
    patch_main_window()
    patch_permissions()
    print("\n🚀 Готово! Запусти: python main_pyside6.py")
