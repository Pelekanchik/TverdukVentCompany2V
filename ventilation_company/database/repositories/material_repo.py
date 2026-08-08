"""ORM-репозиторій для роботи з матеріалами."""

from sqlalchemy.orm import Session

from ventilation_company.database.db import SessionLocal
from ventilation_company.database.models.calc import CalcMaterial, SubtypeMaterial


class MaterialRepository:
    """CRUD для calc_materials, subtype_materials через ORM."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_materials(self) -> list[CalcMaterial]:
        return self.db.query(CalcMaterial).order_by(CalcMaterial.name, CalcMaterial.thickness).all()

    def get_material_by_id(self, material_id: int) -> CalcMaterial | None:
        return self.db.query(CalcMaterial).filter(CalcMaterial.id == material_id).first()

    def get_materials_by_subtype(self, subtype_id: int) -> list[CalcMaterial]:
        return (
            self.db.query(CalcMaterial)
            .join(SubtypeMaterial, CalcMaterial.id == SubtypeMaterial.material_id)
            .filter(SubtypeMaterial.subtype_id == subtype_id)
            .all()
        )

    def add_material(
        self,
        name: str,
        grade: str,
        thickness: float,
        unit: str = "мм",
        price_per_m2: float = 0.0,
        **kwargs,
    ) -> CalcMaterial:
        mat = CalcMaterial(
            name=name,
            grade=grade,
            thickness=thickness,
            unit=unit,
            price_per_m2=price_per_m2,
            **kwargs,
        )
        self.db.add(mat)
        self.db.commit()
        self.db.refresh(mat)
        return mat

    def update_material(self, material_id: int, **kwargs) -> CalcMaterial | None:
        mat = self.get_material_by_id(material_id)
        if not mat:
            return None
        allowed = {
            "name",
            "grade",
            "thickness",
            "unit",
            "price_per_m2",
            "waste_factor",
            "is_active",
        }
        for k, v in kwargs.items():
            if k in allowed and hasattr(mat, k):
                setattr(mat, k, v)
        self.db.commit()
        self.db.refresh(mat)
        return mat

    def delete_material(self, material_id: int) -> bool:
        mat = self.get_material_by_id(material_id)
        if not mat:
            return False
        self.db.delete(mat)
        self.db.commit()
        return True

    # ── subtype_materials ──
    def link_material_to_subtype(
        self, subtype_id: int, material_id: int, is_default: bool = False
    ) -> SubtypeMaterial:
        sm = SubtypeMaterial(
            subtype_id=subtype_id,
            material_id=material_id,
            is_default=1 if is_default else 0,
        )
        self.db.add(sm)
        self.db.commit()
        self.db.refresh(sm)
        return sm


# Зворотна сумісність
MaterialRepo = MaterialRepository

MaterialRepo = MaterialRepository(SessionLocal())
