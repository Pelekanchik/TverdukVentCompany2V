"""ORM-репозиторій для роботи з типами виробів, підтипами та розмірами."""

from sqlalchemy.orm import Session

from ventilation_company.database.db import SessionLocal
from ventilation_company.database.models.product import ProductSubtype, ProductType, SizeRange


class ProductRepository:
    """CRUD для product_types, product_subtypes, size_ranges через ORM."""

    def __init__(self, db: Session):
        self.db = db

    # ── product_types ──
    def get_all_types(self) -> list[ProductType]:
        return self.db.query(ProductType).order_by(ProductType.sort_order).all()

    def get_all_subtypes(self) -> list[ProductSubtype]:
        return self.db.query(ProductSubtype).order_by(ProductSubtype.name).all()

    def get_type_by_id(self, type_id: int) -> ProductType | None:
        return self.db.query(ProductType).filter(ProductType.id == type_id).first()

    def get_type_by_slug(self, slug: str) -> ProductType | None:
        return self.db.query(ProductType).filter(ProductType.slug == slug).first()

    def add_type(self, name: str, slug: str, icon: str | None = None) -> ProductType:
        pt = ProductType(name=name, slug=slug, icon=icon)
        self.db.add(pt)
        self.db.commit()
        self.db.refresh(pt)
        return pt

    def update_type(self, type_id: int, **kwargs) -> ProductType | None:
        pt = self.get_type_by_id(type_id)
        if not pt:
            return None
        for k, v in kwargs.items():
            if hasattr(pt, k):
                setattr(pt, k, v)
        self.db.commit()
        self.db.refresh(pt)
        return pt

    def delete_type(self, type_id: int) -> bool:
        pt = self.get_type_by_id(type_id)
        if not pt:
            return False
        self.db.delete(pt)
        self.db.commit()
        return True

    # ── product_subtypes ──
    def get_subtypes_by_type(self, type_id: int) -> list[ProductSubtype]:
        return (
            self.db.query(ProductSubtype)
            .filter(ProductSubtype.product_type_id == type_id)
            .order_by(ProductSubtype.name)
            .all()
        )

    def get_subtype_by_id(self, subtype_id: int) -> ProductSubtype | None:
        return self.db.query(ProductSubtype).filter(ProductSubtype.id == subtype_id).first()

    def add_subtype(
        self,
        type_id: int,
        name: str,
        slug: str,
        formula: str,
        shape_type: str = "round",
        **kwargs,
    ) -> ProductSubtype:
        st = ProductSubtype(
            product_type_id=type_id,
            name=name,
            slug=slug,
            formula=formula,
            shape_type=shape_type,
            **kwargs,
        )
        self.db.add(st)
        self.db.commit()
        self.db.refresh(st)
        return st

    def update_subtype(self, subtype_id: int, **kwargs) -> ProductSubtype | None:
        st = self.get_subtype_by_id(subtype_id)
        if not st:
            return None
        allowed = {
            "name",
            "slug",
            "formula",
            "shape_type",
            "flange_perimeter_formula",
            "waste_factor",
            "labor_norm",
            "description",
            "is_active",
        }
        for k, v in kwargs.items():
            if k in allowed and hasattr(st, k):
                setattr(st, k, v)
        self.db.commit()
        self.db.refresh(st)
        return st

    def delete_subtype(self, subtype_id: int) -> bool:
        st = self.get_subtype_by_id(subtype_id)
        if not st:
            return False
        self.db.delete(st)
        self.db.commit()
        return True

    # ── size_ranges ──
    def get_sizes_by_subtype(self, subtype_id: int) -> list[SizeRange]:
        return self.db.query(SizeRange).filter(SizeRange.subtype_id == subtype_id).all()

    def add_size_range(
        self, subtype_id: int, param_name: str, param_label: str, **kwargs
    ) -> SizeRange:
        sr = SizeRange(
            subtype_id=subtype_id, param_name=param_name, param_label=param_label, **kwargs
        )
        self.db.add(sr)
        self.db.commit()
        self.db.refresh(sr)
        return sr

    def delete_size_range(self, size_id: int) -> bool:
        sr = self.db.query(SizeRange).filter(SizeRange.id == size_id).first()
        if not sr:
            return False
        self.db.delete(sr)
        self.db.commit()
        return True

    def delete_size(self, size_id: int) -> bool:
        """Alias for delete_size_range."""
        return self.delete_size_range(size_id)


# Зворотна сумісність
ProductRepo = ProductRepository


ProductRepo = ProductRepository(SessionLocal())
