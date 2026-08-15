"""Керування інструментами — перемикання, гарячі клавіші."""

from __future__ import annotations
from typing import Dict, Optional, Type, List

from ventilation_company.project3d_editor.tools.base_tool import BaseTool
from ventilation_company.project3d_editor.tools.select_tool import SelectTool
from ventilation_company.project3d_editor.tools.line_tool import LineTool
from ventilation_company.project3d_editor.tools.wall_tool import WallTool
from ventilation_company.project3d_editor.tools.rect_tool import RectTool
from ventilation_company.project3d_editor.tools.duct_tool import DuctTool
from ventilation_company.project3d_editor.tools.fitting_tool import FittingTool
from ventilation_company.project3d_editor.tools.equipment_tool import EquipmentTool


class ToolManager:
    """Менеджер інструментів CAD-редактора."""

    def __init__(self, renderer, scene):
        self.renderer = renderer
        self.scene = scene
        self._tools: Dict[str, BaseTool] = {}
        self._current_tool: Optional[BaseTool] = None
        self._tool_order: List[str] = []

        # Реєструємо стандартні інструменти
        self.register_tool("select", SelectTool)
        self.register_tool("line", LineTool)
        self.register_tool("wall", WallTool)
        self.register_tool("rect", RectTool)
        self.register_tool("duct", DuctTool)
        self.register_tool("fitting", FittingTool)
        self.register_tool("equipment", EquipmentTool)

        # Активуємо вибір за замовчуванням
        self.activate_tool("select")

        # Прив'язуємо події рендерера до поточного інструменту
        self._bind_renderer_events()

    def register_tool(self, key: str, tool_class: Type[BaseTool]) -> None:
        """Зареєструвати новий інструмент."""
        self._tools[key] = tool_class(self.renderer, self.scene)
        if key not in self._tool_order:
            self._tool_order.append(key)

    def activate_tool(self, key: str) -> bool:
        """Активувати інструмент за ключем."""
        tool = self._tools.get(key)
        if tool is None:
            return False
        if self._current_tool is not None:
            self._current_tool.deactivate()
        self._current_tool = tool
        self._current_tool.activate()
        return True

    def get_current_tool(self) -> Optional[BaseTool]:
        return self._current_tool

    def get_tool(self, key: str) -> Optional[BaseTool]:
        return self._tools.get(key)

    def get_all_tools(self) -> List[BaseTool]:
        return [self._tools[k] for k in self._tool_order if k in self._tools]

    def get_tool_key(self, tool: BaseTool) -> Optional[str]:
        for k, t in self._tools.items():
            if t is tool:
                return k
        return None

    def _bind_renderer_events(self) -> None:
        """Переспрямує події рендерера на поточний інструмент."""
        self.renderer.on_mouse_move = self._on_mouse_move
        self.renderer.on_click = self._on_click
        self.renderer.on_drag = self._on_drag
        self.renderer.on_drag_end = self._on_drag_end
        self.renderer.on_double_click = self._on_double_click
        # Клавіатура
        self.renderer.canvas.bind("<Key>", self._on_key)
        self.renderer.canvas.focus_set()

    def _on_mouse_move(self, point) -> None:
        if self._current_tool:
            self._current_tool.on_mouse_move(point)

    def _on_click(self, point, button) -> None:
        if self._current_tool:
            self._current_tool.on_click(point, button)

    def _on_drag(self, start, current) -> None:
        if self._current_tool:
            self._current_tool.on_drag(start, current)

    def _on_drag_end(self, start, end) -> None:
        if self._current_tool:
            self._current_tool.on_drag_end(start, end)

    def _on_double_click(self, point) -> None:
        if self._current_tool:
            self._current_tool.on_double_click(point)

    def _on_key(self, event) -> None:
        # Гарячі клавіші перемикання інструментів
        key_map = {
            "1": "select",
            "2": "line",
            "3": "wall",
            "4": "rect",
            "5": "duct",
            "6": "fitting",
            "7": "equipment",
        }
        if event.char in key_map:
            self.activate_tool(key_map[event.char])
            return
        if self._current_tool:
            self._current_tool.on_key(event)
