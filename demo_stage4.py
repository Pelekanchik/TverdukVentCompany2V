"""Демо Етапу 4: Інтеграція StandardProduct з metal_cutting.

Запуск (з кореня проєкту):
    python demo_stage4.py
"""

from ventilation_company.standard_products import (
    ProductLibrary,
    make_rect_duct,
    make_round_duct,
)
from ventilation_company.metal_cutting import estimate_metal_needed_for_standard_products


def demo():
    print("=" * 70)
    print("ЕТАП 4: ІНТЕГРАЦІЯ З METAL_CUTTING")
    print("=" * 70)

    # Створюємо бібліотеку виробів
    lib = ProductLibrary()
    lib.add(make_rect_duct(400, 200, 1000, 0.7, quantity=3))
    lib.add(make_rect_duct(400, 200, 1500, 0.7, quantity=5))
    lib.add(make_round_duct(315, 1500, 0.7, quantity=4))
    lib.add(make_round_duct(250, 1000, 0.7, quantity=6))

    print(f"\n1. Бібліотека виробів: {len(lib)} позицій")
    print(f"   Загальна blank_area:  {lib.get_total_blank_area():.3f} м²")
    print(f"   Загальна material_area: {lib.get_total_material_area():.3f} м²")
    print(f"   Загальна ціна:        {lib.get_total_price():.2f} грн")

    # Розкрій з StandardProduct
    print("\n2. РОЗКРІЙ З STANDARDPRODUCT (точні розміри заготовок)")
    summary = estimate_metal_needed_for_standard_products(lib.products)
    print(f"   Кількість деталей:    {summary['details_count']}")
    print(f"   Площа деталей:        {summary['details_area_m2']} м²")
    print(f"   Потрібно листів:      {summary['sheets_required']}")
    print(f"   Розмір листа:         {summary['sheet_size']}")
    print(f"   Загальна площа листів: {summary['total_metal_area_m2']} м²")
    print(f"   Відходи:              {summary['waste_percent']}%")
    print(f"   Використання:         {summary['utilization_percent']}%")

    # Деталі по листах
    plan = summary["plan"]
    print(f"\n3. ДЕТАЛІЗАЦІЯ ПО ЛИСТАХ ({len(plan['sheets'])} листів)")
    for i, sheet in enumerate(plan["sheets"], 1):
        print(f"   Лист {i}: {sheet['sheet_size']} | "
              f"деталей: {sheet['details_count']} | "
              f"використання: {sheet['utilization_percent']}%")

    print("\n✅ Демо Етапу 4 завершено.")


if __name__ == "__main__":
    demo()
