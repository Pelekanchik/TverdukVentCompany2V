"""Вкладка "Проєкти 3D / Креслення" — заміна старої вкладки FreeCAD.

Функціонал:
 • Імпорт: IFC (Revit), DXF/DWG (AutoCAD), STEP (Solidworks), FCStd (FreeCAD), .ventproj
 • Експорт: IFC, DXF, STEP, FCStd, .ventproj
 • 2D-перегляд планів поверхів з накладанням вентиляції (тільки перегляд)
 • 3D-перегляд системи вентиляції в архітектурному контексті
 • Редагування: зміна розмірів, переміщення, видалення через дерево
 • Окремий редактор креслень для інтерактивного креслення мишею
 • Дерево проєкту: Система → Траса → Сегмент/Виріб
"""

import os
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from ventilation_company.project3d import (
    VentProject, ProjectConverter,
    Project3DPreview, Project2DPreview,
    VentilationSystem, VentilationTrunk, DuctSegment, Fitting, Equipment, Point3D,
    Wall,
)
from ventilation_company.project3d.dialogs import (
    EditSegmentDialog, AddSegmentDialog,
    EditEquipmentDialog, AddEquipmentDialog,
    EditWallDialog, AddWallDialog,
    EditFittingDialog, AddFittingDialog,
    EditSystemDialog, AddSystemDialog,
    EditTrunkDialog, AddTrunkDialog,
)

from ventilation_company.project3d.drawing_editor import DrawingEditorWindow


class Project3DTab:
    """Головна вкладка для роботи з 3D-проєктами та кресленнями."""

    def __init__(self, parent, get_products_callback=None):
        self.parent = parent
        self.get_products_callback = get_products_callback
        self.frame = ttk.Frame(parent)
        self.project: VentProject = VentProject()
        self._current_file: str = ""
        self._modified = False

        self._build_ui()
        self._load_demo_if_empty()

    def _build_ui(self):
        # ── Top toolbar — 2 рядки для адаптації під маленькі екрани ──
        toolbar_wrap = ttk.Frame(self.frame, padding=5)
        toolbar_wrap.pack(fill=tk.X)

        # Рядок 1: назва, файл, імпорт/експорт, додати
        tbar1 = ttk.Frame(toolbar_wrap)
        tbar1.pack(fill=tk.X)

        ttk.Label(tbar1, text="🏗️ Проєкти 3D / Креслення", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        ttk.Separator(tbar1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Button(tbar1, text="📂 Новий", command=self._new_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(tbar1, text="💾 Зберегти", command=self._save_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(tbar1, text="📁 Відкрити", command=self._load_project).pack(side=tk.LEFT, padx=2)

        ttk.Separator(tbar1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # Імпорт
        self.import_btn = ttk.Menubutton(tbar1, text="📥 Імпорт", direction="below")
        self.import_btn.pack(side=tk.LEFT, padx=2)
        import_menu = tk.Menu(self.import_btn, tearoff=0)
        import_menu.add_command(label="🏗️ З Revit (IFC)", command=lambda: self._import_file("ifc"))
        import_menu.add_command(label="📐 З AutoCAD (DXF/DWG)", command=lambda: self._import_file("dxf"))
        import_menu.add_command(label="🔧 З Solidworks (STEP)", command=lambda: self._import_file("step"))
        import_menu.add_command(label="🆓 З FreeCAD (FCStd)", command=lambda: self._import_file("fcstd"))
        import_menu.add_separator()
        import_menu.add_command(label="📋 З VentProject", command=lambda: self._import_file("ventproj"))
        self.import_btn["menu"] = import_menu

        # Експорт
        self.export_btn = ttk.Menubutton(tbar1, text="📤 Експорт", direction="below")
        self.export_btn.pack(side=tk.LEFT, padx=2)
        export_menu = tk.Menu(self.export_btn, tearoff=0)
        export_menu.add_command(label="🏗️ У Revit (IFC)", command=lambda: self._export_file("ifc"))
        export_menu.add_command(label="📐 У AutoCAD (DXF)", command=lambda: self._export_file("dxf"))
        export_menu.add_command(label="🔧 У Solidworks (STEP)", command=lambda: self._export_file("step"))
        export_menu.add_command(label="🆓 У FreeCAD (FCStd)", command=lambda: self._export_file("fcstd"))
        export_menu.add_separator()
        export_menu.add_command(label="📋 У VentProject", command=lambda: self._export_file("ventproj"))
        export_menu.add_separator()
        export_menu.add_command(label="🖼️ Зберегти 2D", command=self._export_image_2d)
        export_menu.add_command(label="🖼️ Зберегти 3D", command=self._export_image_3d)
        self.export_btn["menu"] = export_menu

        ttk.Separator(tbar1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # Додавання
        self.add_btn = ttk.Menubutton(tbar1, text="➕ Додати", direction="below")
        self.add_btn.pack(side=tk.LEFT, padx=2)
        add_menu = tk.Menu(self.add_btn, tearoff=0)
        add_menu.add_command(label="🏛️ Поверх", command=self._add_floor)
        add_menu.add_command(label="🧱 Стіна", command=self._add_wall)
        add_menu.add_separator()
        add_menu.add_command(label="🌬️ Систему", command=self._add_system)
        add_menu.add_command(label="📏 Трасу", command=self._add_trunk)
        add_menu.add_command(label="➡️ Сегмент", command=self._add_segment)
        add_menu.add_command(label="🔀 Фасонний виріб", command=self._add_fitting)
        add_menu.add_command(label="⚙️ Обладнання", command=self._add_equipment)
        self.add_btn["menu"] = add_menu

        # Рядок 2: креслення, зіткнення, редагування, видалення
        tbar2 = ttk.Frame(toolbar_wrap)
        tbar2.pack(fill=tk.X, pady=(3, 0))

        ttk.Button(tbar2, text="✏️ Редагувати креслення", command=self._open_drawing_editor).pack(side=tk.LEFT, padx=2)
        ttk.Separator(tbar2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(tbar2, text="⚠️ Перевірити зіткнення", command=self._check_collisions).pack(side=tk.LEFT, padx=2)
        ttk.Separator(tbar2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(tbar2, text="📝 Редагувати", command=self._edit_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(tbar2, text="❌ Видалити", command=self._delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Separator(tbar2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(tbar2, text="📄 КП (PDF)", command=self._generate_proposal).pack(side=tk.LEFT, padx=2)

        # ── Main area: left (tree + props) | right (preview) ──
        paned = ttk.PanedWindow(self.frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ── Left panel ──
        left = ttk.Frame(paned)
        paned.add(left, weight=1)

        # Project tree
        tree_frame = ttk.LabelFrame(left, text="Структура проєкту", padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(tree_frame, show="tree", height=20)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-3>", self._on_tree_right_click)

        # Properties panel
        props_frame = ttk.LabelFrame(left, text="Властивості", padding=5)
        props_frame.pack(fill=tk.X, padx=5, pady=5)

        self.props_text = tk.Text(props_frame, height=10, wrap=tk.WORD, font=("Consolas", 9))
        self.props_text.pack(fill=tk.BOTH, expand=True)
        self.props_text.config(state=tk.DISABLED)

        # Project info
        info_frame = ttk.LabelFrame(left, text="Інформація", padding=5)
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        self.info_label = ttk.Label(info_frame, text="Новий проєкт", foreground="#666", wraplength=280)
        self.info_label.pack(anchor=tk.W)

        # ── Right panel: 2D/3D tabs ──
        right = ttk.Notebook(paned)
        paned.add(right, weight=3)

        # 2D Plan tab
        self.plan_frame = ttk.Frame(right)
        right.add(self.plan_frame, text="📐 План 2D")
        self.preview_2d = Project2DPreview(self.plan_frame)

        # 3D View tab
        self.view3d_frame = ttk.Frame(right)
        right.add(self.view3d_frame, text="🏗️ 3D Вигляд")
        self.preview_3d = Project3DPreview(self.view3d_frame)

        # ── Status bar ──
        self.status = ttk.Label(self.frame, text="Готово", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def _open_drawing_editor(self):
        """Відкрити окреме вікно редактора креслень на весь екран."""
        def on_editor_close(was_modified):
            if was_modified:
                self._modified = True
                self._refresh_tree()
                self._refresh_previews()
                self.status.config(text="✅ Креслення оновлено")

        DrawingEditorWindow(
            parent=self.frame.winfo_toplevel(),
            project=self.project,
            on_close_callback=on_editor_close,
        )

    def _refresh_tree(self):
        # Отримуємо ID об'єктів у зіткненні
        collision_ids = set()
        try:
            from ventilation_company.project3d.collision_detection import CollisionDetector
            detector = CollisionDetector(self.project)
            detector.check_all()
            collision_ids = detector.get_colliding_ids()
        except Exception:
            pass

        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.project:
            return

        root = self.tree.insert("", tk.END, text=f"📁 {self.project.name}", values=("project",), open=True)

        arch_node = self.tree.insert(root, tk.END, text="🏛️ Архітектура", values=("arch",), open=True)
        for floor in self.project.arch_context.floors:
            floor_node = self.tree.insert(arch_node, tk.END,
                                          text=f"🏢 {floor.name} (рівень {floor.level:.0f} мм)",
                                          values=("floor", floor.id), open=True)
            for wall in floor.walls:
                self.tree.insert(floor_node, tk.END,
                                 text=f"🧱 {wall.name} ({wall.length:.0f} мм)",
                                 values=("wall", wall.id))
            for opening in floor.openings:
                self.tree.insert(floor_node, tk.END,
                                 text=f"🕳️ {opening.name} ({opening.width:.0f}×{opening.height:.0f})",
                                 values=("opening", opening.id))

        vent_node = self.tree.insert(root, tk.END, text="💨 Вентиляція", values=("vent",), open=True)
        for system in self.project.ventilation_systems:
            sys_node = self.tree.insert(vent_node, tk.END,
                                        text=f"🌬️ {system.name} ({system.system_type})",
                                        values=("system", system.id), open=True)
            for trunk in system.trunks:
                trunk_node = self.tree.insert(sys_node, tk.END,
                                              text=f"📏 {trunk.name} (L={trunk.total_length:.0f} мм)",
                                              values=("trunk", trunk.id), open=True)
                for seg in trunk.segments:
                    coll_mark = " ⚠️" if seg.id in collision_ids else ""
                    self.tree.insert(trunk_node, tk.END,
                                     text=f"➡️ Сегмент {seg.width:.0f}×{seg.height:.0f} L={seg.length:.0f} мм{coll_mark}",
                                     values=("segment", seg.id))
                for fitting in trunk.fittings:
                    coll_mark = " ⚠️" if fitting.id in collision_ids else ""
                    self.tree.insert(trunk_node, tk.END,
                                     text=f"🔀 {fitting.fitting_type}{coll_mark}",
                                     values=("fitting", fitting.id))
                for eq in trunk.equipment:
                    coll_mark = " ⚠️" if eq.id in collision_ids else ""
                    self.tree.insert(trunk_node, tk.END,
                                     text=f"⚙️ {eq.name}{coll_mark}",
                                     values=("equipment", eq.id))

        if self.project.drawing_files:
            draw_node = self.tree.insert(root, tk.END, text="📋 Креслення", values=("drawings",), open=True)
            for d in self.project.drawing_files:
                self.tree.insert(draw_node, tk.END,
                                 text=f"📄 {os.path.basename(d['path'])} ({d['type']})",
                                 values=("drawing", d.get("id", "")))

        self._update_info()

    def _update_info(self):
        if not self.project:
            self.info_label.config(text="Немає проєкту")
            return
        lines = [
            f"Назва: {self.project.name}",
            f"Клієнт: {self.project.client or '—'}",
            f"Поверхів: {len(self.project.arch_context.floors)}",
            f"Систем: {len(self.project.ventilation_systems)}",
            f"Довжина трас: {self.project.total_duct_length:.0f} мм",
            f"Площа металу: {self.project.total_metal_area:.2f} м²",
            f"Витрата: {self.project.total_air_flow:.0f} м³/год",
        ]
        self.info_label.config(text="\n".join(lines))

    def _on_tree_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values:
            return
        obj_type = values[0]
        obj_id = values[1] if len(values) > 1 else ""
        props = self._get_object_props(obj_type, obj_id)
        self.props_text.config(state=tk.NORMAL)
        self.props_text.delete("1.0", tk.END)
        self.props_text.insert(tk.END, props)
        self.props_text.config(state=tk.DISABLED)

    def _get_object_props(self, obj_type: str, obj_id: str) -> str:
        if obj_type == "project":
            return f"""Проєкт: {self.project.name}
Клієнт: {self.project.client}
Адреса: {self.project.address}
Створено: {self.project.created_at}
Оновлено: {self.project.updated_at}"""

        elif obj_type == "floor":
            for f in self.project.arch_context.floors:
                if f.id == obj_id:
                    return f"""Поверх: {f.name}
Рівень: {f.level:.0f} мм
Висота: {f.height:.0f} мм
Стін: {len(f.walls)}
Отворів: {len(f.openings)}"""

        elif obj_type == "wall":
            for fl in self.project.arch_context.floors:
                for w in fl.walls:
                    if w.id == obj_id:
                        return f"""Стіна: {w.name}
Довжина: {w.length:.0f} мм
Висота: {w.height:.0f} мм
Товщина: {w.thickness:.0f} мм
Матеріал: {w.material.value}
Несуча: {'Так' if w.is_load_bearing else 'Ні'}
Початок: ({w.start.x:.0f}, {w.start.y:.0f}, {w.start.z:.0f})
Кінець: ({w.end.x:.0f}, {w.end.y:.0f}, {w.end.z:.0f})"""

        elif obj_type == "system":
            for s in self.project.ventilation_systems:
                if s.id == obj_id:
                    return f"""Система: {s.name}
Тип: {s.system_type}
Витрата: {s.total_air_flow:.0f} м³/год
Тиск: {s.total_pressure:.0f} Па
Трас: {len(s.trunks)}
Заг. довжина: {s.total_duct_length:.0f} мм"""

        elif obj_type == "segment":
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    for seg in t.segments:
                        if seg.id == obj_id:
                            return f"""Сегмент: {seg.id}
Ширина: {seg.width:.0f} мм
Висота: {seg.height:.0f} мм
Довжина: {seg.length:.0f} мм
Форма: {seg.shape.value}
Тип: {seg.duct_type.value}
Матеріал: {seg.material}
Товщина: {seg.thickness:.1f} мм
Початок: ({seg.start.x:.0f}, {seg.start.y:.0f}, {seg.start.z:.0f})
Кінець: ({seg.end.x:.0f}, {seg.end.y:.0f}, {seg.end.z:.0f})"""

        elif obj_type == "fitting":
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    for fit in t.fittings:
                        if fit.id == obj_id:
                            return f"""Фасонний виріб: {fit.fitting_type}
Позиція: ({fit.position.x:.0f}, {fit.position.y:.0f}, {fit.position.z:.0f})
Вхід: {fit.width_in:.0f}×{fit.height_in:.0f} мм
Вихід: {fit.width_out:.0f}×{fit.height_out:.0f} мм
Кут: {fit.angle:.0f}°
Радіус: {fit.radius:.0f} мм"""

        elif obj_type == "equipment":
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    for eq in t.equipment:
                        if eq.id == obj_id:
                            return f"""Обладнання: {eq.name}
Розміри: {eq.width:.0f}×{eq.height:.0f}×{eq.length:.0f} мм
Витрата: {eq.air_flow:.0f} м³/год
Тиск: {eq.pressure:.0f} Па
Потужність: {eq.power:.1f} кВт
Позиція: ({eq.position.x:.0f}, {eq.position.y:.0f}, {eq.position.z:.0f})"""

        elif obj_type == "trunk":
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    if t.id == obj_id:
                        return f"""Трасса: {t.name}
Поверх: {t.floor}
Тип: {t.duct_type.value}
Витрата: {t.air_flow:.0f} м³/год
Сегментів: {len(t.segments)}
Фасонних: {len(t.fittings)}
Обладнання: {len(t.equipment)}
Заг. довжина: {t.total_length:.0f} мм
Площа: {t.total_area:.2f} м²"""

        return "Виберіть елемент для перегляду властивостей"

    def _on_tree_double_click(self, event=None):
        self._edit_selected()

    def _on_tree_right_click(self, event=None):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            values = self.tree.item(item, "values")
            if not values:
                return
            obj_type = values[0]
            menu = tk.Menu(self.frame, tearoff=0)

            if obj_type not in ("project", "arch", "vent", "drawings"):
                menu.add_command(label="📝 Редагувати", command=self._edit_selected)
                menu.add_command(label="❌ Видалити", command=self._delete_selected)
                menu.add_separator()

            if obj_type in ("trunk", "system"):
                menu.add_command(label="➕ Додати сегмент", command=self._add_segment)
                menu.add_command(label="⚙️ Додати обладнання", command=self._add_equipment)
                menu.add_command(label="🔀 Додати фасонний виріб", command=self._add_fitting)

            if obj_type == "floor":
                menu.add_command(label="🧱 Додати стіну", command=self._add_wall)

            if obj_type == "vent":
                menu.add_command(label="🌬️ Додати систему", command=self._add_system)

            if obj_type == "system":
                menu.add_command(label="📏 Додати трасу", command=self._add_trunk)

            menu.post(event.x_root, event.y_root)

    def _check_collisions(self):
        """Перевірити зіткнення та показати звіт."""
        from ventilation_company.project3d.collision_detection import CollisionDetector

        detector = CollisionDetector(self.project)
        collisions = detector.check_all()

        if not collisions:
            messagebox.showinfo("Перевірка зіткнень", "✅ Зіткнень не виявлено!")
            self.status.config(text="Зіткнень не виявлено")
            self._refresh_tree()
            self._refresh_previews()
            return

        report = [f"⚠️ Виявлено {len(collisions)} зіткнень:\n"]
        for i, col in enumerate(collisions[:20], 1):
            report.append(f"{i}. {col.message}")
            if col.position:
                report.append(f"   📍 ({col.position.x:.0f}, {col.position.y:.0f}, {col.position.z:.0f}) мм")

        if len(collisions) > 20:
            report.append(f"\n... та ще {len(collisions) - 20} зіткнень")

        dialog = tk.Toplevel(self.frame)
        dialog.title("⚠️ Зіткнення")
        dialog.geometry("550x400")
        dialog.transient(self.frame)

        text = tk.Text(dialog, wrap=tk.WORD, font=("Consolas", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert("1.0", "\n".join(report))
        text.config(state=tk.DISABLED)

        ttk.Button(dialog, text="OK", command=dialog.destroy).pack(pady=5)

        self._refresh_tree()
        self._refresh_previews()
        self.status.config(text=f"⚠️ Виявлено {len(collisions)} зіткнень")

    def _generate_proposal(self):
        """Згенерувати Комерційну Пропозицію (КП) у PDF."""
        from ventilation_company.proposal_generator import generate_proposal
        from tkinter import filedialog

        # Збираємо дані проєкту
        project_data = {
            "name": self.project.name,
            "project_number": getattr(self.project, "project_number", ""),
            "client": self.project.client,
            "address": getattr(self.project, "address", ""),
            "proposal_number": f"KP-{datetime.now().strftime("%Y%m%d")}-001",
            "delivery_days": 14,
            "installation_days": 7,
            "warranty_months": 24,
            "payment_terms": "50% аванс, 50% після монтажу",
            "notes": self.project.notes,
        }

        # Збираємо позиції з усіх систем
        items = []
        for system in self.project.ventilation_systems:
            for trunk in system.trunks:
                for seg in trunk.segments:
                    items.append({
                        "name": f"Повітропровід {seg.width:.0f}×{seg.height:.0f} мм ({seg.duct_type.value})",
                        "quantity": seg.length / 1000,  # у метрах
                        "unit": "м.п.",
                        "price": 0,  # ціна буде з прайсу
                    })
                for eq in trunk.equipment:
                    items.append({
                        "name": eq.name or "Обладнання",
                        "quantity": 1,
                        "unit": "шт",
                        "price": 0,
                    })
                for fit in trunk.fittings:
                    items.append({
                        "name": f"{fit.fitting_type} {fit.width_in:.0f}×{fit.height_in:.0f} мм",
                        "quantity": 1,
                        "unit": "шт",
                        "price": 0,
                    })

        # Діалог збереження
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF документ", "*.pdf"), ("Всі файли", "*.*")],
            title="Зберегти Комерційну Пропозицію",
            initialfile=f"KP_{self.project.name.replace(' ', '_')}.pdf",
        )
        if not filepath:
            return

        try:
            generate_proposal(project_data, items, filepath)
            self.status.config(text=f"📄 КП збережено: {filepath}")
            messagebox.showinfo("Успіх", f"Комерційну Пропозицію збережено:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося згенерувати КП:\n{e}")

    def _new_project(self):
        if self._modified:
            if messagebox.askyesno("Зберегти?", "Проєкт змінено. Зберегти перед створенням нового?"):
                self._save_project()
        self.project = VentProject()
        self._current_file = ""
        self._modified = False
        self._refresh_tree()
        self._refresh_previews()
        self.status.config(text="Створено новий проєкт")

    def _save_project(self):
        if not self._current_file:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".ventproj",
                filetypes=(("VentProject", "*.ventproj"), ("Всі файли", "*.*")),
                title="Зберегти проєкт",
            )
            if not filepath:
                return
            self._current_file = filepath
        self.project.save(self._current_file)
        self._modified = False
        self.status.config(text=f"Збережено: {self._current_file}")

    def _load_project(self):
        filepath = filedialog.askopenfilename(
            filetypes=(("VentProject", "*.ventproj"), ("Всі файли", "*.*")),
            title="Відкрити проєкт",
        )
        if not filepath:
            return
        try:
            self.project = VentProject.load(filepath)
            self._current_file = filepath
            self._modified = False
            self._refresh_tree()
            self._refresh_previews()
            self.status.config(text=f"Відкрито: {filepath}")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося відкрити проєкт:\n{e}")

    def _import_file(self, format_hint: str):
        formats = ProjectConverter.get_supported_import_formats()
        filetypes = []
        for name, pattern in formats:
            filetypes.append((name, pattern))
        filetypes.append(("Всі файли", "*.*"))

        filepath = filedialog.askopenfilename(filetypes=filetypes, title="Імпорт")
        if not filepath:
            return
        try:
            imported = ProjectConverter.import_file(filepath)
            if not self.project or not self.project.name or self.project.name == "Новий проєкт":
                self.project = imported
            else:
                self.project.arch_context.floors.extend(imported.arch_context.floors)
                self.project.ventilation_systems.extend(imported.ventilation_systems)
                self.project.drawing_files.extend(imported.drawing_files)
                if imported.notes:
                    self.project.notes += "\n" + imported.notes
            self._modified = True
            self._refresh_tree()
            self._refresh_previews()
            self.status.config(text=f"Імпортовано: {os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("Помилка імпорту", str(e))

    def _export_file(self, format_hint: str):
        formats = ProjectConverter.get_supported_export_formats()
        filetypes = []
        for name, pattern in formats:
            filetypes.append((name, pattern))
        ext_map = {"ifc": ".ifc", "dxf": ".dxf", "step": ".step", "fcstd": ".fcstd", "ventproj": ".ventproj"}
        default_ext = ext_map.get(format_hint, ".ventproj")
        filepath = filedialog.asksaveasfilename(
            defaultextension=default_ext, filetypes=filetypes, title="Експорт"
        )
        if not filepath:
            return
        try:
            ProjectConverter.export_file(self.project, filepath)
            self.status.config(text=f"Експортовано: {filepath}")
            messagebox.showinfo("Успіх", f"Проєкт експортовано:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Помилка експорту", str(e))

    def _export_image_2d(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=(("PNG", "*.png"),), title="Зберегти план 2D")
        if filepath:
            self.preview_2d.export_image(filepath)
            self.status.config(text=f"Зображення 2D: {filepath}")

    def _export_image_3d(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=(("PNG", "*.png"),), title="Зберегти 3D-вигляд")
        if filepath:
            self.preview_3d.export_image(filepath)
            self.status.config(text=f"Зображення 3D: {filepath}")

    def _edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Інформація", "Виберіть елемент для редагування")
            return
        values = self.tree.item(sel[0], "values")
        if not values or len(values) < 2:
            return
        obj_type, obj_id = values[0], values[1]

        if obj_type == "segment":
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    for seg in t.segments:
                        if seg.id == obj_id:
                            data = EditSegmentDialog(self.frame, seg).show()
                            if data:
                                seg.start = data["start"]
                                seg.end = data["end"]
                                seg.width = data["width"]
                                seg.height = data["height"]
                                seg.length = data["length"]
                                seg.shape = data["shape"]
                                seg.duct_type = data["duct_type"]
                                seg.material = data["material"]
                                seg.thickness = data["thickness"]
                                seg.insulation = data["insulation"]
                                seg.notes = data["notes"]
                                self._modified = True
                                self._refresh_tree()
                                self._refresh_previews()
                                return

        elif obj_type == "equipment":
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    for eq in t.equipment:
                        if eq.id == obj_id:
                            data = EditEquipmentDialog(self.frame, eq).show()
                            if data:
                                eq.name = data["name"]
                                eq.position = data["position"]
                                eq.width = data["width"]
                                eq.height = data["height"]
                                eq.length = data["length"]
                                eq.air_flow = data["air_flow"]
                                eq.pressure = data["pressure"]
                                eq.power = data["power"]
                                eq.notes = data["notes"]
                                self._modified = True
                                self._refresh_tree()
                                self._refresh_previews()
                                return

        elif obj_type == "wall":
            for fl in self.project.arch_context.floors:
                for w in fl.walls:
                    if w.id == obj_id:
                        data = EditWallDialog(self.frame, w).show()
                        if data:
                            w.name = data["name"]
                            w.start = data["start"]
                            w.end = data["end"]
                            w.height = data["height"]
                            w.thickness = data["thickness"]
                            w.material = data["material"]
                            w.is_load_bearing = data["is_load_bearing"]
                            w.notes = data["notes"]
                            self._modified = True
                            self._refresh_tree()
                            self._refresh_previews()
                            return

        elif obj_type == "fitting":
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    for fit in t.fittings:
                        if fit.id == obj_id:
                            data = EditFittingDialog(self.frame, fit).show()
                            if data:
                                fit.fitting_type = data["fitting_type"]
                                fit.position = data["position"]
                                fit.width_in = data["width_in"]
                                fit.height_in = data["height_in"]
                                fit.width_out = data["width_out"]
                                fit.height_out = data["height_out"]
                                fit.angle = data["angle"]
                                fit.radius = data["radius"]
                                fit.material = data["material"]
                                fit.thickness = data["thickness"]
                                fit.notes = data["notes"]
                                self._modified = True
                                self._refresh_tree()
                                self._refresh_previews()
                                return

        elif obj_type == "system":
            for s in self.project.ventilation_systems:
                if s.id == obj_id:
                    data = EditSystemDialog(self.frame, s).show()
                    if data:
                        s.name = data["name"]
                        s.system_type = data["system_type"]
                        s.total_air_flow = data["total_air_flow"]
                        s.total_pressure = data["total_pressure"]
                        s.notes = data["notes"]
                        self._modified = True
                        self._refresh_tree()
                        self._refresh_previews()
                        return

        elif obj_type == "trunk":
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    if t.id == obj_id:
                        data = EditTrunkDialog(self.frame, t).show()
                        if data:
                            t.name = data["name"]
                            t.floor = data["floor"]
                            t.duct_type = data["duct_type"]
                            t.air_flow = data["air_flow"]
                            t.notes = data["notes"]
                            self._modified = True
                            self._refresh_tree()
                        self._refresh_previews()
                        return

        else:
            messagebox.showinfo("Інформація", f"Редагування для типу '{obj_type}' буде додано пізніше.")

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values or len(values) < 2:
            return
        obj_type, obj_id = values[0], values[1]
        if obj_type in ("project", "arch", "vent", "drawings"):
            messagebox.showwarning("Увага", "Неможливо видалити кореневий вузол")
            return

        if not messagebox.askyesno("Підтвердження", f"Видалити {obj_type} '{obj_id}'?"):
            return

        deleted = False

        if obj_type == "wall":
            for fl in self.project.arch_context.floors:
                for i, w in enumerate(fl.walls):
                    if w.id == obj_id:
                        fl.walls.pop(i)
                        deleted = True
                        break
                if deleted:
                    break

        elif obj_type == "floor":
            for i, fl in enumerate(self.project.arch_context.floors):
                if fl.id == obj_id:
                    self.project.arch_context.floors.pop(i)
                    deleted = True
                    break

        elif obj_type == "opening":
            for fl in self.project.arch_context.floors:
                for i, o in enumerate(fl.openings):
                    if o.id == obj_id:
                        fl.openings.pop(i)
                        deleted = True
                        break
                if deleted:
                    break

        elif obj_type == "segment":
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    for i, seg in enumerate(t.segments):
                        if seg.id == obj_id:
                            t.segments.pop(i)
                            deleted = True
                            break
                    if deleted:
                        break
                if deleted:
                    break

        elif obj_type == "fitting":
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    for i, fit in enumerate(t.fittings):
                        if fit.id == obj_id:
                            t.fittings.pop(i)
                            deleted = True
                            break
                    if deleted:
                        break
                if deleted:
                    break

        elif obj_type == "equipment":
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    for i, eq in enumerate(t.equipment):
                        if eq.id == obj_id:
                            t.equipment.pop(i)
                            deleted = True
                            break
                    if deleted:
                        break
                if deleted:
                    break

        elif obj_type == "trunk":
            for s in self.project.ventilation_systems:
                for i, t in enumerate(s.trunks):
                    if t.id == obj_id:
                        s.trunks.pop(i)
                        deleted = True
                        break
                if deleted:
                    break

        elif obj_type == "system":
            for i, s in enumerate(self.project.ventilation_systems):
                if s.id == obj_id:
                    self.project.ventilation_systems.pop(i)
                    deleted = True
                    break

        elif obj_type == "drawing":
            deleted = self.project.remove_drawing(obj_id)

        if deleted:
            self._modified = True
            self._refresh_tree()
            self._refresh_previews()
            self.status.config(text=f"Видалено: {obj_type} {obj_id}")
        else:
            messagebox.showwarning("Увага", f"Не вдалося знайти {obj_type} з ID {obj_id}")

    def _get_selected_parent_id(self, parent_types: tuple) -> tuple:
        sel = self.tree.selection()
        if not sel:
            return None, None
        values = self.tree.item(sel[0], "values")
        if not values:
            return None, None
        obj_type = values[0]
        obj_id = values[1] if len(values) > 1 else ""
        if obj_type in parent_types:
            return obj_type, obj_id
        parent = self.tree.parent(sel[0])
        if parent:
            p_values = self.tree.item(parent, "values")
            if p_values and p_values[0] in parent_types:
                return p_values[0], p_values[1] if len(p_values) > 1 else ""
        return None, None

    def _select_parent_dialog(self, title: str, items: list, display_key: str = "name", id_key: str = "id") -> str:
        if not items:
            messagebox.showinfo("Інформація", "Немає доступних елементів.")
            return None
        dialog = tk.Toplevel(self.frame)
        dialog.title(title)
        dialog.geometry("350x200")
        dialog.transient(self.frame)
        dialog.grab_set()

        ttk.Label(dialog, text=title + ":").pack(pady=5)
        var = tk.StringVar()
        combo = ttk.Combobox(dialog, textvariable=var, state="readonly", width=40)
        display_list = []
        id_map = {}
        for item in items:
            if isinstance(item, dict):
                d = item.get(display_key, str(item))
                i = item.get(id_key, str(item))
            else:
                d = getattr(item, display_key, str(item))
                i = getattr(item, id_key, str(item))
            display_list.append(f"{d} [{i}]")
            id_map[display_list[-1]] = i
        combo["values"] = display_list
        if display_list:
            combo.set(display_list[0])
        combo.pack(padx=10, pady=5)

        result = [None]

        def on_ok():
            result[0] = id_map.get(combo.get())
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        ttk.Button(dialog, text="OK", command=on_ok).pack(pady=5)
        ttk.Button(dialog, text="Скасувати", command=on_cancel).pack()

        self.frame.wait_window(dialog)
        return result[0]

    def _get_all_trunks(self):
        trunks = []
        for s in self.project.ventilation_systems:
            for t in s.trunks:
                trunks.append(t)
        return trunks

    def _get_all_systems(self):
        return self.project.ventilation_systems

    def _get_all_floors(self):
        return self.project.arch_context.floors

    def _add_floor(self):
        from ventilation_company.project3d.arch_context import Floor
        level = 0
        if self.project.arch_context.floors:
            level = max(f.level for f in self.project.arch_context.floors) + 3000
        floor = Floor(name=f"Поверх {len(self.project.arch_context.floors) + 1}", level=level)
        self.project.arch_context.floors.append(floor)
        self._modified = True
        self._refresh_tree()
        self._refresh_previews()
        self.status.config(text=f"Додано поверх: {floor.name}")

    def _add_wall(self):
        ptype, pid = self._get_selected_parent_id(("floor",))
        if not pid:
            pid = self._select_parent_dialog("Виберіть поверх", self._get_all_floors(), "name", "id")
        if not pid:
            return
        for fl in self.project.arch_context.floors:
            if fl.id == pid:
                data = AddWallDialog(self.frame).show()
                if data:
                    wall = Wall(
                        id=data["id"], name=data["name"],
                        start=data["start"], end=data["end"],
                        height=data["height"], thickness=data["thickness"],
                        material=data["material"], is_load_bearing=data["is_load_bearing"],
                        notes=data["notes"],
                    )
                    fl.walls.append(wall)
                    self._modified = True
                    self._refresh_tree()
                    self._refresh_previews()
                    self.status.config(text=f"Додано стіну: {wall.name}")
                    return

    def _add_system(self):
        data = AddSystemDialog(self.frame).show()
        if data:
            system = VentilationSystem(
                id=data["id"], name=data["name"],
                system_type=data["system_type"],
                total_air_flow=data["total_air_flow"],
                total_pressure=data["total_pressure"],
                notes=data["notes"],
            )
            self.project.ventilation_systems.append(system)
            self._modified = True
            self._refresh_tree()
            self._refresh_previews()
            self.status.config(text=f"Додано систему: {system.name}")

    def _add_trunk(self):
        ptype, pid = self._get_selected_parent_id(("system",))
        if not pid:
            pid = self._select_parent_dialog("Виберіть систему", self._get_all_systems(), "name", "id")
        if not pid:
            return
        for s in self.project.ventilation_systems:
            if s.id == pid:
                data = AddTrunkDialog(self.frame).show()
                if data:
                    trunk = VentilationTrunk(
                        id=data["id"], name=data["name"],
                        floor=data["floor"], duct_type=data["duct_type"],
                        air_flow=data["air_flow"], notes=data["notes"],
                    )
                    s.trunks.append(trunk)
                    self._modified = True
                    self._refresh_tree()
                    self._refresh_previews()
                    self.status.config(text=f"Додано трасу: {trunk.name}")
                    return

    def _add_segment(self):
        ptype, pid = self._get_selected_parent_id(("trunk",))
        if not pid:
            pid = self._select_parent_dialog("Виберіть трасу", self._get_all_trunks(), "name", "id")
        if not pid:
            return
        default_start = Point3D(0, 0, 2500)
        for s in self.project.ventilation_systems:
            for t in s.trunks:
                if t.id == pid and t.segments:
                    default_start = t.segments[-1].end
        data = AddSegmentDialog(self.frame, default_start).show()
        if data:
            seg = DuctSegment(
                id=data["id"], start=data["start"], end=data["end"],
                width=data["width"], height=data["height"], length=data["length"],
                shape=data["shape"], duct_type=data["duct_type"],
                material=data["material"], thickness=data["thickness"],
                insulation=data["insulation"], notes=data["notes"],
            )
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    if t.id == pid:
                        t.segments.append(seg)
                        self._modified = True
                        self._refresh_tree()
                        self._refresh_previews()
                        self.status.config(text=f"Додано сегмент: {seg.id}")
                        return

    def _add_fitting(self):
        ptype, pid = self._get_selected_parent_id(("trunk",))
        if not pid:
            pid = self._select_parent_dialog("Виберіть трасу", self._get_all_trunks(), "name", "id")
        if not pid:
            return
        default_pos = Point3D(0, 0, 2500)
        for s in self.project.ventilation_systems:
            for t in s.trunks:
                if t.id == pid and t.segments:
                    default_pos = t.segments[-1].end
        data = AddFittingDialog(self.frame, default_pos).show()
        if data:
            fit = Fitting(
                id=data["id"], fitting_type=data["fitting_type"],
                position=data["position"], width_in=data["width_in"],
                height_in=data["height_in"], width_out=data["width_out"],
                height_out=data["height_out"], angle=data["angle"],
                radius=data["radius"], material=data["material"],
                thickness=data["thickness"], notes=data["notes"],
            )
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    if t.id == pid:
                        t.fittings.append(fit)
                        self._modified = True
                        self._refresh_tree()
                        self._refresh_previews()
                        self.status.config(text=f"Додано фасонний виріб: {fit.fitting_type}")
                        return

    def _add_equipment(self):
        ptype, pid = self._get_selected_parent_id(("trunk",))
        if not pid:
            pid = self._select_parent_dialog("Виберіть трасу", self._get_all_trunks(), "name", "id")
        if not pid:
            return
        default_pos = Point3D(0, 0, 2500)
        for s in self.project.ventilation_systems:
            for t in s.trunks:
                if t.id == pid and t.segments:
                    default_pos = t.segments[0].start
        data = AddEquipmentDialog(self.frame, default_pos).show()
        if data:
            eq = Equipment(
                id=data["id"], name=data["name"],
                position=data["position"], width=data["width"],
                height=data["height"], length=data["length"],
                air_flow=data["air_flow"], pressure=data["pressure"],
                power=data["power"], notes=data["notes"],
            )
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    if t.id == pid:
                        t.equipment.append(eq)
                        self._modified = True
                        self._refresh_tree()
                        self._refresh_previews()
                        self.status.config(text=f"Додано обладнання: {eq.name}")
                        return

    def _refresh_previews(self):
        self.preview_2d.set_project(self.project)
        self.preview_3d.set_project(self.project)

    def _load_demo_if_empty(self):
        if not self.project.ventilation_systems and not self.project.arch_context.floors:
            self.project.create_sample_project()
            self._refresh_tree()
            self._refresh_previews()
            self.status.config(text="Завантажено демо-проєкт")
