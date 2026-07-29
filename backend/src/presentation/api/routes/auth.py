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
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
import bcrypt
from jose import JWTError

from src.presentation.api.dependencies import get_user_repository, get_current_user
from src.infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
from src.infrastructure.security.jwt_service import create_access_token, decode_access_token
from src.infrastructure.security.audit_logger import write_audit_event
from src.infrastructure.time_utils import utc_now
from src.presentation.api.schemas.auth_schema import LoginRequest, TokenResponse, ChangePasswordRequest

router = APIRouter(prefix="/auth", tags=["Kimlik Doğrulama"])

_FAILED_LOGIN_WINDOW = timedelta(minutes=5)
_MAX_FAILED_ATTEMPTS = 5
_failed_logins: dict[str, deque[datetime]] = defaultdict(deque)
_AUTH_COOKIE_NAME = "access_token"


def _secure_cookie_auth_enabled() -> bool:
    """AUTH_COOKIE_MODE=secure ise ek HttpOnly cookie oturum destegi verir."""
    return os.environ.get("AUTH_COOKIE_MODE", "").strip().lower() == "secure"


def _access_token_cookie_max_age() -> int:
    """Cookie yasamini access token suresiyle hizalar."""
    try:
        minutes = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "480") or "480")
    except ValueError:
        minutes = 480
    return max(minutes, 1) * 60


def _set_access_token_cookie(response: Response, token: str) -> None:
    """Access token'i yalnizca opsiyonel secure cookie modu aciksa cookie'ye yazar."""
    if not _secure_cookie_auth_enabled():
        return
    response.set_cookie(
        key=_AUTH_COOKIE_NAME,
        value=token,
        max_age=_access_token_cookie_max_age(),
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api",
    )


def _clear_access_token_cookie(response: Response) -> None:
    """Logout sirasinda opsiyonel auth cookie'yi temizler."""
    response.delete_cookie(
        key=_AUTH_COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api",
    )


def _best_effort_logout_actor(request: Request) -> str:
    """Logout audit'i icin Bearer veya cookie token'dan kullaniciyi best-effort cozer."""
    authorization = request.headers.get("authorization", "")
    token = None
    if authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    token = token or request.cookies.get(_AUTH_COOKIE_NAME)
    if not token:
        return "unknown"
    try:
        payload = decode_access_token(token)
    except JWTError:
        return "unknown"
    return str(payload.get("sub") or "unknown")


def _rate_limit_key(request: Request, username: str) -> str:
    """Kullanıcı adı + istemci IP için login deneme anahtarı üretir."""
    client_ip = request.client.host if request.client else "unknown"
    return f"{client_ip}:{username.strip().lower()}"


def _prune_failed_login_attempts(now: datetime | None = None, key: str | None = None) -> None:
    """Rate-limit penceresi disinda kalan basarisiz login denemelerini temizler."""
    current = now or utc_now()
    keys = [key] if key is not None else list(_failed_logins.keys())
    for item_key in keys:
        attempts = _failed_logins.get(item_key)
        if attempts is None:
            continue
        while attempts and current - attempts[0] > _FAILED_LOGIN_WINDOW:
            attempts.popleft()
        if not attempts:
            _failed_logins.pop(item_key, None)


def failed_login_window_summary() -> dict[str, int]:
    """Aktif basarisiz login penceresini hassas anahtar sizdirmadan ozetler."""
    _prune_failed_login_attempts()
    counts = [len(attempts) for attempts in _failed_logins.values()]
    return {
        "active_failed_login_key_count": len(counts),
        "active_failed_login_attempt_count": sum(counts),
        "max_failed_login_attempts_for_key": max(counts, default=0),
        "failed_login_limit": _MAX_FAILED_ATTEMPTS,
        "failed_login_window_seconds": int(_FAILED_LOGIN_WINDOW.total_seconds()),
    }


def _check_login_rate_limit(request: Request, username: str) -> None:
    """Kısa sürede çok fazla başarısız login denemesini engeller."""
    key = _rate_limit_key(request, username)
    now = utc_now()
    attempts = _failed_logins[key]
    _prune_failed_login_attempts(now, key)
    if len(attempts) >= _MAX_FAILED_ATTEMPTS:
        source_ip = request.client.host if request.client else None
        write_audit_event(
            "auth.login_rate_limited",
            username.strip().lower(),
            False,
            source_ip,
            {
                "attempt_count": len(attempts),
                "limit": _MAX_FAILED_ATTEMPTS,
                "window_seconds": int(_FAILED_LOGIN_WINDOW.total_seconds()),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Çok fazla başarısız giriş denemesi. Birkaç dakika sonra tekrar deneyin.",
        )


def _record_failed_login(request: Request, username: str) -> None:
    """Başarısız login denemesini rate-limit penceresine ekler."""
    _failed_logins[_rate_limit_key(request, username)].append(utc_now())


def _clear_failed_logins(request: Request, username: str) -> None:
    """Başarılı login sonrası deneme sayacını temizler."""
    _failed_logins.pop(_rate_limit_key(request, username), None)


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    request: Request,
    response: Response,
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
    _set_access_token_cookie(response, token)
    return TokenResponse(access_token=token, username=user.username, role=user.role.value)


@router.post("/logout")
def logout(
    response: Response,
    request: Request,
):
    """Sunucu tarafinda opsiyonel secure auth cookie'yi temizler ve audit olayi yazar."""
    source_ip = request.client.host if request.client else None
    username = _best_effort_logout_actor(request)
    _clear_access_token_cookie(response)
    write_audit_event("auth.logout", username, True, source_ip)
    return {"message": "Oturum kapatildi."}


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    user_repo: SqlAlchemyUserRepository = Depends(get_user_repository),
):
    """Giriş yapmış olan kullanıcının kendi şifresini değiştirmesini sağlar."""
    username = current_user.get("sub")
    source_ip = request.client.host if request.client else None
    user = user_repo.get_by_username(username)
    if not user or not user.is_active:
        write_audit_event(
            "auth.change_password",
            username,
            False,
            source_ip,
            {"reason": "user_not_found_or_inactive"},
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")

    # Mevcut şifreyi doğrula
    password_matches = bcrypt.checkpw(
        data.old_password.encode("utf-8"),
        user.password_hash.encode("utf-8"),
    )
    if not password_matches:
        write_audit_event(
            "auth.change_password",
            username,
            False,
            source_ip,
            {"reason": "old_password_mismatch"},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mevcut şifre hatalı.")

    # Yeni şifreyi hashle ve güncelle
    new_hash = bcrypt.hashpw(data.new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user.password_hash = new_hash
    user_repo.update(user)
    write_audit_event("auth.change_password", username, True, source_ip)

    return {"message": "Şifre başarıyla güncellendi."}
