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

# JWT imzalama için gizli anahtar — üretimde .env ile sağlanmalı
_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-only-insecure-key-change-in-production")
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
    payload = {"sub": username, "role": role, "exp": expire}
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
    return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
