"""Kullanıcı repository uygulaması; SQLAlchemy modeli ile domain varlığı arasında dönüşüm yapar."""

from typing import Sequence
from sqlalchemy.orm import Session
from src.domain.entities.user import User
from src.domain.entities.user import UserRole
from src.domain.interfaces.user_repository import IUserRepository
from src.infrastructure.database.models import UserModel

class SqlAlchemyUserRepository(IUserRepository):
    """Kullanıcı verilerini SQLite/SQLAlchemy üzerinden yönetir."""

    def __init__(self, db: Session):
        """Repository için kullanılacak SQLAlchemy oturumunu saklar."""
        self._db = db

    def _to_entity(self, model: UserModel) -> User:
        """SQLAlchemy kullanıcı modelini domain varlığına çevirir."""
        return User(
            id=model.id,
            username=model.username,
            password_hash=model.password_hash,
            role=model.role,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    def _to_model(self, entity: User) -> UserModel:
        """Domain kullanıcı varlığını SQLAlchemy modeline çevirir."""
        return UserModel(
            id=entity.id,
            username=entity.username,
            password_hash=entity.password_hash,
            role=entity.role,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )

    def add(self, user: User) -> User:
        """Yeni kullanıcıyı veritabanına ekler."""
        model = self._to_model(user)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._to_entity(model)

    def get_by_id(self, user_id: int) -> User | None:
        """ID değerine göre kullanıcı döner; bulunamazsa None döner."""
        model = self._db.query(UserModel).filter(UserModel.id == user_id).first()
        if model:
            return self._to_entity(model)
        return None

    def get_by_username(self, username: str) -> User | None:
        """Kullanıcı adına göre kullanıcı döner; bulunamazsa None döner."""
        model = self._db.query(UserModel).filter(UserModel.username == username).first()
        if model:
            return self._to_entity(model)
        return None

    def list_all(self) -> Sequence[User]:
        """Tüm kullanıcıları listeler."""
        models = self._db.query(UserModel).all()
        return [self._to_entity(m) for m in models]

    def list_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        role: str = "all",
        active: str = "all",
        sort: str = "username_asc",
    ) -> tuple[Sequence[User], int]:
        """Filtrelenmis kullanici listesini sayfali dondurur."""
        query = self._db.query(UserModel)
        needle = search.strip()
        if needle:
            query = query.filter(UserModel.username.ilike(f"%{needle}%"))
        if role != "all":
            query = query.filter(UserModel.role == UserRole(role))
        if active == "active":
            query = query.filter(UserModel.is_active.is_(True))
        elif active == "inactive":
            query = query.filter(UserModel.is_active.is_(False))

        total = query.count()
        if sort == "username_desc":
            query = query.order_by(UserModel.username.desc())
        elif sort == "role":
            query = query.order_by(UserModel.role.asc(), UserModel.username.asc())
        elif sort == "status":
            query = query.order_by(UserModel.is_active.desc(), UserModel.username.asc())
        elif sort == "id_desc":
            query = query.order_by(UserModel.id.desc())
        else:
            query = query.order_by(UserModel.username.asc())

        offset = max(page - 1, 0) * page_size
        models = query.offset(offset).limit(page_size).all()
        return [self._to_entity(m) for m in models], total

    def update(self, user: User) -> User:
        """Mevcut kullanıcıyı günceller."""
        model = self._db.query(UserModel).filter(UserModel.id == user.id).first()
        if model:
            model.username = user.username
            model.password_hash = user.password_hash
            model.role = user.role
            model.is_active = user.is_active
            self._db.commit()
            self._db.refresh(model)
            return self._to_entity(model)
        raise ValueError(f"User with id {user.id} not found")

    def delete(self, user_id: int) -> None:
        """Kullanıcıyı veritabanından siler."""
        model = self._db.query(UserModel).filter(UserModel.id == user_id).first()
        if not model:
            raise ValueError(f"User with id {user_id} not found")
        self._db.delete(model)
        self._db.commit()
