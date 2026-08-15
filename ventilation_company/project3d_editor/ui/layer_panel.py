"""Панель шарів (Layers)."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable

from ventilation_company.project3d_editor.scene.scene_graph import SceneGraph
from ventilation_company.project3d_editor.scene.layer import Layer


class LayerPanel(ttk.LabelFrame):
    """Панель керування шарами."""

    def __init__(self, parent: tk.Widget, scene: SceneGraph,
                 on_change: Callable = None):
        super().__init__(parent, text="Шари", padding=5)
        self.scene = scene
        self.on_change = on_change
        self._layer_frames: dict = {}
        self._build()
        # Підписуємось на зміни
        self.scene.on_change(self._refresh)

    def _build(self) -> None:
        """Побудувати список шарів."""
        for w in self.winfo_children():
            w.destroy()
        self._layer_frames.clear()

        layers = self.scene.layer_manager.get_all_layers()
        for layer in layers:
            self._add_layer_row(layer)

        # Кнопки
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="➕ Додати", command=self._add_layer).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame, text="🗑️ Видалити", command=self._remove_layer).pack(side=tk.LEFT, padx=1)

    def _add_layer_row(self, layer: Layer) -> None:
        frame = ttk.Frame(self)
        frame.pack(fill=tk.X, pady=1)

        # Іконка видимості
        eye = "👁️" if layer.visible else "🚫"
        btn_eye = tk.Button(frame, text=eye, width=2, relief=tk.FLAT,
                            command=lambda lid=layer.id: self._toggle_visibility(lid))
        btn_eye.pack(side=tk.LEFT)

        # Іконка блокування
        lock = "🔓" if not layer.locked else "🔒"
        btn_lock = tk.Button(frame, text=lock, width=2, relief=tk.FLAT,
                             command=lambda lid=layer.id: self._toggle_lock(lid))
        btn_lock.pack(side=tk.LEFT)

        # Колір
        color_btn = tk.Button(frame, bg=layer.color, width=2, relief=tk.RAISED)
        color_btn.pack(side=tk.LEFT, padx=2)

        # Назва
        name_lbl = tk.Label(frame, text=layer.name, anchor=tk.W, width=18)
        name_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Активний
        is_active = self.scene.layer_manager.active_layer_id == layer.id
        if is_active:
            name_lbl.config(font=("Segoe UI", 9, "bold"), fg="blue")
            frame.config(relief=tk.SUNKEN)

        # Клік по рядку — зробити активним
        frame.bind("<Button-1>", lambda e, lid=layer.id: self._set_active(lid))
        name_lbl.bind("<Button-1>", lambda e, lid=layer.id: self._set_active(lid))

        self._layer_frames[layer.id] = frame

    def _toggle_visibility(self, layer_id: str) -> None:
        self.scene.layer_manager.toggle_visibility(layer_id)
        self._refresh()
        if self.on_change:
            self.on_change()

    def _toggle_lock(self, layer_id: str) -> None:
        self.scene.layer_manager.toggle_lock(layer_id)
        self._refresh()

    def _set_active(self, layer_id: str) -> None:
        self.scene.layer_manager.set_active_layer(layer_id)
        self._refresh()

    def _add_layer(self) -> None:
        from tkinter import simpledialog
        name = simpledialog.askstring("Новий шар", "Назва шару:", parent=self)
        if name:
            self.scene.layer_manager.add_layer(name)
            self._refresh()

    def _remove_layer(self) -> None:
        active = self.scene.layer_manager.active_layer_id
        if active != "default":
            self.scene.layer_manager.remove_layer(active)
            self._refresh()

    def _refresh(self) -> None:
        self._build()
