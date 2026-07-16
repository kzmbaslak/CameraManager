"""
Kimlik doğrulama (authentication) Pydantic şemaları.

Login isteği ve JWT token yanıtı için veri modelleri.
"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Kullanıcı giriş isteği — kullanıcı adı ve şifre."""
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    """Başarılı girişin ardından dönen JWT token bilgisi."""
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class ChangePasswordRequest(BaseModel):
    """Kullanıcının kendi şifresini değiştirmek için kullandığı istek modeli."""
    old_password: str = Field(min_length=1, max_length=256)      # Mevcut şifre
    new_password: str = Field(min_length=8, max_length=256)      # Yeni şifre
