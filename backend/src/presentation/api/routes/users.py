"""
Kullanıcı (User) yönetimi endpoint'leri.

POST   /users/        — yeni kullanıcı oluşturur; şifre bcrypt ile hashlenir.
GET    /users/        — sistemdeki tüm kullanıcıları listeler.
PATCH  /users/{id}    — kullanıcı rolünü, aktiflik durumunu veya şifresini günceller.
DELETE /users/{id}    — kullanıcıyı siler (kendi hesabını silemez).

Şifre hashleme için passlib yerine bcrypt kütüphanesi direkt kullanılır
(passlib 1.7.x, bcrypt 4.x+ ile uyumsuz).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
import bcrypt
from src.presentation.api.dependencies import get_user_repository, get_admin_user
from src.infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
from src.presentation.api.schemas.user_schema import UserCreate, UserUpdate, UserResponse
from src.domain.entities.user import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse)
def create_user(
    user_data: UserCreate,
    repo: SqlAlchemyUserRepository = Depends(get_user_repository),
    current_user: dict = Depends(get_admin_user),
):
    """Sisteme yeni bir kullanıcı ekler."""
    existing = repo.get_by_username(user_data.username)
    if existing:
        raise HTTPException(status_code=400, detail="Kullanıcı adı zaten mevcut (Username already exists)")

    password_hash = bcrypt.hashpw(user_data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(
        id=None,
        username=user_data.username,
        password_hash=password_hash,
        role=user_data.role,
        is_active=True
    )
    return repo.add(user)


@router.get("/", response_model=List[UserResponse])
def list_users(
    repo: SqlAlchemyUserRepository = Depends(get_user_repository),
    current_user: dict = Depends(get_admin_user),
):
    """Sistemdeki tüm kullanıcıları listeler."""
    return repo.list_all()


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    repo: SqlAlchemyUserRepository = Depends(get_user_repository),
    current_user: dict = Depends(get_admin_user),
):
    """Kullanıcı rolünü, aktiflik durumunu veya şifresini günceller."""
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")

    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.password is not None:
        user.password_hash = bcrypt.hashpw(
            data.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    return repo.update(user)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    repo: SqlAlchemyUserRepository = Depends(get_user_repository),
    current_user: dict = Depends(get_admin_user),
):
    """Kullanıcıyı sistemden siler."""
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")
    # Silme işlemi — repository'de delete metodu gerekir
    from src.infrastructure.database.models import UserModel
    from sqlalchemy.orm import Session

    db: Session = repo._db
    model = db.query(UserModel).filter(UserModel.id == user_id).first()
    if model:
        db.delete(model)
        db.commit()
