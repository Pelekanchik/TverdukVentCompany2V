"""Модуль автоматичної специфікації.
Групування виробів, підрахунок, формування зведених таблиць,
експорт у різні формати (JSON, CSV, TXT, HTML).
"""

import csv
import html
import io
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class SpecItem:
    """Один рядок специфікації."""

    position: int
    name: str
    product_type: str
    dimensions: str  # наприклад "400×200×1000"
    material: str
    thickness: float
    unit: str = "шт"
    quantity: int = 1
    weight_per_unit: float = 0.0  # кг
    weight_total: float = 0.0  # кг
    area_per_unit: float = 0.0  # м²
    area_total: float = 0.0  # м²
    price_per_unit: float = 0.0  # грн
    price_total: float = 0.0  # грн
    notes: str = ""

    def __post_init__(self):
        self.weight_total = self.weight_per_unit * self.quantity
        self.area_total = self.area_per_unit * self.quantity
        self.price_total = self.price_per_unit * self.quantity


@dataclass
class Specification:
    """Повна специфікація проєкту."""

    project_name: str
    project_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    items: list[SpecItem] = field(default_factory=list)

    @property
    def total_items(self) -> int:
        return len(self.items)

    @property
    def total_quantity(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def total_weight(self) -> float:
        return sum(item.weight_total for item in self.items)

    @property
    def total_area(self) -> float:
        return sum(item.area_total for item in self.items)

    @property
    def total_price(self) -> float:
        return sum(item.price_total for item in self.items)

    def add_item(self, item: SpecItem):
        item.position = len(self.items) + 1
        self.items.append(item)

    def get_grouped_by_type(self) -> dict[str, list[SpecItem]]:
        grouped = defaultdict(list)
        for item in self.items:
            grouped[item.product_type].append(item)
        return dict(grouped)

    def get_summary_by_type(self) -> list[dict]:
        grouped = self.get_grouped_by_type()
        result = []
        for ptype, items in grouped.items():
            result.append(
                {
                    "product_type": ptype,
                    "count": len(items),
                    "total_quantity": sum(i.quantity for i in items),
                    "total_weight_kg": round(sum(i.weight_total for i in items), 3),
                    "total_area_m2": round(sum(i.area_total for i in items), 4),
                    "total_price": round(sum(i.price_total for i in items), 2),
                }
            )
        return result

    def get_summary_by_material(self) -> list[dict]:
        grouped = defaultdict(lambda: {"quantity": 0, "weight": 0.0, "area": 0.0, "price": 0.0})
        for item in self.items:
            key = (item.material, item.thickness)
            grouped[key]["quantity"] += item.quantity
            grouped[key]["weight"] += item.weight_total
            grouped[key]["area"] += item.area_total
            grouped[key]["price"] += item.price_total

        result = []
        for (material, thickness), data in grouped.items():
            result.append(
                {
                    "material": material,
                    "thickness_mm": thickness,
                    "total_quantity": data["quantity"],
                    "total_weight_kg": round(data["weight"], 3),
                    "total_area_m2": round(data["area"], 4),
                    "total_price": round(data["price"], 2),
                }
            )
        return sorted(result, key=lambda x: (x["material"], x["thickness_mm"]))

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "project_id": self.project_id,
            "created_at": self.created_at,
            "summary": {
                "total_items": self.total_items,
                "total_quantity": self.total_quantity,
                "total_weight_kg": round(self.total_weight, 3),
                "total_area_m2": round(self.total_area, 4),
                "total_price": round(self.total_price, 2),
            },
            "items": [asdict(item) for item in self.items],
            "by_type": self.get_summary_by_type(),
            "by_material": self.get_summary_by_material(),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def to_csv(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "№",
                "Найменування",
                "Тип",
                "Розміри",
                "Матеріал",
                "Товщина, мм",
                "Од. вим.",
                "Кількість",
                "Вага 1 шт, кг",
                "Вага заг., кг",
                "Площа 1 шт, м²",
                "Площа заг., м²",
                "Ціна 1 шт, грн",
                "Ціна заг., грн",
                "Примітки",
            ]
        )
        for item in self.items:
            writer.writerow(
                [
                    item.position,
                    item.name,
                    item.product_type,
                    item.dimensions,
                    item.material,
                    item.thickness,
                    item.unit,
                    item.quantity,
                    round(item.weight_per_unit, 4),
                    round(item.weight_total, 4),
                    round(item.area_per_unit, 4),
                    round(item.area_total, 4),
                    round(item.price_per_unit, 2),
                    round(item.price_total, 2),
                    item.notes,
                ]
            )
        writer.writerow([])
        writer.writerow(
            [
                "",
                "",
                "",
                "",
                "",
                "",
                "ВСЬОГО:",
                self.total_quantity,
                "",
                round(self.total_weight, 4),
                "",
                round(self.total_area, 4),
                "",
                round(self.total_price, 2),
                "",
            ]
        )
        return output.getvalue()

    def to_txt(self) -> str:
        lines = []
        lines.append("=" * 100)
        lines.append(f"СПЕЦИФІКАЦІЯ: {self.project_name}")
        lines.append(f"Дата: {self.created_at}")
        if self.project_id:
            lines.append(f"ID проєкту: {self.project_id}")
        lines.append("=" * 100)
        lines.append("")
        header = f"{'№':<4} {'Найменування':<25} {'Тип':<20} {'Розміри':<15} {'Мат.':<12} {'Товщ.':<6} {'Од.':<4} {'К-ть':<6} {'Вага, кг':<10} {'Площа, м²':<10} {'Ціна, грн':<10}"
        lines.append(header)
        lines.append("-" * 100)
        for item in self.items:
            line = (
                f"{item.position:<4} {item.name:<25} {item.product_type:<20} "
                f"{item.dimensions:<15} {item.material:<12} {item.thickness:<6.1f} "
                f"{item.unit:<4} {item.quantity:<6} {item.weight_total:<10.3f} "
                f"{item.area_total:<10.4f} {item.price_total:<10.2f}"
            )
            lines.append(line)
        lines.append("-" * 100)
        lines.append(
            f"{'':>70} ВСЬОГО: {self.total_quantity:<6} {self.total_weight:<10.3f} "
            f"{self.total_area:<10.4f} {self.total_price:<10.2f}"
        )
        lines.append("")
        lines.append("ЗВЕДЕННЯ ЗА ТИПАМИ ВИРОБІВ:")
        lines.append("-" * 60)
        for s in self.get_summary_by_type():
            lines.append(
                f"  {s['product_type']:<30} к-ть: {s['total_quantity']:<5} "
                f"вага: {s['total_weight_kg']:<8.2f} кг площа: {s['total_area_m2']:<8.3f} м²"
            )
        lines.append("")
        lines.append("ЗВЕДЕННЯ ЗА МАТЕРІАЛАМИ:")
        lines.append("-" * 60)
        for s in self.get_summary_by_material():
            lines.append(
                f"  {s['material']} {s['thickness_mm']} мм: к-ть {s['total_quantity']} шт, "
                f"вага {s['total_weight_kg']:.2f} кг, площа {s['total_area_m2']:.3f} м²"
            )
        lines.append("")
        lines.append("=" * 100)
        return "\n".join(lines)

    def to_html(self) -> str:
        rows = ""
        for item in self.items:
            rows += f"""
            <tr>
              <td>{item.position}</td>
              <td>{html.escape(item.name)}</td>
              <td>{html.escape(item.product_type)}</td>
              <td>{html.escape(item.dimensions)}</td>
              <td>{html.escape(item.material)}</td>
              <td>{item.thickness}</td>
              <td>{item.unit}</td>
              <td>{item.quantity}</td>
              <td>{item.weight_per_unit:.4f}</td>
              <td>{item.weight_total:.4f}</td>
              <td>{item.area_per_unit:.4f}</td>
              <td>{item.area_total:.4f}</td>
              <td>{item.price_per_unit:.2f}</td>
              <td>{item.price_total:.2f}</td>
              <td>{html.escape(item.notes)}</td>
            </tr>
            """
        by_type_rows = ""
        for s in self.get_summary_by_type():
            by_type_rows += f"""
            <tr>
              <td>{html.escape(s['product_type'])}</td>
              <td>{s['count']}</td>
              <td>{s['total_quantity']}</td>
              <td>{s['total_weight_kg']:.3f}</td>
              <td>{s['total_area_m2']:.4f}</td>
              <td>{s['total_price']:.2f}</td>
            </tr>
            """
        by_mat_rows = ""
        for s in self.get_summary_by_material():
            by_mat_rows += f"""
            <tr>
              <td>{html.escape(s['material'])}</td>
              <td>{s['thickness_mm']}</td>
              <td>{s['total_quantity']}</td>
              <td>{s['total_weight_kg']:.3f}</td>
              <td>{s['total_area_m2']:.4f}</td>
              <td>{s['total_price']:.2f}</td>
            </tr>
            """

        return f"""
        <!DOCTYPE html>
        <html lang="uk">
        <head>
          <meta charset="UTF-8">
          <title>Специфікація — {html.escape(self.project_name)}</title>
          <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1, h2 {{ color: #333; }}
            table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
            th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; }}
            th {{ background: #f0f0f0; }}
            .summary {{ background: #e8f5e9; font-weight: bold; }}
            .footer {{ margin-top: 30px; color: #666; font-size: 12px; }}
          </style>
        </head>
        <body>
          <h1>🏭 Специфікація виробів</h1>
          <p><strong>Проєкт:</strong> {html.escape(self.project_name)}</p>
          <p><strong>Дата:</strong> {self.created_at}</p>
          {f'<p><strong>ID:</strong> {self.project_id}</p>' if self.project_id else ''}

          <p>
            Позицій: {self.total_items} | Кількість: {self.total_quantity} шт |
            Вага: {self.total_weight:.3f} кг | Площа: {self.total_area:.4f} м² |
            Вартість: {self.total_price:.2f} грн
          </p>

          <h2>📋 Детальна специфікація</h2>
          <table>
            <thead>
              <tr>
                <th>№</th><th>Найменування</th><th>Тип</th><th>Розміри</th>
                <th>Матеріал</th><th>Товщ.</th><th>Од.</th><th>К-ть</th>
                <th>Вага 1 шт</th><th>Вага заг.</th>
                <th>Площа 1 шт</th><th>Площа заг.</th>
                <th>Ціна 1 шт</th><th>Ціна заг.</th><th>Примітки</th>
              </tr>
            </thead>
            <tbody>
              {rows}
              <tr class="summary">
                <td colspan="7">ВСЬОГО:</td>
                <td>{self.total_quantity}</td>
                <td></td><td>{self.total_weight:.4f}</td>
                <td></td><td>{self.total_area:.4f}</td>
                <td></td><td>{self.total_price:.2f}</td><td></td>
              </tr>
            </tbody>
          </table>

          <h2>📊 Зведення за типами</h2>
          <table>
            <thead>
              <tr><th>Тип виробу</th><th>Позицій</th><th>Кількість</th><th>Вага, кг</th><th>Площа, м²</th><th>Вартість, грн</th></tr>
            </thead>
            <tbody>{by_type_rows}</tbody>
          </table>

          <h2>🔧 Зведення за матеріалами</h2>
          <table>
            <thead>
              <tr><th>Матеріал</th><th>Товщина, мм</th><th>Кількість</th><th>Вага, кг</th><th>Площа, м²</th><th>Вартість, грн</th></tr>
            </thead>
            <tbody>{by_mat_rows}</tbody>
          </table>

          <p class="footer">Сформовано автоматично системою VentCompany</p>
        </body>
        </html>
        """


class SpecBuilder:
    """Білдер для автоматичного створення специфікації з виробів."""

    def __init__(self, project_name: str, project_id: str | None = None):
        self.spec = Specification(project_name=project_name, project_id=project_id)
        self._pricing = None
        try:
            from ventilation_company.gui.settings_tab import PricingSettings

            self._pricing = PricingSettings()
        except ImportError:
            pass

    def set_material_price(self, material: str, price_per_kg: float):
        """Зворотна сумісність — ігнорується, якщо PricingSettings активний."""
        pass

    def _calculate_price(self, product: dict) -> float:
        """Розрахувати ціну виробу через PricingSettings або базову формулу."""
        # Нормалізуємо ключі
        product.setdefault("metal_area", product.get("metal_area_m2", 0))
        product.setdefault("weight", product.get("weight_kg", 0))

        if self._pricing:
            return self._pricing.calculate_product_price(product)

        # Fallback: ціна через площу металу (грн/м²)
        metal_area = product.get("metal_area_m2", product.get("metal_area", 0.0))
        material = product.get("material", "оцинкована сталь")
        base_prices = {
            "оцинкована сталь": 580.0,
            "нержавіюча сталь": 1200.0,
            "алюміній": 400.0,
        }
        return metal_area * base_prices.get(material, 580.0)

    def add_product(self, product: dict):
        """Додати виріб у специфікацію."""
        name = product.get("name", "Невідомий виріб")
        ptype = product.get("type", "")
        w = product.get("width", 0)
        h = product.get("height", 0)
        length = product.get("length", 0)
        material = product.get("material", "оцинкована сталь")
        thickness = product.get("thickness", 0.7)
        qty = product.get("quantity", 1)
        weight = product.get("weight_kg", 0.0)
        area = product.get("metal_area_m2", 0.0)
        notes = product.get("notes", "")

        # Фланці — додаємо примітку
        has_flanges = product.get("has_flanges", False)
        flange_count = product.get("flange_count", 0)
        flange_price = product.get("flange_price", 0.0)
        if has_flanges and flange_count > 0:
            notes = f"{notes} (з фланцями: {flange_count} шт × {flange_price:.2f} грн)".strip()

        dimensions = f"{w}×{h}×{length}" if length else f"{w}×{h}"
        product.setdefault("metal_area", product.get("metal_area_m2", 0))
        product.setdefault("weight", product.get("weight_kg", 0))

        # Передаємо ВСІ поля product_data (включно з динамічними параметрами)
        price_per_unit = self._calculate_price(product)

        item = SpecItem(
            position=0,
            name=name,
            product_type=ptype,
            dimensions=dimensions,
            material=material,
            thickness=thickness,
            quantity=qty,
            weight_per_unit=weight,
            area_per_unit=area,
            price_per_unit=price_per_unit,
            notes=notes,
        )
        self.spec.add_item(item)

    def add_products(self, products: list[dict]):
        for p in products:
            self.add_product(p)

    def build(self) -> Specification:
        return self.spec

    def export(self, format: str = "json") -> str:
        fmt = format.lower()
        if fmt == "json":
            return self.spec.to_json()
        elif fmt == "csv":
            return self.spec.to_csv()
        elif fmt == "txt":
            return self.spec.to_txt()
        elif fmt == "html":
            return self.spec.to_html()
        else:
            raise ValueError(f"Невідомий формат: {format}")

    def save_to_file(self, filepath: str, format: str = "json"):
        content = self.export(format)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)


def build_specification_from_library(
    library, project_name: str, project_id: str | None = None, format: str = "json"
) -> str:
    """Створити специфікацію з ProductLibrary."""
    builder = SpecBuilder(project_name, project_id)
    spec_data = library.get_specification()
    for item in spec_data:
        builder.add_product(
            {
                "name": item["name"],
                "type": item["type"],
                "width": item.get("width", 0),
                "height": item.get("height", 0),
                "length": item.get("length", 0),
                "material": item["material"],
                "thickness": item["thickness"],
                "quantity": item["quantity"],
                "weight_kg": item["total_weight_kg"] / max(item["quantity"], 1),
                "metal_area_m2": item["total_area_m2"] / max(item["quantity"], 1),
            }
        )
    return builder.export(format)


def merge_specifications(specs: list[Specification], new_project_name: str) -> Specification:
    """Об'єднати кілька специфікацій в одну."""
    merged = Specification(project_name=new_project_name)
    grouped = defaultdict(
        lambda: {
            "name": "",
            "type": "",
            "dimensions": "",
            "material": "",
            "thickness": 0.0,
            "unit": "шт",
            "quantity": 0,
            "weight_per_unit": 0.0,
            "area_per_unit": 0.0,
            "price_per_unit": 0.0,
            "notes": "",
        }
    )
    for spec in specs:
        for item in spec.items:
            key = (item.name, item.dimensions, item.material, item.thickness)
            g = grouped[key]
            g["name"] = item.name
            g["type"] = item.product_type
            g["dimensions"] = item.dimensions
            g["material"] = item.material
            g["thickness"] = item.thickness
            g["unit"] = item.unit
            g["quantity"] += item.quantity
            g["weight_per_unit"] = item.weight_per_unit
            g["area_per_unit"] = item.area_per_unit
            g["price_per_unit"] = item.price_per_unit
            g["notes"] = item.notes

    for data in grouped.values():
        merged.add_item(
            SpecItem(
                position=0,
                name=data["name"],
                product_type=data["type"],
                dimensions=data["dimensions"],
                material=data["material"],
                thickness=data["thickness"],
                unit=data["unit"],
                quantity=data["quantity"],
                weight_per_unit=data["weight_per_unit"],
                area_per_unit=data["area_per_unit"],
                price_per_unit=data["price_per_unit"],
                notes=data["notes"],
            )
        )
    return merged
