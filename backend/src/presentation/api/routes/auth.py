"""
Kimlik doğrulama (authentication) endpoint'leri.

POST /auth/login  — kullanıcı adı + şifre doğrular, JWT token döner.

Şifre doğrulaması bcrypt ile yapılır (passlib kullanılmaz — bcrypt 4.x+
uyumsuzluğu nedeniyle kütüphane direkt kullanılmaktadır). Kullanıcı rolü
token'a dahil edilerek rol tabanlı erişim kontrolü (RBAC) diğer
endpoint'lerde uygulanabilir.
"""
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
import bcrypt

from src.presentation.api.dependencies import get_user_repository, get_current_user
from src.infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
from src.infrastructure.security.jwt_service import create_access_token
from src.infrastructure.security.audit_logger import write_audit_event
from src.presentation.api.schemas.auth_schema import LoginRequest, TokenResponse, ChangePasswordRequest

router = APIRouter(prefix="/auth", tags=["Kimlik Doğrulama"])

_FAILED_LOGIN_WINDOW = timedelta(minutes=5)
_MAX_FAILED_ATTEMPTS = 5
_failed_logins: dict[str, deque[datetime]] = defaultdict(deque)


def _rate_limit_key(request: Request, username: str) -> str:
    """Kullanıcı adı + istemci IP için login deneme anahtarı üretir."""
    client_ip = request.client.host if request.client else "unknown"
    return f"{client_ip}:{username.strip().lower()}"


def _check_login_rate_limit(request: Request, username: str) -> None:
    """Kısa sürede çok fazla başarısız login denemesini engeller."""
    key = _rate_limit_key(request, username)
    now = datetime.utcnow()
    attempts = _failed_logins[key]
    while attempts and now - attempts[0] > _FAILED_LOGIN_WINDOW:
        attempts.popleft()
    if len(attempts) >= _MAX_FAILED_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Çok fazla başarısız giriş denemesi. Birkaç dakika sonra tekrar deneyin.",
        )


def _record_failed_login(request: Request, username: str) -> None:
    """Başarısız login denemesini rate-limit penceresine ekler."""
    _failed_logins[_rate_limit_key(request, username)].append(datetime.utcnow())


def _clear_failed_logins(request: Request, username: str) -> None:
    """Başarılı login sonrası deneme sayacını temizler."""
    _failed_logins.pop(_rate_limit_key(request, username), None)


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    request: Request,
    user_repo: SqlAlchemyUserRepository = Depends(get_user_repository),
):
    _check_login_rate_limit(request, credentials.username)
    source_ip = request.client.host if request.client else None
    user = user_repo.get_by_username(credentials.username)
    if not user or not user.is_active:
        _record_failed_login(request, credentials.username)
        write_audit_event("auth.login", credentials.username, False, source_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz kimlik bilgileri.")

    password_matches = bcrypt.checkpw(
        credentials.password.encode("utf-8"),
        user.password_hash.encode("utf-8"),
    )
    if not password_matches:
        _record_failed_login(request, credentials.username)
        write_audit_event("auth.login", credentials.username, False, source_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz kimlik bilgileri.")

    _clear_failed_logins(request, credentials.username)
    write_audit_event("auth.login", user.username, True, source_ip, {"role": user.role.value})
    token = create_access_token(username=user.username, role=user.role.value)
    return TokenResponse(access_token=token, username=user.username, role=user.role.value)


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    request: Request,
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
    source_ip = request.client.host if request.client else None
    write_audit_event("auth.change_password", username, True, source_ip)

    return {"message": "Şifre başarıyla güncellendi."}
