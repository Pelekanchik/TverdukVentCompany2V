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

    def set_project(self, project_data: dict):
        """Завантажити дані проєкту (заглушка для сумісності)."""
        pass

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


        # Рядок 2: креслення, зіткнення, редагування, видалення
        tbar2 = ttk.Frame(toolbar_wrap)
        tbar2.pack(fill=tk.X, pady=(3, 0))

        ttk.Button(tbar2, text="⚠️ Перевірити зіткнення", command=self._check_collisions).pack(side=tk.LEFT, padx=2)
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
        pass
    def _on_tree_right_click(self, event=None):
        pass
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

    def _refresh_previews(self):
        self.preview_2d.set_project(self.project)
        self.preview_3d.set_project(self.project)

    def _load_demo_if_empty(self):
        if not self.project.ventilation_systems and not self.project.arch_context.floors:
            self.project.create_sample_project()
            self._refresh_tree()
            self._refresh_previews()
            self.status.config(text="Завантажено демо-проєкт")
