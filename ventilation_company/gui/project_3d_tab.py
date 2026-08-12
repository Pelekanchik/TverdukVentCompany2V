"""Вкладка "Проєкти 3D / Креслення" — заміна старої вкладки FreeCAD.

Функціонал:
  • Імпорт: IFC (Revit), DXF/DWG (AutoCAD), STEP (Solidworks), FCStd (FreeCAD), .ventproj
  • Експорт: IFC, DXF, STEP, FCStd, .ventproj
  • 2D-перегляд планів поверхів з накладанням вентиляції
  • 3D-перегляд системи вентиляції в архітектурному контексті
  • Редагування: зміна розмірів, переміщення, видалення
  • Дерево проєкту: Система → Траса → Сегмент/Виріб
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ventilation_company.project3d import (
    VentProject, ProjectConverter,
    Project3DPreview, Project2DPreview,
    VentilationSystem, VentilationTrunk, DuctSegment, Fitting, Equipment, Point3D,
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

    # ═══════════════════════════════════════════════════════════════
    # BUILD UI
    # ═══════════════════════════════════════════════════════════════

    def _build_ui(self):
        # ── Top toolbar ──
        toolbar = ttk.Frame(self.frame, padding=5)
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="🏗️ Проєкти 3D / Креслення", font=("Arial", 14, "bold")).pack(side=tk.LEFT)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Button(toolbar, text="📂 Новий проєкт", command=self._new_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="💾 Зберегти", command=self._save_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📁 Відкрити", command=self._load_project).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Імпорт
        self.import_btn = ttk.Menubutton(toolbar, text="📥 Імпорт", direction="below")
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
        self.export_btn = ttk.Menubutton(toolbar, text="📤 Експорт", direction="below")
        self.export_btn.pack(side=tk.LEFT, padx=2)
        export_menu = tk.Menu(self.export_btn, tearoff=0)
        export_menu.add_command(label="🏗️ У Revit (IFC)", command=lambda: self._export_file("ifc"))
        export_menu.add_command(label="📐 У AutoCAD (DXF)", command=lambda: self._export_file("dxf"))
        export_menu.add_command(label="🔧 У Solidworks (STEP)", command=lambda: self._export_file("step"))
        export_menu.add_command(label="🆓 У FreeCAD (FCStd)", command=lambda: self._export_file("fcstd"))
        export_menu.add_separator()
        export_menu.add_command(label="📋 У VentProject", command=lambda: self._export_file("ventproj"))
        export_menu.add_separator()
        export_menu.add_command(label="🖼️ Зберегти зображення 2D", command=self._export_image_2d)
        export_menu.add_command(label="🖼️ Зберегти зображення 3D", command=self._export_image_3d)
        self.export_btn["menu"] = export_menu

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Button(toolbar, text="📝 Редагувати", command=self._edit_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="❌ Видалити", command=self._delete_selected).pack(side=tk.LEFT, padx=2)

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
        info_frame = ttk.LabelFrame(left, text="Інформація про проєкт", padding=5)
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        self.info_label = ttk.Label(info_frame, text="Новий проєкт", foreground="#666")
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

    # ═══════════════════════════════════════════════════════════════
    # TREE & PROJECT MANAGEMENT
    # ═══════════════════════════════════════════════════════════════

    def _refresh_tree(self):
        """Оновити дерево проєкту."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.project:
            return

        root = self.tree.insert("", tk.END, text=f"📁 {self.project.name}", values=("project",))

        # Архітектура
        arch_node = self.tree.insert(root, tk.END, text="🏛️ Архітектура", values=("arch",))
        for floor in self.project.arch_context.floors:
            floor_node = self.tree.insert(arch_node, tk.END,
                                          text=f"🏢 {floor.name} (рівень {floor.level:.0f} мм)",
                                          values=("floor", floor.id))
            for wall in floor.walls:
                self.tree.insert(floor_node, tk.END,
                                 text=f"🧱 {wall.name} ({wall.length:.0f} мм)",
                                 values=("wall", wall.id))
            for opening in floor.openings:
                self.tree.insert(floor_node, tk.END,
                                 text=f"🕳️ {opening.name} ({opening.width:.0f}×{opening.height:.0f})",
                                 values=("opening", opening.id))

        # Вентиляція
        vent_node = self.tree.insert(root, tk.END, text="💨 Вентиляція", values=("vent",))
        for system in self.project.ventilation_systems:
            sys_node = self.tree.insert(vent_node, tk.END,
                                        text=f"🌬️ {system.name} ({system.system_type})",
                                        values=("system", system.id))
            for trunk in system.trunks:
                trunk_node = self.tree.insert(sys_node, tk.END,
                                              text=f"📏 {trunk.name} (L={trunk.total_length:.0f} мм)",
                                              values=("trunk", trunk.id))
                for seg in trunk.segments:
                    self.tree.insert(trunk_node, tk.END,
                                     text=f"➡️ Сегмент {seg.width:.0f}×{seg.height:.0f}  L={seg.length:.0f} мм",
                                     values=("segment", seg.id))
                for fitting in trunk.fittings:
                    self.tree.insert(trunk_node, tk.END,
                                     text=f"🔀 {fitting.fitting_type}",
                                     values=("fitting", fitting.id))
                for eq in trunk.equipment:
                    self.tree.insert(trunk_node, tk.END,
                                     text=f"⚙️ {eq.name}",
                                     values=("equipment", eq.id))

        # Креслення
        if self.project.drawing_files:
            draw_node = self.tree.insert(root, tk.END, text="📋 Креслення", values=("drawings",))
            for d in self.project.drawing_files:
                self.tree.insert(draw_node, tk.END,
                                 text=f"📄 {os.path.basename(d['path'])} ({d['type']})",
                                 values=("drawing", d.get("id", "")))

        self._update_info()

    def _update_info(self):
        """Оновити інформаційну панель."""
        if not self.project:
            self.info_label.config(text="Немає проєкту")
            return

        lines = [
            f"Назва: {self.project.name}",
            f"Клієнт: {self.project.client or '—'}",
            f"Поверхів: {len(self.project.arch_context.floors)}",
            f"Систем вентиляції: {len(self.project.ventilation_systems)}",
            f"Загальна довжина трас: {self.project.total_duct_length:.0f} мм",
            f"Площа металу: {self.project.total_metal_area:.2f} м²",
            f"Витрата повітря: {self.project.total_air_flow:.0f} м³/год",
        ]
        if self.project.notes:
            lines.append(f"Примітки: {self.project.notes}")
        self.info_label.config(text="\n".join(lines))

    def _on_tree_select(self, event=None):
        """Вибір елемента в дереві."""
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        values = self.tree.item(item, "values")
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
        """Отримати властивості об'єкта для відображення."""
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
            for f in self.project.arch_context.floors:
                for w in f.walls:
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
Витрата повітря: {s.total_air_flow:.0f} м³/год
Тиск: {s.total_pressure:.0f} Па
Трас: {len(s.trunks)}
Загальна довжина: {s.total_duct_length:.0f} мм"""

        elif obj_type == "segment":
            for s in self.project.ventilation_systems:
                for t in s.trunks:
                    for seg in t.segments:
                        if seg.id == obj_id:
                            return f"""Сегмент повітропроводу
Ширина: {seg.width:.0f} мм
Висота: {seg.height:.0f} мм
Довжина: {seg.length:.0f} мм
Форма: {seg.shape.value}
Тип: {seg.duct_type.value}
Матеріал: {seg.material}
Товщина: {seg.thickness:.1f} мм
Початок: ({seg.start.x:.0f}, {seg.start.y:.0f}, {seg.start.z:.0f})
Кінець: ({seg.end.x:.0f}, {seg.end.y:.0f}, {seg.end.z:.0f})"""

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

        return "Виберіть елемент для перегляду властивостей"

    def _on_tree_double_click(self, event=None):
        self._edit_selected()

    def _on_tree_right_click(self, event=None):
        """Контекстне меню дерева."""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            menu = tk.Menu(self.frame, tearoff=0)
            menu.add_command(label="Редагувати", command=self._edit_selected)
            menu.add_command(label="Видалити", command=self._delete_selected)
            menu.add_separator()
            menu.add_command(label="Додати сегмент", command=self._add_segment)
            menu.add_command(label="Додати обладнання", command=self._add_equipment)
            menu.post(event.x_root, event.y_root)

    # ═══════════════════════════════════════════════════════════════
    # FILE OPERATIONS
    # ═══════════════════════════════════════════════════════════════

    def _new_project(self):
        if self._modified:
            if not messagebox.askyesno("Зберегти?", "Проєкт змінено. Зберегти перед створенням нового?"):
                pass
            else:
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
                filetypes=[("VentProject", "*.ventproj"), ("Всі файли", "*.*")],
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
            filetypes=[("VentProject", "*.ventproj"), ("Всі файли", "*.*")],
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
        """Імпортувати файл зовнішньої програми."""
        formats = ProjectConverter.get_supported_import_formats()
        filetypes = []
        for name, pattern in formats:
            filetypes.append((name, pattern))
        filetypes.append(("Всі файли", "*.*"))

        filepath = filedialog.askopenfilename(
            filetypes=filetypes,
            title=f"Імпорт з {format_hint.upper()}",
        )
        if not filepath:
            return

        try:
            imported = ProjectConverter.import_file(filepath)
            # Зливаємо з поточним проєктом
            if not self.project or not self.project.name or self.project.name == "Новий проєкт":
                self.project = imported
            else:
                # Додаємо архітектуру та системи
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
        """Експортувати проєкт у зовнішню програму."""
        formats = ProjectConverter.get_supported_export_formats()
        filetypes = []
        for name, pattern in formats:
            filetypes.append((name, pattern))

        # Визначаємо розширення за замовчуванням
        ext_map = {"ifc": ".ifc", "dxf": ".dxf", "step": ".step", "fcstd": ".fcstd", "ventproj": ".ventproj"}
        default_ext = ext_map.get(format_hint, ".ventproj")

        filepath = filedialog.asksaveasfilename(
            defaultextension=default_ext,
            filetypes=filetypes,
            title=f"Експорт у {format_hint.upper()}",
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
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("Всі файли", "*.*")],
            title="Зберегти план 2D",
        )
        if filepath:
            self.preview_2d.export_image(filepath)
            self.status.config(text=f"Зображення 2D збережено: {filepath}")

    def _export_image_3d(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("Всі файли", "*.*")],
            title="Зберегти 3D-вигляд",
        )
        if filepath:
            self.preview_3d.export_image(filepath)
            self.status.config(text=f"Зображення 3D збережено: {filepath}")

    # ═══════════════════════════════════════════════════════════════
    # EDITING
    # ═══════════════════════════════════════════════════════════════

    def _edit_selected(self):
        """Редагувати вибраний елемент."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Інформація", "Виберіть елемент для редагування")
            return
        values = self.tree.item(sel[0], "values")
        if not values or len(values) < 2:
            return

        obj_type, obj_id = values[0], values[1]

        # Відкриваємо діалог редагування
        dialog = tk.Toplevel(self.frame)
        dialog.title(f"Редагування: {obj_type}")
        dialog.geometry("400x500")
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(dialog, text=f"Тип: {obj_type}", font=("Arial", 10, "bold")).pack(pady=5)
        ttk.Label(dialog, text=f"ID: {obj_id}", foreground="#666").pack()

        # TODO: динамічні поля залежно від типу
        ttk.Label(dialog, text="Редагування буде реалізовано у наступній версії.",
                  foreground="#999", wraplength=350).pack(pady=20)

        ttk.Button(dialog, text="Закрити", command=dialog.destroy).pack(pady=10)

    def _delete_selected(self):
        """Видалити вибраний елемент."""
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

        if messagebox.askyesno("Підтвердження", f"Видалити {obj_type} {obj_id}?"):
            # TODO: реалізувати видалення з моделі
            self._modified = True
            self._refresh_tree()
            self._refresh_previews()

    def _add_segment(self):
        """Додати новий сегмент повітропроводу."""
        messagebox.showinfo("Інформація", "Додавання сегментів буде реалізовано у наступній версії.")

    def _add_equipment(self):
        """Додати нове обладнання."""
        messagebox.showinfo("Інформація", "Додавання обладнання буде реалізовано у наступній версії.")

    # ═══════════════════════════════════════════════════════════════
    # PREVIEW
    # ═══════════════════════════════════════════════════════════════

    def _refresh_previews(self):
        """Оновити обидва перегляди."""
        self.preview_2d.set_project(self.project)
        self.preview_3d.set_project(self.project)

    def _load_demo_if_empty(self):
        """Завантажити демо-проєкт, якщо проєкт порожній."""
        if not self.project.ventilation_systems and not self.project.arch_context.floors:
            self.project.create_sample_project()
            self._refresh_tree()
            self._refresh_previews()
            self.status.config(text="Завантажено демо-проєкт")
