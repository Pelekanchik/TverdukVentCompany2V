"""🏷️ Вкладка "Прайс-лист" — повноцінний модуль ціноутворення.

Можливості:
  • CRUD для позицій прайсу (власні вироби + перепродаж + послуги)
  • Два прайси: внутрішній (повний) та замовника (публічний)
  • Експорт у PDF, Excel, CSV, HTML
  • Автосинхронізація з вкладкою "Вироби" та "Архів проєктів"
  • Категорії: власне виробництво, перепродаж, монтаж, послуга
"""

from __future__ import annotations

import csv
import io
import json
import os
import tkinter as tk
import zipfile
from collections.abc import Callable
from dataclasses import asdict, dataclass, field

from ventilation_company.utils.logging_config import get_logger

_logger = get_logger("price_list")
from decimal import Decimal
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

# Спробуємо імпортувати openpyxl для Excel
HAVE_OPENPYXL = False
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    HAVE_OPENPYXL = True
except ImportError:
    pass

# Спробуємо імпортувати reportlab для PDF
HAVE_REPORTLAB = False
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    HAVE_REPORTLAB = True
except ImportError:
    pass


PRICE_LIST_FILE = "data/price_list.json"
ARCHIVE_DIR = "data/archive"


@dataclass

class PriceItem:
    """Одна позиція прайсу."""

    id: str = ""
    name: str = ""
    category: str = "власне виробництво"
    product_type: str = ""
    dimensions: str = ""
    material: str = ""
    thickness: float = 0.0
    unit: str = "шт"
    quantity: int = 1

    cost_price: Decimal = Decimal("0")
    markup_percent: float = 30.0  # % — float OK
    labor_cost: Decimal = Decimal("0")
    material_cost: Decimal = Decimal("0")
    overhead_cost: Decimal = Decimal("0")
    supplier: str = ""
    supplier_price: Decimal = Decimal("0")
    notes_internal: str = ""

    unit_price: Decimal = Decimal("0")
    total_price: Decimal = Decimal("0")
    notes_public: str = ""

    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    source: str = "manual"  # manual / products / archive
    project_id: str = ""      # ID проєкту, якщо з архіву

    def __post_init__(self):
        if not self.id:
            self.id = f"PRICE-{datetime.now().strftime('%Y%m%d%H%M%S')}-{os.urandom(2).hex()}"
        self.recalculate()

    def recalculate(self):
        from ventilation_company.utils.money import money_round
        if self.category == "перепродаж" and self.supplier_price > 0:
            base = self.supplier_price
        else:
            base = self.cost_price + self.labor_cost + self.overhead_cost
        self.unit_price = money_round(base * Decimal(str(1 + self.markup_percent / 100)))
        self.total_price = money_round(self.unit_price * Decimal(str(self.quantity)))

    @property
    def profit(self) -> Decimal:
        from ventilation_company.utils.money import money_round
        if self.category == "перепродаж" and self.supplier_price > 0:
            base = self.supplier_price
        else:
            base = self.cost_price + self.labor_cost + self.overhead_cost
        return money_round((self.unit_price - base) * Decimal(str(self.quantity)))

    def to_dict(self) -> dict:
        data = asdict(self)
        # Конвертуємо Decimal в float для JSON-серіалізації
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = float(value)
        return data
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PriceItem":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        # Конвертуємо Decimal-поля назад у Decimal (JSON зберігає як float)
        decimal_fields = {"cost_price", "labor_cost", "material_cost",
                          "overhead_cost", "supplier_price", "unit_price", "total_price"}
        for key in decimal_fields:
            if key in filtered and not isinstance(filtered[key], Decimal):
                try:
                    filtered[key] = Decimal(str(filtered[key]))
                except Exception:
                    filtered[key] = Decimal("0")
        return cls(**filtered)


class PriceListManager:
    def __init__(self, filepath: str = PRICE_LIST_FILE):
        self.filepath = filepath
        self.items: list[PriceItem] = []
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, encoding="utf-8") as f:
                    data = json.load(f)
                self.items = [PriceItem.from_dict(item) for item in data.get("items", [])]
            except Exception as e:
                _logger.error("Помилка завантаження прайс-листа: %s", e)
                self.items = []
        else:
            self.items = []

    def save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(
                {"items": [item.to_dict() for item in self.items]},
                f, ensure_ascii=False, indent=2,
            )

    def add(self, item: PriceItem) -> PriceItem:
        self.items.append(item)
        self.save()
        return item

    def update(self, item_id: str, **kwargs) -> PriceItem | None:
        for item in self.items:
            if item.id == item_id:
                for key, value in kwargs.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                item.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
                item.recalculate()
                self.save()
                return item
        return None

    def delete(self, item_id: str) -> bool:
        for i, item in enumerate(self.items):
            if item.id == item_id:
                del self.items[i]
                self.save()
                return True
        return False

    def get_by_id(self, item_id: str) -> PriceItem | None:
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def get_by_category(self, category: str) -> list[PriceItem]:
        return [item for item in self.items if item.category == category]

    def get_internal_view(self) -> list[PriceItem]:
        return list(self.items)

    def get_customer_view(self) -> list[PriceItem]:
        result = []
        for item in self.items:
            try:
                if float(item.unit_price) > 0:
                    result.append(item)
            except (TypeError, ValueError):
                pass
        return result

    def get_total_internal(self) -> dict:
        total_cost = sum(i.cost_price * i.quantity for i in self.items)
        total_price = sum(i.total_price for i in self.items)
        total_profit = sum(i.profit for i in self.items)
        return {
            "count": len(self.items),
            "total_cost": total_cost,
            "total_price": total_price,
            "total_profit": total_profit,
            "avg_markup": sum(i.markup_percent for i in self.items) / max(len(self.items), 1),
        }

    def clear(self):
        self.items.clear()
        self.save()

    def import_from_products(self, products: list[dict], project_id: str = ""):
        """Імпортувати вироби з вкладки 'Вироби' для конкретного проєкту."""
        imported = 0
        updated = 0
        
        try:
            from ventilation_company.gui.settings_tab import PricingSettings
            pricing = PricingSettings()
        except Exception:
            pricing = None
        
        for p in products:
            name = p.get("name", "Виріб")
            
            # Розрахунок складових ціни через PricingSettings
            unit_price = p.get("unit_price", 0)
            labor = 0
            overhead_total = 0
            cost_price = 0
            
            if pricing and p.get("metal_area_m2", 0) > 0:
                try:
                    data = {
                        "type": p.get("product_type", p.get("type", "")),
                        "material": p.get("material", "оцинкована сталь"),
                        "thickness": p.get("thickness", 0.5),
                        "metal_area_m2": p.get("metal_area_m2", 0),
                        "weight_kg": p.get("weight_kg", 0),
                        "quantity": p.get("quantity", 1),
                        "width": p.get("width", 0),
                        "height": p.get("height", 0),
                        "length": p.get("length", 0),
                        "profile": p.get("profile", 30.0),
                        "angle": p.get("angle", 90),
                        "radius": p.get("radius", 50),
                        "top_extension": p.get("top_extension", 100),
                        "bottom_extension": p.get("bottom_extension", 100),
                    }
                    result = pricing.calculate_product_price_detailed(data)
                    steps = result["steps"]
                    
                    if len(steps) >= 7:
                        after_waste = steps[1][1]
                        after_labor = steps[3][1]
                        after_depr = steps[4][1]
                        after_elec = steps[5][1]
                        after_overhead = steps[6][1]
                        final_price = steps[7][1] if len(steps) > 7 else after_overhead
                        
                        labor = after_labor - after_waste          # чиста робота
                        depreciation = after_depr - after_labor    # амортизація
                        electricity = after_elec - after_depr      # електроенергія
                        overhead = after_overhead - after_elec     # накладні
                        
                        unit_price = final_price
                        cost_price = after_overhead
                        overhead_total = depreciation + electricity + overhead
                except Exception:
                    pass  # використаємо fallback
            
            # Fallback, якщо PricingSettings не спрацював
            if unit_price == 0 and p.get("metal_area_m2", 0) > 0:
                metal_area = p.get("metal_area_m2", 0)
                material = p.get("material", "оцинкована сталь")
                thickness = p.get("thickness", 0.5)
                material_prices = {
                    "оцинкована сталь": {0.5: 260, 0.7: 380, 0.9: 520, 1.0: 750, 1.2: 900},
                    "нержавіюча сталь": {0.5: 350, 0.7: 500, 0.9: 700, 1.0: 1000, 1.2: 1200},
                    "алюміній": {0.5: 200, 0.7: 300, 0.9: 400, 1.0: 550, 1.2: 700},
                }
                price_per_m2 = material_prices.get(material, {}).get(thickness, 260)
                type_coef = {
                    "rect_duct": 1.15, "round_duct": 1.20,
                    "rect_flange": 1.30, "round_flange": 1.30,
                    "rect_tee": 1.50, "round_tee": 1.55,
                    "rect_transition": 1.40, "round_transition": 1.45,
                    "rect_elbow": 1.60, "round_elbow": 1.65,
                    "rect_cap": 1.25, "round_cap": 1.25,
                    "flexible": 1.0,
                }
                coef = type_coef.get(p.get("product_type", ""), 1.3)
                unit_price = metal_area * price_per_m2 * coef
                cost_price = unit_price / 1.3
                # Розподіляємо собівартість: ~75% матеріали, 10% робота, 15% накладні
                labor = cost_price * 0.10
                overhead_total = cost_price * 0.15
                cost_price = unit_price / 1.3
            
            total_price = unit_price * p.get("quantity", 1)
            
            # Конвертуємо в Decimal для безпечної роботи
            unit_price = Decimal(str(unit_price))
            cost_price = Decimal(str(cost_price))
            labor = Decimal(str(labor))
            overhead_total = Decimal(str(overhead_total))
            total_price = Decimal(str(total_price))
            
            # Шукаємо існуючий виріб
            existing = None
            for i in self.items:
                if i.name == name and i.source == "products" and i.project_id == str(project_id):
                    existing = i
                    break
            
            if existing:
                existing.unit_price = unit_price
                existing.total_price = total_price
                existing.cost_price = cost_price
                existing.labor_cost = labor
                existing.overhead_cost = overhead_total
                existing.quantity = p.get("quantity", 1)
                existing.dimensions = p.get("dimensions", "")
                existing.material = p.get("material", "")
                existing.thickness = p.get("thickness", 0)
                existing.recalculate()
                updated += 1
            existing = None
            for i in self.items:
                if i.name == name and i.source == "products" and i.project_id == str(project_id):
                    existing = i
                    break
            
            if existing:
                existing.unit_price = unit_price
                existing.total_price = total_price
                existing.cost_price = cost_price
                existing.labor_cost = labor
                existing.overhead_cost = overhead_total
                existing.quantity = p.get("quantity", 1)
                existing.dimensions = p.get("dimensions", "")
                existing.material = p.get("material", "")
                existing.thickness = p.get("thickness", 0)
                updated += 1
            else:
                item = PriceItem(
                    name=name,
                    category="власне виробництво",
                    product_type=p.get("product_type", p.get("type", "")),
                    dimensions=p.get("dimensions", ""),
                    material=p.get("material", ""),
                    thickness=p.get("thickness", 0),
                    unit="шт",
                    quantity=p.get("quantity", 1),
                    cost_price=cost_price,
                    labor_cost=labor,
                    overhead_cost=overhead_total,
                    unit_price=unit_price,
                    total_price=total_price,
                    source="products",
                    project_id=str(project_id),
                )
                self.items.append(item)
                imported += 1
        
        if imported > 0 or updated > 0:
            self.save()
        return imported

    def import_from_archive(self, project_id: str = None, db_path: str = "data/company.db") -> int:
        """Імпортувати вироби з конкретного проєкту в архіві (SQLite БД)."""
        imported = 0
        if not project_id:
            return 0
        if os.path.exists(db_path):
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT id, name FROM projects WHERE id = ?", (project_id,))
                project = cursor.fetchone()
                if not project:
                    conn.close()
                    return 0
                project_id_db = project["id"]
                project_name = project["name"]
                cursor.execute("SELECT * FROM project_products WHERE project_id = ?", (project_id_db,))
                products = cursor.fetchall()
                for p in products:
                    item_name = p["name"]
                    if not item_name:
                        continue
                    exists = any(
                        i.name == item_name and i.project_id == str(project_id_db) and i.source == "archive"
                        for i in self.items
                    )
                    if exists:
                        continue
                    w = p["width"] or 0
                    h = p["height"] or 0
                    l = p["length"] or 0
                    dims = f"{w}×{h}×{l}" if l else f"{w}×{h}"
                    unit_price = p["unit_price"] or 0
                    qty = p["quantity"] or 1
                    if unit_price == 0 and p["metal_area_m2"]:
                        material_prices = {"оцинкована сталь": 120.0, "нержавіюча сталь": 350.0, "алюміній": 200.0}
                        area = p["metal_area_m2"] or 0
                        mat = p["material"] or "оцинкована сталь"
                        price_per_m2 = material_prices.get(mat, 120.0)
                        unit_price = area * (price_per_m2 + 50)
                    total_price = unit_price * qty
                    cost = Decimal(str(unit_price)) / Decimal("1.3") if unit_price > 0 else Decimal("0")
                    item = PriceItem(
                        name=item_name,
                        category="власне виробництво",
                        product_type=p["product_type"] or "",
                        dimensions=dims,
                        material=p["material"] or "",
                        thickness=p["thickness"] or 0,
                        unit="шт",
                        quantity=qty,
                        cost_price=Decimal(str(cost)),
                        labor_cost=Decimal("0"),
                        overhead_cost=Decimal("0"),
                        unit_price=Decimal(str(unit_price)),
                        total_price=Decimal(str(total_price)),
                        source="archive",
                        project_id=str(project_id_db),
                        notes_internal=f"З проєкту: {project_name}",
                    )

                    self.items.append(item)
                    imported += 1
                conn.close()
                if imported > 0:
                    self.save()
                return imported
            except Exception as e:
                _logger.error("Помилка читання прайс-листа з БД: %s", e)
        return 0

    def _import_from_zip_archives(self, archive_dir: str = ARCHIVE_DIR) -> int:
        """Імпортувати вироби з ZIP-архівів (старий формат)."""
        imported = 0
        if not os.path.exists(archive_dir):
            return 0

        for filename in os.listdir(archive_dir):
            if not filename.endswith(".zip"):
                continue
            zip_path = os.path.join(archive_dir, filename)
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for name in zf.namelist():
                        if not name.endswith(".json"):
                            continue
                        data = json.loads(zf.read(name).decode("utf-8"))
                        for p in data.get("products", []):
                            item_name = p.get("name", "")
                            if not item_name:
                                continue
                            exists = any(
                                i.name == item_name and i.source == "archive"
                                for i in self.items
                            )
                            if exists:
                                continue
                            item = PriceItem(
                                name=item_name,
                                category="власне виробництво",
                                product_type=p.get("product_type", ""),
                                dimensions=p.get("dimensions", ""),
                                material=p.get("material", ""),
                                thickness=p.get("thickness", 0),
                                unit="шт",
                                quantity=p.get("quantity", 1),
                                cost_price=Decimal(str(p.get("cost_price", 0))),
                                unit_price=Decimal(str(p.get("unit_price", 0))),
                                total_price=Decimal(str(p.get("total_price", 0))),
                                source="archive",
                                notes_internal=f"З архіву: {filename}",
                            )
                            imported += 1
            except Exception as e:
                _logger.error("Помилка читання архіву %s: %s", filename, e)
        if imported > 0:
            self.save()
        return imported
