"""Нова вкладка 'Проекти 3D' — професійний CAD-редактор.

ЕТАП 7  — Інтеграція з VentProject (імпорт виробів)
ЕТАП 8  — 3D-вигляд (рендерер 3D сцени)
ЕТАП 8a — Панель 'Деталі з проєкту' + snap до endpoint
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List, Dict, Any, Tuple
import math

from ventilation_company.project3d_editor.scene.scene_graph import SceneGraph
from ventilation_company.project3d_editor.canvas2d.renderer import Canvas2DRenderer
from ventilation_company.project3d_editor.tools.tool_manager import ToolManager
from ventilation_company.project3d_editor.ui.toolbar import Toolbar
from ventilation_company.project3d_editor.ui.property_panel import PropertyPanel
from ventilation_company.project3d_editor.ui.layer_panel import LayerPanel
from ventilation_company.project3d_editor.ui.tool_settings_panel import ToolSettingsPanel

try:
    from ventilation_company.project3d_editor.renderer3d.scene_renderer_3d import Scene3DRenderer
    RENDERER3D_AVAILABLE = True
except ImportError:
    RENDERER3D_AVAILABLE = False


class Project3DTabNew(ttk.Frame):
    """Нова вкладка Проекти 3D — повноцінний CAD-редактор."""

    def __init__(self, parent: tk.Widget, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.scene = SceneGraph()
        self._project_details: List[Dict[str, Any]] = []
        self._build_ui()
        self.tool_manager = ToolManager(self.renderer, self.scene)
        self.toolbar = Toolbar(self.top_frame, self.tool_manager,
                               on_tool_change=self._on_tool_change)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        self.tool_settings = ToolSettingsPanel(self.top_frame)
        self.tool_settings.pack(side=tk.TOP, fill=tk.X, padx=2, pady=1)
        self.scene.on_change(self._on_scene_change)
        self._load_demo_data()
        self.after(200, self.renderer.zoom_extents)

    def _build_ui(self) -> None:
        self.top_frame = ttk.Frame(self)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)

        if self.controller is not None:
            import_btn = tk.Button(
                self.top_frame, text="📥 Завантажити вироби",
                command=self._on_import_products,
                bg="#4CAF50", fg="white", relief="flat",
                font=("Segoe UI", 9, "bold"), padx=10, pady=2, cursor="hand2"
            )
            import_btn.pack(side=tk.LEFT, padx=5, pady=2)

        self._view_mode = tk.StringVar(value="2d")
        if RENDERER3D_AVAILABLE:
            view_frame = ttk.Frame(self.top_frame)
            view_frame.pack(side=tk.RIGHT, padx=5)
            ttk.Radiobutton(
                view_frame, text="2D План", variable=self._view_mode,
                value="2d", command=self._switch_view
            ).pack(side=tk.LEFT, padx=2)
            ttk.Radiobutton(
                view_frame, text="3D Вигляд", variable=self._view_mode,
                value="3d", command=self._switch_view
            ).pack(side=tk.LEFT, padx=2)

        self.main_paned = tk.PanedWindow(
            self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=4
        )
        self.main_paned.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.center_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.center_frame, minsize=400)

        self.canvas_frame = ttk.Frame(self.center_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.renderer = Canvas2DRenderer(self.canvas_frame, self.scene)

        self.left_paned = tk.PanedWindow(
            self.main_paned, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=4
        )
        self.main_paned.add(self.left_paned, minsize=220, width=250)

        self.left_notebook = ttk.Notebook(self.left_paned)
        self.left_paned.add(self.left_notebook, minsize=150, height=500)

        self.layer_panel = LayerPanel(
            self.left_notebook, self.scene,
            on_change=lambda: self._refresh_current_view()
        )
        self.left_notebook.add(self.layer_panel, text="Шари")

        self.property_panel = PropertyPanel(
            self.left_notebook, self.scene,
            on_change=lambda: self._refresh_current_view()
        )
        self.left_notebook.add(self.property_panel, text="Властивості")

        self.details_panel = self._build_details_panel(self.left_notebook)
        self.left_notebook.add(self.details_panel, text="Деталі з проєкту")

        self.status_bar = ttk.Label(
            self,
            text="Готовий | ЛКМ — вибір/малювання | СКМ — панорама | Колесо — масштаб",
            relief=tk.SUNKEN, anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.bind_all("<Key>", self._on_global_key)

        if RENDERER3D_AVAILABLE:
            self.renderer3d_frame = ttk.Frame(self.center_frame)
            self.renderer3d = Scene3DRenderer(self.renderer3d_frame, self.scene)

    # ═══════════════════════════════════════════════════════════
    # Панель 'Деталі з проєкту'
    # ═══════════════════════════════════════════════════════════
    def _build_details_panel(self, parent: tk.Widget) -> ttk.Frame:
        frame = ttk.Frame(parent)

        header = ttk.Frame(frame)
        header.pack(fill=tk.X, padx=4, pady=(4, 0))
        ttk.Label(header, text="📋 Деталі", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        ttk.Button(header, text="🔄", width=3, command=self._refresh_details_list).pack(side=tk.RIGHT)

        ttk.Label(frame, text="Оберіть деталь і натисніть ➕",
                  font=("Segoe UI", 8), foreground="#666").pack(anchor=tk.W, padx=4)

        cols = ("name", "type", "size", "qty")
        self.details_tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            selectmode="browse", height=12
        )
        self.details_tree.heading("name", text="Назва")
        self.details_tree.heading("type", text="Тип")
        self.details_tree.heading("size", text="Розміри")
        self.details_tree.heading("qty", text="К-ть")
        self.details_tree.column("name", width=90, anchor=tk.W)
        self.details_tree.column("type", width=70, anchor=tk.W)
        self.details_tree.column("size", width=80, anchor=tk.CENTER)
        self.details_tree.column("qty", width=35, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.details_tree.yview)
        self.details_tree.configure(yscrollcommand=vsb.set)

        self.details_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0), pady=2)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4), pady=2)

        self.details_tree.bind("<Double-1>", self._on_detail_double_click)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=4, pady=(0, 4))

        tk.Button(
            btn_frame, text="➕ Додати на креслення",
            command=self._on_add_detail_click,
            bg="#2196F3", fg="white", relief="flat",
            font=("Segoe UI", 9, "bold"), cursor="hand2"
        ).pack(fill=tk.X, pady=1)

        tk.Button(
            btn_frame, text="📥 Завантажити з проєкту",
            command=self._on_import_products,
            bg="#4CAF50", fg="white", relief="flat",
            font=("Segoe UI", 9), cursor="hand2"
        ).pack(fill=tk.X, pady=1)

        # Підказка про snap
        ttk.Label(frame, text="💡 Деталь прилипає до кінця повітропроводу",
                  font=("Segoe UI", 7), foreground="#888").pack(anchor=tk.W, padx=4, pady=(0, 2))

        return frame

    def _refresh_details_list(self):
        for item in self.details_tree.get_children():
            self.details_tree.delete(item)
        if not self.controller:
            return
        try:
            products = self.controller._get_products()
            self._project_details = products or []
        except Exception:
            self._project_details = []
            return
        for p in self._project_details:
            name = p.get("name", "—")
            ptype = p.get("product_type", "—")
            width = float(p.get("width", 0))
            height = float(p.get("height", 0))
            length = float(p.get("length", 0))
            qty = int(p.get("quantity", 1))
            if width > 0 and height > 0:
                size = f"{width:.0f}×{height:.0f}×{length:.0f}"
            elif width > 0:
                size = f"Ø{width:.0f}×{length:.0f}"
            else:
                size = f"L={length:.0f}"
            self.details_tree.insert("", tk.END, values=(name, ptype, size, qty))
        self.status_bar.config(text=f"📋 Деталей у списку: {len(self._project_details)}")

    def _on_detail_double_click(self, event):
        self._on_add_detail_click()

    def _on_add_detail_click(self):
        sel = self.details_tree.selection()
        if not sel:
            messagebox.showinfo("Інформація", "Оберіть деталь у списку.")
            return
        idx = self.details_tree.index(sel[0])
        if idx < 0 or idx >= len(self._project_details):
            return
        detail = self._project_details[idx]
        pos, direction = self._get_placement_position()
        self._add_detail_to_scene(detail, pos, direction)

    def _get_placement_position(self):
        """Отримати точку для розміщення з прилипанням до endpoint.

        Повертає: (Point2D, direction_vector) — точка та напрямок ВІД точки.
        """
        from ventilation_company.project3d_editor.core.point import Point2D

        # Центр екрану
        w = self.renderer.viewport.width
        h = self.renderer.viewport.height
        center_screen = Point2D(w / 2, h / 2)
        world = self.renderer.viewport.screen_to_world(center_screen)

        # Шукаємо найближчий endpoint
        snaps = self.renderer.get_endpoint_snaps()
        best_dist = float('inf')
        best_pos = world
        best_dir = Point2D(0, -1)  # напрямок за замовчуванням — вгору

        for pt, direction in snaps:
            dist = world.distance_to(pt)
            if dist < best_dist:
                best_dist = dist
                best_pos = pt
                best_dir = direction

        # Якщо endpoint ближче 400 мм — прилипаємо
        SNAP_DISTANCE = 400.0
        if best_dist <= SNAP_DISTANCE:
            self.status_bar.config(text=f"🔧 Snap до endpoint (відстань {best_dist:.0f} мм)")
            return best_pos, best_dir

        # Інакше — прив'язка до сітки
        snapped = self.renderer.grid.snap(world, [])
        self.status_bar.config(text="📍 Розміщення в центрі екрану")
        return snapped, Point2D(0, -1)

    def _add_detail_to_scene(self, detail: Dict[str, Any], pos, direction):
        """Додати деталь на сцену з орієнтацією за напрямком."""
        from ventilation_company.project3d_editor.core.point import Point2D
        from ventilation_company.project3d_editor.scene.entities.duct import DuctSegmentEntity
        from ventilation_company.project3d_editor.scene.entities.fitting import DuctFittingEntity
        from ventilation_company.project3d_editor.scene.entities.equipment import EquipmentEntity

        ptype = (detail.get("product_type", "") + " " + detail.get("name", "")).lower()
        width = float(detail.get("width", 100))
        height = float(detail.get("height", 100))
        length = float(detail.get("length", 1000))
        thickness = float(detail.get("thickness", 0.7))
        material = detail.get("material", "оцинкована сталь")
        name = detail.get("name", "Деталь")

        pt = detail.get("product_type", "").lower()
        pn = detail.get("name", "").lower()
        is_rect_duct = "rect_duct" in pt or "duct" in pt or ("прямокутн" in ptype and "повітропровід" in ptype)
        is_round_duct = "round_duct" in pt or ("кругл" in ptype and "повітропровід" in ptype)
        is_rect_elbow = "elbow" in pt or "відвід" in pn or "коліно" in pn
        is_round_elbow = "round_elbow" in pt or (("відвід" in ptype or "коліно" in ptype) and "кругл" in ptype)
        is_rect_tee = "tee" in pt or "трійник" in pn
        is_round_tee = "round_tee" in pt or ("трійник" in ptype and "кругл" in ptype)
        is_rect_transition = "transition" in pt or "перехід" in pn
        is_round_transition = "round_transition" in pt or ("перехід" in ptype and "кругл" in ptype)
        is_rect_flange = "flange" in pt or "фланець" in pn
        is_round_flange = "round_flange" in pt or ("фланець" in ptype and "кругл" in ptype)
        is_rect_cap = "cap" in pt or "заглушка" in pn
        is_round_cap = "round_cap" in pt or ("заглушка" in ptype and "кругл" in ptype)
        is_flexible = "flexible" in pt or "гнучк" in ptype or "вставка" in ptype

        duct_type = "приплив"
        if "витяж" in ptype:
            duct_type = "витяжка"
        elif "дим" in ptype:
            duct_type = "димовидалення"

        # Обчислюємо кут повороту з direction
        # direction — напрямок ВІД точки (куда дивиться повітропровід)
        # Для фітингів: вхідна точка повинна бути протилежною до direction
        angle_deg = math.degrees(math.atan2(direction.x, -direction.y))

        entity = None

        if is_rect_duct or is_round_duct:
            # Повітропровід: ставимо start=pos, end=pos + direction*length
            end = Point2D(
                pos.x + direction.x * length,
                pos.y + direction.y * length
            )
            entity = DuctSegmentEntity(
                name=name, start=pos, end=end,
                width=width, height=height if is_rect_duct else width,
                is_round=is_round_duct, duct_type=duct_type,
                material=material, thickness=thickness,
            )

        elif is_rect_elbow or is_round_elbow:
            entity = DuctFittingEntity(
                name=name, position=pos,
                fitting_type="відвід",
                width_in=width, height_in=height if is_rect_elbow else width,
                duct_type=duct_type, material=material, thickness=thickness,
                angle=float(detail.get("angle", 90)),
                radius=float(detail.get("radius", 150)),
                rotation=angle_deg,  # інвертуємо, щоб вхід був проти direction
            )

        elif is_rect_tee or is_round_tee:
            bw = float(detail.get("branch_width", width * 0.5))
            bh = float(detail.get("branch_height", height * 0.5)) if is_rect_tee else float(detail.get("branch_diameter", width * 0.5))
            entity = DuctFittingEntity(
                name=name, position=pos,
                fitting_type="трійник",
                width_in=width, height_in=height if is_rect_tee else width,
                width_out=bw, height_out=bh,
                duct_type=duct_type, material=material, thickness=thickness,
                rotation=angle_deg,
            )

        elif is_rect_transition or is_round_transition:
            ew = float(detail.get("end_width", 300))
            eh = float(detail.get("end_height", 150)) if is_rect_transition else float(detail.get("end_diameter", 300))
            entity = DuctFittingEntity(
                name=name, position=pos,
                fitting_type="перехід",
                width_in=width, height_in=height if is_rect_transition else width,
                width_out=ew, height_out=eh,
                duct_type=duct_type, material=material, thickness=thickness,
                rotation=angle_deg,
            )

        elif is_rect_flange or is_round_flange:
            entity = DuctFittingEntity(
                name=name, position=pos,
                fitting_type="фланець",
                width_in=width, height_in=height if is_rect_flange else width,
                duct_type=duct_type, material=material, thickness=thickness,
                rotation=angle_deg,
            )

        elif is_rect_cap or is_round_cap:
            entity = DuctFittingEntity(
                name=name, position=pos,
                fitting_type="заглушка",
                width_in=width, height_in=height if is_rect_cap else width,
                duct_type=duct_type, material=material, thickness=thickness,
                rotation=angle_deg,
            )

        elif is_flexible:
            end = Point2D(pos.x + direction.x * length, pos.y + direction.y * length)
            entity = DuctSegmentEntity(
                name=name, start=pos, end=end,
                width=width, height=height, is_round=False,
                duct_type=duct_type, material=material, thickness=thickness,
            )

        else:
            eq_type = "обладнання"
            if "вентилятор" in ptype:
                eq_type = "вентилятор"
            elif "фільтр" in ptype:
                eq_type = "фільтр"
            elif "клапан" in ptype:
                eq_type = "клапан"
            elif "глушник" in ptype or "шумоглушник" in ptype:
                eq_type = "глушник"
            elif "рекуператор" in ptype:
                eq_type = "рекуператор"
            elif "калорифер" in ptype:
                eq_type = "калорифер"

            entity = EquipmentEntity(
                name=name, position=pos,
                width=width if width > 0 else 500,
                height=height if height > 0 else 500,
                depth=length if length > 0 else 500,
                equipment_type=eq_type,
            )

        if entity:
            self.scene.add_entity(entity)
            type_str = "повітропровід" if (is_rect_duct or is_round_duct) else                        "відвід" if (is_rect_elbow or is_round_elbow) else                        "трійник" if (is_rect_tee or is_round_tee) else                        "перехід" if (is_rect_transition or is_round_transition) else                        "фланець" if (is_rect_flange or is_round_flange) else                        "заглушка" if (is_rect_cap or is_round_cap) else                        "гнучка" if is_flexible else "обладнання"
            self.status_bar.config(text=f"✅ Додано: {name} | Тип: {type_str} | Кут: {angle_deg:.0f}°")
            self._refresh_current_view()

    # ═══════════════════════════════════════════════════════════
    # 3D / 2D перемикання
    # ═══════════════════════════════════════════════════════════
    def _switch_view(self):
        mode = self._view_mode.get()
        if mode == "2d":
            self.renderer3d_frame.pack_forget()
            self.canvas_frame.pack(fill=tk.BOTH, expand=True)
            self.status_bar.config(text="Режим: 2D План")
            self.renderer.render()
        else:
            self.canvas_frame.pack_forget()
            self.renderer3d_frame.pack(fill=tk.BOTH, expand=True)
            self.status_bar.config(text="Режим: 3D Вигляд")
            self.renderer3d.refresh()

    def _refresh_current_view(self):
        if self._view_mode.get() == "3d" and RENDERER3D_AVAILABLE:
            self.renderer3d.refresh()
        else:
            self.renderer.render()

    # ═══════════════════════════════════════════════════════════
    # Імпорт
    # ═══════════════════════════════════════════════════════════
    def _on_import_products(self):
        if self.controller is None:
            messagebox.showwarning("Увага", "Контролер не підключено.")
            return
        try:
            products = self.controller._get_products()
            if not products:
                messagebox.showinfo("Інформація", "Немає виробів для імпорту.")
                return
            self._project_details = products
            self._refresh_details_list()
            self.load_from_products(products)
            count = len(products)
            self.status_bar.config(text=f"✅ Імпортовано {count} виробів")
            messagebox.showinfo("Успіх", f"Імпортовано {count} виробів у 3D-сцену.")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося імпортувати вироби: {e}")

    def load_from_products(self, products: List[Dict[str, Any]]) -> None:
        from ventilation_company.project3d_editor.scene.entities.duct import DuctSegmentEntity
        from ventilation_company.project3d_editor.scene.entities.fitting import DuctFittingEntity
        from ventilation_company.project3d_editor.scene.entities.equipment import EquipmentEntity
        from ventilation_company.project3d_editor.core.point import Point2D

        self.scene.clear(record_undo=False)
        x_offset = 0.0
        spacing = 500.0

        for p in products:
            ptype = (p.get("product_type", "") + " " + p.get("name", "")).lower()
            width = float(p.get("width", 100))
            height = float(p.get("height", 100))
            length = float(p.get("length", 1000))
            thickness = float(p.get("thickness", 0.7))
            material = p.get("material", "оцинкована сталь")
            quantity = int(p.get("quantity", 1))
            name = p.get("name", "Виріб")

            # Англійські + українські назви типів
            pt = p.get("product_type", "").lower()
            pn = p.get("name", "").lower()
            # Гнучке розпізнавання: шукаємо ключові слова будь-де
            is_rect_duct = "rect_duct" in pt or "duct" in pt or ("прямокутн" in ptype and "повітропровід" in ptype)
            is_round_duct = "round_duct" in pt or ("кругл" in ptype and "повітропровід" in ptype)
            is_rect_elbow = "elbow" in pt or "відвід" in pn or "коліно" in pn
            is_round_elbow = "round_elbow" in pt or (("відвід" in ptype or "коліно" in ptype) and "кругл" in ptype)
            is_rect_tee = "tee" in pt or "трійник" in pn
            is_round_tee = "round_tee" in pt or ("трійник" in ptype and "кругл" in ptype)
            is_rect_transition = "transition" in pt or "перехід" in pn
            is_round_transition = "round_transition" in pt or ("перехід" in ptype and "кругл" in ptype)
            is_rect_flange = "flange" in pt or "фланець" in pn
            is_round_flange = "round_flange" in pt or ("фланець" in ptype and "кругл" in ptype)
            is_rect_cap = "cap" in pt or "заглушка" in pn
            is_round_cap = "round_cap" in pt or ("заглушка" in ptype and "кругл" in ptype)
            is_flexible = "flexible" in pt or "гнучк" in ptype or "вставка" in ptype

            duct_type = "приплив"
            if "витяж" in ptype:
                duct_type = "витяжка"
            elif "дим" in ptype:
                duct_type = "димовидалення"

            for _ in range(quantity):
                if is_rect_duct or is_round_duct:
                    entity = DuctSegmentEntity(
                        name=name, start=Point2D(x_offset, 0), end=Point2D(x_offset + length, 0),
                        width=width, height=height if is_rect_duct else width,
                        is_round=is_round_duct, duct_type=duct_type,
                        material=material, thickness=thickness,
                    )
                    self.scene.add_entity(entity, record_undo=False)
                    x_offset += length + spacing
                elif is_rect_elbow or is_round_elbow:
                    entity = DuctFittingEntity(
                        name=name, position=Point2D(x_offset, 0), fitting_type="відвід",
                        width_in=width, height_in=height if is_rect_elbow else width,
                        duct_type=duct_type, material=material, thickness=thickness,
                        angle=float(p.get("angle", 90)), radius=float(p.get("radius", 150)),
                    )
                    self.scene.add_entity(entity, record_undo=False)
                    x_offset += 500 + spacing
                elif is_rect_tee or is_round_tee:
                    bw = float(p.get("branch_width", width * 0.5))
                    bh = float(p.get("branch_height", height * 0.5)) if is_rect_tee else float(p.get("branch_diameter", width * 0.5))
                    entity = DuctFittingEntity(
                        name=name, position=Point2D(x_offset, 0), fitting_type="трійник",
                        width_in=width, height_in=height if is_rect_tee else width,
                        width_out=bw, height_out=bh,
                        duct_type=duct_type, material=material, thickness=thickness,
                    )
                    self.scene.add_entity(entity, record_undo=False)
                    x_offset += 500 + spacing
                elif is_rect_transition or is_round_transition:
                    ew = float(p.get("end_width", 300))
                    eh = float(p.get("end_height", 150)) if is_rect_transition else float(p.get("end_diameter", 300))
                    entity = DuctFittingEntity(
                        name=name, position=Point2D(x_offset, 0), fitting_type="перехід",
                        width_in=width, height_in=height if is_rect_transition else width,
                        width_out=ew, height_out=eh,
                        duct_type=duct_type, material=material, thickness=thickness,
                    )
                    self.scene.add_entity(entity, record_undo=False)
                    x_offset += 500 + spacing
                elif is_rect_flange or is_round_flange:
                    entity = DuctFittingEntity(
                        name=name, position=Point2D(x_offset, 0), fitting_type="фланець",
                        width_in=width, height_in=height if is_rect_flange else width,
                        duct_type=duct_type, material=material, thickness=thickness,
                    )
                    self.scene.add_entity(entity, record_undo=False)
                    x_offset += 200 + spacing
                elif is_rect_cap or is_round_cap:
                    entity = DuctFittingEntity(
                        name=name, position=Point2D(x_offset, 0), fitting_type="заглушка",
                        width_in=width, height_in=height if is_rect_cap else width,
                        duct_type=duct_type, material=material, thickness=thickness,
                    )
                    self.scene.add_entity(entity, record_undo=False)
                    x_offset += 200 + spacing
                elif is_flexible:
                    entity = DuctSegmentEntity(
                        name=name, start=Point2D(x_offset, 0), end=Point2D(x_offset + length, 0),
                        width=width, height=height, is_round=False,
                        duct_type=duct_type, material=material, thickness=thickness,
                    )
                    self.scene.add_entity(entity, record_undo=False)
                    x_offset += length + spacing
                else:
                    eq_type = "обладнання"
                    if "вентилятор" in ptype:
                        eq_type = "вентилятор"
                    elif "фільтр" in ptype:
                        eq_type = "фільтр"
                    elif "клапан" in ptype:
                        eq_type = "клапан"
                    elif "глушник" in ptype or "шумоглушник" in ptype:
                        eq_type = "глушник"
                    elif "рекуператор" in ptype:
                        eq_type = "рекуператор"
                    elif "калорифер" in ptype:
                        eq_type = "калорифер"
                    entity = EquipmentEntity(
                        name=name, position=Point2D(x_offset, 0),
                        width=width if width > 0 else 500,
                        height=height if height > 0 else 500,
                        depth=length if length > 0 else 500,
                        equipment_type=eq_type,
                    )
                    self.scene.add_entity(entity, record_undo=False)
                    x_offset += 600 + spacing

        self._refresh_current_view()

    def set_project(self, project) -> None:
        if isinstance(project, list):
            self._project_details = project
            self._refresh_details_list()
            self.load_from_products(project)
        elif isinstance(project, dict):
            products = project.get("products", [])
            self._project_details = products
            self._refresh_details_list()
            self.load_from_products(products)
        else:
            if self.controller is not None:
                try:
                    products = self.controller._get_products()
                    self._project_details = products
                    self._refresh_details_list()
                    self.load_from_products(products)
                except Exception:
                    pass

    def _on_tool_change(self, key: str) -> None:
        tool = self.tool_manager.get_current_tool()
        if tool:
            self.status_bar.config(text=f"Інструмент: {tool.name} | {tool.icon}")
            self.tool_settings.update_for_tool(tool)

    def _on_scene_change(self) -> None:
        self.property_panel.update_for_selection()
        scale_text = self.renderer.viewport.get_scale_str()
        if hasattr(self, 'toolbar'):
            self.toolbar.set_scale_text(scale_text)

    def _on_global_key(self, event) -> None:
        if hasattr(self, 'tool_manager') and self.tool_manager.get_current_tool():
            self.tool_manager.get_current_tool().on_key(event)

    def _load_demo_data(self) -> None:
        from ventilation_company.project3d_editor.core.point import Point2D
        from ventilation_company.project3d_editor.scene.entities.wall import WallEntity
        from ventilation_company.project3d_editor.scene.entities.duct import DuctSegmentEntity
        from ventilation_company.project3d_editor.scene.entities.fitting import DuctFittingEntity
        from ventilation_company.project3d_editor.scene.entities.equipment import EquipmentEntity

        self.scene.add_entity(WallEntity(
            name="Стіна Північ", start=Point2D(0, 0), end=Point2D(8000, 0),
            thickness=250, height=3200, is_load_bearing=True, color="#555555"
        ))
        self.scene.add_entity(WallEntity(
            name="Стіна Схід", start=Point2D(8000, 0), end=Point2D(8000, 6000),
            thickness=200, height=3200, color="#888888"
        ))
        self.scene.add_entity(WallEntity(
            name="Стіна Південь", start=Point2D(8000, 6000), end=Point2D(0, 6000),
            thickness=200, height=3200, color="#888888"
        ))
        self.scene.add_entity(WallEntity(
            name="Стіна Захід", start=Point2D(0, 6000), end=Point2D(0, 0),
            thickness=250, height=3200, is_load_bearing=True, color="#555555"
        ))
        self.scene.add_entity(WallEntity(
            name="Перегородка", start=Point2D(4000, 0), end=Point2D(4000, 6000),
            thickness=100, height=3000, color="#aaaaaa"
        ))
        self.scene.add_entity(DuctSegmentEntity(
            name="Приплив головний", start=Point2D(1000, 500), end=Point2D(7000, 500),
            width=250, height=250, duct_type="приплив", color="#0066cc"
        ))
        self.scene.add_entity(DuctSegmentEntity(
            name="Приплив відгалуження", start=Point2D(4000, 500), end=Point2D(4000, 3000),
            width=200, height=200, duct_type="приплив", color="#0066cc"
        ))
        self.scene.add_entity(DuctSegmentEntity(
            name="Витяжка головна", start=Point2D(1000, 5500), end=Point2D(7000, 5500),
            width=200, height=200, duct_type="витяжка", color="#009900"
        ))
        self.scene.add_entity(DuctFittingEntity(
            name="Трійник", position=Point2D(4000, 500),
            fitting_type="трійник", width_in=250, height_in=250,
            duct_type="приплив", color="#990099"
        ))
        self.scene.add_entity(EquipmentEntity(
            name="ПВУ-1", position=Point2D(1000, 3000),
            width=800, height=600, equipment_type="вентилятор",
            air_flow=5000, power=5.5, color="#cc8800"
        ))

    def get_scene(self) -> SceneGraph:
        return self.scene
