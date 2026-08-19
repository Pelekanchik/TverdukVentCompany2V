"""Smoke test для Етапу 5 (GUI + БД інтеграція blank_area/material_area)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ventilation_company.standard_products import make_rect_duct
from ventilation_company.db_integration import ProjectDatabase

def test_standard_product_has_blank_and_material():
    d = make_rect_duct(400, 200, 1000, 0.7, quantity=3)
    assert d.blank_area > 0, "blank_area має бути > 0"
    assert d.material_area > 0, "material_area має бути > 0"
    assert d.material_area >= d.blank_area, "material_area >= blank_area (KIM <= 1)"
    data = d.to_dict()
    assert "blank_area_m2" in data
    assert "material_area_m2" in data
    print(f"[OK] StandardProduct: blank={d.blank_area:.4f}, material={d.material_area:.4f}")

def test_db_save_and_load():
    db = ProjectDatabase(":memory:")
    pid = db.create_project("Test Stage 5")
    d = make_rect_duct(400, 200, 1000, 0.7, quantity=3)
    product_dict = d.to_dict()
    product_dict["unit_price"] = d.unit_price
    product_dict["total_price"] = d.total_price
    db.add_product_to_project(pid, product_dict)
    
    products = db.get_project_products(pid)
    assert len(products) == 1
    p = products[0]
    assert p.get("blank_area_m2") is not None, "blank_area_m2 має бути в БД"
    assert p.get("material_area_m2") is not None, "material_area_m2 має бути в БД"
    print(f"[OK] БД: blank_area_m2={p['blank_area_m2']}, material_area_m2={p['material_area_m2']}")

def main():
    print("=" * 60)
    print("SMOKE-TEST ЕТАПУ 5 (GUI + БД інтеграція)")
    print("=" * 60)
    try:
        test_standard_product_has_blank_and_material()
        test_db_save_and_load()
        print("\n" + "=" * 60)
        print("✅ ВСІ ТЕСТИ ПРОЙДЕНІ")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n❌ ТЕСТ НЕ ПРОЙДЕНО: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ПОМИЛКА: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
