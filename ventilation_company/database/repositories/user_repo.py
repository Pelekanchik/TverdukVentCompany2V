"""Репозиторій для роботи з користувачами (CRUD + пошук)."""

from __future__ import annotations

from typing import Optional, List

from sqlalchemy.orm import Session

from ventilation_company.database.models.user import UserORM
from ventilation_company.services.auth_service import AuthService


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: int) -> Optional[UserORM]:
        return self.session.query(UserORM).filter(UserORM.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[UserORM]:
        return self.session.query(UserORM).filter(UserORM.username == username).first()

    def get_all(self, active_only: bool = True) -> List[UserORM]:
        query = self.session.query(UserORM)
        if active_only:
            query = query.filter(UserORM.is_active == 1)
        return query.order_by(UserORM.full_name).all()

    def create(self, username: str, password: str, full_name: str,
               role: str = "viewer", is_active: bool = True) -> UserORM:
        if self.get_by_username(username):
            raise ValueError(f"Користувач '{username}' вже існує")

        user = UserORM(
            username=username,
            password_hash=AuthService.hash_password(password),
            full_name=full_name,
            role=role,
            is_active=1 if is_active else 0
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update(self, user_id: int, **kwargs) -> Optional[UserORM]:
        user = self.get_by_id(user_id)
        if not user:
            return None

        if "password" in kwargs:
            kwargs["password_hash"] = AuthService.hash_password(kwargs.pop("password"))

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        self.session.commit()
        self.session.refresh(user)
        return user

    def deactivate(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            return False
        user.is_active = 0
        self.session.commit()
        return True

    def delete(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            return False
        self.session.delete(user)
        self.session.commit()
        return True
