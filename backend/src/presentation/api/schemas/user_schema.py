"""
Kullanıcı (User) Pydantic şemaları — istek ve yanıt veri yapıları.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from src.domain.entities.user import UserRole


class UserCreate(BaseModel):
    """Yeni kullanıcı oluşturma isteği."""
    username: str
    password: str
    role: UserRole = UserRole.VIEWER


class UserUpdate(BaseModel):
    """Kullanıcı bilgilerini kısmi olarak günceller. None alanlar değiştirilmez."""
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None   # None → şifre değiştirilmez


class UserResponse(BaseModel):
    """API'nin kullanıcı bilgisi dönerken kullandığı yanıt modeli. Şifre hiçbir zaman döndürülmez."""
    id: int
    username: str
    role: UserRole
    is_active: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True
