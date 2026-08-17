"""Єдиний шар роботи з БД через SQLAlchemy ORM.

Покращення v2.1:
  • Повністю переписано з raw sqlite3 на SQLAlchemy ORM.
  • Збережено API ProjectDatabase (ті ж методи, ті ж типи повернення).
  • Транзакції через session.begin() / commit() / rollback().
  • Всі ORM-об'єкти конвертуються в dict для зворотної сумісності з GUI.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Generator

from sqlalchemy import func, inspect
from sqlalchemy.orm import Session

from ventilation_company.database.db import SessionLocal
from ventilation_company.database.models.project import Project
from ventilation_company.database.models.unified import (
    Client,
    ClientProject,
    CuttingPlan,
    Interaction,
    MaterialPrice,
    Payment,
    ProjectProduct,
    Specification,
    StandardProductLibrary,
    WarrantyReminder,
)


class TransactionError(Exception):
    """Помилка транзакції БД."""
    pass


def _row_to_dict(obj) -> dict | None:
    """Конвертувати SQLAlchemy ORM об'єкт у dict (як sqlite3.Row)."""
    if obj is None:
        return None
    result = {}
    for col in inspect(obj).mapper.column_attrs:
        key = col.key
        val = getattr(obj, key)
        if isinstance(val, datetime):
            val = val.isoformat()
        # Зворотна сумісність: metadata_json → metadata
        if key == "metadata_json":
            key = "metadata"
        result[key] = val
    return result


def _rows_to_dicts(rows: list) -> list[dict]:
    """Конвертувати список ORM об'єктів у список dict."""
    return [_row_to_dict(r) for r in rows if r is not None]


class ProjectDatabase:
    """Єдиний менеджер БД для вентиляційних проєктів (SQLAlchemy ORM)."""

    def __init__(self, db_path: str = "data/company.db"):
        # db_path ігнорується — використовуємо SessionLocal з db.py,
        # але зберігаємо для зворотної сумісності API.
        self.db_path = db_path

    @contextmanager
    def _session_scope(self) -> Generator[Session, None, None]:
        """Контекстний менеджер для сесій з автоматичним commit/rollback."""
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as exc:
            session.rollback()
            raise TransactionError(f"Помилка транзакції БД: {exc}") from exc
        finally:
            session.close()

    # ═══════════════════════════════════════════════════════════════
    # ПРОЄКТИ
    # ═══════════════════════════════════════════════════════════════

    def create_project(
        self,
        name: str,
        description: str = "",
        client: str = "",
        metadata: dict | None = None,
        **extra_fields,
    ) -> int:
        """Створити новий проєкт."""
        with self._session_scope() as session:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            project = Project(
                project_number=f"PRJ-{timestamp}",
                name=name,
                description=description,
                client=client,
                metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata else None,
                status="draft",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                total_area=0.0,
                customer_price=0.0,
                cost_price=0.0,
                salary_total=0.0,
                profit=0.0,
            )
            # Додаткові поля
            for key, value in extra_fields.items():
                if hasattr(project, key):
                    setattr(project, key, value)

            session.add(project)
            session.flush()  # отримати id до commit
            return project.id

    def get_project(self, project_id: int) -> dict | None:
        """Отримати проєкт за ID."""
        with self._session_scope() as session:
            project = session.get(Project, project_id)
            return _row_to_dict(project)

    def get_all_projects(self, status: str | None = None) -> list[dict]:
        """Отримати всі проєкти (або за статусом)."""
        with self._session_scope() as session:
            query = session.query(Project)
            if status:
                query = query.filter(Project.status == status)
            rows = query.order_by(Project.updated_at.desc()).all()
            return _rows_to_dicts(rows)

    def list_projects(self, status: str | None = None) -> list[dict]:
        """Alias для get_all_projects."""
        return self.get_all_projects(status)

    def update_project(self, project_id: int, **kwargs) -> bool:
        """Оновити проєкт."""
        allowed = {
            "name", "description", "client", "status", "metadata",
            "drawing_path", "customer_price", "cost_price",
            "salary_total", "profit", "notes", "total_area",
            "ventilation_type", "air_flow", "pressure", "address",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        if "metadata" in updates and isinstance(updates["metadata"], dict):
            updates["metadata_json"] = json.dumps(updates.pop("metadata"), ensure_ascii=False)

        with self._session_scope() as session:
            project = session.get(Project, project_id)
            if not project:
                return False
            for k, v in updates.items():
                if hasattr(project, k):
                    setattr(project, k, v)
            project.updated_at = datetime.now()
            return True

    def delete_project(self, project_id: int) -> bool:
        """Видалити проєкт (каскадне видалення через ORM)."""
        with self._session_scope() as session:
            project = session.get(Project, project_id)
            if not project:
                return False
            session.delete(project)
            return True

    def duplicate_project(self, project_id: int, new_name: str | None = None) -> int:
        """Дублювати проєкт з усіма виробами."""
        with self._session_scope() as session:
            project = session.get(Project, project_id)
            if not project:
                raise ValueError(f"Проєкт {project_id} не знайдено")

            # Новий проєкт
            new_project = Project(
                project_number=f"PRJ-{datetime.now().strftime("%Y%m%d-%H%M%S")}",
                name=new_name or f"{project.name} (копія)",
                description=project.description,
                client=project.client,
                status="draft",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                total_area=project.total_area,
                drawing_path=project.drawing_path,
                customer_price=0.0,
                cost_price=0.0,
                salary_total=0.0,
                profit=0.0,
            )
            session.add(new_project)
            session.flush()

            # Копіюємо вироби
            for p in project.project_products:
                new_product = ProjectProduct(
                    project_id=new_project.id,
                    name=p.name,
                    product_type=p.product_type,
                    width=p.width,
                    height=p.height,
                    length=p.length,
                    thickness=p.thickness,
                    material=p.material,
                    quantity=p.quantity,
                    metal_area_m2=p.metal_area_m2,
                    weight_kg=p.weight_kg,
                    unit_price=p.unit_price,
                    total_price=p.total_price,
                    notes=p.notes,
                )
                session.add(new_product)

            return new_project.id

    # ── Хелпери для транзакцій (працюють з існуючою сесією) ──

    def _create_project_in_conn(
        self, session: Session, name: str,
        description: str = "", client: str = "",
        metadata: dict | None = None,
    ) -> int:
        """Створити проєкт у межах транзакції."""
        project = Project(
            project_number=f"PRJ-{datetime.now().strftime("%Y%m%d-%H%M%S")}",
            name=name,
            description=description,
            client=client,
            metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata else None,
            status="draft",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        session.add(project)
        session.flush()
        return project.id

    def _get_project_products_in_conn(
        self, session: Session, project_id: int
    ) -> list[dict]:
        """Отримати вироби проєкту у межах транзакції."""
        rows = (
            session.query(ProjectProduct)
            .filter(ProjectProduct.project_id == project_id)
            .order_by(ProjectProduct.id)
            .all()
        )
        return _rows_to_dicts(rows)

    def _add_product_to_project_in_conn(
        self, session: Session, project_id: int, product: dict
    ) -> int:
        """Додати виріб у межах транзакції."""
        pp = ProjectProduct(
            project_id=project_id,
            name=product.get("name", ""),
            product_type=product.get("product_type", ""),
            width=product.get("width", 0),
            height=product.get("height", 0),
            length=product.get("length", 0),
            thickness=product.get("thickness", 0.7),
            material=product.get("material", "оцинкована сталь"),
            quantity=product.get("quantity", 1),
            metal_area_m2=product.get("metal_area_m2", 0),
            weight_kg=product.get("weight_kg", 0),
            unit_price=product.get("unit_price", 0),
            total_price=product.get("total_price", 0),
            notes=product.get("notes", ""),
        )
        session.add(pp)
        session.flush()
        return pp.id

    # ═══════════════════════════════════════════════════════════════
    # ВИРОБИ В ПРОЄКТІ
    # ═══════════════════════════════════════════════════════════════

    def add_product_to_project(self, project_id: int, product: dict) -> int:
        """Додати виріб до проєкту."""
        with self._session_scope() as session:
            product_id = self._add_product_to_project_in_conn(session, project_id, product)
            project = session.get(Project, project_id)
            if project:
                project.updated_at = datetime.now()
            return product_id

    def get_project_products(self, project_id: int) -> list[dict]:
        """Отримати всі вироби проєкту."""
        with self._session_scope() as session:
            return self._get_project_products_in_conn(session, project_id)

    def update_product(self, product_id: int, **kwargs) -> bool:
        """Оновити виріб."""
        allowed = {
            "name", "product_type", "width", "height", "length",
            "thickness", "material", "quantity", "metal_area_m2",
            "weight_kg", "notes", "unit_price", "total_price",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        with self._session_scope() as session:
            product = session.get(ProjectProduct, product_id)
            if not product:
                return False
            for k, v in updates.items():
                setattr(product, k, v)
            return True

    def delete_product(self, product_id: int) -> bool:
        """Видалити виріб."""
        with self._session_scope() as session:
            product = session.get(ProjectProduct, product_id)
            if not product:
                return False
            session.delete(product)
            return True

    def get_project_summary(self, project_id: int) -> dict:
        """Отримати зведення по проєкту."""
        with self._session_scope() as session:
            result = (
                session.query(
                    func.count(ProjectProduct.id).label("total_items"),
                    func.coalesce(func.sum(ProjectProduct.quantity), 0).label("total_quantity"),
                    func.coalesce(func.sum(ProjectProduct.weight_kg * ProjectProduct.quantity), 0).label("total_weight"),
                    func.coalesce(func.sum(ProjectProduct.metal_area_m2 * ProjectProduct.quantity), 0).label("total_area"),
                )
                .filter(ProjectProduct.project_id == project_id)
                .first()
            )
            return {
                "total_items": result.total_items or 0,
                "total_quantity": result.total_quantity or 0,
                "total_weight": float(result.total_weight or 0),
                "total_area": float(result.total_area or 0),
            }

    # ═══════════════════════════════════════════════════════════════
    # СПЕЦИФІКАЦІЇ
    # ═══════════════════════════════════════════════════════════════

    def save_specification(
        self,
        project_id: int,
        spec_data: dict,
        name: str = "Специфікація",
        format: str = "json",
    ) -> int:
        """Зберегти специфікацію проєкту."""
        content = (
            spec_data
            if isinstance(spec_data, str)
            else json.dumps(spec_data, ensure_ascii=False)
        )
        summary = spec_data.get("summary", {}) if isinstance(spec_data, dict) else {}

        with self._session_scope() as session:
            spec = Specification(
                project_id=project_id,
                name=name,
                format=format,
                content=content,
                total_items=summary.get("total_items", 0),
                total_quantity=summary.get("total_quantity", 0),
                total_weight_kg=summary.get("total_weight_kg", 0),
                total_area_m2=summary.get("total_area_m2", 0),
                total_price=summary.get("total_price", 0),
            )
            session.add(spec)
            session.flush()
            return spec.id

    def get_specifications(self, project_id: int) -> list[dict]:
        """Отримати всі специфікації проєкту."""
        with self._session_scope() as session:
            rows = (
                session.query(Specification)
                .filter(Specification.project_id == project_id)
                .order_by(Specification.created_at.desc())
                .all()
            )
            return _rows_to_dicts(rows)

    def get_specification(self, spec_id: int) -> dict | None:
        """Отримати специфікацію за ID."""
        with self._session_scope() as session:
            spec = session.get(Specification, spec_id)
            data = _row_to_dict(spec)
            if data and data.get("format") == "json" and data.get("content"):
                try:
                    data["parsed_content"] = json.loads(data["content"])
                except Exception:
                    pass
            return data

    # ═══════════════════════════════════════════════════════════════
    # ПЛАНИ РОЗКРОЮ
    # ═══════════════════════════════════════════════════════════════

    def save_cutting_plan(
        self, project_id: int, plan: dict, name: str = "План розкрою"
    ) -> int:
        """Зберегти план розкрою."""
        summary = plan.get("summary", {})

        with self._session_scope() as session:
            cp = CuttingPlan(
                project_id=project_id,
                name=name,
                sheet_width=plan.get("sheet_width", 1250),
                sheet_height=plan.get("sheet_height", 2500),
                thickness=plan.get("thickness", 0.7),
                material=plan.get("material", "оцинкована сталь"),
                sheets_required=summary.get("sheets_required", 0),
                utilization_percent=summary.get("utilization_percent", 0),
                waste_percent=summary.get("waste_percent", 0),
                plan_data=json.dumps(plan, ensure_ascii=False),
            )
            session.add(cp)
            session.flush()
            return cp.id

    def get_cutting_plans(self, project_id: int) -> list[dict]:
        """Отримати плани розкрою проєкту."""
        with self._session_scope() as session:
            rows = (
                session.query(CuttingPlan)
                .filter(CuttingPlan.project_id == project_id)
                .order_by(CuttingPlan.created_at.desc())
                .all()
            )
            result = []
            for r in rows:
                data = _row_to_dict(r)
                if data and data.get("plan_data"):
                    try:
                        data["parsed_plan"] = json.loads(data["plan_data"])
                    except Exception:
                        pass
                result.append(data)
            return result

    # ═══════════════════════════════════════════════════════════════
    # БІБЛІОТЕКА СТАНДАРТНИХ ВИРОБІВ
    # ═══════════════════════════════════════════════════════════════

    def add_standard_product(
        self,
        name: str,
        product_type: str,
        width: float,
        height: float,
        length: float,
        thickness: float,
        material: str,
        parameters: dict | None = None,
    ) -> int:
        """Додати виріб у бібліотеку стандартних виробів."""
        with self._session_scope() as session:
            sp = StandardProductLibrary(
                name=name,
                product_type=product_type,
                width=width,
                height=height,
                length=length,
                thickness=thickness,
                material=material,
                parameters=json.dumps(parameters) if parameters else None,
            )
            session.add(sp)
            session.flush()
            return sp.id

    def get_standard_products(
        self, product_type: str | None = None, active_only: bool = True
    ) -> list[dict]:
        """Отримати стандартні вироби з бібліотеки."""
        with self._session_scope() as session:
            query = session.query(StandardProductLibrary)
            if active_only:
                query = query.filter(StandardProductLibrary.is_active == 1)
            if product_type:
                query = query.filter(StandardProductLibrary.product_type == product_type)
            rows = query.order_by(
                StandardProductLibrary.product_type, StandardProductLibrary.name
            ).all()
            result = []
            for r in rows:
                data = _row_to_dict(r)
                if data and data.get("parameters"):
                    try:
                        data["parsed_parameters"] = json.loads(data["parameters"])
                    except Exception:
                        pass
                result.append(data)
            return result

    def update_standard_product(self, product_id: int, **kwargs) -> bool:
        """Оновити стандартний виріб."""
        allowed = {
            "name", "product_type", "width", "height", "length",
            "thickness", "material", "default_quantity", "parameters", "is_active",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        if "parameters" in updates and isinstance(updates["parameters"], dict):
            updates["parameters"] = json.dumps(updates["parameters"])

        with self._session_scope() as session:
            product = session.get(StandardProductLibrary, product_id)
            if not product:
                return False
            for k, v in updates.items():
                setattr(product, k, v)
            return True

    # ═══════════════════════════════════════════════════════════════
    # ЦІНИ НА МАТЕРІАЛИ
    # ═══════════════════════════════════════════════════════════════

    def set_material_price(
        self,
        material: str,
        thickness: float,
        price_per_kg: float | None = None,
        price_per_m2: float | None = None,
    ) -> int:
        """Встановити/оновити ціну матеріалу."""
        with self._session_scope() as session:
            existing = (
                session.query(MaterialPrice)
                .filter(
                    MaterialPrice.material == material,
                    MaterialPrice.thickness == thickness,
                )
                .first()
            )
            if existing:
                if price_per_kg is not None:
                    existing.price_per_kg = price_per_kg
                if price_per_m2 is not None:
                    existing.price_per_m2 = price_per_m2
                existing.updated_at = datetime.now()
                session.flush()
                return existing.id
            else:
                mp = MaterialPrice(
                    material=material,
                    thickness=thickness,
                    price_per_kg=price_per_kg,
                    price_per_m2=price_per_m2,
                    updated_at=datetime.now(),
                )
                session.add(mp)
                session.flush()
                return mp.id

    def get_material_prices(self) -> list[dict]:
        """Отримати всі ціни на матеріали."""
        with self._session_scope() as session:
            rows = (
                session.query(MaterialPrice)
                .order_by(MaterialPrice.material, MaterialPrice.thickness)
                .all()
            )
            return _rows_to_dicts(rows)

    def get_material_price(self, material: str, thickness: float) -> float | None:
        """Отримати ціну за кг для конкретного матеріалу."""
        with self._session_scope() as session:
            row = (
                session.query(MaterialPrice)
                .filter(
                    MaterialPrice.material == material,
                    MaterialPrice.thickness == thickness,
                )
                .first()
            )
            return row.price_per_kg if row else None

    # ═══════════════════════════════════════════════════════════════
    # КЛІЄНТИ
    # ═══════════════════════════════════════════════════════════════

    def add_client(
        self, name: str, contact: str = "", phone: str = "",
        email: str = "", address: str = "", company_type: str = "",
        edrpou: str = "", notes: str = "",
    ) -> int:
        """Додати клієнта."""
        with self._session_scope() as session:
            client = Client(
                name=name,
                contact_person=contact,
                phone=phone,
                email=email,
                address=address,
                company_type=company_type,
                edrpou=edrpou,
                notes=notes,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            session.add(client)
            session.flush()
            return client.id

    def update_client(self, client_id: int, **kwargs) -> bool:
        """Оновити клієнта."""
        allowed = {"name", "contact_person", "phone", "email", "address",
                   "company_type", "edrpou", "notes"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return False
        fields["updated_at"] = datetime.now()

        with self._session_scope() as session:
            client = session.get(Client, client_id)
            if not client:
                return False
            for k, v in fields.items():
                setattr(client, k, v)
            return True

    def get_client(self, client_id: int) -> dict | None:
        """Отримати клієнта за ID."""
        with self._session_scope() as session:
            return _row_to_dict(session.get(Client, client_id))

    def get_all_clients(self, search: str = "") -> list[dict]:
        """Отримати всіх клієнтів."""
        with self._session_scope() as session:
            query = session.query(Client).order_by(Client.name)
            if search:
                like = f"%{search}%"
                query = query.filter(
                    Client.name.ilike(like)
                    | Client.phone.ilike(like)
                    | Client.email.ilike(like)
                )
            return _rows_to_dicts(query.all())

    def get_clients(self, search: str = "") -> list[dict]:
        """Alias для get_all_clients."""
        return self.get_all_clients(search)

    def delete_client(self, client_id: int) -> bool:
        """Видалити клієнта (каскадне видалення через ORM)."""
        with self._session_scope() as session:
            client = session.get(Client, client_id)
            if not client:
                return False
            session.delete(client)
            return True

    # ═══════════════════════════════════════════════════════════════
    # ВЗАЄМОДІЇ
    # ═══════════════════════════════════════════════════════════════

    def add_interaction(
        self, client_id: int, interaction_type: str = "дзвінок",
        subject: str = "", description: str = "", result: str = "",
        next_action: str = "", next_action_date: str = "",
        created_by: str = "",
    ) -> int:
        """Додати взаємодію."""
        with self._session_scope() as session:
            inter = Interaction(
                client_id=client_id,
                date=datetime.now(),
                interaction_type=interaction_type,
                subject=subject,
                description=description,
                result=result,
                next_action=next_action,
                next_action_date=next_action_date,
                created_by=created_by,
            )
            session.add(inter)
            session.flush()
            return inter.id

    def get_client_interactions(self, client_id: int) -> list[dict]:
        """Отримати взаємодії клієнта."""
        with self._session_scope() as session:
            rows = (
                session.query(Interaction)
                .filter(Interaction.client_id == client_id)
                .order_by(Interaction.date.desc())
                .all()
            )
            return _rows_to_dicts(rows)

    def delete_interaction(self, interaction_id: int) -> bool:
        """Видалити взаємодію."""
        with self._session_scope() as session:
            inter = session.get(Interaction, interaction_id)
            if not inter:
                return False
            session.delete(inter)
            return True

    # ═══════════════════════════════════════════════════════════════
    # ПЛАТЕЖІ
    # ═══════════════════════════════════════════════════════════════

    def add_payment(
        self, client_id: int, amount: float, currency: str = "UAH",
        payment_type: str = "вхідний", purpose: str = "",
        project_name: str = "", notes: str = "",
    ) -> int:
        """Додати платіж."""
        with self._session_scope() as session:
            payment = Payment(
                client_id=client_id,
                date=datetime.now(),
                amount=amount,
                currency=currency,
                payment_type=payment_type,
                purpose=purpose,
                project_name=project_name,
                notes=notes,
            )
            session.add(payment)
            session.flush()
            return payment.id

    def get_client_payments(self, client_id: int) -> list[dict]:
        """Отримати платежі клієнта."""
        with self._session_scope() as session:
            rows = (
                session.query(Payment)
                .filter(Payment.client_id == client_id)
                .order_by(Payment.date.desc())
                .all()
            )
            return _rows_to_dicts(rows)

    def get_client_balance(self, client_id: int) -> float:
        """Отримати баланс клієнта."""
        with self._session_scope() as session:
            result = (
                session.query(
                    func.sum(
                        func.case(
                            (Payment.payment_type == "вхідний", Payment.amount),
                            else_=-Payment.amount,
                        )
                    ).label("balance")
                )
                .filter(Payment.client_id == client_id)
                .first()
            )
            return float(result.balance or 0.0)

    # ═══════════════════════════════════════════════════════════════
    # ПРОЄКТИ КЛІЄНТА
    # ═══════════════════════════════════════════════════════════════

    def add_client_project(
        self, client_id: int, project_name: str,
        project_number: str = "", start_date: str = "",
        end_date: str = "", status: str = "в роботі",
        total_amount: float = 0, warranty_months: int = 24,
        description: str = "",
    ) -> int:
        """Додати проєкт клієнта + нагадування про гарантію."""
        with self._session_scope() as session:
            cp = ClientProject(
                client_id=client_id,
                project_name=project_name,
                project_number=project_number,
                start_date=start_date,
                end_date=end_date,
                status=status,
                total_amount=total_amount,
                warranty_months=warranty_months,
                description=description,
            )
            session.add(cp)
            session.flush()

            # Автоматично створюємо нагадування про гарантію
            if end_date and warranty_months > 0:
                try:
                    end_dt = datetime.fromisoformat(end_date)
                    reminder_dt = end_dt + timedelta(days=warranty_months * 30)
                    wr = WarrantyReminder(
                        client_id=client_id,
                        client_project_id=cp.id,
                        project_name=project_name,
                        reminder_date=reminder_dt.isoformat(),
                        description=f"Гарантійне обслуговування проєкту \"{project_name}\" (завершено {end_date})",
                        is_completed=0,
                    )
                    session.add(wr)
                except Exception:
                    pass
            return cp.id

    def get_client_projects(self, client_id: int) -> list[dict]:
        """Отримати проєкти клієнта."""
        with self._session_scope() as session:
            rows = (
                session.query(ClientProject)
                .filter(ClientProject.client_id == client_id)
                .order_by(ClientProject.start_date.desc())
                .all()
            )
            return _rows_to_dicts(rows)

    def update_client_project_status(self, project_id: int, status: str) -> bool:
        """Оновити статус проєкту клієнта."""
        with self._session_scope() as session:
            cp = session.get(ClientProject, project_id)
            if not cp:
                return False
            cp.status = status
            return True

    # ═══════════════════════════════════════════════════════════════
    # НАГАДУВАННЯ ПРО ГАРАНТІЮ
    # ═══════════════════════════════════════════════════════════════

    def add_warranty_reminder(
        self, client_id: int, project_name: str,
        reminder_date: str, description: str = "",
        client_project_id: int = None, notes: str = "",
    ) -> int:
        """Додати нагадування про гарантію."""
        with self._session_scope() as session:
            wr = WarrantyReminder(
                client_id=client_id,
                client_project_id=client_project_id,
                project_name=project_name,
                reminder_date=reminder_date,
                description=description,
                is_completed=0,
                notes=notes,
            )
            session.add(wr)
            session.flush()
            return wr.id

    def get_warranty_reminders(
        self, client_id: int = None, upcoming_days: int = 30
    ) -> list[dict]:
        """Отримати нагадування про гарантію."""
        future = (datetime.now() + timedelta(days=upcoming_days)).isoformat()
        now = datetime.now().isoformat()

        with self._session_scope() as session:
            query = (
                session.query(WarrantyReminder, Client.name.label("client_name"))
                .join(Client, WarrantyReminder.client_id == Client.id)
                .filter(
                    WarrantyReminder.reminder_date <= future,
                    WarrantyReminder.reminder_date >= now,
                    WarrantyReminder.is_completed == 0,
                )
            )
            if client_id:
                query = query.filter(WarrantyReminder.client_id == client_id)
            rows = query.order_by(WarrantyReminder.reminder_date.asc()).all()

            result = []
            for wr, client_name in rows:
                data = _row_to_dict(wr)
                data["client_name"] = client_name
                result.append(data)
            return result

    def complete_warranty_reminder(self, reminder_id: int, notes: str = "") -> bool:
        """Відмітити нагадування як виконане."""
        with self._session_scope() as session:
            wr = session.get(WarrantyReminder, reminder_id)
            if not wr:
                return False
            wr.is_completed = 1
            wr.completed_at = datetime.now().isoformat()
            wr.notes = notes
            return True

    # ═══════════════════════════════════════════════════════════════
    # ДАШБОРД — СТАТИСТИКА
    # ═══════════════════════════════════════════════════════════════

    def get_dashboard_stats(self) -> dict:
        """KPI для дашборду."""
        with self._session_scope() as session:
            total_revenue = (
                session.query(func.sum(ClientProject.total_amount))
                .filter(ClientProject.status.in_(["завершено", "гарантія", "закрито"]))
                .scalar()
            ) or 0

            avg_check = (
                session.query(func.avg(ClientProject.total_amount))
                .filter(ClientProject.total_amount > 0)
                .scalar()
            ) or 0

            active_projects = (
                session.query(func.count(ClientProject.id))
                .filter(ClientProject.status == "в роботі")
                .scalar()
            ) or 0

            now = datetime.now().isoformat()
            overdue_projects = (
                session.query(func.count(ClientProject.id))
                .filter(ClientProject.end_date < now, ClientProject.status != "закрито")
                .scalar()
            ) or 0

            total_clients = (
                session.query(func.count(Client.id)).scalar()
            ) or 0

            return {
                "total_revenue": float(total_revenue),
                "avg_check": float(avg_check),
                "active_projects": int(active_projects),
                "overdue_projects": int(overdue_projects),
                "total_clients": int(total_clients),
            }

    def get_production_report(self) -> dict:
        """Зведений звіт по виробництву."""
        with self._session_scope() as session:
            total_projects = (
                session.query(func.count(Project.id)).scalar()
            ) or 0

            by_status = {
                row.status: int(row.cnt)
                for row in session.query(
                    Project.status, func.count(Project.id).label("cnt")
                ).group_by(Project.status).all()
            }

            result = (
                session.query(
                    func.count(ProjectProduct.id).label("cnt"),
                    func.coalesce(func.sum(ProjectProduct.quantity), 0).label("total_qty"),
                    func.coalesce(func.sum(ProjectProduct.weight_kg * ProjectProduct.quantity), 0).label("total_weight"),
                    func.coalesce(func.sum(ProjectProduct.metal_area_m2 * ProjectProduct.quantity), 0).label("total_area"),
                )
                .first()
            )

            return {
                "total_projects": int(total_projects),
                "projects_by_status": by_status,
                "total_products": int(result.cnt or 0),
                "total_quantity": int(result.total_qty or 0),
                "total_weight_kg": float(result.total_weight or 0),
                "total_metal_area_m2": float(result.total_area or 0),
            }

    def get_monthly_revenue(self, months: int = 12) -> list[dict]:
        """Виручка по місяцях."""
        since = (datetime.now() - timedelta(days=months * 31)).strftime("%Y-%m")
        with self._session_scope() as session:
            rows = (
                session.query(
                    func.strftime("%Y-%m", ClientProject.end_date).label("month"),
                    func.sum(ClientProject.total_amount).label("amount"),
                )
                .filter(
                    ClientProject.end_date.isnot(None),
                    ClientProject.end_date >= since + "-01",
                )
                .group_by("month")
                .order_by("month")
                .all()
            )
            return [{"month": r.month, "amount": float(r.amount or 0)} for r in rows]

    def get_project_status_counts(self) -> dict:
        """Кількість проєктів за статусами."""
        with self._session_scope() as session:
            rows = (
                session.query(
                    ClientProject.status, func.count(ClientProject.id).label("cnt")
                )
                .group_by(ClientProject.status)
                .all()
            )
            return {r.status: int(r.cnt) for r in rows}

    def get_top_clients(self, limit: int = 5) -> list[dict]:
        """ТОП клієнтів за сумою замовлень."""
        with self._session_scope() as session:
            rows = (
                session.query(
                    Client.name, func.sum(ClientProject.total_amount).label("total")
                )
                .join(ClientProject, Client.id == ClientProject.client_id)
                .group_by(Client.id)
                .order_by(func.sum(ClientProject.total_amount).desc())
                .limit(limit)
                .all()
            )
            return [{"name": r.name, "total": float(r.total or 0)} for r in rows]

    def get_monthly_project_status(self, months: int = 6) -> list[dict]:
        """Кількість проєктів по місяцях за статусами."""
        since = (datetime.now() - timedelta(days=months * 31)).strftime("%Y-%m")
        with self._session_scope() as session:
            rows = (
                session.query(
                    func.strftime("%Y-%m", ClientProject.start_date).label("month"),
                    func.sum(
                        func.case((ClientProject.status == "в роботі", 1), else_=0)
                    ).label("active"),
                    func.sum(
                        func.case(
                            (ClientProject.status.in_(["завершено", "гарантія", "закрито"]), 1),
                            else_=0,
                        )
                    ).label("completed"),
                )
                .filter(
                    ClientProject.start_date.isnot(None),
                    ClientProject.start_date >= since + "-01",
                )
                .group_by("month")
                .order_by("month")
                .all()
            )
            return [
                {"month": r.month, "active": int(r.active or 0), "completed": int(r.completed or 0)}
                for r in rows
            ]

    def get_monthly_avg_check(self, months: int = 12) -> list[dict]:
        """Середній чек по місяцях."""
        since = (datetime.now() - timedelta(days=months * 31)).strftime("%Y-%m")
        with self._session_scope() as session:
            rows = (
                session.query(
                    func.strftime("%Y-%m", ClientProject.end_date).label("month"),
                    func.avg(ClientProject.total_amount).label("avg"),
                )
                .filter(
                    ClientProject.end_date.isnot(None),
                    ClientProject.end_date >= since + "-01",
                    ClientProject.total_amount > 0,
                )
                .group_by("month")
                .order_by("month")
                .all()
            )
            return [{"month": r.month, "avg": float(r.avg or 0)} for r in rows]

    def get_overdue_projects(self) -> list[dict]:
        """Прострочені проєкти."""
        now = datetime.now().isoformat()
        with self._session_scope() as session:
            rows = (
                session.query(ClientProject)
                .filter(ClientProject.end_date < now, ClientProject.status != "закрито")
                .order_by(ClientProject.end_date.asc())
                .all()
            )
            return _rows_to_dicts(rows)

    def get_material_usage_report(self) -> list[dict]:
        """Звіт по використанню матеріалів."""
        with self._session_scope() as session:
            rows = (
                session.query(
                    ProjectProduct.material,
                    ProjectProduct.thickness,
                    func.sum(ProjectProduct.quantity).label("total_quantity"),
                    func.coalesce(func.sum(ProjectProduct.weight_kg * ProjectProduct.quantity), 0).label("total_weight"),
                    func.coalesce(func.sum(ProjectProduct.metal_area_m2 * ProjectProduct.quantity), 0).label("total_area"),
                    func.count(func.distinct(ProjectProduct.project_id)).label("projects_count"),
                )
                .group_by(ProjectProduct.material, ProjectProduct.thickness)
                .order_by(func.sum(ProjectProduct.weight_kg * ProjectProduct.quantity).desc())
                .all()
            )
            return [
                {
                    "material": r.material,
                    "thickness": r.thickness,
                    "total_quantity": int(r.total_quantity or 0),
                    "total_weight": float(r.total_weight or 0),
                    "total_area": float(r.total_area or 0),
                    "projects_count": int(r.projects_count or 0),
                }
                for r in rows
            ]


# ═══════════════════════════════════════════════════════════════════
# ФАБРИКА
# ═══════════════════════════════════════════════════════════════════

def get_db(db_path: str = "data/company.db") -> ProjectDatabase:
    """Швидке отримання екземпляру БД."""
    return ProjectDatabase(db_path)


# ═══════════════════════════════════════════════════════════════════
# ІНТЕГРАЦІЯ
# ═══════════════════════════════════════════════════════════════════

def save_project_full(
    project_name: str,
    products: list[dict],
    spec_data: dict | None = None,
    cutting_plan: dict | None = None,
    db_path: str = "data/company.db",
) -> dict:
    """Зберегти повний проєкт (вироби + специфікація + розкрій) атомарно."""
    db = ProjectDatabase(db_path)

    with db._session_scope() as session:
        project_id = db._create_project_in_conn(session, name=project_name)

        for p in products:
            db._add_product_to_project_in_conn(session, project_id, p)

        spec_id = None
        if spec_data:
            content = json.dumps(spec_data, ensure_ascii=False)
            summary = spec_data.get("summary", {})
            spec = Specification(
                project_id=project_id,
                name="Специфікація",
                format="json",
                content=content,
                total_items=summary.get("total_items", 0),
                total_quantity=summary.get("total_quantity", 0),
                total_weight_kg=summary.get("total_weight_kg", 0),
                total_area_m2=summary.get("total_area_m2", 0),
                total_price=summary.get("total_price", 0),
            )
            session.add(spec)
            session.flush()
            spec_id = spec.id

        plan_id = None
        if cutting_plan:
            summary = cutting_plan.get("summary", {})
            cp = CuttingPlan(
                project_id=project_id,
                name="План розкрою",
                sheet_width=cutting_plan.get("sheet_width", 1250),
                sheet_height=cutting_plan.get("sheet_height", 2500),
                thickness=cutting_plan.get("thickness", 0.7),
                material=cutting_plan.get("material", "оцинкована сталь"),
                sheets_required=summary.get("sheets_required", 0),
                utilization_percent=summary.get("utilization_percent", 0),
                waste_percent=summary.get("waste_percent", 0),
                plan_data=json.dumps(cutting_plan, ensure_ascii=False),
            )
            session.add(cp)
            session.flush()
            plan_id = cp.id

    return {
        "project_id": project_id,
        "specification_id": spec_id,
        "cutting_plan_id": plan_id,
        "products_count": len(products),
    }
