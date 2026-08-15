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

    # Заміна імпорту
    text = text.replace(
        "from ventilation_company.gui.project3d_tab_new import Project3DTabNew",
        "from ventilation_company.gui.project_3d_tab import Project3DTab"
    )
    # Заміна використання
    text = text.replace("Project3DTabNew", "Project3DTab")

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("✅ Оновлено: ventilation_company/gui/main_window.py")

def patch_project_3d_tab():
    """3. У project_3d_tab.py прибрати редакторську частину."""
    path = os.path.join(VC, "gui", "project_3d_tab.py")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    new_lines = []
    skip_mode = None  # 'import', 'method', 'ui'
    brace_depth = 0

    # Слова-маркери для видалення цілих рядків
    remove_imports = [
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

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # --- Прибираємо імпорти dialogs та drawing_editor ---
        if any(r in stripped for r in remove_imports):
            i += 1
            continue

        # --- Прибираємо UI-кнопки "Додати", "Редагувати", "Видалити", "Редагувати креслення" ---
        if any(k in stripped for k in [
            'self.add_btn =',
            'add_menu.add_command',
            'self.add_btn["menu"]',
            'ttk.Button(tbar2, text="✏️ Редагувати креслення"',
            'ttk.Button(tbar2, text="📝 Редагувати"',
            'ttk.Button(tbar2, text="❌ Видалити"',
            'ttk.Separator(tbar2,',  # деякі сепаратори поруч з кнопками редагування
        ]):
            i += 1
            continue

        # --- Прибираємо методи редагування ---
        # Шукаємо заголовок методу
        method_match = re.match(r'    def (_\w+|\w+)\(self', line)
        if method_match:
            method_name = method_match.group(1)
            if method_name in remove_methods:
                # Пропускаємо весь метод
                i += 1
                # Рахуємо відступи: методи класу мають відступ 4 пробіли
                # Тіло методу — відступ >= 8 пробілів або порожні рядки всередині методу
                while i < len(lines):
                    next_line = lines[i]
                    if next_line == '\n':
                        i += 1
                        continue
                    if not next_line.startswith('        ') and not next_line.startswith('    #'):
                        break
                    i += 1
                continue

        new_lines.append(line)
        i += 1

    # Додатково приберемо залишки меню додавання, якщо щось лишилось
    result = "".join(new_lines)

    # Прибираємо блок self.add_btn повністю (якщо лишилися окремі рядки)
    result = re.sub(r'\s*self\.add_btn = ttk\\.Menubutton.*?self\\.add_btn\\["menu"\\] = add_menu\\n', '\\n', result, flags=re.DOTALL)

    # Прибираємо рядок з кнопкою "Додати" якщо лишився
    result = re.sub(r'.*➕ Додати.*\\n', '', result)

    # Прибираємо рядок з кнопкою "Редагувати креслення"
    result = re.sub(r'.*✏️ Редагувати креслення.*\\n', '', result)

    # Прибираємо рядок з кнопкою "Редагувати"
    result = re.sub(r'.*📝 Редагувати.*\\n', '', result)

    # Прибираємо рядок з кнопкою "Видалити"
    result = re.sub(r'.*❌ Видалити.*\\n', '', result)

    # Прибираємо контекстне меню редагування в _on_tree_right_click, якщо воно є
    # Замінюємо його на пусту функцію або прибираємо дії
    result = re.sub(
        r'(def _on_tree_right_click\\(self, event\\):.*?)menu\\.add_command\\(label="Редагувати".*?menu\\.add_command\\(label="Видалити".*?menu\\.post\\(event\\.x_root, event\\.y_root\\))',
        r'\\1pass',
        result,
        flags=re.DOTALL
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(result)
    print("✅ Оновлено: ventilation_company/gui/project_3d_tab.py")

def clean_pycache():
    """4. Прибрати __pycache__ для чистоти."""
    for root, dirs, files in os.walk(VC):
        if '__pycache__' in dirs:
            p = os.path.join(root, '__pycache__')
            shutil.rmtree(p)
            print(f"✅ Очищено: {os.path.relpath(p, BASE)}")

if __name__ == "__main__":
    print("🧹 Починаємо очищення від 3D-редактора...\\n")
    remove_editor()
    patch_main_window()
    patch_project_3d_tab()
    clean_pycache()
    print("\\n✨ Готово! 3D-редактор видалено.")
    print("📋 Залишено:")
    print("   • Імпорт: IFC (Revit), DXF/DWG (AutoCAD), STEP (SolidWorks), FCStd (FreeCAD)")
    print("   • Експорт: IFC, DXF, STEP, FCStd, зображення 2D/3D")
    print("   • Перегляд: 2D план, 3D вигляд, дерево проєкту, властивості")
    print("   • Друк: КП (PDF), перевірка зіткнень")
    print("   • FreeCAD-інтеграція: моделі, прев'ю, експорт")
    print("   • CNC-експорт (SolidWorks)")