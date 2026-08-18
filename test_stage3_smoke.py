"""Smoke-тест для Етапу 3 (запускати вручну).

Перевіряє:
  • Імпорти модулів.
  • Створення виробів.
  • Наявність полів surface_area, blank_area, material_area.
  • CostEngine повертає CostBreakdown.
  • FlexibleConnector — float ціни (не Decimal).
"""

import sys
from pathlib import Path

# Додаємо корінь проєкту до шляху
sys.path.insert(0, str(Path(__file__).parent))

from ventilation_company.standard_products import (
    RectDuct, RoundDuct, RectElbow, RoundElbow,
    RectFlange, RoundFlange, FlexibleConnector,
    ProductLibrary, make_rect_duct, make_round_duct,
)
from ventilation_company.calculations.cost_engine import CostBreakdown, CostEngine
from ventilation_company.manufacturing_params import (
    ProductCategory, get_params, get_material_price, get_labor_rate,
    seam_allowance_for_thickness, validate_settings,
)


def test_imports():
    print("[OK] Імпорти пройшли")


def test_rect_duct():
    d = make_rect_duct(500, 300, 2000, 0.7)
    assert d.surface_area > 0
    assert d.blank_area >= d.surface_area
    assert d.material_area >= d.blank_area
    assert d.weight > 0
    assert float(d.unit_price) > 0
    print(f"[OK] RectDuct: surface={d.surface_area:.4f}, blank={d.blank_area:.4f}, material={d.material_area:.4f}")


def test_round_duct():
    d = make_round_duct(315, 1500, 0.7)
    assert d.surface_area > 0
    assert d.blank_area >= d.surface_area
    assert d.material_area >= d.blank_area
    print(f"[OK] RoundDuct: surface={d.surface_area:.4f}, blank={d.blank_area:.4f}, material={d.material_area:.4f}")


def test_elbow():
    e = RectElbow(name="Коліно", width=500, height=300, angle=90, radius=150)
    assert e.surface_area > 0
    assert e.blank_area >= e.surface_area
    print(f"[OK] RectElbow: surface={e.surface_area:.4f}, blank={e.blank_area:.4f}")


def test_cost_breakdown():
    d = make_rect_duct(500, 300, 2000, 0.7)
    bd = d.get_cost_breakdown()
    assert isinstance(bd, CostBreakdown)
    assert bd.final_price > 0
    assert bd.material_cost > 0
    assert bd.labor_cost > 0
    d_dict = bd.to_dict()
    assert "costs" in d_dict
    assert "pricing" in d_dict
    print(f"[OK] CostBreakdown: final_price={bd.final_price:.2f}")


def test_flexible_connector():
    f = FlexibleConnector(name="ГВ", width=200, height=150, length=300, quantity=2)
    # FlexibleConnector повинен мати float ціни (не Decimal), щоб уникнути помилок у тестах
    assert isinstance(f.unit_price, float)
    assert isinstance(f.total_price, float)
    expected = f.metal_area * 80.0  # поліестер
    assert abs(f.unit_price - expected) < 0.01
    assert abs(f.total_price - expected * 2) < 0.01
    print(f"[OK] FlexibleConnector: unit_price={f.unit_price:.2f}, total_price={f.total_price:.2f}")


def test_library():
    lib = ProductLibrary()
    lib.add(make_rect_duct(500, 300, 1000, 0.7))
    lib.add(make_round_duct(315, 1000, 0.7))
    assert lib.get_total_surface_area() > 0
    assert lib.get_total_blank_area() > 0
    assert lib.get_total_material_area() > 0
    assert lib.get_total_price() > 0
    print(f"[OK] ProductLibrary: {len(lib)} виробів, total_price={lib.get_total_price():.2f}")


def test_settings():
    errors = validate_settings()
    assert not errors, f"Помилки налаштувань: {errors}"
    print("[OK] manufacturing_settings.json — валідні")


def main():
    print("=" * 60)
    print("SMOKE-TEST ЕТАПУ 3")
    print("=" * 60)
    try:
        test_imports()
        test_settings()
        test_rect_duct()
        test_round_duct()
        test_elbow()
        test_cost_breakdown()
        test_flexible_connector()
        test_library()
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
