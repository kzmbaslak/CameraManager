from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


@dataclass
class User:
    id: Optional[int]
    username: str
    password_hash: str
    role: UserRole
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True

    def can_manage_cameras(self) -> bool:
        return self.role in {UserRole.ADMIN, UserRole.OPERATOR}

    def can_manage_users(self) -> bool:
        return self.role == UserRole.ADMIN
