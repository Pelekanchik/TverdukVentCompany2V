"""Панель інструментів (тулбар) з кнопками."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List

from ventilation_company.project3d_editor.tools.base_tool import BaseTool
from ventilation_company.project3d_editor.tools.tool_manager import ToolManager


class Toolbar(ttk.Frame):
    """Панель інструментів CAD-редактора."""

    def __init__(self, parent: tk.Widget, tool_manager: ToolManager,
                 on_tool_change: Callable[[str], None] = None):
        super().__init__(parent, relief=tk.RAISED, padding=2)
        self.tool_manager = tool_manager
        self.on_tool_change = on_tool_change
        self._buttons: Dict[str, tk.Button] = {}
        self._current_key: str = ""

        self._build()

    def _build(self) -> None:
        """Побудувати кнопки інструментів."""
        tools = self.tool_manager.get_all_tools()
        for i, tool in enumerate(tools):
            key = self.tool_manager.get_tool_key(tool)
            if key is None:
                continue
            btn = tk.Button(
                self, text=f"{tool.icon} {tool.name}",
                width=12, height=1,
                relief=tk.RAISED,
                font=("Segoe UI", 9),
                command=lambda k=key: self._on_tool_click(k),
            )
            btn.pack(side=tk.LEFT, padx=1, pady=1)
            self._buttons[key] = btn

        # Роздільник
        ttk.Separator(self, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

        # Додаткові кнопки
        extra = [
            ("🗑️ Очистити", self._on_clear),
            ("🔍 Все в вікно", self._on_zoom_extents),
            ("⬅️ Undo", self._on_undo),
            ("➡️ Redo", self._on_redo),
        ]
        for text, cmd in extra:
            btn = tk.Button(self, text=text, width=10, height=1,
                            relief=tk.RAISED, font=("Segoe UI", 9),
                            command=cmd)
            btn.pack(side=tk.LEFT, padx=1, pady=1)

        # Інфо-панель
        self._info_label = tk.Label(self, text="Масштаб: 100%", font=("Segoe UI", 9))
        self._info_label.pack(side=tk.RIGHT, padx=10)

    def _on_tool_click(self, key: str) -> None:
        self.tool_manager.activate_tool(key)
        self._highlight_button(key)
        if self.on_tool_change:
            self.on_tool_change(key)

    def _highlight_button(self, key: str) -> None:
        for k, btn in self._buttons.items():
            if k == key:
                btn.config(relief=tk.SUNKEN, bg="#d0e8ff")
            else:
                btn.config(relief=tk.RAISED, bg="#f0f0f0")
        self._current_key = key

    def _on_clear(self) -> None:
        self.tool_manager.scene.clear()
        self.tool_manager.renderer.render()

    def _on_zoom_extents(self) -> None:
        self.tool_manager.renderer.zoom_extents()

    def _on_undo(self) -> None:
        self.tool_manager.scene.undo()
        self.tool_manager.renderer.render()

    def _on_redo(self) -> None:
        self.tool_manager.scene.redo()
        self.tool_manager.renderer.render()

    def set_scale_text(self, text: str) -> None:
        self._info_label.config(text=f"Масштаб: {text}")
