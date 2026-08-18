"""Smoke-тест для Етапу 4 (інтеграція з metal_cutting)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ventilation_company.cutting_integration import product_to_detail, products_to_details
from ventilation_company.metal_cutting import (
    MetalCutter,
    calculate_sheet_cutting_for_standard_products,
    estimate_metal_needed_for_standard_products,
)
from ventilation_company.standard_products import (
    RectDuct,
    RoundDuct,
    make_rect_duct,
    make_round_duct,
)


def test_rect_duct_to_detail():
    d = make_rect_duct(400, 200, 1000, 0.7)
    detail = product_to_detail(d)
    assert detail is not None
    assert detail.width > 0
    assert detail.height > 0
    # Припуски вже враховані в розмірах
    assert detail.cut_allowance == 0
    assert detail.bend_allowance == 0
    print(f"[OK] RectDuct → Detail: {detail.width:.1f}×{detail.height:.1f} мм")


def test_round_duct_to_detail():
    d = make_round_duct(250, 1000, 0.7)
    detail = product_to_detail(d)
    assert detail is not None
    assert detail.width > 0
    assert detail.height > 0
    print(f"[OK] RoundDuct → Detail: {detail.width:.1f}×{detail.height:.1f} мм")


def test_cutting_from_standard_products():
    products = [
        make_rect_duct(400, 200, 1000, 0.7, quantity=3),
        make_round_duct(250, 1000, 0.7, quantity=2),
    ]
    plan = calculate_sheet_cutting_for_standard_products(products)
    assert plan.total_sheets >= 1
    placed = sum(len(s.placed_details) for s in plan.sheets)
    assert placed == 5  # 3 + 2
    print(f"[OK] CuttingPlan: {plan.total_sheets} листів, {placed} деталей розміщено")


def test_metal_summary():
    products = [
        make_rect_duct(400, 200, 1000, 0.7, quantity=5),
    ]
    summary = estimate_metal_needed_for_standard_products(products)
    assert summary["details_count"] == 5
    assert summary["sheets_required"] >= 1
    assert summary["utilization_percent"] > 0
    assert "1250×2500" in summary["sheet_size"]
    print(f"[OK] MetalSummary: {summary['details_count']} деталей, "
          f"{summary['sheets_required']} листів, {summary['utilization_percent']}% використання")


def test_metal_cutter_new_methods():
    cutter = MetalCutter()
    products = [make_rect_duct(400, 200, 1000, 0.7)]
    details = cutter.create_details_from_standard_products(products)
    assert len(details) == 1
    plan = cutter.calculate_from_standard_products(products)
    assert plan.total_sheets >= 1
    print("[OK] MetalCutter.create_details_from_standard_products / calculate_from_standard_products")


def main():
    print("=" * 60)
    print("SMOKE-TEST ЕТАПУ 4 (metal_cutting інтеграція)")
    print("=" * 60)
    try:
        test_rect_duct_to_detail()
        test_round_duct_to_detail()
        test_cutting_from_standard_products()
        test_metal_summary()
        test_metal_cutter_new_methods()
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
