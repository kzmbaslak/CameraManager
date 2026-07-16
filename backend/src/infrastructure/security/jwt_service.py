"""
JWT (JSON Web Token) yönetim servisi.

Bu modül, kullanıcı oturumları için erişim token'ları oluşturur ve doğrular.
python-jose kütüphanesi kullanılır; algoritem HS256.

Token'lar şunları içerir:
  - sub: kullanıcı adı
  - role: kullanıcı rolü (admin / operator / viewer)
  - exp: token sona erme zamanı
"""
import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from src.infrastructure.security.runtime_config import require_jwt_secret

# JWT imzalama için gizli anahtar — üretimde .env ile sağlanmalı
_SECRET_KEY = require_jwt_secret()
_ALGORITHM = "HS256"
_DEFAULT_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "480"))


def create_access_token(username: str, role: str, expires_minutes: Optional[int] = None) -> str:
    """
    Verilen kullanıcı adı ve rol için imzalı JWT erişim token'ı oluşturur.

    Args:
        username: Kullanıcı adı (token'ın 'sub' alanı).
        role: Kullanıcı rolü (admin/operator/viewer).
        expires_minutes: Token geçerlilik süresi; None ise env değeri kullanılır.

    Returns:
        İmzalı JWT string'i.
    """
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes or _DEFAULT_EXPIRE_MINUTES)
    payload = {"sub": username, "role": role, "purpose": "access", "exp": expire}
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    JWT token'ını doğrular ve içindeki payload'ı döner.

    Args:
        token: Bearer token string'i.

    Returns:
        Payload dict'i (sub, role, exp).

    Raises:
        JWTError: Token geçersiz veya süresi dolmuşsa.
    """
    payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
    if payload.get("purpose", "access") != "access":
        raise JWTError("Token amacı erişim için uygun değil.")
    return payload


def create_stream_token(username: str, role: str, camera_id: int, expires_seconds: int = 60) -> str:
    """Belirli bir kamera canlı akışı için kısa ömürlü JWT üretir."""
    expire = datetime.utcnow() + timedelta(seconds=expires_seconds)
    payload = {
        "sub": username,
        "role": role,
        "camera_id": camera_id,
        "purpose": "stream",
        "exp": expire,
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_stream_token(token: str, camera_id: int) -> dict:
    """Kısa ömürlü stream token'ını doğrular ve kamera eşleşmesini kontrol eder."""
    payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
    if payload.get("purpose") != "stream" or payload.get("camera_id") != camera_id:
        raise JWTError("Stream token bu kamera için geçerli değil.")
    return payload
