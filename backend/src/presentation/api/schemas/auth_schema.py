"""
Kimlik doğrulama (authentication) Pydantic şemaları.

Login isteği ve JWT token yanıtı için veri modelleri.
"""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Kullanıcı giriş isteği — kullanıcı adı ve şifre."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Başarılı girişin ardından dönen JWT token bilgisi."""
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class ChangePasswordRequest(BaseModel):
    """Kullanıcının kendi şifresini değiştirmek için kullandığı istek modeli."""
    old_password: str                  # Mevcut şifre
    new_password: str                  # Yeni şifre

