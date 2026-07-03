from typing import Sequence
from sqlalchemy.orm import Session
from src.domain.entities.user import User
from src.domain.interfaces.user_repository import IUserRepository
from src.infrastructure.database.models import UserModel

class SqlAlchemyUserRepository(IUserRepository):
    def __init__(self, db: Session):
        self._db = db

    def _to_entity(self, model: UserModel) -> User:
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
        model = self._to_model(user)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._to_entity(model)

    def get_by_id(self, user_id: int) -> User | None:
        model = self._db.query(UserModel).filter(UserModel.id == user_id).first()
        if model:
            return self._to_entity(model)
        return None

    def get_by_username(self, username: str) -> User | None:
        model = self._db.query(UserModel).filter(UserModel.username == username).first()
        if model:
            return self._to_entity(model)
        return None

    def list_all(self) -> Sequence[User]:
        models = self._db.query(UserModel).all()
        return [self._to_entity(m) for m in models]

    def update(self, user: User) -> User:
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
