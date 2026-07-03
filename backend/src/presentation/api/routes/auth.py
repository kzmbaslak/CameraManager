"""
Kimlik doğrulama (authentication) endpoint'leri.

POST /auth/login  — kullanıcı adı + şifre doğrular, JWT token döner.

Şifre doğrulaması bcrypt ile yapılır (passlib kullanılmaz — bcrypt 4.x+
uyumsuzluğu nedeniyle kütüphane direkt kullanılmaktadır). Kullanıcı rolü
token'a dahil edilerek rol tabanlı erişim kontrolü (RBAC) diğer
endpoint'lerde uygulanabilir.
"""
from fastapi import APIRouter, Depends, HTTPException, status
import bcrypt

from src.presentation.api.dependencies import get_user_repository, get_current_user
from src.infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
from src.infrastructure.security.jwt_service import create_access_token
from src.presentation.api.schemas.auth_schema import LoginRequest, TokenResponse, ChangePasswordRequest

router = APIRouter(prefix="/auth", tags=["Kimlik Doğrulama"])


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    user_repo: SqlAlchemyUserRepository = Depends(get_user_repository),
):
    user = user_repo.get_by_username(credentials.username)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz kimlik bilgileri.")

    password_matches = bcrypt.checkpw(
        credentials.password.encode("utf-8"),
        user.password_hash.encode("utf-8"),
    )
    if not password_matches:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz kimlik bilgileri.")

    token = create_access_token(username=user.username, role=user.role.value)
    return TokenResponse(access_token=token, username=user.username, role=user.role.value)


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    user_repo: SqlAlchemyUserRepository = Depends(get_user_repository),
):
    """Giriş yapmış olan kullanıcının kendi şifresini değiştirmesini sağlar."""
    username = current_user.get("sub")
    user = user_repo.get_by_username(username)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")

    # Mevcut şifreyi doğrula
    password_matches = bcrypt.checkpw(
        data.old_password.encode("utf-8"),
        user.password_hash.encode("utf-8"),
    )
    if not password_matches:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mevcut şifre hatalı.")

    # Yeni şifreyi hashle ve güncelle
    new_hash = bcrypt.hashpw(data.new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user.password_hash = new_hash
    user_repo.update(user)

    return {"message": "Şifre başarıyla güncellendi."}

