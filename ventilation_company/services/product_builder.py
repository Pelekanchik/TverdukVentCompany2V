"""Фабрика створення виробів вентиляції.

Винесено з products_tab.py для розділення GUI і бізнес-логіки.
"""

from typing import Any

from ventilation_company.standard_products import (
    FlexibleConnector,
    MaterialType,
    RectCap,
    RectDuct,
    RectElbow,
    RectFlange,
    RectTee,
    RectTransition,
    RoundCap,
    RoundDuct,
    RoundElbow,
    RoundFlange,
    RoundTee,
    RoundTransition,
    StandardProduct,
    Thickness,
    make_rect_duct,
    make_round_duct,
)


class ProductBuilder:
    """Фабрика для створення виробів з параметрів.

    Замінює великий if/elif блок у products_tab.py.
    """

    # Мапінг рядкових назв матеріалів на enum
    MATERIAL_MAP = {
        "оцинкована сталь": MaterialType.GALVANIZED,
        "нержавіюча сталь": MaterialType.STAINLESS,
        "алюміній": MaterialType.ALUMINUM,
    }

    # Мапінг рядкових назв товщин на enum
    THICKNESS_MAP = {
        "0.5": Thickness.T0_5,
        "0.7": Thickness.T0_7,
        "0.9": Thickness.T0_9,
        "1.0": Thickness.T1_0,
        "1.2": Thickness.T1_2,
        "1.5": Thickness.T1_5,
        "2.0": Thickness.T2_0,
    }

    @classmethod
    def resolve_material(cls, material_str: str) -> MaterialType:
        return cls.MATERIAL_MAP.get(material_str, MaterialType.GALVANIZED)

    @classmethod
    def resolve_thickness(cls, thickness_str: str) -> Thickness:
        return cls.THICKNESS_MAP.get(thickness_str, Thickness.T0_7)

    @classmethod
    def build(
        cls,
        ptype: str,
        selected_name: str,
        width: float,
        height: float,
        length: float,
        material_str: str,
        thickness_str: str,
        quantity: int,
        profile: float = 30.0,
        extra_params: dict[str, Any] | None = None,
        dynamic_params: dict[str, Any] | None = None,
    ) -> StandardProduct | None:
        """Створити виріб за типом і параметрами.

        Args:
            ptype: Технічний тип ("rect_duct", "round_flange" тощо)
            selected_name: Назва, яку бачить користувач
            width, height, length: Розміри (мм)
            material_str: Назва матеріалу
            thickness_str: Товщина ("0.7" тощо)
            quantity: Кількість
            profile: Розмір профілю (мм)
            extra_params: Додаткові параметри (angle, radius, branch_width тощо)
            dynamic_params: Кастомні параметри з формули

        Returns:
            Готовий об'єкт StandardProduct або None
        """
        material = cls.resolve_material(material_str)
        thickness = cls.resolve_thickness(thickness_str)
        extra = extra_params or {}

        # Кастомні вироби
        if ptype.startswith("custom_"):
            return cls._build_custom(
                selected_name, width, height, length,
                thickness, material, quantity,
                extra.get("custom_area", 0.0),
                dynamic_params,
            )

        # Стандартні вироби
        builders = {
            "rect_duct": cls._build_rect_duct,
            "round_duct": cls._build_round_duct,
            "rect_flange": cls._build_rect_flange,
            "round_flange": cls._build_round_flange,
            "rect_tee": cls._build_rect_tee,
            "round_tee": cls._build_round_tee,
            "rect_transition": cls._build_rect_transition,
            "round_transition": cls._build_round_transition,
            "rect_elbow": cls._build_rect_elbow,
            "round_elbow": cls._build_round_elbow,
            "rect_cap": cls._build_rect_cap,
            "round_cap": cls._build_round_cap,
            "flexible": cls._build_flexible,
        }

        builder = builders.get(ptype)
        if builder:
            return builder(
                width, height, length, thickness, material, quantity,
                profile, extra,
            )

        return None

    # ── Стандартні вироби ──

    @classmethod
    def _build_rect_duct(
        cls, w: float, h: float, l: float,
        thickness: Thickness, material: MaterialType, qty: int,
        profile: float, extra: dict,
    ) -> RectDuct:
        return make_rect_duct(w, h, l, thickness.value, material, qty)

    @classmethod
    def _build_round_duct(
        cls, w: float, h: float, l: float,
        thickness: Thickness, material: MaterialType, qty: int,
        profile: float, extra: dict,
    ) -> RoundDuct:
        return make_round_duct(w, l, thickness.value, material, qty)

    @classmethod
    def _build_rect_flange(
        cls, w: float, h: float, l: float,
        thickness: Thickness, material: MaterialType, qty: int,
        profile: float, extra: dict,
    ) -> RectFlange:
        return RectFlange(
            name=f"Фланець {w:.0f}×{h:.0f}",
            product_type="rect_flange",
            width=w, height=h, length=0,
            thickness=thickness, material=material, quantity=qty,
            profile=profile,
        )

    @classmethod
    def _build_round_flange(
        cls, w: float, h: float, l: float,
        thickness: Thickness, material: MaterialType, qty: int,
        profile: float, extra: dict,
    ) -> RoundFlange:
        return RoundFlange(
            name=f"Фланець Ø{w:.0f}",
            product_type="round_flange",
            width=w, height=w, length=0,
            thickness=thickness, material=material, quantity=qty,
            profile=profile,
        )

    @classmethod
    def _build_rect_tee(
        cls, w: float, h: float, l: float,
        thickness: Thickness, material: MaterialType, qty: int,
        profile: float, extra: dict,
    ) -> RectTee:
        return RectTee(
            name=f"Трійник {w:.0f}×{h:.0f}/{extra.get('branch_width', 200):.0f}×{extra.get('branch_height', 200):.0f}",
            width=w, height=h, length=l,
            thickness=thickness, material=material, quantity=qty,
            branch_width=extra.get("branch_width", 200),
            branch_height=extra.get("branch_height", 200),
            branch_length=extra.get("branch_length", 400),
            branch_offset=extra.get("branch_offset", 300),
        )

    @classmethod
    def _build_round_tee(
        cls, w: float, h: float, l: float,
        thickness: Thickness, material: MaterialType, qty: int,
        profile: float, extra: dict,
    ) -> RoundTee:
        return RoundTee(
            name=f"Трійник Ø{w:.0f}/Ø{extra.get('branch_diameter', 200):.0f}",
            width=w, height=w, length=l,
            thickness=thickness, material=material, quantity=qty,
            branch_diameter=extra.get("branch_diameter", 200),
            branch_length=extra.get("branch_length", 400),
            branch_offset=extra.get("branch_offset", 300),
        )

    @classmethod
    def _build_rect_transition(
        cls, w: float, h: float, l: float,
        thickness: Thickness, material: MaterialType, qty: int,
        profile: float, extra: dict,
    ) -> RectTransition:
        return RectTransition(
            name=f"Перехід {w:.0f}×{h:.0f}→{extra.get('end_width', 300):.0f}×{extra.get('end_height', 150):.0f}",
            width=w, height=h, length=l,
            thickness=thickness, material=material, quantity=qty,
            end_width=extra.get("end_width", 300),
            end_height=extra.get("end_height", 150),
        )

    @classmethod
    def _build_round_transition(
        cls, w: float, h: float, l: float,
        thickness: Thickness, material: MaterialType, qty: int,
        profile: float, extra: dict,
    ) -> RoundTransition:
        return RoundTransition(
            name=f"Перехід Ø{w:.0f}→Ø{extra.get('end_diameter', 300):.0f}",
            product_type="round_transition",
            width=w, height=w, length=l,
            thickness=thickness, material=material, quantity=qty,
            end_diameter=extra.get("end_diameter", 300),
        )

    @classmethod
    def _build_rect_elbow(
        cls, w: float, h: float, l: float,
        thickness: Thickness, material: MaterialType, qty: int,
        profile: float, extra: dict,
    ) -> RectElbow:
        return RectElbow(
            name=f"Відвід {w:.0f}×{h:.0f} {extra.get('angle', 90):.0f}°",
            product_type="rect_elbow",
            width=w, height=h, length=0,
            thickness=thickness, material=material, quantity=qty,
            angle=extra.get("angle", 90),
            radius=extra.get("radius", 150),
            top_extension=extra.get("top_extension", 100),
            bottom_extension=extra.get("bottom_extension", 100),
        )

    @classmethod
    def _build_round_elbow(
        cls, w: float, h: float, l: float,
        thickness: Thickness, material: MaterialType, qty: int,
        profile: float, extra: dict,
    ) -> RoundElbow:
        return RoundElbow(
            name=f"Відвід Ø{w:.0f} {extra.get('angle', 90):.0f}°",
            product_type="round_elbow",
            width=w, height=w, length=0,
            thickness=thickness, material=material, quantity=qty,
            angle=extra.get("angle", 90),
            radius=extra.get("radius", 150),
            top_extension=extra.get("top_extension", 100),
            bottom_extension=extra.get("bottom_extension", 100),
        )

    @classmethod
    def _build_rect_cap(
        cls, w: float, h: float, l: float,
        thickness: Thickness, material: MaterialType, qty: int,
        profile: float, extra: dict,
    ) -> RectCap:
        return RectCap(
            name=f"Заглушка {w:.0f}×{h:.0f}",
            product_type="rect_cap",
            width=w, height=h, length=0,
            thickness=thickness, material=material, quantity=qty,
            profile=extra.get("border", 25),
        )

    @classmethod
    def _build_round_cap(
        cls, w: float, h: float, l: float,
        thickness: Thickness, material: MaterialType, qty: int,
        profile: float, extra: dict,
    ) -> RoundCap:
        return RoundCap(
            name=f"Заглушка Ø{w:.0f}",
            product_type="round_cap",
            width=w, height=w, length=0,
            thickness=thickness, material=material, quantity=qty,
            depth=extra.get("depth", 30),
        )

    @classmethod
    def _build_flexible(
        cls, w: float, h: float, l: float,
        thickness: Thickness, material: MaterialType, qty: int,
        profile: float, extra: dict,
    ) -> FlexibleConnector:
        return FlexibleConnector(
            name=f"Гнучка вставка {w:.0f}×{h:.0f}",
            product_type="flexible",
            width=w, height=h, length=l,
            thickness=thickness, material=material, quantity=qty,
            fabric_type=extra.get("fabric_type", "поліестер"),
        )

    @classmethod
    def _build_custom(
        cls, selected_name: str, w: float, h: float, l: float,
        thickness: Thickness, material: MaterialType, qty: int,
        custom_area: float,
        dynamic_params: dict[str, Any] | None,
    ) -> StandardProduct:
        """Створити кастомний виріб."""
        dynamic = dynamic_params or {}

        class CustomProduct(StandardProduct):
            def __post_init__(self):
                self.product_type = selected_name
                super().__post_init__()

            def calculate_metal_area(self) -> float:
                return custom_area

        product = CustomProduct(
            name=selected_name,
            product_type=selected_name,
            width=w, height=h, length=l,
            thickness=thickness, material=material, quantity=qty,
        )
        product._dynamic_params = dynamic
        return product

    @classmethod
    def build_flange(
        cls,
        ptype: str,
        w: float, h: float,
        thickness: Thickness,
        material: MaterialType,
        flange_qty: int,
        profile: float,
    ) -> RectFlange | RoundFlange | None:
        """Створити фланець для повітропроводу."""
        total_qty = flange_qty
        if ptype == "rect_duct":
            return RectFlange(
                name=f"Фланець {w:.0f}×{h:.0f}",
                width=w, height=h, length=0,
                thickness=thickness, material=material,
                quantity=total_qty, profile=profile,
            )
        elif ptype == "round_duct":
            return RoundFlange(
                name=f"Фланець Ø{w:.0f}",
                width=w, height=w, length=0,
                thickness=thickness, material=material,
                quantity=total_qty, profile=profile,
            )
        return None
