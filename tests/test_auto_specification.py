"""Тести для автоматичної специфікації (auto_specification)."""

import json

import pytest

from ventilation_company.auto_specification import (
    SpecBuilder,
    SpecItem,
    Specification,
    build_specification_from_library,
    merge_specifications,
)
from ventilation_company.standard_products import ProductLibrary, RectDuct


class TestSpecItem:
    """Тести для рядка специфікації."""

    def test_creation(self):
        item = SpecItem(
            position=1,
            name="Повітропровід 400×200",
            product_type="повітропровід прямокутний",
            dimensions="400×200×1000",
            material="оцинкована сталь",
            thickness=0.7,
            quantity=5,
            weight_per_unit=12.5,
            area_per_unit=1.2,
            price_per_unit=850.0,
        )
        assert item.position == 1
        assert item.name == "Повітропровід 400×200"
        assert item.weight_total == 62.5  # 12.5 * 5
        assert item.area_total == 6.0  # 1.2 * 5
        assert item.price_total == 4250.0  # 850 * 5

    def test_zero_quantity(self):
        item = SpecItem(
            position=1,
            name="Тест",
            product_type="тест",
            dimensions="100×100",
            material="сталь",
            thickness=0.5,
            quantity=0,
            weight_per_unit=10.0,
            area_per_unit=1.0,
            price_per_unit=100.0,
        )
        assert item.weight_total == 0
        assert item.price_total == 0


class TestSpecification:
    """Тести для повної специфікації."""

    def test_empty_spec(self):
        spec = Specification(project_name="Тест")
        assert spec.total_items == 0
        assert spec.total_quantity == 0
        assert spec.total_weight == 0
        assert spec.total_area == 0
        assert spec.total_price == 0

    def test_add_item(self):
        spec = Specification(project_name="Тест")
        item = SpecItem(
            position=0,
            name="ПП",
            product_type="повітропровід",
            dimensions="400×200×1000",
            material="оцинкована сталь",
            thickness=0.7,
            quantity=2,
            weight_per_unit=10.0,
            area_per_unit=1.0,
            price_per_unit=500.0,
        )
        spec.add_item(item)
        assert spec.total_items == 1
        assert spec.total_quantity == 2
        assert spec.total_weight == 20.0
        assert spec.total_price == 1000.0
        assert item.position == 1  # автоматично призначено

    def test_add_multiple_items(self):
        spec = Specification(project_name="Тест")
        for i in range(3):
            spec.add_item(
                SpecItem(
                    position=0,
                    name=f"ПП{i}",
                    product_type="повітропровід",
                    dimensions="400×200×1000",
                    material="оцинкована сталь",
                    thickness=0.7,
                    quantity=1,
                    weight_per_unit=10.0,
                    area_per_unit=1.0,
                    price_per_unit=500.0,
                )
            )
        assert spec.total_items == 3
        assert spec.total_quantity == 3
        # Перевірка автоматичної нумерації
        assert spec.items[0].position == 1
        assert spec.items[1].position == 2
        assert spec.items[2].position == 3

    def test_get_grouped_by_type(self):
        spec = Specification(project_name="Тест")
        spec.add_item(
            SpecItem(
                position=0, name="ПП1", product_type="повітропровід",
                dimensions="400×200", material="сталь", thickness=0.7,
                quantity=1, weight_per_unit=10, area_per_unit=1, price_per_unit=500,
            )
        )
        spec.add_item(
            SpecItem(
                position=0, name="Ф1", product_type="фланець",
                dimensions="400×200", material="сталь", thickness=0.7,
                quantity=1, weight_per_unit=5, area_per_unit=0.5, price_per_unit=200,
            )
        )
        grouped = spec.get_grouped_by_type()
        assert "повітропровід" in grouped
        assert "фланець" in grouped
        assert len(grouped["повітропровід"]) == 1
        assert len(grouped["фланець"]) == 1

    def test_get_summary_by_type(self):
        spec = Specification(project_name="Тест")
        spec.add_item(
            SpecItem(
                position=0, name="ПП1", product_type="повітропровід",
                dimensions="400×200", material="сталь", thickness=0.7,
                quantity=2, weight_per_unit=10, area_per_unit=1, price_per_unit=500,
            )
        )
        spec.add_item(
            SpecItem(
                position=0, name="ПП2", product_type="повітропровід",
                dimensions="300×150", material="сталь", thickness=0.7,
                quantity=3, weight_per_unit=8, area_per_unit=0.8, price_per_unit=400,
            )
        )
        summary = spec.get_summary_by_type()
        assert len(summary) == 1
        assert summary[0]["product_type"] == "повітропровід"
        assert summary[0]["count"] == 2
        assert summary[0]["total_quantity"] == 5
        assert summary[0]["total_weight_kg"] == 44.0  # 2*10 + 3*8
        assert summary[0]["total_price"] == 2200.0  # 2*500 + 3*400

    def test_get_summary_by_material(self):
        spec = Specification(project_name="Тест")
        spec.add_item(
            SpecItem(
                position=0, name="ПП1", product_type="повітропровід",
                dimensions="400×200", material="оцинкована сталь", thickness=0.7,
                quantity=2, weight_per_unit=10, area_per_unit=1, price_per_unit=500,
            )
        )
        spec.add_item(
            SpecItem(
                position=0, name="ПП2", product_type="повітропровід",
                dimensions="300×150", material="нержавіюча сталь", thickness=0.8,
                quantity=1, weight_per_unit=15, area_per_unit=1.5, price_per_unit=1200,
            )
        )
        summary = spec.get_summary_by_material()
        assert len(summary) == 2
        materials = [s["material"] for s in summary]
        assert "оцинкована сталь" in materials
        assert "нержавіюча сталь" in materials

    def test_to_dict(self):
        spec = Specification(project_name="Тест", project_id="PRJ-001")
        spec.add_item(
            SpecItem(
                position=0, name="ПП", product_type="повітропровід",
                dimensions="400×200", material="сталь", thickness=0.7,
                quantity=1, weight_per_unit=10, area_per_unit=1, price_per_unit=500,
            )
        )
        d = spec.to_dict()
        assert d["project_name"] == "Тест"
        assert d["project_id"] == "PRJ-001"
        assert "summary" in d
        assert "items" in d
        assert "by_type" in d
        assert "by_material" in d
        assert d["summary"]["total_items"] == 1

    def test_to_json(self):
        spec = Specification(project_name="Тест")
        spec.add_item(
            SpecItem(
                position=0, name="ПП", product_type="повітропровід",
                dimensions="400×200", material="сталь", thickness=0.7,
                quantity=1, weight_per_unit=10, area_per_unit=1, price_per_unit=500,
            )
        )
        json_str = spec.to_json()
        data = json.loads(json_str)
        assert data["project_name"] == "Тест"
        assert len(data["items"]) == 1

    def test_to_csv(self):
        spec = Specification(project_name="Тест")
        spec.add_item(
            SpecItem(
                position=0, name="ПП", product_type="повітропровід",
                dimensions="400×200", material="сталь", thickness=0.7,
                quantity=1, weight_per_unit=10, area_per_unit=1, price_per_unit=500,
            )
        )
        csv_str = spec.to_csv()
        assert "ПП" in csv_str
        assert "ВСЬОГО:" in csv_str
        assert "500" in csv_str

    def test_to_txt(self):
        spec = Specification(project_name="Тест")
        spec.add_item(
            SpecItem(
                position=0, name="ПП", product_type="повітропровід",
                dimensions="400×200", material="сталь", thickness=0.7,
                quantity=1, weight_per_unit=10, area_per_unit=1, price_per_unit=500,
            )
        )
        txt = spec.to_txt()
        assert "СПЕЦИФІКАЦІЯ" in txt
        assert "ПП" in txt
        assert "ВСЬОГО:" in txt

    def test_to_html(self):
        spec = Specification(project_name="Тест")
        spec.add_item(
            SpecItem(
                position=0, name="ПП", product_type="повітропровід",
                dimensions="400×200", material="сталь", thickness=0.7,
                quantity=1, weight_per_unit=10, area_per_unit=1, price_per_unit=500,
            )
        )
        html = spec.to_html()
        assert "<!DOCTYPE html>" in html
        assert "ПП" in html
        assert "</html>" in html


class TestSpecBuilder:
    """Тести для білдера специфікації."""

    def test_creation(self):
        builder = SpecBuilder(project_name="Проєкт А", project_id="PRJ-001")
        spec = builder.build()
        assert spec.project_name == "Проєкт А"
        assert spec.project_id == "PRJ-001"

    def test_add_product(self):
        builder = SpecBuilder(project_name="Тест")
        builder.add_product({
            "name": "Повітропровід 400×200",
            "type": "повітропровід прямокутний",
            "width": 400,
            "height": 200,
            "length": 1000,
            "material": "оцинкована сталь",
            "thickness": 0.7,
            "quantity": 3,
            "weight_kg": 12.5,
            "metal_area_m2": 1.2,
        })
        spec = builder.build()
        assert spec.total_items == 1
        assert spec.total_quantity == 3

    def test_add_products(self):
        builder = SpecBuilder(project_name="Тест")
        products = [
            {"name": "ПП1", "type": "повітропровід", "width": 400, "height": 200, "length": 1000,
             "material": "сталь", "thickness": 0.7, "quantity": 2, "weight_kg": 10, "metal_area_m2": 1},
            {"name": "ПП2", "type": "повітропровід", "width": 300, "height": 150, "length": 800,
             "material": "сталь", "thickness": 0.7, "quantity": 1, "weight_kg": 8, "metal_area_m2": 0.8},
        ]
        builder.add_products(products)
        spec = builder.build()
        assert spec.total_items == 2
        assert spec.total_quantity == 3

    def test_export_json(self):
        builder = SpecBuilder(project_name="Тест")
        builder.add_product({
            "name": "ПП", "type": "повітропровід", "width": 400, "height": 200, "length": 1000,
            "material": "сталь", "thickness": 0.7, "quantity": 1, "weight_kg": 10, "metal_area_m2": 1,
        })
        result = builder.export("json")
        data = json.loads(result)
        assert data["project_name"] == "Тест"

    def test_export_csv(self):
        builder = SpecBuilder(project_name="Тест")
        builder.add_product({
            "name": "ПП", "type": "повітропровід", "width": 400, "height": 200, "length": 1000,
            "material": "сталь", "thickness": 0.7, "quantity": 1, "weight_kg": 10, "metal_area_m2": 1,
        })
        result = builder.export("csv")
        assert "ПП" in result

    def test_export_txt(self):
        builder = SpecBuilder(project_name="Тест")
        builder.add_product({
            "name": "ПП", "type": "повітропровід", "width": 400, "height": 200, "length": 1000,
            "material": "сталь", "thickness": 0.7, "quantity": 1, "weight_kg": 10, "metal_area_m2": 1,
        })
        result = builder.export("txt")
        assert "СПЕЦИФІКАЦІЯ" in result

    def test_export_html(self):
        builder = SpecBuilder(project_name="Тест")
        builder.add_product({
            "name": "ПП", "type": "повітропровід", "width": 400, "height": 200, "length": 1000,
            "material": "сталь", "thickness": 0.7, "quantity": 1, "weight_kg": 10, "metal_area_m2": 1,
        })
        result = builder.export("html")
        assert "<!DOCTYPE html>" in result

    def test_export_unknown_format_raises(self):
        builder = SpecBuilder(project_name="Тест")
        with pytest.raises(ValueError, match="Невідомий формат"):
            builder.export("xml")

    def test_add_product_with_flanges(self):
        builder = SpecBuilder(project_name="Тест")
        builder.add_product({
            "name": "ПП з фланцями",
            "type": "повітропровід",
            "width": 400, "height": 200, "length": 1000,
            "material": "сталь", "thickness": 0.7, "quantity": 1,
            "weight_kg": 10, "metal_area_m2": 1,
            "has_flanges": True,
            "flange_count": 2,
            "flange_price": 150.0,
        })
        spec = builder.build()
        assert "фланцями" in spec.items[0].notes

    def test_save_to_file(self, tmp_path):
        builder = SpecBuilder(project_name="Тест")
        builder.add_product({
            "name": "ПП", "type": "повітропровід", "width": 400, "height": 200, "length": 1000,
            "material": "сталь", "thickness": 0.7, "quantity": 1, "weight_kg": 10, "metal_area_m2": 1,
        })
        filepath = tmp_path / "spec.json"
        builder.save_to_file(str(filepath), format="json")
        assert filepath.exists()
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        assert data["project_name"] == "Тест"


class TestBuildSpecificationFromLibrary:
    """Тести створення специфікації з бібліотеки."""

    def test_from_library(self):
        """Створення специфікації з ProductLibrary (баг виправлено)."""
        lib = ProductLibrary()
        lib.add(RectDuct(name="ПП 400×200", width=400, height=200, length=1000, quantity=2))
        result = build_specification_from_library(lib, "Проєкт Б", format="json")
        data = json.loads(result)
        assert data["project_name"] == "Проєкт Б"
        assert data["summary"]["total_quantity"] == 2
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "ПП 400×200"


class TestMergeSpecifications:
    """Тести об'єднання специфікацій."""

    def test_merge_two_specs(self):
        spec1 = Specification(project_name="П1")
        spec1.add_item(SpecItem(
            position=0, name="ПП", product_type="повітропровід",
            dimensions="400×200", material="сталь", thickness=0.7,
            quantity=2, weight_per_unit=10, area_per_unit=1, price_per_unit=500,
        ))

        spec2 = Specification(project_name="П2")
        spec2.add_item(SpecItem(
            position=0, name="ПП", product_type="повітропровід",
            dimensions="400×200", material="сталь", thickness=0.7,
            quantity=3, weight_per_unit=10, area_per_unit=1, price_per_unit=500,
        ))

        merged = merge_specifications([spec1, spec2], "Об'єднаний")
        assert merged.project_name == "Об'єднаний"
        assert merged.total_items == 1
        assert merged.total_quantity == 5  # 2 + 3

    def test_merge_different_items(self):
        spec1 = Specification(project_name="П1")
        spec1.add_item(SpecItem(
            position=0, name="ПП", product_type="повітропровід",
            dimensions="400×200", material="сталь", thickness=0.7,
            quantity=1, weight_per_unit=10, area_per_unit=1, price_per_unit=500,
        ))

        spec2 = Specification(project_name="П2")
        spec2.add_item(SpecItem(
            position=0, name="Фланець", product_type="фланець",
            dimensions="400×200", material="сталь", thickness=0.7,
            quantity=2, weight_per_unit=5, area_per_unit=0.5, price_per_unit=200,
        ))

        merged = merge_specifications([spec1, spec2], "Об'єднаний")
        assert merged.total_items == 2
        assert merged.total_quantity == 3
