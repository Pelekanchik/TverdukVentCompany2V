"""Нова вкладка 'Проекти 3D' — професійний CAD-редактор."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Optional

from ventilation_company.project3d_editor.scene.scene_graph import SceneGraph
from ventilation_company.project3d_editor.canvas2d.renderer import Canvas2DRenderer
from ventilation_company.project3d_editor.tools.tool_manager import ToolManager
from ventilation_company.project3d_editor.ui.toolbar import Toolbar
from ventilation_company.project3d_editor.ui.property_panel import PropertyPanel
from ventilation_company.project3d_editor.ui.layer_panel import LayerPanel
from ventilation_company.project3d_editor.ui.tool_settings_panel import ToolSettingsPanel


class Project3DTabNew(ttk.Frame):
    """Нова вкладка Проекти 3D — повноцінний CAD-редактор."""

    def __init__(self, parent: tk.Widget, controller=None):
        super().__init__(parent)
        self.controller = controller

        # Сцена
        self.scene = SceneGraph()

        # Головний layout
        self._build_ui()

        # Ініціалізація інструментів
        self.tool_manager = ToolManager(self.renderer, self.scene)

        # Тулбар
        self.toolbar = Toolbar(self.top_frame, self.tool_manager,
                               on_tool_change=self._on_tool_change)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # Панель налаштувань інструменту (під тулбаром)
        self.tool_settings = ToolSettingsPanel(self.top_frame)
        self.tool_settings.pack(side=tk.TOP, fill=tk.X, padx=2, pady=1)

        # Підписуємось на зміни сцени
        self.scene.on_change(self._on_scene_change)

        # Демо-дані
        self._load_demo_data()

        # Підігнати під об'єкти
        self.after(200, self.renderer.zoom_extents)

    def _build_ui(self) -> None:
        """Побудувати інтерфейс з resizable панелями."""
        # Верхня панель (тулбар)
        self.top_frame = ttk.Frame(self)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)

        # Головний PanedWindow (горизонтальний: ліво | центр)
        self.main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=4)
        self.main_paned.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # ── СПОЧАТКУ Canvas (центр) — створюємо renderer ──
        self.canvas_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.canvas_frame, minsize=400)

        self.renderer = Canvas2DRenderer(self.canvas_frame, self.scene)

        # ── ЛІВА ПАНЕЛЬ: Шари + Властивості (вертикальний PanedWindow) ──
        self.left_paned = tk.PanedWindow(self.main_paned, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=4)
        self.main_paned.add(self.left_paned, minsize=200, width=230)

        # Панель шарів (зверху)
        self.layer_panel = LayerPanel(self.left_paned, self.scene,
                                      on_change=lambda: self.renderer.render())
        self.left_paned.add(self.layer_panel, minsize=120, height=250)

        # Панель властивостей (знизу)
        self.property_panel = PropertyPanel(self.left_paned, self.scene,
                                            on_change=lambda: self.renderer.render())
        self.left_paned.add(self.property_panel, minsize=150, height=350)

        # ── Статус-бар ──
        self.status_bar = ttk.Label(self, text="Готовий | ЛКМ — вибір/малювання | СКМ — панорама | Колесо — масштаб | 1-7 — інструменти",
                                    relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Прив'язка клавіш
        self.bind_all("<Key>", self._on_global_key)

    def _on_tool_change(self, key: str) -> None:
        tool = self.tool_manager.get_current_tool()
        if tool:
            self.status_bar.config(text=f"Інструмент: {tool.name} | {tool.icon}")
            self.tool_settings.update_for_tool(tool)

    def _on_scene_change(self) -> None:
        """Викликається при зміні сцени."""
        self.property_panel.update_for_selection()
        scale_text = self.renderer.viewport.get_scale_str()
        if hasattr(self, 'toolbar'):
            self.toolbar.set_scale_text(scale_text)

    def _on_global_key(self, event) -> None:
        """Глобальні гарячі клавіші."""
        if hasattr(self, 'tool_manager') and self.tool_manager.get_current_tool():
            self.tool_manager.get_current_tool().on_key(event)

    def _load_demo_data(self) -> None:
        """Завантажити демо-дані для тестування."""
        from ventilation_company.project3d_editor.core.point import Point2D
        from ventilation_company.project3d_editor.scene.entities.wall import WallEntity
        from ventilation_company.project3d_editor.scene.entities.duct import DuctSegmentEntity
        from ventilation_company.project3d_editor.scene.entities.fitting import DuctFittingEntity
        from ventilation_company.project3d_editor.scene.entities.equipment import EquipmentEntity

        # Стіни приміщення
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
        # Перегородка
        self.scene.add_entity(WallEntity(
            name="Перегородка", start=Point2D(4000, 0), end=Point2D(4000, 6000),
            thickness=100, height=3000, color="#aaaaaa"
        ))

        # Повітропровід приплив
        self.scene.add_entity(DuctSegmentEntity(
            name="Приплив головний", start=Point2D(1000, 500), end=Point2D(7000, 500),
            width=250, height=250, duct_type="приплив", color="#0066cc"
        ))
        self.scene.add_entity(DuctSegmentEntity(
            name="Приплив відгалуження", start=Point2D(4000, 500), end=Point2D(4000, 3000),
            width=200, height=200, duct_type="приплив", color="#0066cc"
        ))

        # Витяжка
        self.scene.add_entity(DuctSegmentEntity(
            name="Витяжка головна", start=Point2D(1000, 5500), end=Point2D(7000, 5500),
            width=200, height=200, duct_type="витяжка", color="#009900"
        ))

        # Фітинги
        self.scene.add_entity(DuctFittingEntity(
            name="Трійник", position=Point2D(4000, 500),
            fitting_type="трійник", width_in=250, height_in=250,
            duct_type="приплив", color="#990099"
        ))

        # Обладнання
        self.scene.add_entity(EquipmentEntity(
            name="ПВУ-1", position=Point2D(1000, 3000),
            width=800, height=600, equipment_type="вентилятор",
            air_flow=5000, power=5.5, color="#cc8800"
        ))

    def set_project(self, project) -> None:
        """Завантажити існуючий VentProject у сцену."""
        pass

    def get_scene(self) -> SceneGraph:
        return self.scene
