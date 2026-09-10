"""
Пакет GUI для VentCompany.
"""

from .cutting_tab import CuttingTab
from .products_tab import ProductsTab
from .specification_tab import SpecificationTab

# MainWindow НЕ імпортуємо тут — імпортуйте напряму:
#   from ventilation_company.gui.main_window import MainWindow

__all__ = ["ProductsTab", "SpecificationTab", "CuttingTab"]
