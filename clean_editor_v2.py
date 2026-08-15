#!/usr/bin/env python3
"""
Скрипт для очищення VentCompany від 3D-редактора.
Залишає тільки: імпорт, перегляд, друк (Revit, AutoCAD, SolidWorks, FreeCAD).
"""

import os
import shutil
import re

BASE = os.path.dirname(os.path.abspath(__file__))
VC = os.path.join(BASE, "ventilation_company")


def remove_editor():
    """1. Видалити каталог 3D-редактора та вкладку CAD-редактора."""
    targets = [
        os.path.join(VC, "project3d_editor"),
        os.path.join(VC, "gui", "project3d_tab_new.py"),
    ]
    for t in targets:
        if os.path.exists(t):
            if os.path.isdir(t):
                shutil.rmtree(t)
            else:
                os.remove(t)
            print(f"✅ Видалено: {os.path.relpath(t, BASE)}")


def patch_main_window():
    """2. У main_window.py замінити Project3DTabNew на Project3DTab."""
    path = os.path.join(VC, "gui", "main_window.py")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    text = text.replace(
        "from ventilation_company.gui.project3d_tab_new import Project3DTabNew",
        "from ventilation_company.gui.project_3d_tab import Project3DTab"
    )
    text = text.replace("Project3DTabNew", "Project3DTab")

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("✅ Оновлено: ventilation_company/gui/main_window.py")


def patch_project_3d_tab():
    """3. У project_3d_tab.py прибрати редакторську частину."""
    path = os.path.join(VC, "gui", "project_3d_tab.py")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    # Методи, які треба повністю видалити
    remove_methods = {
        "_open_drawing_editor",
        "_edit_selected",
        "_delete_selected",
        "_get_selected_parent_id",
        "_select_parent_dialog",
        "_get_all_trunks",
        "_get_all_systems",
        "_get_all_floors",
        "_add_floor",
        "_add_wall",
        "_add_system",
        "_add_trunk",
        "_add_segment",
        "_add_fitting",
        "_add_equipment",
    }

    # Імпорти/слова, рядки з якими пропускаємо
    remove_line_keywords = [
        "from ventilation_company.project3d.dialogs import",
        "from ventilation_company.project3d.drawing_editor import",
        "EditSegmentDialog", "AddSegmentDialog",
        "EditEquipmentDialog", "AddEquipmentDialog",
        "EditWallDialog", "AddWallDialog",
        "EditFittingDialog", "AddFittingDialog",
        "EditSystemDialog", "AddSystemDialog",
        "EditTrunkDialog", "AddTrunkDialog",
        "DrawingEditorWindow",
    ]

    # UI-рядки, які пропускаємо
    remove_ui_keywords = [
        'self.add_btn =',
        'add_menu.add_command',
        'self.add_btn["menu"]',
        '✏️ Редагувати креслення',
        '📝 Редагувати',
        '❌ Видалити',
    ]

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Пропускаємо імпорти dialogs / drawing_editor
        if any(k in stripped for k in remove_line_keywords):
            i += 1
            continue

        # Пропускаємо UI-рядки додавання/редагування/видалення
        if any(k in stripped for k in remove_ui_keywords):
            i += 1
            continue

        # Пропускаємо сепаратори, що йдуть поруч з видаленими кнопками
        if stripped.startswith('ttk.Separator(tbar2') and new_lines and 'ttk.Button(tbar2' not in new_lines[-1]:
            # Перевіримо, чи це сепаратор між кнопками — якщо попередній рядок не кнопка, пропускаємо
            i += 1
            continue

        # Шукаємо заголовок методу
        method_match = re.match(r'    def (_\w+|\w+)\(self', line)
        if method_match:
            method_name = method_match.group(1)
            if method_name in remove_methods:
                # Пропускаємо весь метод
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    if next_line == '\n':
                        i += 1
                        continue
                    # Якщо рядок не починається з 8+ пробілів і не коментар — метод закінчився
                    if not next_line.startswith('        ') and not next_line.startswith('    #'):
                        break
                    i += 1
                continue

        new_lines.append(line)
        i += 1

    result = "".join(new_lines)

    # Прибираємо залишки блоку self.add_btn
    result = re.sub(
        r'\s*self\.add_btn = ttk\.Menubutton\(tbar1, text="➕ Додати".*?self\.add_btn\["menu"\] = add_menu\n',
        '\n',
        result,
        flags=re.DOTALL
    )

    # Прибираємо рядки контекстного меню "Редагувати" / "Видалити"
    result = re.sub(r'.*menu\.add_command\(label="Редагувати".*?\n', '', result)
    result = re.sub(r'.*menu\.add_command\(label="Видалити".*?\n', '', result)

    # Прибираємо порожні блоки try/except, якщо залишилися
    result = re.sub(r'\n\n+', '\n\n', result)

    with open(path, "w", encoding="utf-8") as f:
        f.write(result)
    print("✅ Оновлено: ventilation_company/gui/project_3d_tab.py")


def clean_pycache():
    """4. Прибрати __pycache__."""
    for root, dirs, files in os.walk(VC):
        if '__pycache__' in dirs:
            p = os.path.join(root, '__pycache__')
            shutil.rmtree(p)
            print(f"✅ Очищено: {os.path.relpath(p, BASE)}")


if __name__ == "__main__":
    print("🧹 Починаємо очищення від 3D-редактора...\n")
    remove_editor()
    patch_main_window()
    patch_project_3d_tab()
    clean_pycache()
    print("\n✨ Готово! 3D-редактор видалено.")
    print("📋 Залишено:")
    print("   • Імпорт: IFC (Revit), DXF/DWG (AutoCAD), STEP (SolidWorks), FCStd (FreeCAD)")
    print("   • Експорт: IFC, DXF, STEP, FCStd, зображення 2D/3D")
    print("   • Перегляд: 2D план, 3D вигляд, дерево проєкту, властивості")
    print("   • Друк: КП (PDF), перевірка зіткнень")
    print("   • FreeCAD-інтеграція: моделі, прев'ю, експорт")
    print("   • CNC-експорт (SolidWorks)")
