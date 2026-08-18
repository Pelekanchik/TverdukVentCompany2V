"""Демо Етапу 3: CostEngine + покращені площі.

Запуск (з кореня проєкту):
    python demo_stage3.py
"""

from ventilation_company.standard_products import (
    RectDuct,
    RoundDuct,
    RectElbow,
    make_rect_duct,
    make_round_duct,
)


def demo():
    print("=" * 70)
    print("ЕТАП 3: ДЕМО CostEngine + ПОКРАЩЕНІ ПЛОЩІ")
    print("=" * 70)

    # --- 1. Прямокутний повітропровід ---
    duct = make_rect_duct(width=500, height=300, length=2000, thickness=0.7)
    print(f"\n1. {duct.name}")
    print(f"   Площа поверхні (surface_area): {duct.surface_area:.4f} м²")
    print(f"   Площа заготовки  (blank_area):  {duct.blank_area:.4f} м²")
    print(f"   Площа матеріалу  (material_area): {duct.material_area:.4f} м²")
    print(f"   Вага: {duct.weight:.3f} кг")
    print(f"   Ціна за шт: {duct.unit_price:.2f} грн")
    print(f"   Загальна ціна (×{duct.quantity}): {duct.total_price:.2f} грн")

    # Детальний розбив
    breakdown = duct.get_cost_breakdown()
    d = breakdown.to_dict()
    print(f"   --- Розбив собівартості ---")
    print(f"       Матеріал: {d['costs']['material']:.2f} грн")
    print(f"       Робота:   {d['costs']['labor']:.2f} грн")
    print(f"       Накладні: {d['costs']['overhead']:.2f} грн")
    print(f"       Амортиз.: {d['costs']['depreciation']:.2f} грн")
    print(f"       Базова:   {d['costs']['base']:.2f} грн")
    print(f"       Прибуток: {d['costs']['profit']:.2f} грн")
    print(f"       Без ПДВ:  {d['pricing']['price_no_vat']:.2f} грн")
    print(f"       ПДВ 20%:  {d['pricing']['vat']:.2f} грн")
    print(f"       КІНЦЕВА:  {d['pricing']['final_price']:.2f} грн")

    # --- 2. Круглий повітропровід ---
    round_duct = make_round_duct(diameter=315, length=1500, thickness=0.7)
    print(f"\n2. {round_duct.name}")
    print(f"   surface_area: {round_duct.surface_area:.4f} м²")
    print(f"   blank_area:   {round_duct.blank_area:.4f} м²")
    print(f"   material_area: {round_duct.material_area:.4f} м²")
    print(f"   Вага: {round_duct.weight:.3f} кг")
    print(f"   Ціна за шт: {round_duct.unit_price:.2f} грн")

    # --- 3. Коліно ---
    elbow = RectElbow(
        name="Коліно 500×300 90°",
        product_type="відвід прямокутний",
        width=500,
        height=300,
        length=0,
        angle=90,
        radius=150,
        top_extension=100,
        bottom_extension=100,
    )
    print(f"\n3. {elbow.name}")
    print(f"   surface_area: {elbow.surface_area:.4f} м²")
    print(f"   blank_area:   {elbow.blank_area:.4f} м²")
    print(f"   material_area: {elbow.material_area:.4f} м²")
    print(f"   Вага: {elbow.weight:.3f} кг")
    print(f"   Ціна за шт: {elbow.unit_price:.2f} грн")

    # --- 4. Порівняння зі старим методом ---
    print("\n" + "=" * 70)
    print("4. ПОРІВНЯННЯ: surface vs blank vs material (площа, м²)")
    print("=" * 70)
    print(f"{'Виріб':<35} {'surface':>10} {'blank':>10} {'material':>10}")
    print("-" * 70)
    for p in [duct, round_duct, elbow]:
        print(f"{p.name:<35} {p.surface_area:>10.4f} {p.blank_area:>10.4f} {p.material_area:>10.4f}")

    print("\n✅ Демо завершено.")


if __name__ == "__main__":
    demo()
