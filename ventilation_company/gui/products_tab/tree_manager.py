"""Управління деревом продуктів та дії (редагування, експорт, видалення)."""

import tkinter as tk
from tkinter import ttk


def refresh_tree(tree: ttk.Treeview, products: list, prices: list[float]):
    """Оновити дерево продуктів."""
    for item in tree.get_children():
        tree.delete(item)
    for i, (product, price) in enumerate(zip(products, prices), 1):
        dims = getattr(product, "dimensions_str", None) or "—"
        tree.insert(
            "",
            tk.END,
            values=(
                i,
                getattr(product, "name", "—"),
                getattr(product, "subtype", None) or "—",
                dims,
                getattr(product, "quantity", 1),
                f"{price:,.2f}",
                getattr(product, "material", ""),
                getattr(product, "thickness", 0),
            ),
        )


def update_summary(products: list, prices: list[float]) -> dict[str, float]:
    """Оновити підсумкові дані."""
    total_qty = sum(getattr(p, "quantity", 1) for p in products)
    total_price = sum(prices)
    total_area = sum(p.calculate_metal_area() for p in products)
    return {
        "total_qty": total_qty,
        "total_price": total_price,
        "total_area": total_area,
    }
