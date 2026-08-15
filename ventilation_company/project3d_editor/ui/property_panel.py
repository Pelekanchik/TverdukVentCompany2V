"""Панель властивостей вибраного об'єкта."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

from ventilation_company.project3d_editor.scene.scene_graph import SceneGraph
from ventilation_company.project3d_editor.scene.entity import Entity
from ventilation_company.project3d_editor.scene.entities.wall import WallEntity
from ventilation_company.project3d_editor.scene.entities.duct import DuctSegmentEntity
from ventilation_company.project3d_editor.scene.entities.fitting import DuctFittingEntity
from ventilation_company.project3d_editor.scene.entities.equipment import EquipmentEntity
from ventilation_company.project3d_editor.scene.entities.rect import RectEntity


class PropertyPanel(ttk.LabelFrame):
    """Панель властивостей — редагування атрибутів вибраного об'єкта."""

    def __init__(self, parent: tk.Widget, scene: SceneGraph,
                 on_change: Callable = None):
        super().__init__(parent, text="Властивості", padding=5)
        self.scene = scene
        self.on_change = on_change
        self._current_entity_id: Optional[str] = None
        self._fields: dict = {}
        self._build_empty()

    def _build_empty(self) -> None:
        """Показати порожній стан."""
        for w in self.winfo_children():
            w.destroy()
        self._fields.clear()
        tk.Label(self, text="Нічого не вибрано", fg="gray").pack(pady=20)

    def update_for_selection(self) -> None:
        """Оновити панель відповідно до поточного вибору."""
        selection = self.scene.get_selection()
        if len(selection) == 0:
            self._build_empty()
            return
        if len(selection) == 1:
            self._build_for_entity(selection[0])
        else:
            self._build_multi_selection(selection)

    def _build_for_entity(self, entity: Entity) -> None:
        """Побудувати форму для однієї сутності."""
        for w in self.winfo_children():
            w.destroy()
        self._fields.clear()
        self._current_entity_id = entity.id

        # Загальні поля
        self._add_field("name", "Назва", entity.name)
        self._add_field("color", "Колір", entity.color)
        self._add_field("line_width", "Товщина лінії", str(entity.line_width))

        # Специфічні поля
        if isinstance(entity, WallEntity):
            self._add_field("thickness", "Товщина (мм)", str(entity.thickness))
            self._add_field("height", "Висота (мм)", str(entity.height))
            self._add_field("material", "Матеріал", entity.material)
            self._add_bool("is_load_bearing", "Несуча", entity.is_load_bearing)
        elif isinstance(entity, DuctSegmentEntity):
            self._add_field("width", "Ширина (мм)", str(entity.width))
            self._add_field("height", "Висота (мм)", str(entity.height))
            self._add_field("duct_type", "Тип", entity.duct_type)
            self._add_field("material", "Матеріал", entity.material)
            self._add_field("air_flow", "Витрата (м³/год)", str(entity.air_flow))
        elif isinstance(entity, DuctFittingEntity):
            self._add_field("fitting_type", "Тип виробу", entity.fitting_type)
            self._add_field("width_in", "Вхідна ширина", str(entity.width_in))
            self._add_field("width_out", "Вихідна ширина", str(entity.width_out))
            self._add_field("angle", "Кут (°)", str(entity.angle))
        elif isinstance(entity, EquipmentEntity):
            self._add_field("equipment_type", "Тип", entity.equipment_type)
            self._add_field("width", "Ширина (мм)", str(entity.width))
            self._add_field("height", "Висота (мм)", str(entity.height))
            self._add_field("air_flow", "Витрата (м³/год)", str(entity.air_flow))
            self._add_field("power", "Потужність (кВт)", str(entity.power))
        elif isinstance(entity, RectEntity):
            self._add_field("width", "Ширина (мм)", str(entity.width))
            self._add_field("height", "Висота (мм)", str(entity.height))
            self._add_field("rotation", "Поворот (°)", str(entity.rotation))

        # Кнопка застосувати
        ttk.Button(self, text="💾 Застосувати", command=self._apply).pack(pady=5, fill=tk.X)

    def _build_multi_selection(self, entities: list) -> None:
        """Показати інфо про кілька об'єктів."""
        for w in self.winfo_children():
            w.destroy()
        tk.Label(self, text=f"Вибрано: {len(entities)} об'єктів", font=("Segoe UI", 10, "bold")).pack(pady=5)
        types = {}
        for e in entities:
            t = e.entity_type.name
            types[t] = types.get(t, 0) + 1
        for t, c in types.items():
            tk.Label(self, text=f"  {t}: {c}").pack(anchor=tk.W)

    def _add_field(self, key: str, label: str, value: str) -> None:
        frame = ttk.Frame(self)
        frame.pack(fill=tk.X, pady=1)
        ttk.Label(frame, text=label, width=18).pack(side=tk.LEFT)
        var = tk.StringVar(value=value)
        entry = ttk.Entry(frame, textvariable=var, width=15)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._fields[key] = var

    def _add_bool(self, key: str, label: str, value: bool) -> None:
        frame = ttk.Frame(self)
        frame.pack(fill=tk.X, pady=1)
        var = tk.BooleanVar(value=value)
        chk = ttk.Checkbutton(frame, text=label, variable=var)
        chk.pack(side=tk.LEFT)
        self._fields[key] = var

    def _apply(self) -> None:
        """Застосувати зміни до сутності."""
        entity = self.scene.get_entity(self._current_entity_id)
        if not entity:
            return
        try:
            if "name" in self._fields:
                entity.name = self._fields["name"].get()
            if "color" in self._fields:
                entity.color = self._fields["color"].get()
            if "line_width" in self._fields:
                entity.line_width = float(self._fields["line_width"].get())

            if isinstance(entity, WallEntity):
                if "thickness" in self._fields:
                    entity.thickness = float(self._fields["thickness"].get())
                if "height" in self._fields:
                    entity.height = float(self._fields["height"].get())
                if "material" in self._fields:
                    entity.material = self._fields["material"].get()
                if "is_load_bearing" in self._fields:
                    entity.is_load_bearing = self._fields["is_load_bearing"].get()
            elif isinstance(entity, DuctSegmentEntity):
                if "width" in self._fields:
                    entity.width = float(self._fields["width"].get())
                if "height" in self._fields:
                    entity.height = float(self._fields["height"].get())
                if "duct_type" in self._fields:
                    entity.duct_type = self._fields["duct_type"].get()
                if "air_flow" in self._fields:
                    entity.air_flow = float(self._fields["air_flow"].get())
            elif isinstance(entity, RectEntity):
                if "width" in self._fields:
                    entity.width = float(self._fields["width"].get())
                if "height" in self._fields:
                    entity.height = float(self._fields["height"].get())
                if "rotation" in self._fields:
                    entity.rotation = float(self._fields["rotation"].get())

            self.scene._notify_change()
            if self.on_change:
                self.on_change()
        except ValueError:
            pass  # Некоректне число — ігноруємо
